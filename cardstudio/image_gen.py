from __future__ import annotations

import logging
import os
import sys
import textwrap
from typing import TYPE_CHECKING, Any

from ballsdex.core.image_generator import image_gen as bd_image_gen
from PIL import Image, ImageDraw, ImageFont, ImageOps
from settings.models import settings

from cardstudio.models import CardConfig

if TYPE_CHECKING:
    from bd_models.models import BallInstance

log = logging.getLogger("ballsdex.packages.cardstudio.image_gen")

original_draw_card = bd_image_gen.draw_card

DEFAULT_FONTS = {
    "title": "ArsenicaTrial-Extrabold.ttf",
    "capacity_name": "Bobby Jones Soft.otf",
    "capacity_description": "OpenSans-Semibold.ttf",
    "stats": "Bobby Jones Soft.otf",
    "credits": "arial.ttf",
    "rarity": "Bobby Jones Soft.otf",
}


def hex_to_rgba(value: str, default: tuple[int, int, int, int] = (0, 0, 0, 255)) -> tuple[int, int, int, int]:
    cleaned = (value or "").strip().lstrip("#")
    if not cleaned:
        return default
    if len(cleaned) == 3:
        cleaned = "".join(char * 2 for char in cleaned)
    if len(cleaned) != 6:
        return default
    return (int(cleaned[0:2], 16), int(cleaned[2:4], 16), int(cleaned[4:6], 16), 255)


def _field_path(field: Any) -> str:
    name = getattr(field, "name", None)
    if isinstance(name, str) and name.startswith("/"):
        storage = getattr(field, "storage", None)
        if storage is not None and hasattr(storage, "path"):
            return storage.path(name.lstrip("/"))
    return field.path

def _open_image_field(field: Any) -> Image.Image:
    name = getattr(field, "name", None)
    storage = getattr(field, "storage", None)

    if isinstance(name, str):
        if name.startswith("/"):
            log.warning(
                "CardStudio received an absolute-looking storage path %r; "
                "normalizing it before opening.",
                name,
            )
            name = name.lstrip("/")

        if storage is not None:
            if hasattr(storage, "path"):
                return Image.open(storage.path(name)).convert("RGBA")

            with storage.open(name, "rb") as file:
                with Image.open(file) as image:
                    return image.convert("RGBA")

    path = getattr(field, "path", None)
    if path:
        return Image.open(path).convert("RGBA")

    with field.open("rb") as file:
        with Image.open(file) as image:
            return image.convert("RGBA")

def load_font(field: Any, size: int, default_name: str) -> ImageFont.FreeTypeFont:
    if field and field.name:
        path = _field_path(field)
        if os.path.isfile(path):
            return ImageFont.truetype(path, size)
    return ImageFont.truetype(str(bd_image_gen.SOURCES_PATH / default_name), size)


def draw_card(ball_instance: BallInstance) -> tuple[Image.Image, dict[str, Any]]:
    config = CardConfig.get_config()
    if config is None:
        return original_draw_card(ball_instance)

    try:
        return _draw_card_styled(ball_instance, config)
    except Exception:
        log.exception("CardStudio draw_card failed; falling back to original")
        return original_draw_card(ball_instance)


