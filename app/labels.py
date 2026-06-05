"""Generate 1.5" round nutrition and recipe card labels with UPC-A barcodes."""

import os
import random
import re
import subprocess
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

SIZE = 450
CENTER = SIZE // 2
RADIUS = SIZE // 2


def _find_fonts():
    """Find suitable bold and regular fonts."""
    candidates_bold = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial Bold.ttf",
    ]
    candidates_regular = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ]

    bold_path = None
    regular_path = None

    for p in candidates_bold:
        if os.path.exists(p):
            bold_path = p
            break
    for p in candidates_regular:
        if os.path.exists(p):
            regular_path = p
            break

    # Fallback: fc-match
    if not bold_path:
        try:
            result = subprocess.run(
                ["fc-match", "sans:bold", "-f", "%{file}"],
                capture_output=True, text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                bold_path = result.stdout.strip()
        except FileNotFoundError:
            pass

    if not regular_path:
        try:
            result = subprocess.run(
                ["fc-match", "sans", "-f", "%{file}"],
                capture_output=True, text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                regular_path = result.stdout.strip()
        except FileNotFoundError:
            pass

    bold_path = bold_path or regular_path or "arial"
    regular_path = regular_path or bold_path or "arial"
    return bold_path, regular_path


_BOLD_PATH, _REGULAR_PATH = _find_fonts()


def _font_bold(size):
    try:
        f = ImageFont.truetype(_BOLD_PATH, size, index=1)
    except Exception:
        try:
            f = ImageFont.truetype(_BOLD_PATH, size)
        except Exception:
            f = ImageFont.load_default()
    return f


def _font_regular(size):
    try:
        f = ImageFont.truetype(_REGULAR_PATH, size, index=0)
    except Exception:
        try:
            f = ImageFont.truetype(_REGULAR_PATH, size)
        except Exception:
            f = ImageFont.load_default()
    return f


def _text_height(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[3] - bbox[1]


def _apply_circle_mask(img):
    """Apply circular mask with transparent outside and light gray outline."""
    mask = Image.new("L", (SIZE, SIZE), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse([0, 0, SIZE - 1, SIZE - 1], fill=255)
    img.putalpha(mask)
    draw = ImageDraw.Draw(img)
    draw.ellipse([0, 0, SIZE - 1, SIZE - 1], outline=(200, 200, 200, 255), width=2)
    return img


def generate_upc(prefix=2):
    """Generate a random UPC-A code with the given prefix digit."""
    digits = [prefix]
    for _ in range(10):
        digits.append(random.randint(0, 9))
    odd_sum = sum(digits[i] for i in range(0, 11, 2))
    even_sum = sum(digits[i] for i in range(1, 11, 2))
    check = (10 - (odd_sum * 3 + even_sum) % 10) % 10
    digits.append(check)
    return "".join(str(d) for d in digits)


def validate_upc(upc_str):
    """Return True if upc_str is a valid 12-digit UPC-A."""
    if not upc_str or len(upc_str) != 12 or not upc_str.isdigit():
        return False
    digits = [int(c) for c in upc_str]
    odd_sum = sum(digits[i] for i in range(0, 11, 2))
    even_sum = sum(digits[i] for i in range(1, 11, 2))
    check = (10 - (odd_sum * 3 + even_sum) % 10) % 10
    return digits[11] == check


def _render_barcode_image(upc_str):
    """Render a UPC-A barcode and return as a PIL Image (bars only, no text)."""
    import barcode
    from barcode.writer import ImageWriter

    writer = ImageWriter()
    upc_code = barcode.get("upca", upc_str[:11], writer=writer)
    buf = BytesIO()
    upc_code.write(buf, options={
        "write_text": False,
        "font_size": 0,
        "module_width": 0.33,
        "module_height": 8.0,
        "quiet_zone": 2.0,
    })
    buf.seek(0)
    bc_img = Image.open(buf).convert("RGBA")

    bbox = bc_img.getbbox()
    if bbox:
        bc_img = bc_img.crop(bbox)

    target_w = 280
    ratio = target_w / bc_img.width
    new_h = int(bc_img.height * ratio)
    bc_img = bc_img.resize((target_w, new_h), Image.LANCZOS)
    return bc_img


def slugify(title):
    """Convert a title to a filesystem-safe slug."""
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


def generate_nutrition_label(title, cal, fat, protein, carb, serving, upc_str, output_path):
    """Generate the 1.5" round nutrition facts label.

    Returns the output_path for chaining.
    """
    img = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Pick font sizes based on title length
    title_size = 20
    if len(title) > 24:
        title_size = 17
    if len(title) > 30:
        title_size = 14

    f_title = _font_bold(title_size)
    f_nf = _font_bold(15)
    f_serving = _font_regular(12)
    f_cal_label = _font_bold(16)
    f_cal_val = _font_bold(22)
    f_row_label = _font_bold(12)
    f_row_val = _font_regular(12)
    f_upc_text = _font_regular(13)

    bc_img = _render_barcode_image(upc_str)

    margin_l = 55
    margin_r = 395

    # Format macro values
    fat_s = f"{fat:g}g" if isinstance(fat, (int, float)) else f"{fat}g"
    protein_s = f"{protein:g}g" if isinstance(protein, (int, float)) else f"{protein}g"
    carb_s = f"{carb:g}g" if isinstance(carb, (int, float)) else f"{carb}g"

    macro_rows = [
        ("Total Fat", fat_s),
        ("Total Carb", carb_s),
        ("Protein", protein_s),
    ]

    # Build element list: (kind, height, *extras)
    elements = []
    elements.append(("title", _text_height(draw, title, f_title)))
    elements.append(("thin_rule", 1))
    elements.append(("gap", 3))
    elements.append(("nf", _text_height(draw, "Nutrition Facts", f_nf)))
    elements.append(("thick_rule", 3))
    elements.append(("serving", _text_height(draw, f"Serv. Size {serving}", f_serving)))
    elements.append(("thin_rule", 1))
    elements.append(("gap", 2))
    cal_h = max(
        _text_height(draw, "Calories", f_cal_label),
        _text_height(draw, str(cal), f_cal_val),
    )
    elements.append(("calories", cal_h))
    elements.append(("thick_rule", 3))
    row_h = _text_height(draw, "Total Fat", f_row_label)
    for i, (label, val) in enumerate(macro_rows):
        elements.append(("macro_row", row_h, label, val))
        if i < len(macro_rows) - 1:
            elements.append(("thin_rule", 1))
    elements.append(("gap", 5))
    elements.append(("barcode", bc_img.height))
    elements.append(("gap", 2))
    elements.append(("upc_text", _text_height(draw, upc_str, f_upc_text)))

    total_h = sum(e[1] for e in elements)
    y = (SIZE - total_h) // 2

    for e in elements:
        kind, h = e[0], e[1]
        if kind == "title":
            draw.text((CENTER, y), title, font=f_title, fill="black", anchor="mt")
        elif kind == "nf":
            draw.text((CENTER, y), "Nutrition Facts", font=f_nf, fill="black", anchor="mt")
        elif kind == "serving":
            draw.text((CENTER, y), f"Serv. Size {serving}", font=f_serving, fill="black", anchor="mt")
        elif kind == "calories":
            draw.text((margin_l, y), "Calories", font=f_cal_label, fill="black", anchor="lt")
            draw.text((margin_r, y), str(cal), font=f_cal_val, fill="black", anchor="rt")
        elif kind == "macro_row":
            draw.text((margin_l, y), e[2], font=f_row_label, fill="black", anchor="lt")
            draw.text((margin_r, y), e[3], font=f_row_val, fill="black", anchor="rt")
        elif kind == "thin_rule":
            draw.line([(margin_l, y), (margin_r, y)], fill="black", width=1)
        elif kind == "thick_rule":
            draw.rectangle([(margin_l, y), (margin_r, y + 2)], fill="black")
        elif kind == "barcode":
            bc_x = (SIZE - bc_img.width) // 2
            img.paste(bc_img, (bc_x, y), bc_img)
        elif kind == "upc_text":
            draw.text((CENTER, y), upc_str, font=f_upc_text, fill="black", anchor="mt")
        y += h

    img = _apply_circle_mask(img)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG", dpi=(300, 300))
    return output_path


def generate_recipe_label(title, suffix, ingredients_list, cal, fat, protein, carb,
                          total_weight, output_path):
    """Generate the 1.5" round recipe card label.

    Returns the output_path for chaining.
    """
    img = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    base_name = title
    if suffix and title.endswith(suffix):
        base_name = title[: -len(suffix)].strip()

    title_size = 16
    if len(base_name) > 22:
        title_size = 14

    f_title = _font_bold(title_size)
    f_suffix = _font_regular(11)
    f_ingr = _font_regular(11)
    f_macro = _font_bold(10)
    f_total = _font_regular(10)

    margin_l = 65
    margin_r = 385
    ingr_lh = 14

    fat_s = f"{fat:g}" if isinstance(fat, (int, float)) else str(fat)
    protein_s = f"{protein:g}" if isinstance(protein, (int, float)) else str(protein)
    carb_s = f"{carb:g}" if isinstance(carb, (int, float)) else str(carb)

    macro_line = f"{cal}cal | {fat_s}gF | {protein_s}gP | {carb_s}gC /100g"
    total_line = f"Total: {total_weight}g"

    elements = []
    elements.append(("title", _text_height(draw, base_name, f_title)))
    elements.append(("suffix", _text_height(draw, suffix, f_suffix)))
    elements.append(("gap", 2))
    elements.append(("thin_rule", 1))
    elements.append(("gap", 3))
    for ingr in ingredients_list:
        elements.append(("ingredient", ingr_lh, ingr.strip()))
    elements.append(("gap", 3))
    elements.append(("thin_rule", 1))
    elements.append(("gap", 3))
    elements.append(("macro", _text_height(draw, macro_line, f_macro)))
    elements.append(("total_weight", _text_height(draw, total_line, f_total)))

    total_h = sum(e[1] for e in elements)
    y = (SIZE - total_h) // 2

    for e in elements:
        kind, h = e[0], e[1]
        if kind == "title":
            draw.text((CENTER, y), base_name, font=f_title, fill="black", anchor="mt")
        elif kind == "suffix":
            draw.text((CENTER, y), suffix, font=f_suffix, fill=(128, 128, 128, 255), anchor="mt")
        elif kind == "ingredient":
            draw.text((margin_l, y), e[2], font=f_ingr, fill="black", anchor="lt")
        elif kind == "macro":
            draw.text((CENTER, y), macro_line, font=f_macro, fill="black", anchor="mt")
        elif kind == "total_weight":
            draw.text((CENTER, y), total_line, font=f_total, fill="black", anchor="mt")
        elif kind == "thin_rule":
            draw.line([(margin_l, y), (margin_r, y)], fill="black", width=1)
        y += h

    img = _apply_circle_mask(img)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG", dpi=(300, 300))
    return output_path
