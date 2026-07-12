# Selection and Audit Reference

Use this reference to turn the principles in `SKILL.md` into a concrete palette decision or figure review.

## Decision Table

| Data semantics | Map class | Required property | Common choices |
|---|---|---|---|
| Magnitude, concentration, probability, elevation | Sequential | Ordered, preferably monotonic lightness | `viridis`, `cividis`, `magma`, `batlow`, suitable cmocean map |
| Signed anomaly around a meaningful baseline | Diverging | Two ordered arms meeting at the true baseline | `vik`, `broc`, cmocean `balance`, ColorBrewer diverging maps |
| Direction, phase, orientation, time of day | Cyclic | Endpoints meet without a seam | `romaO`, `twilight`, cmocean `phase` |
| Unordered classes | Categorical | Distinct colors with comparable visual weight | ColorBrewer qualitative maps, categorical Scientific Colour Maps |
| Ordered bins | Discrete sequential or diverging | Ordered bins and visible boundaries | Sample a validated continuous map at equal intervals |

Palette names are starting points, not universal answers. Verify availability, version, license, background behavior, and suitability for the exact data range.

## Selection Procedure

1. Identify whether the variable is continuous, ordinal, categorical, or periodic.
2. Identify whether a reference value has domain meaning.
3. Decide whether viewers must estimate values, detect local variation, compare regions, or find threshold crossings.
4. Choose a map class from the decision table.
5. Choose a documented palette in that class.
6. Set normalization and limits from the analysis, not from aesthetics.
7. Render with the actual data, output size, background, overlays, and color bar.
8. Run accessibility and distortion checks.

## Normalization Rules

- Linear data usually require linear normalization.
- Log normalization is appropriate for positive values spanning orders of magnitude; label logarithmic ticks clearly.
- Symmetric-log normalization can show signed values with a linear region near zero; disclose the threshold.
- Diverging normalization must map the meaningful center to the palette midpoint. Do not assume the arithmetic midpoint of `vmin` and `vmax` is correct.
- Quantile or histogram equalization changes the visual meaning of distance. Use it only for a stated exploratory purpose and label it.
- Clipping can be legitimate for robust display, but report the clipped range and show out-of-range values distinctly when they matter.

## Audit Checklist

### Data semantics

- Does the map class match the variable?
- Is a diverging center meaningful and correctly positioned?
- Are cyclic endpoints visually continuous?
- Are unordered groups encoded without false ordering?

### Perceptual integrity

- Is the palette documented as perceptually uniform or supported by measured diagnostics?
- Does lightness progress monotonically for sequential data?
- Are there artificial bright or dark bands that create false boundaries?
- Have validated palette segments been stretched, clipped, or concatenated?

### Accessibility

- Does the figure remain interpretable in grayscale?
- Are red and green distinguished by more than hue?
- Do common color-vision simulations preserve important comparisons?
- Are critical states reinforced with labels, shapes, line styles, or texture where appropriate?

### Scale and context

- Is the color bar present, labeled, and using the exact plot normalization?
- Are units, limits, ticks, center, and nonlinear transforms clear?
- Is missing data visually distinct from valid minima and maxima?
- Do background, alpha, interpolation, and adjacent colors alter perception?
- Is the palette appropriate for both screen and print output?

## Common Findings and Fixes

| Finding | Why it matters | Preferred fix |
|---|---|---|
| `jet`, rainbow, or `turbo` on scalar data | Uneven perceptual gradients invent and hide structure | Replace with a perceptually uniform map of the correct class |
| Red-green comparison at similar lightness | Common color-vision deficiencies collapse the distinction | Use a CVD-safe palette and redundant encodings |
| Diverging palette with no meaningful center | Implies two semantic directions that may not exist | Use sequential mapping |
| Meaningful zero not at visual midpoint | Biases the apparent magnitude or area of either side | Use centered/two-slope normalization |
| Missing color bar | Prevents quantitative interpretation | Add labeled color bar with units and transformation |
| Palette doubles as missing-data color | Makes absence look like a measured extreme | Assign a separate neutral or patterned missing-data treatment |
| Directly touching heatmap cells are hard to compare | Simultaneous contrast can shift perceived colors | Add subtle separation when appropriate and verify at final size |

## Implementation Patterns

### Matplotlib

```python
from matplotlib.colors import TwoSlopeNorm

# Sequential
ax.imshow(values, cmap="viridis", vmin=lower, vmax=upper)

# Diverging around a meaningful zero
norm = TwoSlopeNorm(vmin=lower, vcenter=0, vmax=upper)
image = ax.imshow(anomaly, cmap=verified_diverging_cmap, norm=norm)
fig.colorbar(image, ax=ax, label="Anomaly (units)")
```

Load `verified_diverging_cmap` from a maintained scientific palette package available in the project. The example demonstrates correct centered normalization without prescribing an unverified fallback.

### ggplot2

```r
ggplot(df, aes(x, y, fill = value)) +
  geom_raster() +
  scale_fill_viridis_c(name = "Value (units)")
```

For diverging data, set the meaningful midpoint explicitly and use a validated diverging palette.

### JavaScript visualization libraries

Use a perceptually uniform interpolator such as a viridis-family scale for sequential data. Set the scale domain, clamp behavior, unknown value, legend ticks, and interpolation explicitly. For diverging data, use a three-point domain whose middle value is the meaningful reference value.

## Source Basis

This workflow is adapted from:

- Fabio Crameri, Grace E. Shephard, and Philip J. Heron, "The misuse of colour in science communication," *Nature Communications* 11, 5444 (2020), DOI: [10.1038/s41467-020-19160-7](https://doi.org/10.1038/s41467-020-19160-7), CC BY 4.0.
- Open full text: [PubMed Central PMC7595127](https://pmc.ncbi.nlm.nih.gov/articles/PMC7595127/).

The paper establishes the core requirements used here: perceptual uniformity, perceptual order, color-vision accessibility, grayscale readability, correct map class, an intact color axis, and proactive rejection of visually distorting maps. The operational decision tables and implementation checks are condensed adaptations for agent use.
