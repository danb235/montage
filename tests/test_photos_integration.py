"""Tests for Photos library integration functions with osxphotos mocking."""

import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, os.path.dirname(__file__))

from conftest import create_mock_video

from main import export_videos, query_videos


class TestQueryVideos:
    """Tests for query_videos() function."""

    def test_queries_photos_library_with_correct_params(self, mocker, mock_console):
        """Test that PhotosDB is queried with correct parameters."""
        mock_photosdb = MagicMock()
        mock_photosdb.photos.return_value = []
        mocker.patch("main.osxphotos.PhotosDB", return_value=mock_photosdb)

        start = datetime(2024, 6, 15)
        end = datetime(2024, 6, 20)

        query_videos(start, end)

        mock_photosdb.photos.assert_called_once_with(
            movies=True, images=False, from_date=start, to_date=end
        )

    def test_returns_videos_from_photos_library(
        self, mocker, mock_console, mock_video_list
    ):
        """Test that videos from PhotosDB are returned."""
        mock_photosdb = MagicMock()
        mock_photosdb.photos.return_value = mock_video_list
        mocker.patch("main.osxphotos.PhotosDB", return_value=mock_photosdb)

        start = datetime(2024, 6, 15)
        end = datetime(2024, 6, 20)

        videos = query_videos(start, end)

        assert len(videos) == len(mock_video_list)

    def test_filters_trashed_videos(self, mocker, mock_console):
        """Test that trashed videos are excluded from results."""
        videos = [
            create_mock_video(uuid="v1", intrash=False),
            create_mock_video(uuid="v2", intrash=True),  # Should be excluded
            create_mock_video(uuid="v3", intrash=False),
        ]

        mock_photosdb = MagicMock()
        mock_photosdb.photos.return_value = videos
        mocker.patch("main.osxphotos.PhotosDB", return_value=mock_photosdb)

        result = query_videos(datetime(2024, 1, 1), datetime(2024, 12, 31))

        assert len(result) == 2
        assert all(not v.intrash for v in result)
        uuids = [v.uuid for v in result]
        assert "v1" in uuids
        assert "v2" not in uuids
        assert "v3" in uuids

    def test_returns_empty_for_no_videos(self, mocker, mock_console):
        """Test behavior when no videos are found."""
        mock_photosdb = MagicMock()
        mock_photosdb.photos.return_value = []
        mocker.patch("main.osxphotos.PhotosDB", return_value=mock_photosdb)

        result = query_videos(datetime(2024, 1, 1), datetime(2024, 12, 31))

        assert result == []

    def test_all_trashed_returns_empty(self, mocker, mock_console):
        """Test when all videos are in trash."""
        videos = [
            create_mock_video(uuid="v1", intrash=True),
            create_mock_video(uuid="v2", intrash=True),
        ]

        mock_photosdb = MagicMock()
        mock_photosdb.photos.return_value = videos
        mocker.patch("main.osxphotos.PhotosDB", return_value=mock_photosdb)

        result = query_videos(datetime(2024, 1, 1), datetime(2024, 12, 31))

        assert result == []


