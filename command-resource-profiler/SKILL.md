---
name: command-resource-profiler
description: Run a specific command under process-tree monitoring and report application-scoped CPU time, average CPU utilization, peak RSS/VMS memory, disk I/O, wall time, exit code, and optional interval samples. Use for command performance tests, runtime resource monitoring, before/after comparisons, regression checks, CLI benchmarks, or requests to measure one application's CPU and memory without mixing in unrelated system processes.
---

# Command Resource Profiler

Use the bundled profiler as the default measurement path:

```powershell
python <skill-dir>/scripts/profile_command.py --output profile.json -- <command> <args...>
```

Resolve `<skill-dir>` to this skill's directory. Keep the target command after `--` so its flags are not parsed as profiler flags.

## Workflow

1. Confirm the exact executable, arguments, working directory, and whether descendants belong to the workload.
2. Check that Python and `psutil` are available. If `psutil` is missing, report `python -m pip install psutil`; do not install it without authorization.
3. Choose a sampling interval. Use `0.2` seconds normally, `0.05`-`0.1` seconds for short workloads, and `0.5`-`1` second for long workloads.
4. Run at least one warmup and three measured repetitions when comparing performance:

   ```powershell
   python <skill-dir>/scripts/profile_command.py --warmup 1 --repeat 3 --interval 0.1 --output profile.json --samples-output samples.csv -- <command> <args...>
   ```

5. Report the command, environment, exit code, wall time, total CPU time, both CPU percentage conventions, peak concurrent RSS, I/O, interval, repetitions, and observed limitations.
6. Compare runs only when inputs and relevant environment conditions are equivalent. Prefer medians for noisy wall-time comparisons and peak values for capacity planning.

## Scope and safety

- Measure only the root command and descendants discovered from that root; do not substitute whole-system CPU or memory.
- Launch without a shell by default. Use `--shell` only when shell syntax such as pipelines, redirection, or built-ins is required.
- Apply `--timeout` to unattended or potentially unbounded commands.
- On timeout or interruption, terminate only the tracked process tree after verifying PID creation identity.
- Preserve the target's stdout and stderr. Store the structured report with `--output` when clean machine-readable output matters.
- Treat sampling as approximate for subprocesses that start and exit between samples. Read [metrics.md](references/metrics.md) before claiming kernel-level exactness or comparing results across platforms.

## Useful options

```text
--interval 0.1             Sampling interval in seconds
--warmup 1                 Unreported warmup executions
--repeat 5                 Measured executions
--timeout 120              Per-run timeout in seconds
--cwd PATH                 Target working directory
--output report.json       JSON summary and per-run metrics
--samples-output data.csv  Interval samples for graphing
--shell                    Execute through the platform shell
--label NAME               Label embedded in the report
```

## Interpreting CPU

- `average_cpu_percent_core_scale`: 100% means one logical CPU fully occupied and values may exceed 100%.
- `average_cpu_percent_machine`: 100% means all logical CPUs fully occupied.
- `cpu_total_s`: accumulated user plus system CPU time for observed members of the process tree.

For metric definitions and known sampling boundaries, read [metrics.md](references/metrics.md).
