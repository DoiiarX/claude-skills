#!/usr/bin/env python3
"""Build and inspect deterministic multi-size ICO families."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

try:
    from icon_resampler_core import (
        STABLE_FRAMES_DIR,
        STABLE_ICON_NAME,
        STABLE_PREVIEW_NAME,
        STABLE_REPORT_NAME,
        SUPPORTED_STRATEGIES,
        build_icon_family,
        inspect_ico,
        load_recipe,
    )
except ModuleNotFoundError as error:
    package = {"PIL": "Pillow", "numpy": "numpy", "scipy": "scipy"}.get(
        error.name or "", error.name or "unknown"
    )
    print(
        f"Error: missing Python package {package}. Install Pillow, numpy, and scipy, then retry.",
        file=sys.stderr,
    )
    raise SystemExit(2) from error


BUILD_EXAMPLES = """Examples:
  python scripts/icon_resampler.py build --input logo.png --config icon-recipe.json
  python scripts/icon_resampler.py build --input logo.png --config icon-recipe.json --preset windows-full
  python scripts/icon_resampler.py build --input logo.png --config icon-recipe.json --output-dir dist/icon --json
  python scripts/icon_resampler.py build --input logo.png --config icon-recipe.json --dry-run
"""

INSPECT_EXAMPLES = """Examples:
  python scripts/icon_resampler.py inspect --input icon-output/icon.ico
  python scripts/icon_resampler.py inspect --input icon-output/icon.ico --json
"""

SIZE_PRESETS = {
    "windows-minimum": [16, 24, 32, 48, 256],
    "windows-full": [16, 20, 24, 30, 32, 36, 40, 48, 60, 64, 72, 80, 96, 128, 256],
}


class AgentArgumentParser(argparse.ArgumentParser):
    """Append a correct invocation to argparse failures."""

    def __init__(self, *args: Any, example: str | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.example = example

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        print(f"Error: {message}", file=sys.stderr)
        if self.example:
            print(f"Try: {self.example}", file=sys.stderr)
        raise SystemExit(2)


def build_parser() -> AgentArgumentParser:
    parser = AgentArgumentParser(
        description="Preserve semantic color cores while building tiny ICO frames.",
        epilog=(
            "Run a subcommand with --help for examples. Stable outputs are always "
            f"{STABLE_ICON_NAME}, {STABLE_PREVIEW_NAME}, {STABLE_REPORT_NAME}, and {STABLE_FRAMES_DIR}/."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        example="python scripts/icon_resampler.py build --help",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser(
        "build",
        help="build the stable ICO output family",
        description="Build an ICO, preview, report, and exact PNG frames from one recipe.",
        epilog=BUILD_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    build.example = "python scripts/icon_resampler.py build --input logo.png --config icon-recipe.json"
    build.set_defaults(_example=build.example)
    build.add_argument("--input", required=True, type=Path, help="source PNG or raster image")
    build.add_argument("--config", required=True, type=Path, help="JSON resampling recipe")
    build.add_argument(
        "--output-dir",
        type=Path,
        default=Path("icon-output"),
        help="output directory (default: icon-output)",
    )
    build.add_argument(
        "--strategy",
        choices=SUPPORTED_STRATEGIES,
        default="core-inheritance-v4",
        help="versioned internal algorithm (default: core-inheritance-v4)",
    )
    size_group = build.add_mutually_exclusive_group()
    size_group.add_argument(
        "--sizes",
        type=_parse_sizes,
        help="comma-separated size override, for example 16,24,32,48,64,128,256",
    )
    size_group.add_argument(
        "--preset",
        choices=sorted(SIZE_PRESETS),
        help="built-in Windows size set; windows-full avoids display-scale fallback",
    )
    build.add_argument("--dry-run", action="store_true", help="validate and print the plan without writing")
    build.add_argument("--json", action="store_true", help="print machine-readable JSON")

    inspect = subparsers.add_parser(
        "inspect",
        help="list ICO frames and hashes",
        description="Inspect the embedded sizes and decoded frame hashes in an ICO.",
        epilog=INSPECT_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    inspect.example = "python scripts/icon_resampler.py inspect --input icon-output/icon.ico"
    inspect.set_defaults(_example=inspect.example)
    inspect.add_argument("--input", required=True, type=Path, help="ICO file to inspect")
    inspect.add_argument("--json", action="store_true", help="print machine-readable JSON")
    return parser


def _parse_sizes(value: str) -> list[int]:
    try:
        sizes = [int(item.strip()) for item in value.split(",") if item.strip()]
    except ValueError as error:
        raise argparse.ArgumentTypeError("sizes must be comma-separated integers") from error
    if not sizes or any(size <= 0 for size in sizes):
        raise argparse.ArgumentTypeError("sizes must contain positive integers")
    return sizes


def _print_result(result: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return
    if result.get("dry_run"):
        print("validated icon build plan")
        print(f"strategy: {result['strategy']}")
        print(f"sizes: {','.join(str(size) for size in result['sizes'])}")
        print(f"output_dir: {result['output_dir']}")
        return
    print("built icon family")
    print(f"strategy: {result['strategy']}")
    print(f"icon: {result['icon']}")
    print(f"preview: {result['preview']}")
    print(f"report: {result['report']}")
    print(f"frames_exact: {result['verification']['all_frames_exact']}")


def _print_inspection(result: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return
    print(f"icon: {result['path']}")
    print(f"sha256: {result['sha256']}")
    print(f"sizes: {','.join(str(size) for size in result['sizes'])}")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            recipe = load_recipe(args.config)
            result = build_icon_family(
                input_path=args.input,
                recipe=recipe,
                output_dir=args.output_dir,
                strategy=args.strategy,
                sizes_override=args.sizes or SIZE_PRESETS.get(args.preset),
                dry_run=args.dry_run,
            )
            _print_result(result, as_json=args.json)
            return 0
        result = inspect_ico(args.input)
        _print_inspection(result, as_json=args.json)
        return 0
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        example = getattr(args, "_example", None)
        if example:
            print(f"Try: {example}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
