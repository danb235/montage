"""Tests for interactive prompt functions with questionary mocking."""

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import (
    EncodingSelection,
    _get_encoder_settings,
    prompt_date_range,
    prompt_duration_filter,
    prompt_people_selection,
    prompt_quality_selection,
)


class TestPromptDateRange:
    """Tests for prompt_date_range() function."""

    def test_valid_date_range(self, mocker, mock_console):
        """Test successful date input."""
        mock_text = mocker.patch("main.questionary.text")
        mock_text.return_value.ask.side_effect = ["2024-06-15", "2024-06-20"]

        start, end = prompt_date_range()

        assert start == datetime(2024, 6, 15)
        assert end.date() == datetime(2024, 6, 20).date()
        assert end.hour == 23
        assert end.minute == 59
        assert end.second == 59

    def test_same_day_range(self, mocker, mock_console):
        """Test when start and end are the same day."""
        mock_text = mocker.patch("main.questionary.text")
        mock_text.return_value.ask.side_effect = ["2024-06-15", "2024-06-15"]

        start, end = prompt_date_range()

        assert start.date() == end.date()
        assert start.hour == 0
        assert end.hour == 23

    def test_user_cancels_start_date(self, mocker, mock_console):
        """Test user cancellation on start date (returns None)."""
        mock_text = mocker.patch("main.questionary.text")
        mock_text.return_value.ask.return_value = None

        with pytest.raises(SystemExit) as exc_info:
            prompt_date_range()
        assert exc_info.value.code == 0

    def test_user_cancels_end_date(self, mocker, mock_console):
        """Test user cancellation on end date."""
        mock_text = mocker.patch("main.questionary.text")
        mock_text.return_value.ask.side_effect = ["2024-06-15", None]

        with pytest.raises(SystemExit) as exc_info:
            prompt_date_range()
        assert exc_info.value.code == 0

    def test_text_prompt_called_twice(self, mocker, mock_console):
        """Verify text prompt is called for both start and end dates."""
        mock_text = mocker.patch("main.questionary.text")
        mock_text.return_value.ask.side_effect = ["2024-06-15", "2024-06-20"]

        prompt_date_range()

        assert mock_text.call_count == 2


class TestPromptPeopleSelection:
    """Tests for prompt_people_selection() function."""

    def test_select_specific_people(self, mocker, mock_console):
        """Test selecting specific people from the list."""
        mock_checkbox = mocker.patch("main.questionary.checkbox")
        mock_checkbox.return_value.ask.return_value = ["Alice", "Bob"]

        selected = prompt_people_selection(["Alice", "Bob", "Charlie"])

        assert selected == ["Alice", "Bob"]

    def test_select_all_option(self, mocker, mock_console):
        """Test selecting the ALL option returns None."""
        mock_checkbox = mocker.patch("main.questionary.checkbox")
        mock_checkbox.return_value.ask.return_value = ["ALL (include all videos)"]

        selected = prompt_people_selection(["Alice", "Bob"])

        assert selected is None

    def test_empty_selection_returns_none(self, mocker, mock_console):
        """Test empty selection returns None (include all)."""
        mock_checkbox = mocker.patch("main.questionary.checkbox")
        mock_checkbox.return_value.ask.return_value = []

        selected = prompt_people_selection(["Alice", "Bob"])

        assert selected is None

    def test_no_persons_available(self, mocker, mock_console):
        """Test when no persons are found in videos."""
        selected = prompt_people_selection([])

        assert selected is None

    def test_user_cancels(self, mocker, mock_console):
        """Test user cancellation (Ctrl+C or escape)."""
        mock_checkbox = mocker.patch("main.questionary.checkbox")
        mock_checkbox.return_value.ask.return_value = None

        with pytest.raises(SystemExit) as exc_info:
            prompt_people_selection(["Alice"])
        assert exc_info.value.code == 0

    def test_single_person_selection(self, mocker, mock_console):
        """Test selecting a single person."""
        mock_checkbox = mocker.patch("main.questionary.checkbox")
        mock_checkbox.return_value.ask.return_value = ["Alice"]

        selected = prompt_people_selection(["Alice", "Bob", "Charlie"])

        assert selected == ["Alice"]

    def test_all_people_selected_individually(self, mocker, mock_console):
        """Test when all people are selected individually (not via ALL option)."""
        mock_checkbox = mocker.patch("main.questionary.checkbox")
        mock_checkbox.return_value.ask.return_value = ["Alice", "Bob", "Charlie"]

        selected = prompt_people_selection(["Alice", "Bob", "Charlie"])

        assert selected == ["Alice", "Bob", "Charlie"]


