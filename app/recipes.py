"""Recipe markdown log management, dedup search, and suffix generation."""

import os
import random
import re
import string
from datetime import date


def parse_recipes(recipes_md_path):
    """Parse recipes.md into a list of structured recipe dicts.

    Each entry has: name, suffix, date, upc, total_weight, serving_size,
    status, ingredients (list of str), macros (dict), notes, iteration_of.
    """
    if not os.path.exists(recipes_md_path):
        return []

    with open(recipes_md_path, "r") as f:
        content = f.read()

    entries = []
    # Split on markdown H2 headers (recipe entries)
    sections = re.split(r"(?=^## )", content, flags=re.MULTILINE)

    for section in sections:
        section = section.strip()
        if not section.startswith("## "):
            continue

        entry = {}
        # Extract name from header
        header_match = re.match(r"^## (.+)$", section, re.MULTILINE)
        if not header_match:
            continue

        full_name = header_match.group(1).strip()
        entry["full_name"] = full_name

        # Extract suffix (last 4 alphanumeric chars)
        suffix_match = re.search(r"([A-Z0-9]{4})$", full_name)
        entry["suffix"] = suffix_match.group(1) if suffix_match else ""
        entry["base_name"] = full_name[: -len(entry["suffix"])].strip() if entry["suffix"] else full_name

        # Extract metadata fields
        date_match = re.search(r"\*\*Date:\*\*\s*(.+)", section)
        entry["date"] = date_match.group(1).strip() if date_match else ""

        upc_match = re.search(r"\*\*UPC:\*\*\s*(.+)", section)
        entry["upc"] = upc_match.group(1).strip() if upc_match else ""

        weight_match = re.search(r"\*\*Total Weight:\*\*\s*(.+)", section)
        entry["total_weight"] = weight_match.group(1).strip() if weight_match else ""

        serving_match = re.search(r"\*\*Serving Size:\*\*\s*(.+)", section)
        entry["serving_size"] = serving_match.group(1).strip() if serving_match else ""

        status_match = re.search(r"\*\*Status:\*\*\s*(.+)", section)
        entry["status"] = status_match.group(1).strip() if status_match else "new"

        iteration_match = re.search(r"\*\*Iteration of:\*\*\s*(.+)", section)
        entry["iteration_of"] = iteration_match.group(1).strip() if iteration_match else ""

        # Extract ingredients
        ingr_section = re.search(
            r"### Ingredients\n(.*?)(?=\n###|\Z)", section, re.DOTALL
        )
        ingredients = []
        if ingr_section:
            for line in ingr_section.group(1).strip().splitlines():
                line = line.strip()
                if line.startswith("- "):
                    ingredients.append(line[2:].strip())
        entry["ingredients"] = ingredients

        # Extract ingredient names only (for dedup comparison)
        entry["ingredient_names"] = _extract_ingredient_names(ingredients)

        # Extract macros
        entry["macros"] = {"cal": 0, "fat": 0, "protein": 0, "carb": 0}
        macro_table = re.search(
            r"\| Calories.*?\n\|[-\s|]+\n\|\s*(\d+)\s*\|\s*([\d.]+)g?\s*\|\s*([\d.]+)g?\s*\|\s*([\d.]+)g?\s*\|",
            section,
        )
        if macro_table:
            entry["macros"] = {
                "cal": int(macro_table.group(1)),
                "fat": float(macro_table.group(2)),
                "protein": float(macro_table.group(3)),
                "carb": float(macro_table.group(4)),
            }

        entries.append(entry)

    return entries


def _extract_ingredient_names(ingredients):
    """Extract just the ingredient name from entries like '800g whole milk'."""
    names = []
    for ingr in ingredients:
        # Remove leading quantity (e.g. "800g", "28g (2 tbsp)")
        cleaned = re.sub(r"^[\d.]+g?\s*(\([^)]*\)\s*)?", "", ingr).strip()
        if cleaned:
            names.append(cleaned.lower())
    return names


def search_similar(ingredients_list, recipes_md_path, base_name=None):
    """Search for similar recipes by ingredient overlap or name.

    Returns list of dicts: {entry, similarity, match_type}
    """
    entries = parse_recipes(recipes_md_path)
    if not entries:
        return []

    new_names = _extract_ingredient_names(ingredients_list)
    matches = []

    for entry in entries:
        similarity = 0.0
        match_type = None

        # Check ingredient name overlap
        if new_names and entry["ingredient_names"]:
            all_names = set(new_names) | set(entry["ingredient_names"])
            overlap = set(new_names) & set(entry["ingredient_names"])
            if all_names:
                similarity = len(overlap) / len(all_names)

        # Check base name match
        name_match = False
        if base_name and entry["base_name"]:
            if base_name.lower() == entry["base_name"].lower():
                name_match = True
                similarity = max(similarity, 1.0)

        if similarity >= 0.6 or name_match:
            match_type = "name" if name_match else "ingredients"
            matches.append({
                "entry": entry,
                "similarity": round(similarity, 2),
                "match_type": match_type,
            })

    matches.sort(key=lambda m: m["similarity"], reverse=True)
    return matches


def generate_suffix(recipes_md_path):
    """Generate a unique 4-char alphanumeric suffix (uppercase + digits)."""
    existing = set()
    entries = parse_recipes(recipes_md_path)
    for entry in entries:
        if entry.get("suffix"):
            existing.add(entry["suffix"])

    chars = string.ascii_uppercase + string.digits
    for _ in range(100):
        suffix = "".join(random.choices(chars, k=4))
        if suffix not in existing:
            return suffix

    raise RuntimeError("Could not generate unique suffix after 100 attempts")


def append_recipe(entry, recipes_md_path):
    """Append a formatted recipe entry to recipes.md.

    entry dict should contain: full_name, date, upc, total_weight, serving_size,
    status, ingredients (list), macros (dict with cal/fat/protein/carb),
    iteration_of (optional).
    """
    today = entry.get("date", date.today().isoformat())
    upc = entry.get("upc", "")
    total_weight = entry.get("total_weight", "")
    serving = entry.get("serving_size", "100g")
    status = entry.get("status", "new")
    full_name = entry["full_name"]

    lines = [
        "",
        "---",
        "",
        f"## {full_name}",
        "",
        f"- **Date:** {today}",
        f"- **UPC:** {upc}",
        f"- **Total Weight:** {total_weight}",
        f"- **Serving Size:** {serving}",
        f"- **Status:** {status}",
    ]

    if entry.get("iteration_of"):
        anchor = entry["iteration_of"].lower().replace(" ", "-")
        lines.append(f"- **Iteration of:** [{entry['iteration_of']}](#{anchor})")

    lines.append("")
    lines.append("### Ingredients")
    for ingr in entry.get("ingredients", []):
        lines.append(f"- {ingr}")

    macros = entry.get("macros", {})
    lines.append("")
    lines.append("### Macros (per 100g)")
    lines.append("| Calories | Fat | Protein | Carbs |")
    lines.append("|----------|-----|---------|-------|")
    cal = macros.get("cal", 0)
    fat = macros.get("fat", 0)
    protein = macros.get("protein", 0)
    carb = macros.get("carb", 0)
    lines.append(f"| {cal}       | {fat}g  | {protein}g      | {carb}g    |")

    lines.append("")
    lines.append("### Notes")
    lines.append("_(empty, for manual annotation later)_")
    lines.append("")

    with open(recipes_md_path, "a") as f:
        f.write("\n".join(lines))