def _draw_card_styled(ball_instance: BallInstance, config: CardConfig) -> tuple[Image.Image, dict[str, Any]]:
    ball = ball_instance.countryball
    special_credits = ""
    card_name = ball.cached_regime.name

    if special_image := ball_instance.special_card:
        card_name = getattr(ball_instance.specialcard, "name", card_name)
        image = _open_image_field(special_image)
        if ball_instance.specialcard and ball_instance.specialcard.credits:
            special_credits += f" • Special Author: {ball_instance.specialcard.credits}"
    else:
        image = _open_image_field(ball.cached_regime.background)
    image = image.convert("RGBA")

    economy = ball.cached_economy
    icon = _open_image_field(economy.icon).convert("RGBA") if economy else None

    draw = ImageDraw.Draw(image)

    title_font = load_font(config.title_font, config.title_size, DEFAULT_FONTS["title"])
    draw.text(
        (config.title_x, config.title_y),
        ball.short_name or ball.country,
        font=title_font,
        fill=hex_to_rgba(config.title_color),
        stroke_width=config.title_stroke_width,
        stroke_fill=hex_to_rgba(config.title_stroke_color),
        anchor=config.title_anchor or None,
    )

    capacity_name_font = load_font(config.capacity_name_font, config.capacity_name_size, DEFAULT_FONTS["capacity_name"])
    cap_name = textwrap.wrap(f"Ability: {ball.capacity_name}", width=config.capacity_name_line_width)
    for i, line in enumerate(cap_name):
        draw.text(
            (config.capacity_name_x, config.capacity_name_y + config.capacity_name_line_spacing * i),
            line,
            font=capacity_name_font,
            fill=hex_to_rgba(config.capacity_name_color),
            stroke_width=config.capacity_name_stroke_width,
            stroke_fill=hex_to_rgba(config.capacity_name_stroke_color),
        )

    capacity_description_font = load_font(
        config.capacity_description_font,
        config.capacity_description_size,
        DEFAULT_FONTS["capacity_description"],
    )
    capacity_description_lines = (
        wrapped_line
        for newline in ball.capacity_description.splitlines()
        for wrapped_line in textwrap.wrap(newline, width=config.capacity_description_line_width)
    )
    for i, line in enumerate(capacity_description_lines):
        draw.text(
            (
                config.capacity_description_x,
                config.capacity_description_y
                + config.capacity_name_line_spacing * len(cap_name)
                + config.capacity_description_line_spacing * i,
            ),
            line,
            font=capacity_description_font,
            fill=hex_to_rgba(config.capacity_description_color),
            stroke_width=config.capacity_description_stroke_width,
            stroke_fill=hex_to_rgba(config.capacity_description_stroke_color),
        )

    stats_font = load_font(config.stats_font, config.stats_size, DEFAULT_FONTS["stats"])
    draw.text(
        (config.health_x, config.health_y),
        str(ball_instance.health),
        font=stats_font,
        fill=hex_to_rgba(config.health_color),
        stroke_width=config.stats_stroke_width,
        stroke_fill=hex_to_rgba(config.stats_stroke_color),
    )
    draw.text(
        (config.attack_x, config.attack_y),
        str(ball_instance.attack),
        font=stats_font,
        fill=hex_to_rgba(config.attack_color),
        stroke_width=config.stats_stroke_width,
        stroke_fill=hex_to_rgba(config.stats_stroke_color),
        anchor=config.attack_anchor or None,
    )

    if settings.show_rarity:
        rarity_font = load_font(config.rarity_font, config.rarity_size, DEFAULT_FONTS["rarity"])
        draw.text(
            (config.rarity_x, config.rarity_y),
            str(ball.rarity),
            font=rarity_font,
            fill=hex_to_rgba(config.rarity_color),
            stroke_width=config.rarity_stroke_width,
            stroke_fill=hex_to_rgba(config.rarity_stroke_color),
        )

    if config.credits_color:
        credits_color = hex_to_rgba(config.credits_color)
    elif card_name in bd_image_gen.credits_color_cache:
        credits_color = bd_image_gen.credits_color_cache[card_name]
    else:
        credits_color = bd_image_gen.get_credit_color(image, (0, int(image.height * 0.8), image.width, image.height))
        bd_image_gen.credits_color_cache[card_name] = credits_color

    credits_font = load_font(config.credits_font, config.credits_size, DEFAULT_FONTS["credits"])
    draw.text(
        (config.credits_x, config.credits_y),
        f"Created by El Laggron{special_credits}\nArtwork author: {ball.credits}",
        font=credits_font,
        fill=credits_color,
        stroke_width=config.credits_stroke_width,
        stroke_fill=hex_to_rgba(config.credits_stroke_color),
    )

    artwork = _open_image_field(ball.collection_card).convert("RGBA")
    artwork_size = (max(1, config.artwork_x2 - config.artwork_x1), max(1, config.artwork_y2 - config.artwork_y1))
    image.paste(ImageOps.fit(artwork, artwork_size), (config.artwork_x1, config.artwork_y1))

    if icon:
        icon = ImageOps.fit(icon, (max(1, config.icon_size), max(1, config.icon_size)))
        image.paste(icon, (config.icon_x, config.icon_y), mask=icon)
        icon.close()
    artwork.close()

    return image, {"format": "WEBP"}


def apply_patches() -> None:
    bd_image_gen.draw_card = draw_card

    from bd_models import models as bd_models

    bd_models.draw_card = draw_card

    for module_name in ("preview.views", "preview.management.commands.preview"):
        module = sys.modules.get(module_name)
        if module is not None and hasattr(module, "draw_card"):
            module.draw_card = draw_card
