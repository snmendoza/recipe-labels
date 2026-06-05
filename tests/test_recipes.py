"""Tests for recipe markdown management."""

import os
import tempfile

import pytest

from app.recipes import (
    parse_recipes,
    search_similar,
    generate_suffix,
    append_recipe,
)


SAMPLE_RECIPES_MD = """# Recipe Label Log

Recipes logged via nutrition label workflow.

---

## Milk Butter Blend A3F7

- **Date:** 2026-06-05
- **UPC:** 265134160017
- **Total Weight:** 1065g
- **Serving Size:** 100g
- **Status:** new

### Ingredients
- 800g whole milk
- 28g butter
- 237g water

### Macros (per 100g)
| Calories | Fat | Protein | Carbs |
|----------|-----|---------|-------|
| 65       | 4.5g  | 2.5g      | 3.5g    |

### Notes
_(empty, for manual annotation later)_

---

## Oat Milk Blend R7K2

- **Date:** 2026-06-04
- **UPC:** 234567890128
- **Total Weight:** 950g
- **Serving Size:** 100g
- **Status:** new

### Ingredients
- 500g oat milk
- 200g whole milk
- 250g water

### Macros (per 100g)
| Calories | Fat | Protein | Carbs |
|----------|-----|---------|-------|
| 40       | 1.5g  | 1.5g      | 6g    |

### Notes
_(empty, for manual annotation later)_
"""


@pytest.fixture
def recipes_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(SAMPLE_RECIPES_MD)
        f.flush()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def empty_recipes_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("# Recipe Label Log\n\nRecipes logged via nutrition label workflow.\n")
        f.flush()
        yield f.name
    os.unlink(f.name)


class TestParseRecipes:
    def test_parse_count(self, recipes_file):
        entries = parse_recipes(recipes_file)
        assert len(entries) == 2

    def test_parse_fields(self, recipes_file):
        entries = parse_recipes(recipes_file)
        milk = entries[0]
        assert milk["full_name"] == "Milk Butter Blend A3F7"
        assert milk["suffix"] == "A3F7"
        assert milk["base_name"] == "Milk Butter Blend"
        assert milk["upc"] == "265134160017"
        assert milk["date"] == "2026-06-05"
        assert len(milk["ingredients"]) == 3
        assert milk["macros"]["cal"] == 65

    def test_parse_empty(self, empty_recipes_file):
        entries = parse_recipes(empty_recipes_file)
        assert len(entries) == 0

    def test_parse_missing_file(self):
        entries = parse_recipes("/nonexistent/path.md")
        assert entries == []


class TestSearchSimilar:
    def test_find_by_ingredients(self, recipes_file):
        matches = search_similar(
            ["800g whole milk", "28g butter", "200g water"],
            recipes_file,
        )
        assert len(matches) >= 1
        assert matches[0]["entry"]["base_name"] == "Milk Butter Blend"

    def test_find_by_name(self, recipes_file):
        matches = search_similar(
            ["100g something else"],
            recipes_file,
            base_name="Milk Butter Blend",
        )
        assert len(matches) >= 1

    def test_no_match(self, recipes_file):
        matches = search_similar(
            ["500g chicken", "200g rice"],
            recipes_file,
        )
        assert len(matches) == 0


class TestGenerateSuffix:
    def test_length(self, empty_recipes_file):
        suffix = generate_suffix(empty_recipes_file)
        assert len(suffix) == 4

    def test_alphanumeric(self, empty_recipes_file):
        suffix = generate_suffix(empty_recipes_file)
        assert suffix.isalnum()
        assert suffix == suffix.upper()

    def test_no_collision(self, recipes_file):
        suffix = generate_suffix(recipes_file)
        assert suffix not in ("A3F7", "R7K2")


class TestAppendRecipe:
    def test_append(self, empty_recipes_file):
        append_recipe(
            {
                "full_name": "Test Recipe X1Y2",
                "upc": "200000000001",
                "total_weight": "500g",
                "serving_size": "100g",
                "status": "new",
                "ingredients": ["200g flour", "100g sugar", "200g water"],
                "macros": {"cal": 150, "fat": 2, "protein": 5, "carb": 30},
            },
            empty_recipes_file,
        )
        entries = parse_recipes(empty_recipes_file)
        assert len(entries) == 1
        assert entries[0]["full_name"] == "Test Recipe X1Y2"

    def test_append_iteration(self, recipes_file):
        append_recipe(
            {
                "full_name": "Milk Butter Blend V2B3",
                "upc": "200000000002",
                "total_weight": "1100g",
                "serving_size": "100g",
                "status": "iteration",
                "iteration_of": "Milk Butter Blend A3F7",
                "ingredients": ["900g whole milk", "28g butter", "200g water"],
                "macros": {"cal": 60, "fat": 4, "protein": 2.5, "carb": 3.5},
            },
            recipes_file,
        )
        entries = parse_recipes(recipes_file)
        assert len(entries) == 3
        latest = entries[-1]
        assert "iteration" in latest["status"]
