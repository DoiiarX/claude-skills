#!/usr/bin/env python3
"""Agent-friendly CLI for screening color palettes using only Python stdlib."""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from pathlib import Path

HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-fA-F])")
VERSION = "1.1.0"


class AgentArgumentParser(argparse.ArgumentParser):
    """Argument parser that adds copy-pasteable examples to actionable errors."""

    def __init__(self, *args: object, examples: tuple[str, ...] = (), **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.examples = examples

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        print(f"{self.prog}: error: {message}", file=sys.stderr)
        if self.examples:
            print("Examples:", file=sys.stderr)
            for example in self.examples:
                print(f"  {example}", file=sys.stderr)
        self.exit(2)


def parse_color(value: str) -> tuple[str, tuple[float, float, float]]:
    value = value.strip()
    if not value.startswith("#"):
        value = "#" + value
    if not re.fullmatch(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?", value):
        raise ValueError(f"invalid color: {value}")
    if len(value) == 4:
        value = "#" + "".join(ch * 2 for ch in value[1:])
    rgb = tuple(int(value[i : i + 2], 16) / 255.0 for i in (1, 3, 5))
    return value.lower(), rgb  # type: ignore[return-value]


def srgb_to_linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def rgb_to_lab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    r, g, b = (srgb_to_linear(channel) for channel in rgb)
    x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b

    def f(value: float) -> float:
        delta = 6 / 29
        return value ** (1 / 3) if value > delta**3 else value / (3 * delta**2) + 4 / 29

    fx, fy, fz = f(x / 0.95047), f(y), f(z / 1.08883)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def relative_luminance(rgb: tuple[float, float, float]) -> float:
    r, g, b = (srgb_to_linear(channel) for channel in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def delta_e(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


def monotonic(values: list[float], tolerance: float = 0.25) -> dict[str, object]:
    if len(values) < 2:
        return {"monotonic": True, "direction": "flat", "violations": 0}
    direction = 1 if values[-1] >= values[0] else -1
    violations = sum(1 for a, b in zip(values, values[1:]) if direction * (b - a) < -tolerance)
    return {
        "monotonic": violations == 0,
        "direction": "increasing" if direction > 0 else "decreasing",
        "violations": violations,
    }


def rounded(values: list[float]) -> list[float]:
    return [round(value, 3) for value in values]


def extract_colors(text: str) -> list[str]:
    matches = HEX_RE.findall(text)
    if matches:
        return matches
    return [part for part in re.split(r"[\s,]+", text) if part]


def load_colors(arguments: argparse.Namespace, parser: AgentArgumentParser) -> list[str]:
    sources = sum((bool(arguments.colors), bool(arguments.file), bool(arguments.stdin)))
    if sources == 0:
        parser.error("no colors provided; pass hex colors, --file <path>, or --stdin")
    if sources > 1:
        parser.error("choose exactly one input source: positional colors, --file, or --stdin")

    if arguments.stdin or arguments.file == "-":
        source_text = sys.stdin.read()
        if not source_text.strip():
            parser.error("stdin was empty")
        tokens = extract_colors(source_text)
    elif arguments.file:
        tokens = extract_colors(Path(arguments.file).read_text(encoding="utf-8"))
    else:
        tokens = list(arguments.colors)

    expanded: list[str] = []
    for token in tokens:
        matches = HEX_RE.findall(token)
        expanded.extend(matches if matches else [part for part in token.split(",") if part.strip()])
    if len(expanded) < 2:
        parser.error("provide at least two colors")
    return expanded


def audit(colors: list[str], palette_class: str) -> dict[str, object]:
    parsed = [parse_color(color) for color in colors]
    canonical = [item[0] for item in parsed]
    rgbs = [item[1] for item in parsed]
    labs = [rgb_to_lab(rgb) for rgb in rgbs]
    lightness = [lab[0] for lab in labs]
    luminance = [relative_luminance(rgb) for rgb in rgbs]
    adjacent_delta_e = [delta_e(a, b) for a, b in zip(labs, labs[1:])]
    adjacent_delta_l = [abs(a - b) for a, b in zip(lightness, lightness[1:])]
    warnings: list[str] = []

    mean_delta = statistics.fmean(adjacent_delta_e)
    cv_delta = statistics.pstdev(adjacent_delta_e) / mean_delta if mean_delta else 0.0
    if cv_delta > 0.35:
        warnings.append("adjacent perceptual steps are uneven (CIE76 coefficient of variation > 0.35)")
    if min(adjacent_delta_l) < 2.0:
        warnings.append("at least one adjacent pair has weak grayscale lightness separation (Delta L* < 2)")

    structural: dict[str, object] = {}
    if palette_class == "sequential":
        structural = monotonic(lightness)
        if not structural["monotonic"]:
            warnings.append("sequential palette lightness is not monotonic")
    elif palette_class == "diverging":
        middle = len(lightness) // 2
        left = list(reversed(lightness[: middle + 1]))
        right = lightness[middle:]
        structural = {
            "middle_index": middle,
            "left_arm_from_center": monotonic(left),
            "right_arm_from_center": monotonic(right),
            "middle_is_lightness_extremum": lightness[middle] in (min(lightness), max(lightness)),
        }
        if not structural["middle_is_lightness_extremum"]:
            warnings.append("diverging midpoint is not a lightness extremum")
    elif palette_class == "cyclic":
        endpoint_delta = delta_e(labs[0], labs[-1])
        structural = {"endpoint_delta_e76": round(endpoint_delta, 3)}
        if endpoint_delta > mean_delta * 1.5:
            warnings.append("cyclic endpoints are less continuous than adjacent samples")
    else:
        pairwise = [delta_e(labs[i], labs[j]) for i in range(len(labs)) for j in range(i + 1, len(labs))]
        structural = {"minimum_pairwise_delta_e76": round(min(pairwise), 3)}
        if min(pairwise) < 10:
            warnings.append("categorical palette contains a weakly separated pair (Delta E76 < 10)")

    status = "warnings" if warnings else "pass"
    return {
        "schema_version": "1.0",
        "tool": "audit_palette",
        "tool_version": VERSION,
        "status": status,
        "palette_class": palette_class,
        "colors": canonical,
        "sample_count": len(canonical),
        "lab_lightness": rounded(lightness),
        "relative_luminance": rounded(luminance),
        "adjacent_delta_e76": rounded(adjacent_delta_e),
        "adjacent_delta_l": rounded(adjacent_delta_l),
        "adjacent_delta_e76_cv": round(cv_delta, 3),
        "structure": structural,
        "warnings": warnings,
        "scope": "Screening only; not CVD, appearance-model, print, or viewing-condition certification.",
    }


def print_text(report: dict[str, object]) -> None:
    print(f"status: {report['status']}")
    print(f"class: {report['palette_class']}")
    print(f"colors: {', '.join(report['colors'])}")
    print(f"L*: {report['lab_lightness']}")
    print(f"adjacent Delta E76: {report['adjacent_delta_e76']}")
    print(f"adjacent Delta L*: {report['adjacent_delta_l']}")
    print(f"Delta E76 CV: {report['adjacent_delta_e76_cv']}")
    print(f"structure: {json.dumps(report['structure'], ensure_ascii=False)}")
    warnings = report["warnings"]
    if warnings:
        print("warnings:")
        for warning in warnings:
            print(f"- {warning}")
    else:
        print("warnings: none from this screening")
    print(f"scope: {report['scope']}")


def build_parser() -> tuple[AgentArgumentParser, AgentArgumentParser]:
    parser = AgentArgumentParser(
        description="Screen color palettes for basic perceptual structure.",
        examples=(
            "python3 scripts/audit_palette.py audit --help",
            "python3 scripts/audit_palette.py --version",
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    commands = parser.add_subparsers(dest="command", metavar="COMMAND", title="commands")

    examples = (
        "python3 scripts/audit_palette.py audit --class sequential '#f7fcf0' '#74c476' '#00441b'",
        "python3 scripts/audit_palette.py audit --class diverging --file palette.css --format json",
        "printf '#f7fcf0\\n#74c476\\n#00441b\\n' | python3 scripts/audit_palette.py audit --class sequential --stdin",
        "python3 scripts/audit_palette.py audit --class sequential --file palette.txt --warnings-as-errors",
    )
    audit_parser = commands.add_parser(
        "audit",
        help="audit exact palette samples",
        description="Audit exact palette samples from arguments, a UTF-8 file, or stdin.",
        epilog="Examples:\n  " + "\n  ".join(examples),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        examples=examples,
    )
    audit_parser.add_argument("colors", nargs="*", help="Hex colors, individually or comma-separated")
    audit_parser.add_argument("--file", metavar="PATH", help="extract hex colors from a UTF-8 text file; use - for stdin")
    audit_parser.add_argument("--stdin", action="store_true", help="read colors from stdin")
    audit_parser.add_argument(
        "--class",
        dest="palette_class",
        choices=("sequential", "diverging", "cyclic", "categorical"),
        required=True,
        help="Intended palette class",
    )
    audit_parser.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )
    audit_parser.add_argument(
        "--json",
        dest="output_format",
        action="store_const",
        const="json",
        help="alias for --format json",
    )
    audit_parser.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="exit 1 after emitting a report when screening warnings exist",
    )
    return parser, audit_parser


def normalize_legacy_args(arguments: list[str]) -> list[str]:
    if not arguments or arguments[0] in {"audit", "-h", "--help", "--version"}:
        return arguments
    return ["audit", *arguments]


def main(argv: list[str] | None = None) -> int:
    parser, audit_parser = build_parser()
    normalized = normalize_legacy_args(list(sys.argv[1:] if argv is None else argv))
    if not normalized:
        parser.print_help()
        return 0
    arguments = parser.parse_args(normalized)
    if arguments.command != "audit":
        parser.error("choose a command")
    try:
        report = audit(load_colors(arguments, audit_parser), arguments.palette_class)
    except (OSError, ValueError) as error:
        audit_parser.error(str(error))
    if arguments.output_format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_text(report)
    return 1 if arguments.warnings_as_errors and report["warnings"] else 0


if __name__ == "__main__":
    sys.exit(main())
