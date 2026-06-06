"""Macro computation via Anthropic API."""

import json
import os

import anthropic

SYSTEM_PROMPT = """You are a nutrition computation assistant. Given a list of recipe ingredients with quantities:
1. Normalize all quantities to grams.
2. Look up macros per 100g for each ingredient (use USDA SR Legacy reference values).
3. Compute weighted totals.
4. Compute per-100g values for the total recipe.
5. Respond ONLY with JSON, no markdown fences, no preamble:
{
  "ingredients": [
    {"original": "800g whole milk", "grams": 800, "cal": 488, "fat": 26.4, "protein": 26.4, "carb": 38.4}
  ],
  "totals": {"grams": 1065, "cal": 690, "fat": 49.4, "protein": 26.6, "carb": 38.4},
  "per_100g": {"cal": 65, "fat": 4.5, "protein": 2.5, "carb": 3.5},
  "suggested_name": "Milk Butter Blend"
}
Round calories to nearest integer, macros to nearest 0.5g."""


def compute_macros(ingredient_text):
    """Send ingredients to Claude and return structured macro data.

    Args:
        ingredient_text: Raw text describing ingredients (e.g. "800g whole milk, 2 tbsp butter, 1 cup water").

    Returns:
        Parsed dict with keys: ingredients, totals, per_100g, suggested_name.

    Raises:
        ValueError: If the API response can't be parsed or macros fail validation.
        anthropic.APIError: If the API call fails.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": ingredient_text},
        ],
    )

    raw_text = message.content[0].text.strip()

    # Strip markdown fences if present
    if raw_text.startswith("```"):
        lines = raw_text.splitlines()
        lines = [l for l in lines if not l.startswith("```")]
        raw_text = "\n".join(lines)

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse API response as JSON: {e}\nRaw: {raw_text}")

    # Validate required keys
    for key in ("ingredients", "totals", "per_100g"):
        if key not in data:
            raise ValueError(f"Missing key '{key}' in API response")

    # Validate calorie sanity: cal ≈ fat*9 + protein*4 + carb*4
    per_100 = data["per_100g"]
    expected_cal = per_100.get("fat", 0) * 9 + per_100.get("protein", 0) * 4 + per_100.get("carb", 0) * 4
    actual_cal = per_100.get("cal", 0)
    warnings = []

    if expected_cal > 0:
        ratio = abs(actual_cal - expected_cal) / expected_cal
        if ratio > 0.15:
            warnings.append(
                f"Calorie mismatch: reported {actual_cal} cal but fat*9+protein*4+carb*4 = {expected_cal:.0f} "
                f"(off by {ratio*100:.0f}%)"
            )

    data["warnings"] = warnings
    return data


def validate_calories(cal, fat, protein, carb):
    """Check if calories ≈ fat*9 + protein*4 + carb*4 within 15%.

    Returns (is_valid, expected_cal, actual_cal, pct_diff).
    """
    expected = fat * 9 + protein * 4 + carb * 4
    if expected == 0:
        return (True, 0, cal, 0)
    pct_diff = abs(cal - expected) / expected
    return (pct_diff <= 0.15, round(expected), cal, round(pct_diff * 100))
