#!/usr/bin/env python3
"""Screen a color palette for basic perceptual structure using only stdlib."""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from pathlib import Path

HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-fA-F])")


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


def load_colors(arguments: argparse.Namespace) -> list[str]:
    tokens = list(arguments.colors)
    if arguments.file:
        tokens.extend(HEX_RE.findall(Path(arguments.file).read_text(encoding="utf-8")))
    expanded: list[str] = []
    for token in tokens:
        matches = HEX_RE.findall(token)
        expanded.extend(matches if matches else [part for part in token.split(",") if part.strip()])
    if len(expanded) < 2:
        raise ValueError("provide at least two colors")
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

    return {
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("colors", nargs="*", help="Hex colors, individually or comma-separated")
    parser.add_argument("--file", help="Read and extract hex colors from a UTF-8 text file")
    parser.add_argument(
        "--class",
        dest="palette_class",
        choices=("sequential", "diverging", "cyclic", "categorical"),
        required=True,
        help="Intended palette class",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    arguments = parser.parse_args()
    try:
        report = audit(load_colors(arguments), arguments.palette_class)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    if arguments.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_text(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
