# Recipe schema

The CLI accepts a JSON object. Keep exact anchor colors in `#RRGGBB` form.

## Top-level fields

| Field | Meaning |
|---|---|
| `strategy` | Internal algorithm name; currently `core-inheritance-v4`. |
| `sizes` | ICO frame sizes. Default: `16,24,32,48,64,128,256`. |
| `small_sizes` | Sizes that receive matte and inheritance passes. |
| `small_size_max` | Optional inclusive threshold that optimizes arbitrary small sizes such as 20, 29, 30, 36, 40, and 44px. |
| `crop` | Optional Pillow crop box: `[left, top, right, bottom]`. |
| `background` | Exact semantic background anchor. |
| `preview_background` | Dark preview canvas color. |
| `corner_radius_ratio` | Rounded-mask radius divided by frame width. |
| `supersample` | Supersampling factor used for the alpha mask. |
| `strengthen` | Optional broad anchor strengthening stage. |
| `chroma_mattes` | Saturated semantic layers detected by channel dominance. |
| `projection_mattes` | Layers detected along background-to-anchor color lines. |
| `protected_anchors` | Target colors later layers may not overwrite. |
| `core_colors` | Connected components eligible for one-pixel core inheritance. |

## Minimal structure

```json
{
  "strategy": "core-inheritance-v4",
  "sizes": [16, 24, 32, 48, 64, 128, 256],
  "small_sizes": [16, 24, 32, 48],
  "small_size_max": 48,
  "background": "#FFFFFF",
  "corner_radius_ratio": 0.22,
  "supersample": 4,
  "projection_mattes": [
    {
      "name": "dark_detail",
      "anchor": "#101828",
      "matte_mix": 0.45,
      "source_min_projection": 0.2,
      "source_residual_tolerance": 24,
      "mask_dilation": 17,
      "mask_blur": 1.5,
      "output_residual_tolerance": 24,
      "core_projection": 0.7,
      "core_residual_tolerance": 18,
      "blend_strength": 0.8,
      "priority": 10
    }
  ],
  "protected_anchors": [],
  "core_colors": [
    {
      "name": "dark_detail",
      "anchor": "#101828",
      "source_min_projection": 0.2,
      "source_residual_tolerance": 24,
      "source_confidence_threshold": 0.28,
      "min_source_area": 24,
      "min_importance": 0.025,
      "target_core_projection": 0.68,
      "target_core_residual_tolerance": 24,
      "priority": 10
    }
  ]
}
```

## Strengthen stage

Set `background_anchor` to the anchor name that must not receive gain. Provide per-size maps for `core_radius`, `gain_radius`, and `gain`.

Set `max_size` to enable strengthening for intermediate sizes. Values not explicitly present in the maps are linearly interpolated from their nearest configured sizes; exact configured sizes remain unchanged.

```json
{
  "sizes": [16, 24, 32, 48],
  "max_size": 48,
  "background_anchor": "white",
  "anchors": [
    {"name": "white", "color": "#FFFFFF"},
    {"name": "ink", "color": "#101828"}
  ],
  "core_radius": {"16": 38, "24": 34, "32": 30, "48": 24},
  "gain_radius": {"16": 92, "24": 82, "32": 72, "48": 58},
  "gain": {"16": 0.2, "24": 0.17, "32": 0.14, "48": 0.1}
}
```

## Chroma matte stage

Use for saturated details whose dominant RGB channel remains identifiable. `dominant_channel` may be `r`, `g`, `b`, or `auto`.

Important controls:

- `matte`: intermediate hue-matched background replacement.
- `source_channel_min` and `source_dominance`: source-layer detection.
- `mask_dilation`: source mask expansion before resize.
- `output_channel_min` and `output_dominance`: resized color acceptance.
- `weight_divisor`: converts mask coverage to blend weight.
- `core_dominance` and `core_distance`: exact-anchor snapping.

## Projection matte stage

Important controls:

- `source_min_projection`: minimum progress from background toward anchor.
- `source_residual_tolerance`: maximum perpendicular distance from the color line.
- `matte_mix`: intermediate matte position on the color line.
- `output_min_projection` and `output_residual_tolerance`: resized candidate gate.
- `core_projection`, `core_residual_tolerance`, and `core_mask_threshold`: exact core gate.
- `blend_strength`: maximum semantic-layer blend.
- `priority`: exclusive ownership order and deterministic reporting order.

## Core inheritance stage

Important controls:

- `source_confidence_threshold`: connected-component mask threshold.
- `min_source_area`: reject tiny source noise.
- `min_importance`: reject components with insufficient projected coverage and contrast.
- `target_core_projection` and `target_core_residual_tolerance`: define an already-surviving core.

Change one threshold family at a time and compare the same actual-size frames after every run.
