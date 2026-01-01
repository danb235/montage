"""Tests for video compilation functions with subprocess mocking."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import EncodingSelection, _encoder_cache, _get_encoder_settings, compile_movie


class TestCompileMovie:
    """Tests for compile_movie() function."""

    @pytest.fixture(autouse=True)
    def clear_encoder_cache(self):
        """Clear encoder cache before each test."""
        _encoder_cache.clear()
        yield
        _encoder_cache.clear()

    @pytest.fixture
    def gpu_encoding_balanced(self):
        """GPU encoding with balanced quality."""
        return EncodingSelection(
            encoder_type="gpu",
            quality_tier="balanced",
            encoder_name="hevc_videotoolbox",
            encoder_settings=_get_encoder_settings("hevc_videotoolbox"),
        )

    @pytest.fixture
    def cpu_encoding_high(self):
        """CPU encoding with high quality."""
        return EncodingSelection(
            encoder_type="cpu",
            quality_tier="high",
            encoder_name="libx265",
            encoder_settings=_get_encoder_settings("libx265"),
        )

    @pytest.fixture
    def cpu_encoding_balanced(self):
        """CPU encoding with balanced quality."""
        return EncodingSelection(
            encoder_type="cpu",
            quality_tier="balanced",
            encoder_name="libx265",
            encoder_settings=_get_encoder_settings("libx265"),
        )

    @pytest.fixture
    def cpu_encoding_fast(self):
        """CPU encoding with fast quality."""
        return EncodingSelection(
            encoder_type="cpu",
            quality_tier="fast",
            encoder_name="libx265",
            encoder_settings=_get_encoder_settings("libx265"),
        )

    def test_builds_ffmpeg_command(self, mocker, mock_console, sample_playlist):
        """Test that ffmpeg command is built correctly."""
        mocker.patch("main._test_encoder", return_value=True)

        mock_popen = MagicMock()
        mock_popen.stdout = iter([])
        mock_popen.wait.return_value = None
        mock_popen.returncode = 0
        mocker.patch("main.subprocess.Popen", return_value=mock_popen)

        # None triggers auto-detection mode
        compile_movie(sample_playlist, None)

        # Verify Popen was called
        import main

        main.subprocess.Popen.assert_called_once()
        cmd = main.subprocess.Popen.call_args[0][0]
        assert cmd[0] == "ffmpeg"

    def test_uses_hevc_videotoolbox_when_available(
        self, mocker, mock_console, sample_playlist, gpu_encoding_balanced
    ):
        """Test that HEVC VideoToolbox is used when provided in EncodingSelection."""
        mock_popen = MagicMock()
        mock_popen.stdout = iter([])
        mock_popen.wait.return_value = None
        mock_popen.returncode = 0
        mocker.patch("main.subprocess.Popen", return_value=mock_popen)

        compile_movie(sample_playlist, gpu_encoding_balanced)

        import main

        cmd = main.subprocess.Popen.call_args[0][0]

        encoder_idx = cmd.index("-c:v") + 1
        assert cmd[encoder_idx] == "hevc_videotoolbox"

    def test_uses_libx265_for_cpu_quality(
        self, mocker, mock_console, sample_playlist, cpu_encoding_high
    ):
        """Test that libx265 is used for CPU quality selection."""
        mock_popen = MagicMock()
        mock_popen.stdout = iter([])
        mock_popen.wait.return_value = None
        mock_popen.returncode = 0
        mocker.patch("main.subprocess.Popen", return_value=mock_popen)

        compile_movie(sample_playlist, cpu_encoding_high)

        import main

        cmd = main.subprocess.Popen.call_args[0][0]

        encoder_idx = cmd.index("-c:v") + 1
        assert cmd[encoder_idx] == "libx265"

    def test_empty_playlist_returns_none(self, mocker, mock_console, tmp_path):
        """Test that empty playlist returns None."""
        playlist_data = {
            "created": "2024-01-01T00:00:00",
            "project_name": "empty",
            "filters": {
                "start_date": "2024-01-01T00:00:00",
                "end_date": "2024-01-01T23:59:59",
            },
            "videos": [],
        }

        playlist_path = tmp_path / "playlist.json"
        playlist_path.write_text(json.dumps(playlist_data))

        result = compile_movie(playlist_path)

        assert result is None

    def test_ffmpeg_not_found_returns_none(self, mocker, mock_console, sample_playlist):
        """Test handling when ffmpeg is not installed."""
        mocker.patch("main._test_encoder", return_value=True)
        mocker.patch("main.subprocess.Popen", side_effect=FileNotFoundError())

        result = compile_movie(sample_playlist)

        assert result is None

    def test_ffmpeg_failure_returns_none(self, mocker, mock_console, sample_playlist):
        """Test handling when ffmpeg fails."""
        mocker.patch("main._test_encoder", return_value=True)

        mock_popen = MagicMock()
        mock_popen.stdout = iter([])
        mock_popen.wait.return_value = None
        mock_popen.returncode = 1  # Failure
        mocker.patch("main.subprocess.Popen", return_value=mock_popen)

        result = compile_movie(sample_playlist)

        assert result is None

    def test_portrait_video_uses_blur_filter(self, mocker, mock_console, tmp_path):
        """Test that portrait videos use blur filter."""
        mocker.patch("main._test_encoder", return_value=True)

        playlist_data = {
            "created": "2024-01-01T00:00:00",
            "project_name": "portrait_test",
            "filters": {
                "start_date": "2024-01-01T00:00:00",
                "end_date": "2024-01-01T23:59:59",
            },
            "videos": [
                {
                    "uuid": "portrait-uuid",
                    "date": "2024-01-01T10:00:00",
                    "duration": 30.0,
                    "filename": "portrait.mov",
                    "persons": [],
                    "is_portrait": True,
                    "width": 1080,
                    "height": 1920,
                    "path": "/path/to/video.mov",
                }
            ],
        }

        playlist_path = tmp_path / "playlist.json"
        playlist_path.write_text(json.dumps(playlist_data))

        mock_popen = MagicMock()
        mock_popen.stdout = iter([])
        mock_popen.wait.return_value = None
        mock_popen.returncode = 0
        mocker.patch("main.subprocess.Popen", return_value=mock_popen)

        compile_movie(playlist_path)

        import main

        cmd = main.subprocess.Popen.call_args[0][0]
        filter_idx = cmd.index("-filter_complex") + 1
        filter_str = cmd[filter_idx]

        assert "gblur" in filter_str

    def test_landscape_video_uses_pad_filter(self, mocker, mock_console, tmp_path):
        """Test that landscape videos use pad filter."""
        mocker.patch("main._test_encoder", return_value=True)

        playlist_data = {
            "created": "2024-01-01T00:00:00",
            "project_name": "landscape_test",
            "filters": {
                "start_date": "2024-01-01T00:00:00",
                "end_date": "2024-01-01T23:59:59",
            },
            "videos": [
                {
                    "uuid": "landscape-uuid",
                    "date": "2024-01-01T10:00:00",
                    "duration": 30.0,
                    "filename": "landscape.mov",
                    "persons": [],
                    "is_portrait": False,
                    "width": 1920,
                    "height": 1080,
                    "path": "/path/to/video.mov",
                }
            ],
        }

        playlist_path = tmp_path / "playlist.json"
        playlist_path.write_text(json.dumps(playlist_data))

        mock_popen = MagicMock()
        mock_popen.stdout = iter([])
        mock_popen.wait.return_value = None
        mock_popen.returncode = 0
        mocker.patch("main.subprocess.Popen", return_value=mock_popen)

        compile_movie(playlist_path)

        import main

        cmd = main.subprocess.Popen.call_args[0][0]
        filter_idx = cmd.index("-filter_complex") + 1
        filter_str = cmd[filter_idx]

        assert "pad=" in filter_str

    def test_high_quality_uses_crf_20(
        self, mocker, mock_console, sample_playlist, cpu_encoding_high
    ):
        """Test that high quality uses CRF 20."""
        mock_popen = MagicMock()
        mock_popen.stdout = iter([])
        mock_popen.wait.return_value = None
        mock_popen.returncode = 0
        mocker.patch("main.subprocess.Popen", return_value=mock_popen)

        compile_movie(sample_playlist, cpu_encoding_high)

        import main

        cmd = main.subprocess.Popen.call_args[0][0]

        assert "-crf" in cmd
        crf_idx = cmd.index("-crf") + 1
        assert cmd[crf_idx] == "20"

    def test_balanced_quality_uses_crf_22(
        self, mocker, mock_console, sample_playlist, cpu_encoding_balanced
    ):
        """Test that balanced quality uses CRF 22."""
        mock_popen = MagicMock()
        mock_popen.stdout = iter([])
        mock_popen.wait.return_value = None
        mock_popen.returncode = 0
        mocker.patch("main.subprocess.Popen", return_value=mock_popen)

        compile_movie(sample_playlist, cpu_encoding_balanced)

        import main

        cmd = main.subprocess.Popen.call_args[0][0]

        crf_idx = cmd.index("-crf") + 1
        assert cmd[crf_idx] == "22"

    def test_fast_quality_uses_crf_24(
        self, mocker, mock_console, sample_playlist, cpu_encoding_fast
    ):
        """Test that fast quality uses CRF 24."""
        mock_popen = MagicMock()
        mock_popen.stdout = iter([])
        mock_popen.wait.return_value = None
        mock_popen.returncode = 0
        mocker.patch("main.subprocess.Popen", return_value=mock_popen)

        compile_movie(sample_playlist, cpu_encoding_fast)

        import main

        cmd = main.subprocess.Popen.call_args[0][0]

        crf_idx = cmd.index("-crf") + 1
        assert cmd[crf_idx] == "24"

    def test_includes_aac_audio_codec(self, mocker, mock_console, sample_playlist):
        """Test that AAC audio codec is specified."""
        mocker.patch("main._test_encoder", return_value=True)

        mock_popen = MagicMock()
        mock_popen.stdout = iter([])
        mock_popen.wait.return_value = None
        mock_popen.returncode = 0
        mocker.patch("main.subprocess.Popen", return_value=mock_popen)

        compile_movie(sample_playlist)

        import main

        cmd = main.subprocess.Popen.call_args[0][0]

        assert "-c:a" in cmd
        audio_idx = cmd.index("-c:a") + 1
        assert cmd[audio_idx] == "aac"

    def test_includes_faststart_flag(self, mocker, mock_console, sample_playlist):
        """Test that faststart flag is included for web playback."""
        mocker.patch("main._test_encoder", return_value=True)

        mock_popen = MagicMock()
        mock_popen.stdout = iter([])
        mock_popen.wait.return_value = None
        mock_popen.returncode = 0
        mocker.patch("main.subprocess.Popen", return_value=mock_popen)

        compile_movie(sample_playlist)

        import main

        cmd = main.subprocess.Popen.call_args[0][0]

        assert "-movflags" in cmd
        idx = cmd.index("-movflags") + 1
        assert "+faststart" in cmd[idx]

    def test_multiple_videos_have_transitions(
        self, mocker, mock_console, sample_playlist_multiple_videos
    ):
        """Test that multiple videos include xfade transitions."""
        mocker.patch("main._test_encoder", return_value=True)

        mock_popen = MagicMock()
        mock_popen.stdout = iter([])
        mock_popen.wait.return_value = None
        mock_popen.returncode = 0
        mocker.patch("main.subprocess.Popen", return_value=mock_popen)

        compile_movie(sample_playlist_multiple_videos)

        import main

        cmd = main.subprocess.Popen.call_args[0][0]
        filter_idx = cmd.index("-filter_complex") + 1
        filter_str = cmd[filter_idx]

        assert "xfade" in filter_str
        assert "acrossfade" in filter_str

    def test_general_exception_returns_none(
        self, mocker, mock_console, sample_playlist
    ):
        """Test handling of general exceptions."""
        mocker.patch("main._test_encoder", return_value=True)
        mocker.patch("main.subprocess.Popen", side_effect=Exception("Unexpected error"))

        result = compile_movie(sample_playlist)

        assert result is None

    def test_rotation_90_applies_transpose(self, mocker, mock_console, tmp_path):
        """Test that 90 degree rotation applies transpose=1 filter."""
        mocker.patch("main._test_encoder", return_value=True)

        playlist_data = {
            "created": "2024-01-01T00:00:00",
            "project_name": "rotation_test",
            "filters": {
                "start_date": "2024-01-01T00:00:00",
                "end_date": "2024-01-01T23:59:59",
            },
            "videos": [
                {
                    "uuid": "rotated-uuid",
                    "date": "2024-01-01T10:00:00",
                    "duration": 30.0,
                    "filename": "rotated.mov",
                    "persons": [],
                    "is_portrait": False,
                    "width": 1920,
                    "height": 1080,
                    "path": "/path/to/video.mov",
                    "rotation": 90,
                }
            ],
        }

        playlist_path = tmp_path / "playlist.json"
        playlist_path.write_text(json.dumps(playlist_data))

        mock_popen = MagicMock()
        mock_popen.stdout = iter([])
        mock_popen.wait.return_value = None
        mock_popen.returncode = 0
        mocker.patch("main.subprocess.Popen", return_value=mock_popen)

        compile_movie(playlist_path)

        import main

        cmd = main.subprocess.Popen.call_args[0][0]
        filter_idx = cmd.index("-filter_complex") + 1
        filter_str = cmd[filter_idx]

        assert "transpose=1" in filter_str

    def test_rotation_180_applies_double_transpose(
        self, mocker, mock_console, tmp_path
    ):
        """Test that 180 degree rotation applies transpose=1,transpose=1 filter."""
        mocker.patch("main._test_encoder", return_value=True)

        playlist_data = {
            "created": "2024-01-01T00:00:00",
            "project_name": "rotation_test",
            "filters": {
                "start_date": "2024-01-01T00:00:00",
                "end_date": "2024-01-01T23:59:59",
            },
            "videos": [
                {
                    "uuid": "rotated-uuid",
                    "date": "2024-01-01T10:00:00",
                    "duration": 30.0,
                    "filename": "rotated.mov",
                    "persons": [],
                    "is_portrait": False,
                    "width": 1920,
                    "height": 1080,
                    "path": "/path/to/video.mov",
                    "rotation": 180,
                }
            ],
        }

        playlist_path = tmp_path / "playlist.json"
        playlist_path.write_text(json.dumps(playlist_data))

        mock_popen = MagicMock()
        mock_popen.stdout = iter([])
        mock_popen.wait.return_value = None
        mock_popen.returncode = 0
        mocker.patch("main.subprocess.Popen", return_value=mock_popen)

        compile_movie(playlist_path)

        import main

        cmd = main.subprocess.Popen.call_args[0][0]
        filter_idx = cmd.index("-filter_complex") + 1
        filter_str = cmd[filter_idx]

        assert "transpose=1,transpose=1" in filter_str

    def test_rotation_270_applies_transpose_2(self, mocker, mock_console, tmp_path):
        """Test that 270 degree rotation applies transpose=2 filter."""
        mocker.patch("main._test_encoder", return_value=True)

        playlist_data = {
            "created": "2024-01-01T00:00:00",
            "project_name": "rotation_test",
            "filters": {
                "start_date": "2024-01-01T00:00:00",
                "end_date": "2024-01-01T23:59:59",
            },
            "videos": [
                {
                    "uuid": "rotated-uuid",
                    "date": "2024-01-01T10:00:00",
                    "duration": 30.0,
                    "filename": "rotated.mov",
                    "persons": [],
                    "is_portrait": False,
                    "width": 1920,
                    "height": 1080,
                    "path": "/path/to/video.mov",
                    "rotation": 270,
                }
            ],
        }

        playlist_path = tmp_path / "playlist.json"
        playlist_path.write_text(json.dumps(playlist_data))

        mock_popen = MagicMock()
        mock_popen.stdout = iter([])
        mock_popen.wait.return_value = None
        mock_popen.returncode = 0
        mocker.patch("main.subprocess.Popen", return_value=mock_popen)

        compile_movie(playlist_path)

        import main

        cmd = main.subprocess.Popen.call_args[0][0]
        filter_idx = cmd.index("-filter_complex") + 1
        filter_str = cmd[filter_idx]

        assert "transpose=2" in filter_str

    def test_no_rotation_no_transpose(self, mocker, mock_console, sample_playlist):
        """Test that videos without rotation don't have transpose filter."""
        mocker.patch("main._test_encoder", return_value=True)

        mock_popen = MagicMock()
        mock_popen.stdout = iter([])
        mock_popen.wait.return_value = None
        mock_popen.returncode = 0
        mocker.patch("main.subprocess.Popen", return_value=mock_popen)

        compile_movie(sample_playlist)

        import main

        cmd = main.subprocess.Popen.call_args[0][0]
        filter_idx = cmd.index("-filter_complex") + 1
        filter_str = cmd[filter_idx]

        assert "transpose" not in filter_str

    def test_portrait_with_rotation(self, mocker, mock_console, tmp_path):
        """Test that portrait videos with rotation apply both blur and transpose."""
        mocker.patch("main._test_encoder", return_value=True)

        playlist_data = {
            "created": "2024-01-01T00:00:00",
            "project_name": "portrait_rotation_test",
            "filters": {
                "start_date": "2024-01-01T00:00:00",
                "end_date": "2024-01-01T23:59:59",
            },
            "videos": [
                {
                    "uuid": "portrait-rotated-uuid",
                    "date": "2024-01-01T10:00:00",
                    "duration": 30.0,
                    "filename": "portrait_rotated.mov",
                    "persons": [],
                    "is_portrait": True,
                    "width": 1080,
                    "height": 1920,
                    "path": "/path/to/video.mov",
                    "rotation": 90,
                }
            ],
        }

        playlist_path = tmp_path / "playlist.json"
        playlist_path.write_text(json.dumps(playlist_data))

        mock_popen = MagicMock()
        mock_popen.stdout = iter([])
        mock_popen.wait.return_value = None
        mock_popen.returncode = 0
        mocker.patch("main.subprocess.Popen", return_value=mock_popen)

        compile_movie(playlist_path)

        import main

        cmd = main.subprocess.Popen.call_args[0][0]
        filter_idx = cmd.index("-filter_complex") + 1
        filter_str = cmd[filter_idx]

        # Should have both blur (portrait) and transpose (rotation)
        assert "gblur" in filter_str
        assert "transpose=1" in filter_str
