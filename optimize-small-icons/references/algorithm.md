# Semantic matte and core inheritance

## Why normal resizing fails

Lanczos and similar filters correctly average source coverage, but a feature narrower than one target pixel becomes a mixture of foreground and background. Geometry survives while color identity disappears: purple becomes pale lavender, black becomes gray, and a dark dot can vanish completely.

Do not globally darken or quantize the result. That damages antialiased edges and unrelated colors. Preserve colors through semantic layers instead.

## Pipeline

1. Crop the original art without destructively editing it.
2. Resize the base image normally and apply the final alpha mask.
3. Optionally pull pixels already near an anchor toward that anchor. Keep low-confidence boundary pixels antialiased.
4. For a fragile chromatic layer, replace neutral background with an intermediate hue-matched matte, resize the matte and its source mask, restore untouched matte pixels to the background, then composite only through the layer mask.
5. For neutral or low-chroma layers, detect membership by projecting each source pixel onto the background-to-anchor color line. Use the projection amount as coverage and the perpendicular residual as color confidence.
6. Assign each source pixel to only its highest-confidence semantic layer. This prevents gray pixels from also being claimed by a dark layer whose color line passes nearby.
7. Protect target pixels already owned by important anchors before applying later layers.
8. Snap only high-confidence interiors back to exact anchors.
9. Split each semantic mask into connected source components and project its confidence-weighted coverage to the target grid.
10. If an important component has no surviving target core, promote its highest-coverage target pixel to the exact anchor.

## Inheritance weight

Use:

```text
importance = projected confidence-weighted coverage x background contrast
```

The projected mask already contains color confidence, so its summed area represents both geometric coverage and confidence. Contrast is the RGB distance between the anchor and background, normalized by the maximum RGB distance.

Apply minimum source-area and minimum-importance gates. This avoids promoting noise while allowing a high-contrast dot or short line to inherit one representative pixel.

## Invariants

- Never overwrite a target component that already has an acceptable core.
- Never let one semantic layer claim the same source pixel as another layer.
- Never let a later layer overwrite a protected target anchor or its configured boundary ring.
- Preserve partial-alpha mask pixels; core inheritance changes RGB, not alpha.
- Verify every ICO frame decodes to the same RGBA pixels as its corresponding PNG frame.
- Compare 16, 24, and 32px at actual size and with nearest-neighbor magnification.

## Diagnosing defects

- Color is present but washed out: lower matte output thresholds or strengthen the layer mask.
- Color is absent from a disconnected detail: lower core inheritance gates only for that semantic color.
- Shapes become too thick: reduce matte dilation, blur, blend strength, or core radius.
- Black or navy turns gray: add it as a protected anchor and a core-inheritance color.
- One color contaminates another: tighten residual tolerance or check exclusive ownership priority.
- Jagged silhouettes: keep antialiasing and alpha untouched; do not snap boundary pixels.
