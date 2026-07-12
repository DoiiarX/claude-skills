---
name: scientific-color-maps
description: Select, implement, and audit scientifically accurate, perceptually uniform, and color-vision-accessible color maps for data visualization. Use when creating or reviewing plots, heatmaps, maps, scalar fields, probability bars, progress indicators, scientific figures, dashboards, or visualization code; when choosing a palette or deciding whether hue changes carry real meaning; when replacing rainbow, jet, turbo, arbitrary low-medium-high colors, or red-green scales; or when checking grayscale readability, color blindness, color bars, normalization, and possible visual distortion. Also trigger on British spellings such as colour, colour map, and colour-vision deficiency.
---

# Scientific Color Maps

Treat color as a quantitative axis, not decoration. Preserve the structure of the data, make the mapping interpretable, and keep it readable under common color-vision deficiencies and grayscale reproduction.

## Workflow

1. Inspect the data and intended claim before choosing colors.
2. Identify whether color is the primary quantitative channel or only reinforces position, length, height, or labels.
3. Classify the variable and select the matching map class.
4. Decide whether hue changes have a defensible semantic or perceptual purpose.
5. Choose a documented perceptually uniform palette.
6. Implement the scale, normalization, limits, and color bar together.
7. Validate the result under grayscale, color-vision simulation, and the final background.
8. Report the exact palette and mapping decisions when reproducibility matters.

Read [references/selection-and-audit.md](references/selection-and-audit.md) when selecting among map classes, auditing an existing figure, or needing implementation guidance.

## Classify the Data

- Use a **sequential** map for ordered values progressing from low to high.
- Use a **diverging** map only when a meaningful reference value separates two directions, such as zero, an anomaly, or a target. Place the visual midpoint at that value.
- Use a **cyclic** map for periodic values whose endpoints are equivalent, such as phase, angle, time of day, or orientation.
- Use **categorical** colors for unordered groups. Do not imply magnitude through a continuous gradient.
- Use a discrete form of the appropriate ordered map when values are binned. Keep bin boundaries explicit.

Do not choose a diverging map merely because the data contain positive and negative values; require a meaningful center. Do not choose a categorical palette for continuous measurements.

## Decide Whether Hue Carries Meaning

Do not interpret “different values need different colors” as permission to assign unrelated hues. First identify the role of color:

- When **position, length, height, area, or text already carries the value**, treat color as redundant reinforcement. Prefer one fixed hue with monotonic lightness or saturation. Keep zero, missing, disabled, and out-of-domain states visually separate.
- When **color is the primary quantitative channel** in a dense heatmap, image, map, or scalar field, allow a documented perceptually uniform sequential map to vary in hue if its lightness remains ordered and its transitions do not create false boundaries.
- Use **distinct categorical hues** only for genuinely unordered identities or states.
- Use **discrete threshold hues** only when thresholds define real named business or scientific states. Label the thresholds; otherwise retain a continuous sequential scale.
- Use **opposing hues** only for a diverging variable with a meaningful center.
- Use **cyclic hue progression** only for periodic variables whose endpoints are equivalent.

For compact probability bars, progress bars, meters, ranked bars, and sparklines, default to a single-hue ordered ramp when bar height or length already expresses magnitude. Do not map arbitrary low, medium, and high bands to blue, amber, and green unless those bands are established operational states with documented thresholds and actions.

## Preserve Data Meaning

- Prefer palettes with approximately uniform perceptual change along the scale and a monotonic lightness path where the class permits it.
- Prefer the least complex color encoding that preserves the intended comparison. Adding hue is not automatically more informative.
- Avoid `rainbow`, `jet`, and rainbow-like scales, including `turbo`, for quantitative scientific data. Their uneven lightness and color transitions can invent boundaries, hide variation, and overemphasize arbitrary ranges.
- Avoid red-green encoding at similar lightness. Never rely on hue alone for critical distinctions.
- Keep palette sampling uniform. Do not squeeze, stretch, splice, or reorder sections of a validated palette.
- Use nonlinear normalization only when justified by the data or task. Label it explicitly and ensure the color bar uses the same transformation.
- Set limits from a defensible rule. Disclose clipping, saturation, winsorization, logarithmic transforms, and asymmetric ranges.
- Keep a visible, labeled color bar for continuous or ordered color encodings unless values are directly labeled.
- Account for the final background, neighboring marks, interpolation, transparency, and print conditions.

## Prefer Trusted Palette Families

Start with maintained, documented families rather than inventing a palette:

- Matplotlib perceptually uniform maps: `viridis`, `cividis`, `magma`, `inferno`, `plasma`.
- Fabio Crameri Scientific Colour Maps: sequential, diverging, cyclic, discrete, and categorical options with diagnostics and versioned releases.
- cmocean: parameter-oriented sequential, diverging, and cyclic maps.
- ColorBrewer: especially useful for discrete sequential, diverging, and qualitative maps.
- CET palettes: broad coverage, but verify the specific palette because quality varies across the collection.

Match the palette to the data semantics; a reputable palette from the wrong class is still misleading.

## Validate Before Delivery

Perform checks on the rendered output, not only on palette swatches:

- Convert to grayscale and confirm ordering, extrema, and important structures remain legible.
- Simulate deuteranopia, protanopia, and tritanopia when tools permit.
- Check that equal data steps do not produce conspicuously unequal visual steps.
- Check whether every hue transition has a data-semantic or perceptual justification. Remove hue changes that merely decorate an already encoded magnitude.
- Check that the most visually salient point corresponds to a meaningful value rather than an accidental bright band.
- Confirm that the center, endpoints, limits, ticks, units, and missing-data color are unambiguous.
- Check legends and annotations independently; accessibility of the continuous map does not guarantee accessibility of every overlay.

When only a raster image is available, label findings as visual heuristics. Do not claim perceptual uniformity has been measured unless the palette samples or source code are available for analysis in a perceptual color space.

## Deliver Actionable Results

When creating a visualization, state the selected map class, palette name, normalization, limits, center if any, missing-data treatment, and validation performed. When auditing, distinguish:

- definite defects visible in the artifact,
- likely risks that require source data or palette samples to verify,
- concrete replacements and code-level changes.

Preserve the user's plotting library and visual conventions unless they conflict with accurate representation or accessibility.