class TestPromptQualitySelection:
    """Tests for prompt_quality_selection() function."""

    def test_gpu_balanced_when_available(self, mocker, mock_console):
        """Test selecting GPU Balanced quality when GPU is available."""
        gpu_settings = _get_encoder_settings("hevc_videotoolbox")
        mocker.patch(
            "main._test_gpu_availability",
            return_value=(True, "hevc_videotoolbox", gpu_settings),
        )
        mock_select = mocker.patch("main.questionary.select")
        mock_select.return_value.ask.return_value = ("gpu", "balanced")

        result = prompt_quality_selection()

        assert isinstance(result, EncodingSelection)
        assert result.encoder_type == "gpu"
        assert result.quality_tier == "balanced"
        assert result.encoder_name == "hevc_videotoolbox"

    def test_gpu_high_quality(self, mocker, mock_console):
        """Test selecting GPU High quality."""
        gpu_settings = _get_encoder_settings("hevc_videotoolbox")
        mocker.patch(
            "main._test_gpu_availability",
            return_value=(True, "hevc_videotoolbox", gpu_settings),
        )
        mock_select = mocker.patch("main.questionary.select")
        mock_select.return_value.ask.return_value = ("gpu", "high")

        result = prompt_quality_selection()

        assert result.encoder_type == "gpu"
        assert result.quality_tier == "high"

    def test_gpu_fast_quality(self, mocker, mock_console):
        """Test selecting GPU Fast quality."""
        gpu_settings = _get_encoder_settings("hevc_videotoolbox")
        mocker.patch(
            "main._test_gpu_availability",
            return_value=(True, "hevc_videotoolbox", gpu_settings),
        )
        mock_select = mocker.patch("main.questionary.select")
        mock_select.return_value.ask.return_value = ("gpu", "fast")

        result = prompt_quality_selection()

        assert result.encoder_type == "gpu"
        assert result.quality_tier == "fast"

    def test_cpu_balanced_when_gpu_unavailable(self, mocker, mock_console):
        """Test selecting CPU Balanced when GPU is not available."""
        mocker.patch(
            "main._test_gpu_availability",
            return_value=(False, None, None),
        )
        mock_select = mocker.patch("main.questionary.select")
        mock_select.return_value.ask.return_value = ("cpu", "balanced")

        result = prompt_quality_selection()

        assert isinstance(result, EncodingSelection)
        assert result.encoder_type == "cpu"
        assert result.quality_tier == "balanced"
        assert result.encoder_name == "libx265"

    def test_cpu_high_quality(self, mocker, mock_console):
        """Test selecting CPU High quality."""
        mocker.patch(
            "main._test_gpu_availability",
            return_value=(False, None, None),
        )
        mock_select = mocker.patch("main.questionary.select")
        mock_select.return_value.ask.return_value = ("cpu", "high")

        result = prompt_quality_selection()

        assert result.encoder_type == "cpu"
        assert result.quality_tier == "high"

    def test_cpu_fast_quality(self, mocker, mock_console):
        """Test selecting CPU Fast quality."""
        mocker.patch(
            "main._test_gpu_availability",
            return_value=(False, None, None),
        )
        mock_select = mocker.patch("main.questionary.select")
        mock_select.return_value.ask.return_value = ("cpu", "fast")

        result = prompt_quality_selection()

        assert result.encoder_type == "cpu"
        assert result.quality_tier == "fast"

    def test_default_is_gpu_balanced_when_available(self, mocker, mock_console):
        """Test that default selection is GPU Balanced when GPU is available."""
        gpu_settings = _get_encoder_settings("hevc_videotoolbox")
        mocker.patch(
            "main._test_gpu_availability",
            return_value=(True, "hevc_videotoolbox", gpu_settings),
        )
        mock_select = mocker.patch("main.questionary.select")
        mock_select.return_value.ask.return_value = ("gpu", "balanced")

        prompt_quality_selection()

        # Check that default was set to GPU balanced
        call_kwargs = mock_select.call_args
        assert call_kwargs.kwargs["default"] == ("gpu", "balanced")

    def test_default_is_cpu_balanced_when_gpu_unavailable(self, mocker, mock_console):
        """Test that default selection is CPU Balanced when GPU is unavailable."""
        mocker.patch(
            "main._test_gpu_availability",
            return_value=(False, None, None),
        )
        mock_select = mocker.patch("main.questionary.select")
        mock_select.return_value.ask.return_value = ("cpu", "balanced")

        prompt_quality_selection()

        # Check that default was set to CPU balanced
        call_kwargs = mock_select.call_args
        assert call_kwargs.kwargs["default"] == ("cpu", "balanced")

    def test_gpu_unavailable_shows_disabled_option(self, mocker, mock_console):
        """Test that GPU option is disabled when unavailable."""
        import questionary

        mocker.patch(
            "main._test_gpu_availability",
            return_value=(False, None, None),
        )
        mock_select = mocker.patch("main.questionary.select")
        mock_select.return_value.ask.return_value = ("cpu", "balanced")

        prompt_quality_selection()

        # Check that a disabled Choice (not Separator) was passed
        call_kwargs = mock_select.call_args
        choices = call_kwargs.kwargs["choices"]
        disabled_choices = [
            c
            for c in choices
            if isinstance(c, questionary.Choice)
            and not isinstance(c, questionary.Separator)
            and hasattr(c, "disabled")
            and c.disabled
        ]
        assert len(disabled_choices) == 1
        assert "no VideoToolbox" in disabled_choices[0].disabled

    def test_user_cancels(self, mocker, mock_console):
        """Test user cancellation."""
        mocker.patch(
            "main._test_gpu_availability",
            return_value=(False, None, None),
        )
        mock_select = mocker.patch("main.questionary.select")
        mock_select.return_value.ask.return_value = None

        with pytest.raises(SystemExit) as exc_info:
            prompt_quality_selection()
        assert exc_info.value.code == 0

    def test_h264_fallback_when_hevc_unavailable(self, mocker, mock_console):
        """Test H.264 GPU encoder is used when HEVC is unavailable."""
        h264_settings = _get_encoder_settings("h264_videotoolbox")
        mocker.patch(
            "main._test_gpu_availability",
            return_value=(True, "h264_videotoolbox", h264_settings),
        )
        mock_select = mocker.patch("main.questionary.select")
        mock_select.return_value.ask.return_value = ("gpu", "balanced")

        result = prompt_quality_selection()

        assert result.encoder_type == "gpu"
        assert result.encoder_name == "h264_videotoolbox"


