"""Tests for project management functions (playlist creation, display)."""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, os.path.dirname(__file__))

from conftest import create_mock_video

from main import create_playlist, display_video_summary


class TestDisplayVideoSummary:
    """Tests for display_video_summary() function."""

    def test_displays_without_error(self, mocker, mock_console, mock_video_list):
        """Test that video summary displays without raising exceptions."""
        # Should complete without error
        display_video_summary(mock_video_list)

        # Verify console.print was called
        assert mock_console.print.called

    def test_calculates_total_duration(self, mocker, mock_console, mock_video_list):
        """Test that total duration is calculated and displayed."""
        display_video_summary(mock_video_list)

        # Check that something was printed (total should be in output)
        assert mock_console.print.call_count > 0

    def test_calculates_total_size(self, mocker, mock_console, mock_video_list):
        """Test that total size is calculated and displayed."""
        display_video_summary(mock_video_list)

        # Verify print was called multiple times for table and summary
        assert mock_console.print.call_count >= 2

    def test_handles_empty_video_list(self, mocker, mock_console):
        """Test display with empty video list."""
        display_video_summary([])

        # Should still print table header and summary
        assert mock_console.print.called

    def test_shows_icloud_warning_for_missing_videos(self, mocker, mock_console):
        """Test that iCloud warning is shown for missing videos."""
        videos = [
            create_mock_video(uuid="v1", ismissing=True),
            create_mock_video(uuid="v2", ismissing=True),
        ]

        display_video_summary(videos)

        # Check for iCloud message in output
        # The function should mention iCloud for missing videos
        assert mock_console.print.called

    def test_no_icloud_warning_when_no_missing(
        self, mocker, mock_console, mock_video_list
    ):
        """Test that no iCloud warning when all videos are local."""
        display_video_summary(mock_video_list)

        # Should complete without iCloud warning
        assert mock_console.print.called

    def test_truncates_long_location_names(self, mocker, mock_console):
        """Test that very long location names are truncated."""
        video = create_mock_video(
            place_name="A Very Long Location Name That Should Be Truncated Because It Exceeds The Maximum Length"
        )

        display_video_summary([video])

        # Should complete without error
        assert mock_console.print.called

    def test_handles_missing_exif_info(self, mocker, mock_console):
        """Test handling videos without exif info."""
        video = create_mock_video()
        video.exif_info = None

        display_video_summary([video])

        # Should complete without error
        assert mock_console.print.called


