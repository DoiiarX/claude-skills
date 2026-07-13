---
name: optimize-small-icons
description: Build and audit Windows ICO families whose 16-48px frames preserve fragile semantic colors, dark cores, dots, lines, and disconnected details instead of losing them to antialiasing. Use when resizing app icons or logos for Windows taskbars, title bars, Explorer, shortcuts, installers, or other tiny raster contexts; when a normal Lanczos resize turns important colors into pale half-tones; or when a reproducible agent-friendly icon CLI is needed.
---

# Optimize Small Icons

Preserve the visual meaning of tiny features while retaining antialiased boundaries. Treat each important color as a semantic layer, then inherit a solid core pixel only when an important source component otherwise loses every core pixel.

## Workflow

1. Preserve the source artwork and write outputs to a separate directory during tuning.
2. Identify the background and the exact anchor colors whose identity must survive at 16, 24, 32, and 48px.
3. Read [references/algorithm.md](references/algorithm.md) before choosing matte layers or core inheritance thresholds.
4. Read [references/recipe-schema.md](references/recipe-schema.md) when creating or editing the JSON recipe. Read [references/platform-assets.md](references/platform-assets.md) before producing Windows, macOS, Linux, Android, or iOS release assets.
5. Validate the invocation without writes:

```bash
python scripts/icon_resampler.py build \
  --input logo.png \
  --config icon-recipe.json \
  --output-dir icon-output \
  --dry-run
```

6. Build the family:

```bash
python scripts/icon_resampler.py build \
  --input logo.png \
  --config icon-recipe.json \
  --preset windows-full \
  --output-dir icon-output \
  --json
```

7. Inspect the actual-size row and nearest-neighbor detail row in `preview.png`. Do not judge only a smooth zoomed preview.
8. Confirm `report.json` says `verification.all_frames_exact: true`, then inspect anchor counts and any promoted core pixels.
9. Inspect the embedded ICO independently when replacing a production asset:

```bash
python scripts/icon_resampler.py inspect --input icon-output/icon.ico --json
```

## Stable CLI contract

Keep algorithm revisions internal through `--strategy`; the current strategy is `core-inheritance-v4`. Always keep these external outputs stable:

- `icon.ico`
- `preview.png`
- `report.json`
- `frames/<size>x<size>.png`

Rerunning the same build is safe and replaces only these owned outputs. Use `--sizes` only for deliberate frame-set overrides.

Use the built-in `windows-full` preset for 16/20/24/30/32/36/40/48/60/64/72/80/96/128/256px. Use `windows-minimum` only when a constrained toolchain cannot carry the full set.

For multi-platform projects, expose one project command that regenerates every platform from the same canonical high-resolution source. Never make one platform consume another platform's already-resized output.

## Tuning order

Tune in this order to avoid compensating for one defect with another:

1. Crop and corner radius.
2. Background and exact semantic anchors.
3. Broad core strengthening for already-visible colors.
4. Chroma mattes for saturated subpixel details.
5. Projection mattes for neutral or low-chroma details.
6. Protected ownership so later layers cannot overwrite earlier colors.
7. Contrast-weighted core inheritance for disconnected components that still lack a solid core.

Prefer the lowest thresholds that restore identity without thickening shapes. A component that already retains a core must remain untouched.

## Dependencies

Run with Python 3.10+ and install `Pillow`, `numpy`, and `scipy`. If imports fail, report the exact missing package and use the environment's normal dependency manager rather than silently changing the algorithm.
