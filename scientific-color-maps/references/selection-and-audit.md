# Selection and Audit Reference

Use this reference to turn the principles in `SKILL.md` into a concrete palette decision or figure review.

## Decision Table

| Data semantics and display role | Map class | Required property | Common choices |
|---|---|---|---|
| Magnitude shown primarily by color in a heatmap, image, or map | Sequential | Ordered, preferably monotonic lightness; hue variation may assist range discrimination | `viridis`, `cividis`, `magma`, `batlow`, suitable cmocean map |
| Magnitude already shown by bar length, height, position, or label | Single-hue sequential reinforcement | Fixed hue with monotonic lightness or saturation; color remains secondary | One accessible brand hue sampled from light to dark |
| Signed anomaly around a meaningful baseline | Diverging | Two ordered arms meeting at the true baseline | `vik`, `broc`, cmocean `balance`, ColorBrewer diverging maps |
| Direction, phase, orientation, time of day | Cyclic | Endpoints meet without a seam | `romaO`, `twilight`, cmocean `phase` |
| Unordered classes | Categorical | Distinct colors with comparable visual weight | ColorBrewer qualitative maps, categorical Scientific Colour Maps |
| Named operational states with real thresholds and actions | Discrete categorical or ordered states | Thresholds documented and labels visible | Accessible state colors plus text or icon reinforcement |
| Ordered bins | Discrete sequential or diverging | Ordered bins and visible boundaries | Sample a validated continuous map at equal intervals |

Palette names are starting points, not universal answers. Verify availability, version, license, background behavior, and suitability for the exact data range.

## Selection Procedure

1. Identify whether the variable is continuous, ordinal, categorical, or periodic.
2. Identify whether a reference value has domain meaning.
3. Identify the primary visual channel: color, position, length, height, area, shape, or text.
4. Decide whether viewers must estimate values, detect local variation, compare regions, or find threshold crossings.
5. Require an explicit reason for every hue change: category identity, real threshold state, diverging direction, cyclic position, or improved perception in a color-primary field.
6. Choose a map class from the decision table.
7. Choose a documented palette in that class.
8. Set normalization and limits from the analysis, not from aesthetics.
9. Render with the actual data, output size, background, overlays, and color bar.
10. Run accessibility and distortion checks.

## Hue-Change Decision Test

Ask these questions in order:

1. Is the value already encoded by position, bar length, bar height, or a direct label?
   - Yes: start with one hue and monotonic lightness. Add hue variation only for a separate meaningful variable or state.
2. Does a color boundary correspond to a named threshold with a different action?
   - Yes: discrete state colors are defensible if the thresholds and labels are visible.
   - No: do not invent low, medium, and high hues; preserve a continuous ramp.
3. Does the variable have two meaningful directions around a center?
   - Yes: use a diverging map centered on that value.
4. Is the variable periodic?
   - Yes: use a cyclic map.
5. Is color the primary way to read a dense continuous field?
   - Yes: a perceptually uniform multi-hue sequential map is acceptable when it improves discrimination and retains ordered lightness.

The presence of hue variation is neither automatically scientific nor automatically unscientific. Its validity depends on data semantics, perceptual uniformity, and whether another visual channel already communicates the same magnitude more clearly.

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
- Is color primary or redundant, and is the palette complexity appropriate for that role?
- Does every hue transition correspond to real semantics or a justified perceptual benefit?

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
| Probability or progress bars jump from blue to amber to green | Unrelated hues imply categorical states even when the value is continuous | Keep bar length or height primary and use a single-hue light-to-dark ramp |
| Arbitrary low, medium, and high bands | Visual boundaries imply real thresholds and actions that may not exist | Use a continuous sequential scale or define and label genuine operational thresholds |
| Multi-hue palette reinforces a value already encoded by position or length | Adds visual complexity without new information | Reduce color to a single hue or neutral-to-accent emphasis |

## Probability Bar Pattern

For a probability bar whose height or width already maps `0–100%`:

- Use bar geometry as the primary quantitative channel.
- Use one hue with ordered lightness as secondary reinforcement.
- Render `0%` as an empty neutral track rather than a colored minimum bar.
- Keep missing or unavailable data distinct from `0%`, for example with a pattern, icon, or explicit label.
- Avoid arbitrary blue/amber/green bands unless they represent documented operational states such as “ignore,” “review,” and “act,” each with explicit thresholds.
- If operational states exist, preserve the numeric bar and add a labeled badge or marker; do not rely on hue alone.

Example CSS structure:

```css
.probability-track { background: #e7edef; }
.probability-1 { background: #b8e3dc; }
.probability-2 { background: #8dd2c7; }
.probability-3 { background: #62c0b1; }
.probability-4 { background: #36ad9a; }
.probability-5 { background: #087d70; }
```

Treat these hex values as an illustrative ordered ramp, not a universal palette. Validate contrast and lightness in the actual interface.

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
