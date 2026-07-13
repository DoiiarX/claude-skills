"""Deterministic small-icon rendering primitives.

The public CLI lives in ``icon_resampler.py``.  Keep strategy names versioned
inside this module while keeping output filenames stable at the CLI boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage


RGB = tuple[int, int, int]
STABLE_ICON_NAME = "icon.ico"
STABLE_PREVIEW_NAME = "preview.png"
STABLE_REPORT_NAME = "report.json"
STABLE_FRAMES_DIR = "frames"
SUPPORTED_STRATEGIES = ("core-inheritance-v4",)


def parse_color(value: str) -> RGB:
    text = value.strip().lstrip("#")
    if len(text) != 6:
        raise ValueError(f"invalid RGB color {value!r}; expected #RRGGBB")
    try:
        return tuple(int(text[index : index + 2], 16) for index in (0, 2, 4))
    except ValueError as error:
        raise ValueError(f"invalid RGB color {value!r}; expected #RRGGBB") from error


def color_hex(color: RGB) -> str:
    return "#" + "".join(f"{channel:02X}" for channel in color)


def load_recipe(path: Path) -> dict[str, Any]:
    try:
        recipe = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"recipe does not exist: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(
            f"invalid JSON recipe at line {error.lineno}, column {error.colno}: {error.msg}"
        ) from error
    if not isinstance(recipe, dict):
        raise ValueError("recipe root must be a JSON object")
    validate_recipe(recipe)
    return recipe


def validate_recipe(recipe: dict[str, Any]) -> None:
    strategy = recipe.get("strategy", "core-inheritance-v4")
    if strategy not in SUPPORTED_STRATEGIES:
        supported = ", ".join(SUPPORTED_STRATEGIES)
        raise ValueError(f"unsupported recipe strategy {strategy!r}; supported: {supported}")
    parse_color(_required_text(recipe, "background"))
    sizes = recipe.get("sizes", [16, 24, 32, 48, 64, 128, 256])
    if not sizes or any(not isinstance(size, int) or size <= 0 for size in sizes):
        raise ValueError("sizes must be a non-empty array of positive integers")
    small_sizes = recipe.get("small_sizes", [16, 24, 32, 48])
    if any(size not in sizes for size in small_sizes):
        raise ValueError("every small_sizes entry must also appear in sizes")
    crop = recipe.get("crop")
    if crop is not None and (
        not isinstance(crop, list)
        or len(crop) != 4
        or any(not isinstance(value, int) for value in crop)
        or crop[0] >= crop[2]
        or crop[1] >= crop[3]
    ):
        raise ValueError("crop must be [left, top, right, bottom]")
    for section in ("strengthen", "chroma_mattes", "projection_mattes", "core_colors"):
        if section in recipe and recipe[section] is None:
            raise ValueError(f"{section} cannot be null")


def _required_text(mapping: dict[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing non-empty string field: {key}")
    return value


def _rgb_array(color: RGB) -> np.ndarray:
    return np.asarray(color, dtype=np.float32)


def _projection(
    pixels: np.ndarray, background: np.ndarray, anchor: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    direction = anchor - background
    denominator = float(np.dot(direction, direction))
    if denominator <= 0:
        raise ValueError("semantic anchor must differ from the background")
    relative = pixels - background
    amount = np.sum(relative * direction, axis=-1) / denominator
    reconstructed = background + amount[..., None] * direction
    residual = np.linalg.norm(pixels - reconstructed, axis=-1)
    return amount, residual


def _color_distance(left: RGB, right: RGB) -> float:
    return math.sqrt(sum((left[index] - right[index]) ** 2 for index in range(3)))


def _matte_color(background: RGB, anchor: RGB, mix: float) -> RGB:
    background_array = _rgb_array(background)
    anchor_array = _rgb_array(anchor)
    value = background_array + (anchor_array - background_array) * mix
    return tuple(int(round(channel)) for channel in value)


def _normalized_sizes(recipe: dict[str, Any], override: list[int] | None) -> list[int]:
    sizes = list(override or recipe.get("sizes", [16, 24, 32, 48, 64, 128, 256]))
    if not sizes or any(size <= 0 for size in sizes):
        raise ValueError("sizes must contain positive integers")
    if len(set(sizes)) != len(sizes):
        raise ValueError("sizes must not contain duplicates")
    return sorted(sizes)


def rounded_mask(size: int, *, radius_ratio: float, supersample: int) -> Image.Image:
    render_size = size * supersample
    mask = Image.new("L", (render_size, render_size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, render_size - 1, render_size - 1),
        radius=round(render_size * radius_ratio),
        fill=255,
    )
    return mask.resize((size, size), Image.Resampling.LANCZOS)


def render_base(source: Image.Image, size: int, recipe: dict[str, Any]) -> Image.Image:
    image = source.resize((size, size), Image.Resampling.LANCZOS).convert("RGBA")
    image.putalpha(
        rounded_mask(
            size,
            radius_ratio=float(recipe.get("corner_radius_ratio", 0.2237)),
            supersample=int(recipe.get("supersample", 4)),
        )
    )
    return image


def strengthen_semantic_cores(
    image: Image.Image, size: int, config: dict[str, Any] | None
) -> Image.Image:
    if not config:
        return image.copy()
    reference_sizes = [int(value) for value in config.get("sizes", [16, 24, 32, 48])]
    max_size = int(config.get("max_size", max(reference_sizes)))
    if size > max_size:
        return image.copy()
    anchors = [
        (entry["name"], parse_color(entry["color"]))
        for entry in config.get("anchors", [])
    ]
    if not anchors:
        return image.copy()
    core_radius = float(_size_value(config, "core_radius", size))
    gain_radius = float(_size_value(config, "gain_radius", size))
    gain = float(_size_value(config, "gain", size))
    background_name = str(config.get("background_anchor", "background"))
    source = image.convert("RGBA")
    output = Image.new("RGBA", source.size)
    source_pixels = source.load()
    output_pixels = output.load()
    for y in range(size):
        for x in range(size):
            red, green, blue, alpha = source_pixels[x, y]
            if alpha == 0:
                output_pixels[x, y] = (0, 0, 0, 0)
                continue
            choices = sorted(
                (_color_distance((red, green, blue), color), name, color)
                for name, color in anchors
            )
            anchor_distance, name, anchor = choices[0]
            if anchor_distance <= core_radius:
                adjusted = anchor
            elif name != background_name and anchor_distance <= gain_radius:
                adjusted = tuple(
                    round(channel + (anchor[index] - channel) * gain)
                    for index, channel in enumerate((red, green, blue))
                )
            else:
                adjusted = (red, green, blue)
            output_pixels[x, y] = (*adjusted, alpha)
    return output


def _size_value(config: dict[str, Any], key: str, size: int) -> Any:
    values = config.get(key)
    if not isinstance(values, dict) or not values:
        raise ValueError(f"strengthen.{key} must be a non-empty size map")
    points = sorted((int(point), float(value)) for point, value in values.items())
    for point, value in points:
        if size == point:
            return value
    if size <= points[0][0]:
        return points[0][1]
    if size >= points[-1][0]:
        return points[-1][1]
    for (left_size, left_value), (right_size, right_value) in zip(points, points[1:]):
        if left_size < size < right_size:
            progress = (size - left_size) / (right_size - left_size)
            return left_value + (right_value - left_value) * progress
    raise ValueError(f"could not interpolate strengthen.{key} for {size}px")


def apply_chroma_matte(
    source: Image.Image,
    base: Image.Image,
    size: int,
    layer: dict[str, Any],
    background: RGB,
) -> Image.Image:
    anchor = parse_color(_required_text(layer, "anchor"))
    matte_rgb = parse_color(_required_text(layer, "matte"))
    channel = _dominant_channel(layer.get("dominant_channel", "auto"), anchor)
    channel_index = {"r": 0, "g": 1, "b": 2}[channel]
    other_indexes = [index for index in range(3) if index != channel_index]
    matte = source.copy().convert("RGB")
    matte_pixels = matte.load()
    mask = Image.new("L", source.size, 0)
    mask_pixels = mask.load()
    neutral_min = int(layer.get("background_neutral_min", 238))
    neutral_range = int(layer.get("background_neutral_range", 18))
    source_min = int(layer.get("source_channel_min", 150))
    source_dominance = int(layer.get("source_dominance", 20))
    for y in range(source.height):
        for x in range(source.width):
            rgb = source.getpixel((x, y))
            if min(rgb) >= neutral_min and max(rgb) - min(rgb) <= neutral_range:
                matte_pixels[x, y] = matte_rgb
            if (
                rgb[channel_index] >= source_min
                and rgb[channel_index] - max(rgb[index] for index in other_indexes)
                >= source_dominance
            ):
                mask_pixels[x, y] = 255
    dilation = _odd_filter_size(int(layer.get("mask_dilation", 31)))
    if dilation > 1:
        mask = mask.filter(ImageFilter.MaxFilter(dilation))
    matte = matte.resize((size, size), Image.Resampling.LANCZOS)
    mask = mask.resize((size, size), Image.Resampling.LANCZOS)
    recovered = Image.new("RGB", (size, size))
    recovered_pixels = recovered.load()
    recover_tolerance = float(layer.get("recover_tolerance", 12))
    for y in range(size):
        for x in range(size):
            rgb = matte.getpixel((x, y))
            recovered_pixels[x, y] = (
                background if _color_distance(rgb, matte_rgb) <= recover_tolerance else rgb
            )
    return _composite_chroma_matte(base, recovered, mask, anchor, layer, channel_index)


def _dominant_channel(value: Any, anchor: RGB) -> str:
    if value == "auto":
        return ("r", "g", "b")[int(np.argmax(np.asarray(anchor)))]
    if value not in ("r", "g", "b"):
        raise ValueError("dominant_channel must be r, g, b, or auto")
    return str(value)


def _odd_filter_size(value: int) -> int:
    if value <= 1:
        return 1
    return value if value % 2 == 1 else value + 1


def _composite_chroma_matte(
    base: Image.Image,
    matte: Image.Image,
    mask: Image.Image,
    anchor: RGB,
    layer: dict[str, Any],
    channel_index: int,
) -> Image.Image:
    size = base.width
    other_indexes = [index for index in range(3) if index != channel_index]
    output = base.copy().convert("RGBA")
    output_pixels = output.load()
    mask_pixels = mask.load()
    coverage_threshold = int(layer.get("mask_coverage_threshold", 8))
    output_min = int(layer.get("output_channel_min", 145))
    output_dominance = int(layer.get("output_dominance", 9))
    weight_divisor = float(layer.get("weight_divisor", 150))
    core_dominance = int(layer.get("core_dominance", 55))
    core_distance = float(layer.get("core_distance", 105))
    for y in range(size):
        for x in range(size):
            coverage = mask_pixels[x, y]
            if coverage <= coverage_threshold:
                continue
            rgb = matte.getpixel((x, y))
            dominance = rgb[channel_index] - max(rgb[index] for index in other_indexes)
            if dominance < output_dominance or rgb[channel_index] < output_min:
                continue
            base_rgb = output_pixels[x, y][:3]
            weight = min(1.0, coverage / weight_divisor)
            adjusted = tuple(
                round(base_rgb[index] + (rgb[index] - base_rgb[index]) * weight)
                for index in range(3)
            )
            if dominance >= core_dominance and _color_distance(adjusted, anchor) <= core_distance:
                adjusted = anchor
            output_pixels[x, y] = (*adjusted, output_pixels[x, y][3])
    return output


@dataclass(frozen=True)
class ProjectionMatteLayer:
    name: str
    anchor: RGB
    matte_mix: float
    source_min_projection: float
    source_residual_tolerance: float
    mask_dilation: int = 31
    mask_blur: float = 2.0
    output_min_projection: float = 0.08
    output_residual_tolerance: float = 32.0
    recover_tolerance: float = 12.0
    core_projection: float = 0.68
    core_residual_tolerance: float = 20.0
    core_mask_threshold: int = 96
    blend_strength: float = 1.0
    priority: int = 0


@dataclass(frozen=True)
class ProtectedAnchor:
    name: str
    anchor: RGB
    min_projection: float
    residual_tolerance: float
    dilation: int = 0


class ProjectionMatteResampler:
    def __init__(
        self,
        source: Image.Image,
        *,
        background: RGB,
        layers: list[ProjectionMatteLayer],
        protected_anchors: list[ProtectedAnchor],
        background_tolerance: float,
        background_core_radius: float,
    ) -> None:
        self.source = source.convert("RGB")
        self.background = background
        self.layers = sorted(layers, key=lambda layer: layer.priority)
        self.protected_anchors = protected_anchors
        self.background_tolerance = background_tolerance
        self.background_core_radius = background_core_radius
        self.prepared = self._prepare_layers()

    def _prepare_layers(self) -> dict[str, tuple[Image.Image, Image.Image]]:
        pixels = np.asarray(self.source, dtype=np.float32)
        background = _rgb_array(self.background)
        confidences = []
        for layer in self.layers:
            amount, residual = _projection(pixels, background, _rgb_array(layer.anchor))
            projection_score = np.clip(
                (amount - layer.source_min_projection)
                / max(0.001, 1.0 - layer.source_min_projection),
                0.0,
                1.0,
            )
            residual_score = np.clip(
                1.0 - residual / layer.source_residual_tolerance, 0.0, 1.0
            )
            confidences.append(np.sqrt(projection_score) * residual_score)
        if not confidences:
            return {}
        confidence_stack = np.stack(confidences, axis=0)
        owners = np.argmax(confidence_stack, axis=0)
        prepared = {}
        for index, layer in enumerate(self.layers):
            confidence = np.where(owners == index, confidence_stack[index], 0.0)
            prepared[layer.name] = self._prepare_layer(layer, confidence, pixels, background)
        return prepared

    def _prepare_layer(
        self,
        layer: ProjectionMatteLayer,
        confidence: np.ndarray,
        pixels: np.ndarray,
        background: np.ndarray,
    ) -> tuple[Image.Image, Image.Image]:
        mask = Image.fromarray(
            np.asarray(np.round(confidence * 255), dtype=np.uint8), mode="L"
        )
        dilation = _odd_filter_size(layer.mask_dilation)
        if dilation > 1:
            mask = mask.filter(ImageFilter.MaxFilter(dilation))
        if layer.mask_blur > 0:
            mask = mask.filter(ImageFilter.GaussianBlur(layer.mask_blur))
        matte = np.asarray(np.clip(pixels, 0, 255), dtype=np.uint8).copy()
        background_distance = np.linalg.norm(
            matte.astype(np.float32) - background, axis=-1
        )
        matte[background_distance <= self.background_tolerance] = _matte_color(
            self.background, layer.anchor, layer.matte_mix
        )
        return Image.fromarray(matte, mode="RGB"), mask

    def resize(self, base: Image.Image, size: int) -> Image.Image:
        output = np.asarray(base.convert("RGBA"), dtype=np.float32).copy()
        background = _rgb_array(self.background)
        protected = self._protected_mask(output, background, size)
        for layer in self.layers:
            output = self._apply_layer(output, protected, background, layer, size)
        background_distance = np.linalg.norm(output[..., :3] - background, axis=-1)
        output[background_distance <= self.background_core_radius, :3] = background
        return Image.fromarray(
            np.asarray(np.clip(np.round(output), 0, 255), dtype=np.uint8), mode="RGBA"
        )

    def _protected_mask(
        self, output: np.ndarray, background: np.ndarray, size: int
    ) -> np.ndarray:
        protected = np.zeros((size, size), dtype=bool)
        for item in self.protected_anchors:
            amount, residual = _projection(output[..., :3], background, _rgb_array(item.anchor))
            item_mask = (amount >= item.min_projection) & (
                residual <= item.residual_tolerance
            )
            if item.dilation > 0:
                diameter = item.dilation * 2 + 1
                image = Image.fromarray(
                    np.asarray(item_mask * 255, dtype=np.uint8), mode="L"
                ).filter(ImageFilter.MaxFilter(diameter))
                item_mask = np.asarray(image, dtype=np.uint8) > 0
            protected |= item_mask
        return protected

    def _apply_layer(
        self,
        output: np.ndarray,
        protected: np.ndarray,
        background: np.ndarray,
        layer: ProjectionMatteLayer,
        size: int,
    ) -> np.ndarray:
        matte_source, source_mask = self.prepared[layer.name]
        matte = np.asarray(
            matte_source.resize((size, size), Image.Resampling.LANCZOS), dtype=np.float32
        ).copy()
        mask = np.asarray(
            source_mask.resize((size, size), Image.Resampling.LANCZOS), dtype=np.float32
        ) / 255.0
        matte_rgb = _rgb_array(_matte_color(self.background, layer.anchor, layer.matte_mix))
        matte_distance = np.linalg.norm(matte - matte_rgb, axis=-1)
        matte[matte_distance <= layer.recover_tolerance] = background
        anchor = _rgb_array(layer.anchor)
        amount, residual = _projection(matte, background, anchor)
        valid = (
            (amount >= layer.output_min_projection)
            & (residual <= layer.output_residual_tolerance)
            & (mask > 0)
            & (~protected)
        )
        weight = np.clip(mask * layer.blend_strength, 0.0, 1.0)
        weight = np.where(valid, weight, 0.0)
        output[..., :3] = output[..., :3] * (1.0 - weight[..., None]) + matte * weight[..., None]
        adjusted_amount, adjusted_residual = _projection(output[..., :3], background, anchor)
        core = (
            valid
            & (adjusted_amount >= layer.core_projection)
            & (adjusted_residual <= layer.core_residual_tolerance)
            & (mask * 255 >= layer.core_mask_threshold)
        )
        output[core, :3] = anchor
        return output


@dataclass(frozen=True)
class CoreColor:
    name: str
    anchor: RGB
    source_min_projection: float
    source_residual_tolerance: float
    source_confidence_threshold: float = 0.28
    min_source_area: int = 24
    min_importance: float = 0.025
    target_core_projection: float = 0.68
    target_core_residual_tolerance: float = 24.0
    priority: int = 0


class ColorCoreInheritor:
    def __init__(self, source: Image.Image, *, background: RGB, colors: list[CoreColor]) -> None:
        self.source = source.convert("RGB")
        self.background = background
        self.colors = sorted(colors, key=lambda color: color.priority)
        self.components = self._find_components()

    def _find_components(self) -> list[tuple[CoreColor, np.ndarray, int]]:
        pixels = np.asarray(self.source, dtype=np.float32)
        background = _rgb_array(self.background)
        confidences = []
        for color in self.colors:
            amount, residual = _projection(pixels, background, _rgb_array(color.anchor))
            projection_score = np.clip(
                (amount - color.source_min_projection)
                / max(0.001, 1.0 - color.source_min_projection),
                0.0,
                1.0,
            )
            residual_score = np.clip(
                1.0 - residual / color.source_residual_tolerance, 0.0, 1.0
            )
            confidences.append(np.sqrt(projection_score) * residual_score)
        if not confidences:
            return []
        confidence_stack = np.stack(confidences, axis=0)
        owners = np.argmax(confidence_stack, axis=0)
        components = []
        structure = np.ones((3, 3), dtype=np.uint8)
        for color_index, color in enumerate(self.colors):
            confidence = np.where(owners == color_index, confidence_stack[color_index], 0.0)
            binary = confidence >= color.source_confidence_threshold
            labels, count = ndimage.label(binary, structure=structure)
            objects = ndimage.find_objects(labels)
            for label_index in range(1, count + 1):
                slices = objects[label_index - 1]
                if slices is None:
                    continue
                component = labels[slices] == label_index
                area = int(component.sum())
                if area < color.min_source_area:
                    continue
                weighted = np.where(component, confidence[slices], 0.0)
                full_mask = np.zeros(binary.shape, dtype=np.uint8)
                full_mask[slices] = np.asarray(np.round(weighted * 255), dtype=np.uint8)
                components.append((color, full_mask, area))
        return components

    def apply(self, image: Image.Image, size: int) -> tuple[Image.Image, list[dict[str, Any]]]:
        output = np.asarray(image.convert("RGBA"), dtype=np.uint8).copy()
        rgb = output[..., :3].astype(np.float32)
        background = _rgb_array(self.background)
        inherited = []
        for color, source_mask, source_area in self.components:
            projected = np.asarray(
                Image.fromarray(source_mask, mode="L").resize(
                    (size, size), Image.Resampling.BOX
                ),
                dtype=np.float32,
            ) / 255.0
            projected_area = float(projected.sum())
            contrast = float(
                np.linalg.norm(_rgb_array(color.anchor) - background)
                / np.linalg.norm(np.asarray((255, 255, 255), dtype=np.float32))
            )
            importance = projected_area * contrast
            if importance < color.min_importance or projected.max() <= 0:
                continue
            amount, residual = _projection(rgb, background, _rgb_array(color.anchor))
            support = projected > 0
            already_has_core = np.any(
                support
                & (amount >= color.target_core_projection)
                & (residual <= color.target_core_residual_tolerance)
            )
            if already_has_core:
                continue
            best_y, best_x = np.unravel_index(np.argmax(projected), projected.shape)
            output[best_y, best_x, :3] = color.anchor
            rgb[best_y, best_x] = color.anchor
            inherited.append(
                {
                    "color": color.name,
                    "pixel": [int(best_x), int(best_y)],
                    "source_area": source_area,
                    "projected_area": round(projected_area, 4),
                    "contrast": round(contrast, 4),
                    "importance": round(importance, 4),
                }
            )
        return Image.fromarray(output, mode="RGBA"), inherited


class IconPipeline:
    def __init__(self, source: Image.Image, recipe: dict[str, Any]) -> None:
        self.recipe = recipe
        self.background = parse_color(recipe["background"])
        crop = recipe.get("crop")
        self.source = source.convert("RGB").crop(tuple(crop)) if crop else source.convert("RGB")
        self.small_sizes = {int(size) for size in recipe.get("small_sizes", [16, 24, 32, 48])}
        self.small_size_max = recipe.get("small_size_max")
        self.projection_resampler = self._make_projection_resampler()
        self.core_inheritor = self._make_core_inheritor()

    def _make_projection_resampler(self) -> ProjectionMatteResampler | None:
        layers = [_projection_layer(entry) for entry in self.recipe.get("projection_mattes", [])]
        if not layers:
            return None
        protected = [_protected_anchor(entry) for entry in self.recipe.get("protected_anchors", [])]
        return ProjectionMatteResampler(
            self.source,
            background=self.background,
            layers=layers,
            protected_anchors=protected,
            background_tolerance=float(self.recipe.get("background_tolerance", 28)),
            background_core_radius=float(self.recipe.get("background_core_radius", 8)),
        )

    def _make_core_inheritor(self) -> ColorCoreInheritor | None:
        colors = [_core_color(entry) for entry in self.recipe.get("core_colors", [])]
        if not colors:
            return None
        return ColorCoreInheritor(self.source, background=self.background, colors=colors)

    def render(self, size: int) -> tuple[Image.Image, list[dict[str, Any]]]:
        image = render_base(self.source, size, self.recipe)
        image = strengthen_semantic_cores(image, size, self.recipe.get("strengthen"))
        optimize_small = size in self.small_sizes or (
            self.small_size_max is not None and size <= int(self.small_size_max)
        )
        if not optimize_small:
            return image, []
        for layer in self.recipe.get("chroma_mattes", []):
            image = apply_chroma_matte(self.source, image, size, layer, self.background)
        if self.projection_resampler is not None:
            image = self.projection_resampler.resize(image, size)
        if self.core_inheritor is not None:
            return self.core_inheritor.apply(image, size)
        return image, []


def _projection_layer(entry: dict[str, Any]) -> ProjectionMatteLayer:
    return ProjectionMatteLayer(
        name=_required_text(entry, "name"),
        anchor=parse_color(_required_text(entry, "anchor")),
        matte_mix=float(entry["matte_mix"]),
        source_min_projection=float(entry["source_min_projection"]),
        source_residual_tolerance=float(entry["source_residual_tolerance"]),
        mask_dilation=int(entry.get("mask_dilation", 31)),
        mask_blur=float(entry.get("mask_blur", 2.0)),
        output_min_projection=float(entry.get("output_min_projection", 0.08)),
        output_residual_tolerance=float(entry.get("output_residual_tolerance", 32)),
        recover_tolerance=float(entry.get("recover_tolerance", 12)),
        core_projection=float(entry.get("core_projection", 0.68)),
        core_residual_tolerance=float(entry.get("core_residual_tolerance", 20)),
        core_mask_threshold=int(entry.get("core_mask_threshold", 96)),
        blend_strength=float(entry.get("blend_strength", 1.0)),
        priority=int(entry.get("priority", 0)),
    )


def _protected_anchor(entry: dict[str, Any]) -> ProtectedAnchor:
    return ProtectedAnchor(
        name=_required_text(entry, "name"),
        anchor=parse_color(_required_text(entry, "anchor")),
        min_projection=float(entry["min_projection"]),
        residual_tolerance=float(entry["residual_tolerance"]),
        dilation=int(entry.get("dilation", 0)),
    )


def _core_color(entry: dict[str, Any]) -> CoreColor:
    return CoreColor(
        name=_required_text(entry, "name"),
        anchor=parse_color(_required_text(entry, "anchor")),
        source_min_projection=float(entry["source_min_projection"]),
        source_residual_tolerance=float(entry["source_residual_tolerance"]),
        source_confidence_threshold=float(entry.get("source_confidence_threshold", 0.28)),
        min_source_area=int(entry.get("min_source_area", 24)),
        min_importance=float(entry.get("min_importance", 0.025)),
        target_core_projection=float(entry.get("target_core_projection", 0.68)),
        target_core_residual_tolerance=float(entry.get("target_core_residual_tolerance", 24)),
        priority=int(entry.get("priority", 0)),
    )


def build_icon_family(
    *,
    input_path: Path,
    recipe: dict[str, Any],
    output_dir: Path,
    strategy: str,
    sizes_override: list[int] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    if strategy not in SUPPORTED_STRATEGIES:
        raise ValueError(f"unsupported strategy: {strategy}")
    if recipe.get("strategy", strategy) != strategy:
        raise ValueError(
            f"CLI strategy {strategy!r} does not match recipe strategy {recipe.get('strategy')!r}"
        )
    if not input_path.is_file():
        raise ValueError(f"input image does not exist: {input_path}")
    sizes = _normalized_sizes(recipe, sizes_override)
    plan = {
        "strategy": strategy,
        "input": str(input_path),
        "output_dir": str(output_dir),
        "sizes": sizes,
        "outputs": [STABLE_ICON_NAME, STABLE_PREVIEW_NAME, STABLE_REPORT_NAME, STABLE_FRAMES_DIR],
        "dry_run": dry_run,
    }
    if dry_run:
        return plan
    with Image.open(input_path) as opened:
        pipeline = IconPipeline(opened, recipe)
        rendered = {size: pipeline.render(size) for size in sizes}
    frames = {size: value[0] for size, value in rendered.items()}
    inheritance = {str(size): value[1] for size, value in rendered.items()}
    output_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = output_dir / STABLE_FRAMES_DIR
    frames_dir.mkdir(parents=True, exist_ok=True)
    frame_hashes = _write_frames(frames, frames_dir)
    icon_path = output_dir / STABLE_ICON_NAME
    icon_hash = _write_ico(frames, icon_path)
    preview_path = output_dir / STABLE_PREVIEW_NAME
    preview_hash = _write_png(make_preview(frames, recipe), preview_path)
    verification = verify_ico(icon_path, frames)
    report = {
        "schema_version": 1,
        "strategy": strategy,
        "input": {"name": input_path.name, "sha256": _file_hash(input_path)},
        "recipe_sha256": _json_hash(recipe),
        "sizes": sizes,
        "outputs": {
            STABLE_ICON_NAME: icon_hash,
            STABLE_PREVIEW_NAME: preview_hash,
            STABLE_FRAMES_DIR: frame_hashes,
        },
        "anchor_counts": _anchor_counts(frames, recipe),
        "core_inheritance": inheritance,
        "verification": verification,
    }
    _atomic_write(
        output_dir / STABLE_REPORT_NAME,
        (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    return {
        **plan,
        "dry_run": False,
        "icon": str(icon_path),
        "preview": str(preview_path),
        "report": str(output_dir / STABLE_REPORT_NAME),
        "verification": verification,
    }


def _write_frames(frames: dict[int, Image.Image], frames_dir: Path) -> dict[str, str]:
    expected = {f"{size}x{size}.png" for size in frames}
    for stale in frames_dir.glob("*x*.png"):
        if stale.name not in expected:
            stale.unlink()
    hashes = {}
    for size, frame in frames.items():
        name = f"{size}x{size}.png"
        hashes[name] = _write_png(frame, frames_dir / name)
    return hashes


def _write_png(image: Image.Image, path: Path) -> str:
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    data = buffer.getvalue()
    _atomic_write(path, data)
    return sha256(data).hexdigest()


def _write_ico(frames: dict[int, Image.Image], path: Path) -> str:
    sizes = sorted(frames)
    images = [frames[size] for size in sizes]
    buffer = BytesIO()
    images[-1].save(
        buffer,
        format="ICO",
        append_images=images[:-1],
        sizes=[(size, size) for size in sizes],
    )
    data = buffer.getvalue()
    _atomic_write(path, data)
    return sha256(data).hexdigest()


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def make_preview(frames: dict[int, Image.Image], recipe: dict[str, Any]) -> Image.Image:
    preview_sizes = [size for size in sorted(frames) if size <= 48]
    background = parse_color(recipe.get("preview_background", "#2A2933"))
    cell_width = 172
    width = max(360, 20 + cell_width * len(preview_sizes))
    canvas = Image.new("RGBA", (width, 224), (*background, 255))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    draw.text((14, 12), "actual pixels", fill="white", font=font)
    draw.text((14, 70), "nearest-neighbor detail", fill="white", font=font)
    for index, size in enumerate(preview_sizes):
        left = 112 + index * cell_width
        draw.text((left, 12), f"{size}px", fill="white", font=font)
        canvas.alpha_composite(frames[size], (left + 8, 34))
        factor = max(1, min(8, 128 // size))
        enlarged = frames[size].resize(
            (size * factor, size * factor), Image.Resampling.NEAREST
        )
        canvas.alpha_composite(enlarged, (left, 88))
    return canvas


def _anchor_counts(frames: dict[int, Image.Image], recipe: dict[str, Any]) -> dict[str, Any]:
    anchors: dict[str, RGB] = {}
    for entry in (recipe.get("strengthen") or {}).get("anchors", []):
        anchors[entry["name"]] = parse_color(entry["color"])
    for section in ("chroma_mattes", "projection_mattes", "core_colors"):
        for entry in recipe.get(section, []):
            anchors[entry["name"]] = parse_color(entry["anchor"])
    counts = {}
    for size, frame in frames.items():
        pixels = np.asarray(frame.convert("RGBA"), dtype=np.uint8)[..., :3]
        counts[str(size)] = {
            name: int(np.all(pixels == np.asarray(color, dtype=np.uint8), axis=-1).sum())
            for name, color in anchors.items()
        }
    return counts


def verify_ico(path: Path, expected: dict[int, Image.Image] | None = None) -> dict[str, Any]:
    with Image.open(path) as icon:
        sizes = sorted(size[0] for size in icon.ico.sizes())
        hashes = {}
        exact = {}
        for size in sizes:
            frame = icon.ico.getimage((size, size)).convert("RGBA")
            hashes[str(size)] = _image_hash(frame)
            if expected is not None and size in expected:
                exact[str(size)] = bool(
                    np.array_equal(
                        np.asarray(frame, dtype=np.uint8),
                        np.asarray(expected[size].convert("RGBA"), dtype=np.uint8),
                    )
                )
    result: dict[str, Any] = {"sizes": sizes, "frame_sha256": hashes}
    if expected is not None:
        result["exact_frame_match"] = exact
        result["all_frames_exact"] = set(sizes) == set(expected) and all(exact.values())
    return result


def inspect_ico(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"ICO does not exist: {path}")
    result = verify_ico(path)
    result["path"] = str(path)
    result["sha256"] = _file_hash(path)
    return result


def _image_hash(image: Image.Image) -> str:
    return sha256(image.convert("RGBA").tobytes()).hexdigest()


def _file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_hash(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(data).hexdigest()
