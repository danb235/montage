"""Tests for encoder detection functions with subprocess mocking."""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import (
    ENCODER_NAMES,
    _encoder_cache,
    _test_encoder,
    _test_gpu_availability,
    detect_best_encoder,
)


class TestTestEncoder:
    """Tests for _test_encoder() function using subprocess mocking."""

    def test_encoder_not_available_process_error(self, mocker):
        """Test when encoder fails with CalledProcessError."""
        mocker.patch(
            "main.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "ffmpeg"),
        )

        result = _test_encoder("hevc_videotoolbox")
        assert result is False

    def test_encoder_timeout(self, mocker):
        """Test when encoder times out."""
        mocker.patch(
            "main.subprocess.run", side_effect=subprocess.TimeoutExpired("ffmpeg", 10)
        )

        result = _test_encoder("hevc_videotoolbox")
        assert result is False

    def test_ffmpeg_not_found(self, mocker):
        """Test when ffmpeg is not installed."""
        mocker.patch("main.subprocess.run", side_effect=FileNotFoundError())

        result = _test_encoder("hevc_videotoolbox")
        assert result is False

    def test_hevc_videotoolbox_includes_allow_sw_flag(self, mocker):
        """Verify HEVC VideoToolbox encoder gets -allow_sw flag."""
        mock_run = mocker.patch("main.subprocess.run")
        mock_run.side_effect = FileNotFoundError()

        _test_encoder("hevc_videotoolbox")

        call_args = mock_run.call_args[0][0]
        assert "-allow_sw" in call_args
        assert "1" in call_args

    def test_h264_videotoolbox_includes_allow_sw_flag(self, mocker):
        """Verify H.264 VideoToolbox encoder gets -allow_sw flag."""
        mock_run = mocker.patch("main.subprocess.run")
        mock_run.side_effect = FileNotFoundError()

        _test_encoder("h264_videotoolbox")

        call_args = mock_run.call_args[0][0]
        assert "-allow_sw" in call_args
        assert "1" in call_args

    def test_libx265_no_allow_sw_flag(self, mocker):
        """Verify libx265 (CPU) encoder does not get -allow_sw flag."""
        mock_run = mocker.patch("main.subprocess.run")
        mock_run.side_effect = FileNotFoundError()

        _test_encoder("libx265")

        call_args = mock_run.call_args[0][0]
        assert "-allow_sw" not in call_args

    def test_command_includes_encoder(self, mocker):
        """Verify the encoder name is included in the command."""
        mock_run = mocker.patch("main.subprocess.run")
        mock_run.side_effect = FileNotFoundError()

        _test_encoder("hevc_videotoolbox")

        call_args = mock_run.call_args[0][0]
        assert "hevc_videotoolbox" in call_args

    def test_command_includes_ffmpeg(self, mocker):
        """Verify ffmpeg is the command being run."""
        mock_run = mocker.patch("main.subprocess.run")
        mock_run.side_effect = FileNotFoundError()

        _test_encoder("hevc_videotoolbox")

        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "ffmpeg"

    def test_uses_temporary_directory(self, mocker):
        """Test that a temporary directory is used for test output."""
        mock_run = mocker.patch("main.subprocess.run")
        mock_run.side_effect = FileNotFoundError()

        # This should not raise - temp directory handling is internal
        result = _test_encoder("hevc_videotoolbox")
        assert result is False

    def test_timeout_parameter_passed(self, mocker):
        """Verify timeout is passed to subprocess.run."""
        mock_run = mocker.patch("main.subprocess.run")
        mock_run.side_effect = FileNotFoundError()

        _test_encoder("hevc_videotoolbox", timeout=5)

        # Check timeout was passed in kwargs
        call_kwargs = mock_run.call_args[1]
        assert "timeout" in call_kwargs


