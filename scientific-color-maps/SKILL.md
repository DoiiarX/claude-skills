---
name: scientific-color-maps
description: Select, implement, and audit scientifically accurate, perceptually uniform, and color-vision-accessible color maps for data visualization. Use when creating or reviewing plots, heatmaps, maps, scalar fields, scientific figures, dashboards, or visualization code; when choosing a palette or colormap; when replacing rainbow, jet, turbo, or red-green scales; or when checking grayscale readability, color blindness, color bars, normalization, and possible visual distortion. Also trigger on British spellings such as colour, colour map, and colour-vision deficiency.
---

# Scientific Color Maps

Treat color as a quantitative axis, not decoration. Preserve the structure of the data, make the mapping interpretable, and keep it readable under common color-vision deficiencies and grayscale reproduction.

## Workflow

1. Inspect the data and intended claim before choosing colors.
2. Classify the variable and select the matching map class.
3. Choose a documented perceptually uniform palette.
4. Implement the scale, normalization, limits, and color bar together.
5. Validate the result under grayscale, color-vision simulation, and the final background.
6. Report the exact palette and mapping decisions when reproducibility matters.

Read [references/selection-and-audit.md](references/selection-and-audit.md) when selecting among map classes, auditing an existing figure, or needing implementation guidance.

## Classify the Data

- Use a **sequential** map for ordered values progressing from low to high.
- Use a **diverging** map only when a meaningful reference value separates two directions, such as zero, an anomaly, or a target. Place the visual midpoint at that value.
- Use a **cyclic** map for periodic values whose endpoints are equivalent, such as phase, angle, time of day, or orientation.
- Use **categorical** colors for unordered groups. Do not imply magnitude through a continuous gradient.
- Use a discrete form of the appropriate ordered map when values are binned. Keep bin boundaries explicit.

Do not choose a diverging map merely because the data contain positive and negative values; require a meaningful center. Do not choose a categorical palette for continuous measurements.

## Preserve Data Meaning

- Prefer palettes with approximately uniform perceptual change along the scale and a monotonic lightness path where the class permits it.
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
