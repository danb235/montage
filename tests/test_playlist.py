"""Tests for playlist creation functions."""

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import create_playlist
from tests.conftest import create_mock_video


class TestCreatePlaylist:
    """Tests for create_playlist() function."""

    @pytest.fixture
    def mock_videos(self):
        """Create a list of mock videos for testing."""
        return [
            create_mock_video(
                uuid="video-001",
                date=datetime(2024, 6, 15, 10, 0),
                duration=30.0,
                persons=["Alice"],
                width=1920,
                height=1080,
            ),
            create_mock_video(
                uuid="video-002",
                date=datetime(2024, 6, 15, 14, 0),
                duration=45.0,
                persons=["Bob"],
                width=1080,
                height=1920,  # Portrait
            ),
        ]

    @pytest.fixture
    def mock_exported(self, tmp_path, mock_videos):
        """Create mock exported paths."""
        return {v.uuid: tmp_path / f"{v.uuid}.mov" for v in mock_videos}

    @pytest.fixture
    def mock_filters(self):
        """Create mock filter dict with ISO format strings."""
        return {
            "start_date": "2024-06-15T00:00:00",
            "end_date": "2024-06-15T23:59:59",
            "people": ["Alice", "Bob"],
            "min_duration": None,
            "max_duration": None,
        }

    def test_creates_playlist_json(
        self, mocker, mock_console, tmp_path, mock_videos, mock_exported, mock_filters
    ):
        """Test that playlist.json is created."""
        mocker.patch("main.PROJECTS_DIR", tmp_path)

        playlist_path = create_playlist(
            mock_videos, "test_project", mock_filters, mock_exported
        )

        assert playlist_path.exists()
        assert playlist_path.name == "playlist.json"

    def test_playlist_contains_videos(
        self, mocker, mock_console, tmp_path, mock_videos, mock_exported, mock_filters
    ):
        """Test that playlist contains video entries."""
        mocker.patch("main.PROJECTS_DIR", tmp_path)

        playlist_path = create_playlist(
            mock_videos, "test_project", mock_filters, mock_exported
        )

        with open(playlist_path) as f:
            playlist = json.load(f)

        assert len(playlist["videos"]) == 2

    def test_videos_sorted_by_date(
        self, mocker, mock_console, tmp_path, mock_videos, mock_exported, mock_filters
    ):
        """Test that videos are sorted by date in playlist."""
        mocker.patch("main.PROJECTS_DIR", tmp_path)

        # Reverse the order before passing
        reversed_videos = list(reversed(mock_videos))

        playlist_path = create_playlist(
            reversed_videos, "test_project", mock_filters, mock_exported
        )

        with open(playlist_path) as f:
            playlist = json.load(f)

        # First video should be earlier date
        assert playlist["videos"][0]["uuid"] == "video-001"
        assert playlist["videos"][1]["uuid"] == "video-002"

    def test_rotation_defaults_to_zero(
        self, mocker, mock_console, tmp_path, mock_videos, mock_exported, mock_filters
    ):
        """Test that rotation defaults to 0 when not specified."""
        mocker.patch("main.PROJECTS_DIR", tmp_path)

        playlist_path = create_playlist(
            mock_videos, "test_project", mock_filters, mock_exported
        )

        with open(playlist_path) as f:
            playlist = json.load(f)

        for video in playlist["videos"]:
            assert video["rotation"] == 0

    def test_rotation_from_rotation_map(
        self, mocker, mock_console, tmp_path, mock_videos, mock_exported, mock_filters
    ):
        """Test that rotation values are saved from rotation_map."""
        mocker.patch("main.PROJECTS_DIR", tmp_path)

        rotation_map = {"video-001": 90, "video-002": 180}

        playlist_path = create_playlist(
            mock_videos, "test_project", mock_filters, mock_exported, rotation_map
        )

        with open(playlist_path) as f:
            playlist = json.load(f)

        video_rotations = {v["uuid"]: v["rotation"] for v in playlist["videos"]}
        assert video_rotations["video-001"] == 90
        assert video_rotations["video-002"] == 180

    def test_partial_rotation_map(
        self, mocker, mock_console, tmp_path, mock_videos, mock_exported, mock_filters
    ):
        """Test that only videos in rotation_map get rotation values."""
        mocker.patch("main.PROJECTS_DIR", tmp_path)

        # Only one video has rotation
        rotation_map = {"video-001": 270}

        playlist_path = create_playlist(
            mock_videos, "test_project", mock_filters, mock_exported, rotation_map
        )

        with open(playlist_path) as f:
            playlist = json.load(f)

        video_rotations = {v["uuid"]: v["rotation"] for v in playlist["videos"]}
        assert video_rotations["video-001"] == 270
        assert video_rotations["video-002"] == 0  # Default

    def test_empty_rotation_map(
        self, mocker, mock_console, tmp_path, mock_videos, mock_exported, mock_filters
    ):
        """Test that empty rotation_map results in zero rotation."""
        mocker.patch("main.PROJECTS_DIR", tmp_path)

        playlist_path = create_playlist(
            mock_videos, "test_project", mock_filters, mock_exported, {}
        )

        with open(playlist_path) as f:
            playlist = json.load(f)

        for video in playlist["videos"]:
            assert video["rotation"] == 0

    def test_none_rotation_map(
        self, mocker, mock_console, tmp_path, mock_videos, mock_exported, mock_filters
    ):
        """Test that None rotation_map results in zero rotation."""
        mocker.patch("main.PROJECTS_DIR", tmp_path)

        playlist_path = create_playlist(
            mock_videos, "test_project", mock_filters, mock_exported, None
        )

        with open(playlist_path) as f:
            playlist = json.load(f)

        for video in playlist["videos"]:
            assert video["rotation"] == 0

    def test_portrait_detection(
        self, mocker, mock_console, tmp_path, mock_videos, mock_exported, mock_filters
    ):
        """Test that portrait videos are correctly identified."""
        mocker.patch("main.PROJECTS_DIR", tmp_path)

        playlist_path = create_playlist(
            mock_videos, "test_project", mock_filters, mock_exported
        )

        with open(playlist_path) as f:
            playlist = json.load(f)

        video_portrait = {v["uuid"]: v["is_portrait"] for v in playlist["videos"]}
        assert video_portrait["video-001"] is False  # 1920x1080 landscape
        assert video_portrait["video-002"] is True  # 1080x1920 portrait

    def test_playlist_includes_filters(
        self, mocker, mock_console, tmp_path, mock_videos, mock_exported, mock_filters
    ):
        """Test that filters are saved in playlist."""
        mocker.patch("main.PROJECTS_DIR", tmp_path)

        playlist_path = create_playlist(
            mock_videos, "test_project", mock_filters, mock_exported
        )

        with open(playlist_path) as f:
            playlist = json.load(f)

        assert "filters" in playlist
        assert playlist["filters"]["people"] == ["Alice", "Bob"]

    def test_playlist_includes_project_name(
        self, mocker, mock_console, tmp_path, mock_videos, mock_exported, mock_filters
    ):
        """Test that project name is saved in playlist."""
        mocker.patch("main.PROJECTS_DIR", tmp_path)

        playlist_path = create_playlist(
            mock_videos, "my_special_project", mock_filters, mock_exported
        )

        with open(playlist_path) as f:
            playlist = json.load(f)

        assert playlist["project_name"] == "my_special_project"