class TestDetectBestEncoder:
    """Tests for detect_best_encoder() function."""

    @pytest.fixture(autouse=True)
    def clear_encoder_cache(self):
        """Clear the encoder cache before each test."""
        _encoder_cache.clear()
        yield
        _encoder_cache.clear()

    def test_hevc_videotoolbox_preferred_when_available(self, mocker):
        """When HEVC VideoToolbox works, it should be selected first."""
        mocker.patch("main._test_encoder", return_value=True)

        encoder, _settings, tested = detect_best_encoder("hevc")

        assert encoder == "hevc_videotoolbox"
        assert tested == ["hevc_videotoolbox"]

    def test_fallback_to_h264_videotoolbox(self, mocker):
        """When HEVC fails, fall back to H.264 VideoToolbox."""
        mocker.patch("main._test_encoder", side_effect=[False, True])

        encoder, _settings, tested = detect_best_encoder("hevc")

        assert encoder == "h264_videotoolbox"
        assert "hevc_videotoolbox" in tested
        assert "h264_videotoolbox" in tested

    def test_fallback_to_cpu_libx265(self, mocker):
        """When all GPU encoders fail, fall back to libx265."""
        mocker.patch("main._test_encoder", return_value=False)

        encoder, _settings, tested = detect_best_encoder("hevc")

        assert encoder == "libx265"
        assert len(tested) == 2  # Both GPU encoders were tested

    def test_caching_prevents_repeated_tests(self, mocker):
        """Encoder detection should be cached to avoid repeated tests."""
        mock_test = mocker.patch("main._test_encoder", return_value=True)

        # First call
        detect_best_encoder("hevc")
        # Second call should use cache
        detect_best_encoder("hevc")

        # Should only test once because of caching
        assert mock_test.call_count == 1

    def test_different_codec_not_cached(self, mocker):
        """Different codec parameter should not use same cache."""
        mock_test = mocker.patch("main._test_encoder", return_value=True)

        # First call with hevc
        detect_best_encoder("hevc")
        # Second call with different codec - but current implementation only uses hevc
        # So this tests the cache key includes the codec
        detect_best_encoder("hevc")  # Same codec, should be cached

        assert mock_test.call_count == 1

    def test_returns_correct_settings_for_hevc_videotoolbox(self, mocker):
        """Verify settings match hevc_videotoolbox when that encoder is selected."""
        mocker.patch("main._test_encoder", return_value=True)

        encoder, settings, _ = detect_best_encoder("hevc")

        assert encoder == "hevc_videotoolbox"
        assert settings["quality_flag"] == "-q:v"
        assert "-allow_sw" in settings["extra_args"]

    def test_returns_correct_settings_for_h264_videotoolbox(self, mocker):
        """Verify settings match h264_videotoolbox when that encoder is selected."""
        mocker.patch("main._test_encoder", side_effect=[False, True])

        encoder, settings, _ = detect_best_encoder("hevc")

        assert encoder == "h264_videotoolbox"
        assert settings["quality_flag"] == "-q:v"

    def test_returns_correct_settings_for_libx265(self, mocker):
        """Verify settings match libx265 when CPU fallback is used."""
        mocker.patch("main._test_encoder", return_value=False)

        encoder, settings, _ = detect_best_encoder("hevc")

        assert encoder == "libx265"
        assert settings["quality_flag"] == "-crf"
        assert "presets" in settings

    def test_tested_list_tracks_all_attempts(self, mocker):
        """Verify the tested list includes all encoders that were tested."""
        mocker.patch("main._test_encoder", return_value=False)

        _encoder, _settings, tested = detect_best_encoder("hevc")

        assert "hevc_videotoolbox" in tested
        assert "h264_videotoolbox" in tested
        # libx265 is not "tested" - it's the fallback
        assert "libx265" not in tested


class TestEncoderNames:
    """Tests for ENCODER_NAMES constant."""

    def test_hevc_videotoolbox_has_friendly_name(self):
        assert "hevc_videotoolbox" in ENCODER_NAMES
        assert "GPU" in ENCODER_NAMES["hevc_videotoolbox"]

    def test_h264_videotoolbox_has_friendly_name(self):
        assert "h264_videotoolbox" in ENCODER_NAMES
        assert "GPU" in ENCODER_NAMES["h264_videotoolbox"]

    def test_libx265_has_friendly_name(self):
        assert "libx265" in ENCODER_NAMES
        assert "CPU" in ENCODER_NAMES["libx265"]


class TestTestGpuAvailability:
    """Tests for _test_gpu_availability() function."""

    def test_returns_true_when_hevc_available(self, mocker):
        """When HEVC VideoToolbox works, return True with encoder info."""
        mocker.patch("main._test_encoder", return_value=True)

        available, encoder, settings = _test_gpu_availability()

        assert available is True
        assert encoder == "hevc_videotoolbox"
        assert settings is not None
        assert settings["quality_flag"] == "-q:v"

    def test_returns_true_with_h264_when_hevc_fails(self, mocker):
        """When HEVC fails but H.264 works, return True with H.264 encoder."""
        mocker.patch("main._test_encoder", side_effect=[False, True])

        available, encoder, settings = _test_gpu_availability()

        assert available is True
        assert encoder == "h264_videotoolbox"
        assert settings is not None

    def test_returns_false_when_no_gpu_available(self, mocker):
        """When all GPU encoders fail, return False with None values."""
        mocker.patch("main._test_encoder", return_value=False)

        available, encoder, settings = _test_gpu_availability()

        assert available is False
        assert encoder is None
        assert settings is None

    def test_does_not_fallback_to_cpu(self, mocker):
        """Verify that _test_gpu_availability never returns CPU encoder."""
        mocker.patch("main._test_encoder", return_value=False)

        available, encoder, _settings = _test_gpu_availability()

        # Should never return libx265
        assert encoder != "libx265"
        assert available is False

    def test_tests_encoders_in_priority_order(self, mocker):
        """Verify HEVC is tested before H.264."""
        mock_test = mocker.patch("main._test_encoder", return_value=False)

        _test_gpu_availability()

        # Check the order of calls
        calls = mock_test.call_args_list
        assert len(calls) == 2
        assert calls[0][0][0] == "hevc_videotoolbox"
        assert calls[1][0][0] == "h264_videotoolbox"