class TestPromptDurationFilter:
    """Tests for prompt_duration_filter() function."""

    def test_no_filter_empty_inputs(self, mocker, mock_console):
        """Test no duration filter when both inputs are empty."""
        mock_text = mocker.patch("main.questionary.text")
        mock_text.return_value.ask.side_effect = ["", ""]

        min_dur, max_dur = prompt_duration_filter()

        assert min_dur is None
        assert max_dur is None

    def test_min_duration_only(self, mocker, mock_console):
        """Test setting only minimum duration."""
        mock_text = mocker.patch("main.questionary.text")
        mock_text.return_value.ask.side_effect = ["30", ""]

        min_dur, max_dur = prompt_duration_filter()

        assert min_dur == 30.0
        assert max_dur is None

    def test_max_duration_only(self, mocker, mock_console):
        """Test setting only maximum duration."""
        mock_text = mocker.patch("main.questionary.text")
        mock_text.return_value.ask.side_effect = ["", "120"]

        min_dur, max_dur = prompt_duration_filter()

        assert min_dur is None
        assert max_dur == 120.0

    def test_both_durations(self, mocker, mock_console):
        """Test setting both min and max duration."""
        mock_text = mocker.patch("main.questionary.text")
        mock_text.return_value.ask.side_effect = ["30", "120"]

        min_dur, max_dur = prompt_duration_filter()

        assert min_dur == 30.0
        assert max_dur == 120.0

    def test_user_cancels_min_duration(self, mocker, mock_console):
        """Test user cancellation on min duration prompt."""
        mock_text = mocker.patch("main.questionary.text")
        mock_text.return_value.ask.side_effect = [None]

        with pytest.raises(SystemExit):
            prompt_duration_filter()

    def test_user_cancels_max_duration(self, mocker, mock_console):
        """Test user cancellation on max duration prompt."""
        mock_text = mocker.patch("main.questionary.text")
        mock_text.return_value.ask.side_effect = ["30", None]

        with pytest.raises(SystemExit):
            prompt_duration_filter()

    def test_decimal_duration_values(self, mocker, mock_console):
        """Test decimal duration values are parsed correctly."""
        mock_text = mocker.patch("main.questionary.text")
        mock_text.return_value.ask.side_effect = ["30.5", "120.75"]

        min_dur, max_dur = prompt_duration_filter()

        assert min_dur == 30.5
        assert max_dur == 120.75

    def test_zero_duration(self, mocker, mock_console):
        """Test zero as a valid duration value."""
        mock_text = mocker.patch("main.questionary.text")
        mock_text.return_value.ask.side_effect = ["0", "60"]

        min_dur, max_dur = prompt_duration_filter()

        assert min_dur == 0.0
        assert max_dur == 60.0
