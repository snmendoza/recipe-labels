"""Tests for label generation."""

import os
import tempfile

import pytest
from PIL import Image

from app.labels import (
    generate_nutrition_label,
    generate_recipe_label,
    generate_upc,
    validate_upc,
    slugify,
)


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


class TestUPC:
    def test_generate_upc_length(self):
        upc = generate_upc(prefix=2)
        assert len(upc) == 12
        assert upc.isdigit()

    def test_generate_upc_prefix(self):
        upc = generate_upc(prefix=2)
        assert upc[0] == "2"

    def test_generate_upc_valid_check_digit(self):
        upc = generate_upc(prefix=2)
        assert validate_upc(upc)

    def test_validate_upc_valid(self):
        assert validate_upc("296263238308")

    def test_validate_upc_invalid(self):
        assert not validate_upc("296263238309")
        assert not validate_upc("12345")
        assert not validate_upc("")
        assert not validate_upc("abcdefghijkl")


class TestSlugify:
    def test_basic(self):
        assert slugify("Milk Butter Blend A3F7") == "milk-butter-blend-a3f7"

    def test_special_chars(self):
        assert slugify("Mac & Cheese  v2!") == "mac-cheese-v2"


class TestNutritionLabel:
    def test_generates_png(self, tmp_dir):
        path = os.path.join(tmp_dir, "test_nutrition.png")
        result = generate_nutrition_label(
            title="Test Label A1B2",
            cal=65, fat=4.5, protein=2.5, carb=3.5,
            serving="100g",
            upc_str=generate_upc(),
            output_path=path,
        )
        assert os.path.exists(result)
        assert os.path.getsize(result) > 0

    def test_dimensions(self, tmp_dir):
        path = os.path.join(tmp_dir, "test_nutrition.png")
        generate_nutrition_label(
            title="Test Label A1B2",
            cal=65, fat=4.5, protein=2.5, carb=3.5,
            serving="100g",
            upc_str=generate_upc(),
            output_path=path,
        )
        img = Image.open(path)
        assert img.size == (450, 450)

    def test_long_title(self, tmp_dir):
        path = os.path.join(tmp_dir, "test_nutrition.png")
        generate_nutrition_label(
            title="A Very Long Recipe Name That Exceeds Limits X9Y8",
            cal=100, fat=5, protein=10, carb=12,
            serving="100g",
            upc_str=generate_upc(),
            output_path=path,
        )
        assert os.path.exists(path)


class TestRecipeLabel:
    def test_generates_png(self, tmp_dir):
        path = os.path.join(tmp_dir, "test_recipe.png")
        result = generate_recipe_label(
            title="Test Label A1B2",
            suffix="A1B2",
            ingredients_list=["800g whole milk", "28g butter", "237g water"],
            cal=65, fat=4.5, protein=2.5, carb=3.5,
            total_weight=1065,
            output_path=path,
        )
        assert os.path.exists(result)
        assert os.path.getsize(result) > 0

    def test_dimensions(self, tmp_dir):
        path = os.path.join(tmp_dir, "test_recipe.png")
        generate_recipe_label(
            title="Test Label A1B2",
            suffix="A1B2",
            ingredients_list=["800g whole milk", "28g butter"],
            cal=65, fat=4.5, protein=2.5, carb=3.5,
            total_weight=828,
            output_path=path,
        )
        img = Image.open(path)
        assert img.size == (450, 450)

    def test_many_ingredients(self, tmp_dir):
        path = os.path.join(tmp_dir, "test_recipe.png")
        ingredients = [
            "200g flour", "100g sugar", "50g butter", "2 eggs",
            "100ml milk", "5g baking powder", "2g salt", "10g vanilla"
        ]
        generate_recipe_label(
            title="Complex Recipe Z9W8",
            suffix="Z9W8",
            ingredients_list=ingredients,
            cal=250, fat=10, protein=5, carb=35,
            total_weight=470,
            output_path=path,
        )
        assert os.path.exists(path)
