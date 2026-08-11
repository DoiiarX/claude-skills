#!/usr/bin/env python3
"""Profile CPU, memory, and I/O for a command and its observed process tree."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import os
import platform
import shlex
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    import psutil
except ImportError:
    print(
        "profile_command.py requires psutil. Install it with: "
        f"{shlex.quote(sys.executable)} -m pip install psutil",
        file=sys.stderr,
    )
    raise SystemExit(2)


SCHEMA_VERSION = 1


def positive_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a positive finite number")
    return number


def nonnegative_int(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return number


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a command and profile its observed process-tree resources.",
        epilog="Place the target command after --, for example: %(prog)s -- python app.py",
    )
    parser.add_argument("--interval", type=positive_float, default=0.2)
    parser.add_argument("--warmup", type=nonnegative_int, default=0)
    parser.add_argument("--repeat", type=positive_int, default=1)
    parser.add_argument("--timeout", type=positive_float)
    parser.add_argument("--cwd")
    parser.add_argument("--output", help="Write the JSON report to this path.")
    parser.add_argument("--samples-output", help="Write interval samples as CSV.")
    parser.add_argument("--label")
    parser.add_argument(
        "--shell",
        action="store_true",
        help="Run through the platform shell. Disabled by default.",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("a target command is required after --")
    if args.cwd:
        cwd = Path(args.cwd).expanduser().resolve()
        if not cwd.is_dir():
            parser.error(f"--cwd is not a directory: {cwd}")
        args.cwd = str(cwd)
    return args


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def process_key(process: psutil.Process) -> tuple[int, float]:
    return process.pid, process.create_time()


def still_same_process(process: psutil.Process, key: tuple[int, float]) -> bool:
    try:
        return process.pid == key[0] and abs(process.create_time() - key[1]) < 0.01
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def add_process(
    process: psutil.Process,
    known: dict[tuple[int, float], psutil.Process],
) -> None:
    try:
        key = process_key(process)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return
    known.setdefault(key, process)


def discover_descendants(
    known: dict[tuple[int, float], psutil.Process],
) -> None:
    for key, process in list(known.items()):
        if not still_same_process(process, key):
            continue
        try:
            for child in process.children(recursive=True):
                add_process(child, known)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


def sample_processes(
    known: dict[tuple[int, float], psutil.Process],
    last_cpu: dict[tuple[int, float], tuple[float, float]],
    last_io: dict[tuple[int, float], tuple[int, int]],
) -> dict[str, int | float]:
    discover_descendants(known)
    current_rss = 0
    current_vms = 0
    alive = 0

    for key, process in list(known.items()):
        if not still_same_process(process, key):
            continue
        try:
            if not process.is_running() or process.status() == psutil.STATUS_ZOMBIE:
                continue
            alive += 1
            cpu = process.cpu_times()
            last_cpu[key] = (float(cpu.user), float(cpu.system))
            memory = process.memory_info()
            current_rss += int(memory.rss)
            current_vms += int(memory.vms)
            try:
                io = process.io_counters()
                last_io[key] = (int(io.read_bytes), int(io.write_bytes))
            except (psutil.AccessDenied, psutil.NotImplementedError, AttributeError):
                pass
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    cpu_user = sum(item[0] for item in last_cpu.values())
    cpu_system = sum(item[1] for item in last_cpu.values())
    io_read = sum(item[0] for item in last_io.values())
    io_write = sum(item[1] for item in last_io.values())
    return {
        "alive_processes": alive,
        "rss_bytes": current_rss,
        "vms_bytes": current_vms,
        "cpu_user_s": cpu_user,
        "cpu_system_s": cpu_system,
        "cpu_total_s": cpu_user + cpu_system,
        "io_read_bytes": io_read,
        "io_write_bytes": io_write,
    }


def terminate_owned_tree(
    known: dict[tuple[int, float], psutil.Process],
    grace_seconds: float = 2.0,
) -> None:
    verified: list[psutil.Process] = []
    for key, process in known.items():
        if still_same_process(process, key):
            verified.append(process)

    for process in sorted(verified, key=lambda item: item.pid, reverse=True):
        try:
            process.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    _, alive = psutil.wait_procs(verified, timeout=grace_seconds)
    for process in alive:
        try:
            process.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    if alive:
        psutil.wait_procs(alive, timeout=grace_seconds)


def command_for_popen(command: list[str], use_shell: bool) -> list[str] | str:
    if not use_shell:
        return command
    if os.name == "nt":
        return subprocess.list2cmdline(command)
    return shlex.join(command)


def profile_once(
    command: list[str],
    args: argparse.Namespace,
    run_index: int,
    phase: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    popen_args = command_for_popen(command, args.shell)
    popen_kwargs: dict[str, Any] = {
        "cwd": args.cwd,
        "shell": args.shell,
    }
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    started_at = utc_now()
    started = time.monotonic()
    child = subprocess.Popen(popen_args, **popen_kwargs)
    root = psutil.Process(child.pid)
    known: dict[tuple[int, float], psutil.Process] = {}
    add_process(root, known)
    last_cpu: dict[tuple[int, float], tuple[float, float]] = {}
    last_io: dict[tuple[int, float], tuple[int, int]] = {}
    samples: list[dict[str, Any]] = []
    peak_rss = 0
    peak_vms = 0
    peak_concurrent = 0
    timed_out = False

    try:
        while True:
            elapsed = time.monotonic() - started
            snapshot = sample_processes(known, last_cpu, last_io)
            peak_rss = max(peak_rss, int(snapshot["rss_bytes"]))
            peak_vms = max(peak_vms, int(snapshot["vms_bytes"]))
            peak_concurrent = max(peak_concurrent, int(snapshot["alive_processes"]))
            samples.append(
                {
                    "phase": phase,
                    "run_index": run_index,
                    "elapsed_s": round(elapsed, 6),
                    **snapshot,
                }
            )

            root_done = child.poll() is not None
            if root_done and int(snapshot["alive_processes"]) == 0:
                break
            if args.timeout is not None and elapsed >= args.timeout:
                timed_out = True
                terminate_owned_tree(known)
                child.poll()
                final_snapshot = sample_processes(known, last_cpu, last_io)
                peak_rss = max(peak_rss, int(final_snapshot["rss_bytes"]))
                peak_vms = max(peak_vms, int(final_snapshot["vms_bytes"]))
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        terminate_owned_tree(known)
        raise

    wall_time = time.monotonic() - started
    exit_code = child.poll()
    if exit_code is None:
        try:
            exit_code = child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            terminate_owned_tree(known)
            exit_code = child.wait(timeout=2)

    cpu_user = sum(item[0] for item in last_cpu.values())
    cpu_system = sum(item[1] for item in last_cpu.values())
    cpu_total = cpu_user + cpu_system
    logical_cpus = psutil.cpu_count(logical=True) or 1
    core_scale = (cpu_total / wall_time * 100.0) if wall_time > 0 else 0.0
    machine_scale = core_scale / logical_cpus
    result = {
        "phase": phase,
        "run_index": run_index,
        "started_at": started_at,
        "wall_time_s": round(wall_time, 6),
        "exit_code": exit_code,
        "timed_out": timed_out,
        "sample_count": len(samples),
        "sampling_interval_s": args.interval,
        "process_count_seen": len(known),
        "peak_concurrent_processes": peak_concurrent,
        "cpu_user_s": round(cpu_user, 6),
        "cpu_system_s": round(cpu_system, 6),
        "cpu_total_s": round(cpu_total, 6),
        "average_cpu_percent_core_scale": round(core_scale, 3),
        "average_cpu_percent_machine": round(machine_scale, 3),
        "peak_rss_bytes": peak_rss,
        "peak_rss_mib": round(peak_rss / (1024 * 1024), 3),
        "peak_vms_bytes": peak_vms,
        "peak_vms_mib": round(peak_vms / (1024 * 1024), 3),
        "io_read_bytes": sum(item[0] for item in last_io.values()),
        "io_write_bytes": sum(item[1] for item in last_io.values()),
    }
    return result, samples


def stats(values: list[float | int]) -> dict[str, float]:
    numeric = [float(value) for value in values]
    result = {
        "min": min(numeric),
        "max": max(numeric),
        "mean": statistics.fmean(numeric),
        "median": statistics.median(numeric),
        "stdev": statistics.stdev(numeric) if len(numeric) > 1 else 0.0,
    }
    return {key: round(value, 6) for key, value in result.items()}


def build_aggregate(runs: list[dict[str, Any]]) -> dict[str, Any]:
    fields = [
        "wall_time_s",
        "cpu_total_s",
        "average_cpu_percent_core_scale",
        "average_cpu_percent_machine",
        "peak_rss_bytes",
        "peak_vms_bytes",
        "io_read_bytes",
        "io_write_bytes",
    ]
    aggregate: dict[str, Any] = {
        "run_count": len(runs),
        "successful_runs": sum(
            1 for run in runs if run["exit_code"] == 0 and not run["timed_out"]
        ),
    }
    for field in fields:
        aggregate[field] = stats([run[field] for run in runs])
    return aggregate


def write_json(path: str, report: dict[str, Any]) -> None:
    destination = Path(path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Profile report: {destination}", file=sys.stderr)


def write_samples(path: str, samples: list[dict[str, Any]]) -> None:
    destination = Path(path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "phase",
        "run_index",
        "elapsed_s",
        "alive_processes",
        "rss_bytes",
        "vms_bytes",
        "cpu_user_s",
        "cpu_system_s",
        "cpu_total_s",
        "io_read_bytes",
        "io_write_bytes",
    ]
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(samples)
    print(f"Sample data: {destination}", file=sys.stderr)


def main() -> int:
    args = parse_args()
    command = list(args.command)
    all_samples: list[dict[str, Any]] = []

    for index in range(1, args.warmup + 1):
        result, samples = profile_once(command, args, index, "warmup")
        all_samples.extend(samples)
        if result["timed_out"] or result["exit_code"] != 0:
            print(
                f"Warmup {index} failed with exit code {result['exit_code']}; aborting.",
                file=sys.stderr,
            )
            return 124 if result["timed_out"] else 1

    runs: list[dict[str, Any]] = []
    for index in range(1, args.repeat + 1):
        result, samples = profile_once(command, args, index, "measured")
        runs.append(result)
        all_samples.extend(samples)

    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "label": args.label,
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "logical_cpu_count": psutil.cpu_count(logical=True),
            "physical_cpu_count": psutil.cpu_count(logical=False),
            "total_memory_bytes": psutil.virtual_memory().total,
        },
        "configuration": {
            "command": command,
            "shell": args.shell,
            "cwd": args.cwd or os.getcwd(),
            "interval_s": args.interval,
            "warmup": args.warmup,
            "repeat": args.repeat,
            "timeout_s": args.timeout,
        },
        "runs": runs,
        "aggregate": build_aggregate(runs),
        "limitations": [
            "Subprocesses that start and exit entirely between samples may be missed.",
            "RSS and virtual-memory semantics vary by operating system.",
            "Use Windows Job Objects or Linux cgroup v2 for enforcement-grade accounting.",
        ],
    }

    if args.output:
        write_json(args.output, report)
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.samples_output:
        write_samples(args.samples_output, all_samples)

    if any(run["timed_out"] for run in runs):
        return 124
    for run in runs:
        code = run["exit_code"]
        if code not in (None, 0):
            return code if isinstance(code, int) and 1 <= code <= 255 else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
