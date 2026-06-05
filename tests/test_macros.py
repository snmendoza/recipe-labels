"""Tests for macro computation (mocked API)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.macros import compute_macros, validate_calories


SAMPLE_API_RESPONSE = {
    "ingredients": [
        {"original": "800g whole milk", "grams": 800, "cal": 488, "fat": 26.4, "protein": 26.4, "carb": 38.4},
        {"original": "28g butter", "grams": 28, "cal": 202, "fat": 22.8, "protein": 0.2, "carb": 0.0},
        {"original": "237g water", "grams": 237, "cal": 0, "fat": 0, "protein": 0, "carb": 0},
    ],
    "totals": {"grams": 1065, "cal": 690, "fat": 49.2, "protein": 26.6, "carb": 38.4},
    "per_100g": {"cal": 65, "fat": 4.5, "protein": 2.5, "carb": 3.5},
    "suggested_name": "Milk Butter Blend",
}


class TestValidateCalories:
    def test_valid(self):
        is_valid, expected, actual, pct = validate_calories(65, 4.5, 2.5, 3.5)
        assert is_valid

    def test_invalid(self):
        is_valid, expected, actual, pct = validate_calories(200, 4.5, 2.5, 3.5)
        assert not is_valid
        assert pct > 15

    def test_zero_macros(self):
        is_valid, expected, actual, pct = validate_calories(0, 0, 0, 0)
        assert is_valid


class TestComputeMacros:
    @patch("app.macros.anthropic")
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_parse_response(self, mock_anthropic):
        # Mock the API client
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        mock_message = MagicMock()
        mock_content = MagicMock()
        mock_content.text = json.dumps(SAMPLE_API_RESPONSE)
        mock_message.content = [mock_content]
        mock_client.messages.create.return_value = mock_message

        result = compute_macros("800g whole milk, 28g butter, 237g water")

        assert "ingredients" in result
        assert "totals" in result
        assert "per_100g" in result
        assert result["per_100g"]["cal"] == 65
        assert result["suggested_name"] == "Milk Butter Blend"

    @patch("app.macros.anthropic")
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_strips_markdown_fences(self, mock_anthropic):
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        mock_message = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "```json\n" + json.dumps(SAMPLE_API_RESPONSE) + "\n```"
        mock_message.content = [mock_content]
        mock_client.messages.create.return_value = mock_message

        result = compute_macros("800g whole milk, 28g butter, 237g water")
        assert result["per_100g"]["cal"] == 65

    @patch("app.macros.anthropic")
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_calorie_warning(self, mock_anthropic):
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        bad_data = dict(SAMPLE_API_RESPONSE)
        bad_data["per_100g"] = {"cal": 200, "fat": 4.5, "protein": 2.5, "carb": 3.5}

        mock_message = MagicMock()
        mock_content = MagicMock()
        mock_content.text = json.dumps(bad_data)
        mock_message.content = [mock_content]
        mock_client.messages.create.return_value = mock_message

        result = compute_macros("test")
        assert len(result["warnings"]) > 0
        assert "mismatch" in result["warnings"][0].lower()

    def test_no_api_key(self):
        import os
        old = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                compute_macros("test")
        finally:
            if old:
                os.environ["ANTHROPIC_API_KEY"] = old
