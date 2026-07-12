# Evidence Scope and Tooling

Use this reference to distinguish reliable quantitative-color guidance from adjacent perception research and to select validation tools.

## Contents

- Evidence hierarchy
- Direct visualization evidence
- Adjacent perception evidence
- Visual-weight safeguards
- Cross-figure standardization
- Bundled and external tools
- Reproducibility record

## Evidence Hierarchy

Apply evidence in this order:

1. **Direct visualization evidence**: studies of colormaps, color spaces, map classes, accessibility, and data interpretation. Use these to choose quantitative encodings.
2. **Domain and standardization evidence**: guidance for consistent color semantics within a scientific field, organization, report, or visualization system.
3. **Adjacent perception evidence**: product, marketing, object, affect, and visual-weight studies. Use these to identify possible bias, not to override quantitative accuracy.

When levels conflict, preserve accurate and accessible data encoding. Decorative weight, stability, mood, or brand preference is secondary.

## Direct Visualization Evidence

- Crameri, Shephard, and Heron (2020), [The misuse of colour in science communication](https://doi.org/10.1038/s41467-020-19160-7): perceptual uniformity, color-vision accessibility, grayscale readability, map-class selection, and rejection of rainbow-like maps.
- Brewer (1994), [Color Use Guidelines for Mapping and Visualization](https://doi.org/10.1016/B978-0-08-042415-6.50014-4): sequential, diverging, and qualitative map selection.
- Moreland (2009), [Diverging Color Maps for Scientific Visualization](https://doi.org/10.1007/978-3-642-10520-3_9): diverging map construction and meaningful centers.
- Kovesi (2015), [Good Colour Maps: How to Design Them](https://arxiv.org/abs/1509.03700): perceptual diagnostics and lightness structure.
- Bujack et al. (2018), [The Good, the Bad, and the Ugly](https://doi.org/10.1109/TVCG.2017.2743978): theoretical assessment of continuous colormaps.
- Szafir (2018), [Modeling Color Difference for Visualization Design](https://doi.org/10.1109/TVCG.2017.2744359): color-difference modeling for visualization marks.

## Adjacent Perception Evidence

- Xu et al. (2023), [The Influences of gradient color on the weight perception and stability perception](https://doi.org/10.1177/20416695231197797), is a preliminary online product-perception study. For six product forms, a monochrome gradient with a darker bottom and lighter top increased perceived weight and stability relative to the reverse direction. The weight effect was statistically significant but moderate. Do not generalize this result to chart accuracy, every hue, or every culture and display condition.
- Hagtvedt's product-color work and Hagtvedt and Brasel (2017), [Color Saturation Increases Perceived Product Size](https://doi.org/10.1093/jcr/ucx039), show that color appearance can bias judgments of physical product properties. Treat this as a warning about unintended salience and size cues, not as a palette recipe for quantitative graphics.

Do not encode claims such as “warm is always heavier than cool,” “red is always heaviest,” or “yellow is always lightest.” Such rankings confound hue with lightness, saturation, area, position, background, context, and culture.

## Visual-Weight Safeguards

- Avoid decorative gradients inside bars, areas, bubbles, nodes, and other marks whose geometry already encodes magnitude.
- Avoid making one quantitative range darker, warmer, or more saturated merely to make it feel more important.
- Use salience only when it corresponds to a real state such as selection, warning, threshold crossing, or annotation.
- Reinforce critical states with labels, icons, shape, or line style rather than hue alone.
- Apply weight and stability findings to covers, panels, illustrations, and brand surfaces only after separating them from data marks and legends.

## Cross-Figure Standardization

- Kulesza et al. (2017), [Standardization of Color Palettes for Scientific Visualization](https://doi.org/10.2172/1363736), supports reusable palette standards rather than ad hoc choices.
- Garrison and Bruckner (2022), [Considering best practices in color palettes for molecular visualizations](https://doi.org/10.1515/jib-2022-0016), highlights how arbitrary and semantically inconsistent colors reduce interpretability across molecular visualizations.
- Okabe-Ito's [Color Universal Design palette](https://jfly.uni-koeln.de/color/) is a widely used practitioner resource for categorical colors. Treat it as a starting palette, not proof that every combination, background, and mark size is accessible.

Maintain a registry containing semantic key, display label, color, fallback pattern or shape, allowed backgrounds, and usage notes. Reuse it across related views.

## Bundled and External Tools

### Bundle

Use `scripts/audit_palette.py` for deterministic first-pass analysis of exact color samples. It has no third-party dependencies and reports:

- CIELAB `L*` and relative luminance;
- adjacent CIE76 color differences;
- lightness monotonicity for sequential maps;
- arm structure for diverging maps;
- endpoint continuity for cyclic maps;
- minimum pairwise separation for categorical maps;
- warnings about weak grayscale spacing and uneven perceptual steps.

### Use externally when available

- Use `colorspacious`, `colour-science`, or equivalent maintained libraries for CIEDE2000, appearance models, and color-vision-deficiency simulation.
- Use `viscm` or palette-specific diagnostics for Matplotlib colormaps.
- Use browser or operating-system CVD simulation on the final rendered interface.
- Print or export the final figure to grayscale and inspect it at delivery size.

### Do not bundle by default

- Do not auto-generate “scientific” palettes from a brand color without gamut mapping and perceptual validation.
- Do not infer a palette from screenshots as authoritative; antialiasing, transparency, compression, and backgrounds contaminate samples.
- Do not implement a simplified CVD simulator and present its result as certification.

## Reproducibility Record

For publication or regulated reporting, record:

- palette family, map name, source, and version;
- exact ordered color samples or lookup-table hash;
- map class and semantic meaning;
- normalization, limits, center, clipping, and transform;
- missing, under-range, and over-range colors;
- background and transparency;
- validation tools and versions;
- grayscale and CVD checks performed.