class TestExportVideos:
    """Tests for export_videos() function."""

    def test_exports_video_to_cache(self, mocker, mock_console, tmp_path):
        """Test successful video export to cache directory."""
        video = create_mock_video(uuid="test-uuid")
        exported_file = tmp_path / "exported_video.mov"
        exported_file.write_bytes(b"fake video data")
        video.export.return_value = [str(exported_file)]

        videos_dir = tmp_path / "videos"
        mocker.patch("main.VIDEOS_DIR", videos_dir)

        result = export_videos([video])

        assert "test-uuid" in result
        assert result["test-uuid"].name == "test-uuid.mov"

    def test_skips_cached_videos(self, mocker, mock_console, tmp_path):
        """Test that already cached videos are skipped."""
        video = create_mock_video(uuid="cached-uuid")

        videos_dir = tmp_path / "videos"
        videos_dir.mkdir()
        cached_file = videos_dir / "cached-uuid.mov"
        cached_file.write_bytes(b"already cached video")

        mocker.patch("main.VIDEOS_DIR", videos_dir)

        result = export_videos([video])

        # Should not call export since file already exists
        video.export.assert_not_called()
        assert "cached-uuid" in result

    def test_handles_export_failure(self, mocker, mock_console, tmp_path):
        """Test handling when video export fails (returns empty list)."""
        video = create_mock_video(uuid="fail-uuid")
        video.export.return_value = []  # Export failed

        mocker.patch("main.VIDEOS_DIR", tmp_path / "videos")

        result = export_videos([video])

        assert "fail-uuid" not in result

    def test_handles_export_exception(self, mocker, mock_console, tmp_path):
        """Test handling when video export raises exception."""
        video = create_mock_video(uuid="error-uuid")
        video.export.side_effect = Exception("Export error")

        mocker.patch("main.VIDEOS_DIR", tmp_path / "videos")

        result = export_videos([video])

        assert "error-uuid" not in result

    def test_creates_videos_directory(self, mocker, mock_console, tmp_path):
        """Test that videos directory is created if it doesn't exist."""
        video = create_mock_video(uuid="test-uuid")
        exported_file = tmp_path / "exported.mov"
        exported_file.write_bytes(b"data")
        video.export.return_value = [str(exported_file)]

        videos_dir = tmp_path / "videos"
        assert not videos_dir.exists()

        mocker.patch("main.VIDEOS_DIR", videos_dir)

        export_videos([video])

        assert videos_dir.exists()

    def test_exports_multiple_videos(self, mocker, mock_console, tmp_path):
        """Test exporting multiple videos."""
        videos = [
            create_mock_video(uuid="uuid-1"),
            create_mock_video(uuid="uuid-2"),
        ]

        videos_dir = tmp_path / "videos"
        mocker.patch("main.VIDEOS_DIR", videos_dir)

        # Mock Progress to avoid Rich internals issues with MagicMock
        mock_progress = MagicMock()
        mock_progress.__enter__ = MagicMock(return_value=mock_progress)
        mock_progress.__exit__ = MagicMock(return_value=False)
        mocker.patch("main.Progress", return_value=mock_progress)

        for i, video in enumerate(videos):
            exported_file = tmp_path / f"video{i}.mov"
            exported_file.write_bytes(b"data")
            video.export.return_value = [str(exported_file)]

        result = export_videos(videos)

        assert len(result) == 2
        assert "uuid-1" in result
        assert "uuid-2" in result

    def test_videos_sorted_by_date_before_export(self, mocker, mock_console, tmp_path):
        """Test that videos are sorted by date before exporting."""
        video1 = create_mock_video(uuid="uuid-1", date=datetime(2024, 6, 20))
        video2 = create_mock_video(uuid="uuid-2", date=datetime(2024, 6, 10))
        videos = [video1, video2]  # Out of order

        videos_dir = tmp_path / "videos"
        mocker.patch("main.VIDEOS_DIR", videos_dir)

        # Mock Progress to avoid Rich internals issues with MagicMock
        mock_progress = MagicMock()
        mock_progress.__enter__ = MagicMock(return_value=mock_progress)
        mock_progress.__exit__ = MagicMock(return_value=False)
        mocker.patch("main.Progress", return_value=mock_progress)

        export_order = []

        # Set up side effects to track export order
        def make_export_tracker(uuid):
            def track_export(*a, **k):
                export_order.append(uuid)
                return []

            return track_export

        video1.export.side_effect = make_export_tracker("uuid-1")
        video2.export.side_effect = make_export_tracker("uuid-2")

        export_videos(videos)

        # Should be sorted by date, so uuid-2 (earlier date) should be first
        if len(export_order) >= 2:
            assert export_order[0] == "uuid-2"
            assert export_order[1] == "uuid-1"