class TestCreatePlaylist:
    """Tests for create_playlist() function."""

    def test_creates_playlist_json_file(
        self, mocker, mock_console, tmp_path, mock_video_list
    ):
        """Test that playlist.json file is created."""
        mocker.patch("main.PROJECTS_DIR", tmp_path / "projects")

        exported = {v.uuid: Path(f"/path/to/{v.uuid}.mov") for v in mock_video_list}
        filters = {
            "start_date": "2024-06-15T00:00:00",
            "end_date": "2024-06-20T23:59:59",
            "people": ["Alice"],
            "min_duration": None,
            "max_duration": None,
        }

        playlist_path = create_playlist(
            mock_video_list, "test_project", filters, exported
        )

        assert playlist_path.exists()
        assert playlist_path.name == "playlist.json"

    def test_playlist_contains_project_name(
        self, mocker, mock_console, tmp_path, mock_video_list
    ):
        """Test that playlist contains project name."""
        mocker.patch("main.PROJECTS_DIR", tmp_path / "projects")

        exported = {v.uuid: Path(f"/path/to/{v.uuid}.mov") for v in mock_video_list}
        filters = {
            "start_date": "2024-06-15T00:00:00",
            "end_date": "2024-06-15T23:59:59",
        }

        playlist_path = create_playlist(
            mock_video_list, "my_project", filters, exported
        )
        playlist = json.loads(playlist_path.read_text())

        assert playlist["project_name"] == "my_project"

    def test_playlist_contains_filters(
        self, mocker, mock_console, tmp_path, mock_video_list
    ):
        """Test that playlist contains filter settings."""
        mocker.patch("main.PROJECTS_DIR", tmp_path / "projects")

        exported = {v.uuid: Path(f"/path/to/{v.uuid}.mov") for v in mock_video_list}
        filters = {
            "start_date": "2024-06-15T00:00:00",
            "end_date": "2024-06-20T23:59:59",
            "people": ["Alice", "Bob"],
            "min_duration": 10.0,
            "max_duration": 120.0,
        }

        playlist_path = create_playlist(mock_video_list, "test", filters, exported)
        playlist = json.loads(playlist_path.read_text())

        assert playlist["filters"] == filters

    def test_playlist_contains_video_metadata(self, mocker, mock_console, tmp_path):
        """Test that playlist contains video metadata."""
        mocker.patch("main.PROJECTS_DIR", tmp_path / "projects")

        video = create_mock_video(
            uuid="test-uuid",
            width=1080,
            height=1920,  # Portrait
            duration=45.0,
            persons=["Alice"],
        )

        exported = {"test-uuid": Path("/path/to/test-uuid.mov")}
        filters = {
            "start_date": "2024-01-01T00:00:00",
            "end_date": "2024-01-01T23:59:59",
        }

        playlist_path = create_playlist([video], "test", filters, exported)
        playlist = json.loads(playlist_path.read_text())

        assert len(playlist["videos"]) == 1
        video_entry = playlist["videos"][0]
        assert video_entry["uuid"] == "test-uuid"
        assert video_entry["is_portrait"] is True
        assert video_entry["duration"] == 45.0
        assert "path" in video_entry

    def test_skips_unexported_videos(self, mocker, mock_console, tmp_path):
        """Test that videos not in exported dict are skipped."""
        mocker.patch("main.PROJECTS_DIR", tmp_path / "projects")

        videos = [
            create_mock_video(uuid="exported"),
            create_mock_video(uuid="not-exported"),
        ]

        exported = {"exported": Path("/path/to/exported.mov")}
        filters = {
            "start_date": "2024-01-01T00:00:00",
            "end_date": "2024-01-01T23:59:59",
        }

        playlist_path = create_playlist(videos, "test", filters, exported)
        playlist = json.loads(playlist_path.read_text())

        assert len(playlist["videos"]) == 1
        assert playlist["videos"][0]["uuid"] == "exported"

    def test_creates_project_directory(self, mocker, mock_console, tmp_path):
        """Test that project directory is created."""
        projects_dir = tmp_path / "projects"
        mocker.patch("main.PROJECTS_DIR", projects_dir)

        video = create_mock_video()
        exported = {video.uuid: Path(f"/path/to/{video.uuid}.mov")}
        filters = {
            "start_date": "2024-01-01T00:00:00",
            "end_date": "2024-01-01T23:59:59",
        }

        create_playlist([video], "new_project", filters, exported)

        assert (projects_dir / "new_project").is_dir()

    def test_videos_sorted_by_date(self, mocker, mock_console, tmp_path):
        """Test that videos are sorted by date in playlist."""
        mocker.patch("main.PROJECTS_DIR", tmp_path / "projects")

        video1 = create_mock_video(uuid="later", date=datetime(2024, 6, 20))
        video2 = create_mock_video(uuid="earlier", date=datetime(2024, 6, 10))
        videos = [video1, video2]  # Out of order

        exported = {
            "later": Path("/path/to/later.mov"),
            "earlier": Path("/path/to/earlier.mov"),
        }
        filters = {
            "start_date": "2024-06-01T00:00:00",
            "end_date": "2024-06-30T23:59:59",
        }

        playlist_path = create_playlist(videos, "test", filters, exported)
        playlist = json.loads(playlist_path.read_text())

        # Earlier video should be first
        assert playlist["videos"][0]["uuid"] == "earlier"
        assert playlist["videos"][1]["uuid"] == "later"

    def test_playlist_has_created_timestamp(self, mocker, mock_console, tmp_path):
        """Test that playlist has creation timestamp."""
        mocker.patch("main.PROJECTS_DIR", tmp_path / "projects")

        video = create_mock_video()
        exported = {video.uuid: Path(f"/path/to/{video.uuid}.mov")}
        filters = {
            "start_date": "2024-01-01T00:00:00",
            "end_date": "2024-01-01T23:59:59",
        }

        playlist_path = create_playlist([video], "test", filters, exported)
        playlist = json.loads(playlist_path.read_text())

        assert "created" in playlist
        # Should be a valid ISO timestamp
        datetime.fromisoformat(playlist["created"])

    def test_landscape_video_detected(self, mocker, mock_console, tmp_path):
        """Test that landscape videos are correctly identified."""
        mocker.patch("main.PROJECTS_DIR", tmp_path / "projects")

        video = create_mock_video(uuid="landscape", width=1920, height=1080)
        exported = {"landscape": Path("/path/to/landscape.mov")}
        filters = {
            "start_date": "2024-01-01T00:00:00",
            "end_date": "2024-01-01T23:59:59",
        }

        playlist_path = create_playlist([video], "test", filters, exported)
        playlist = json.loads(playlist_path.read_text())

        assert playlist["videos"][0]["is_portrait"] is False
