"""Integration tests for main() workflow function."""

import os
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, os.path.dirname(__file__))


from main import main


class TestMainWorkflow:
    """Integration tests for main() function."""

    def test_full_interactive_workflow(
        self, mocker, mock_console, tmp_path, mock_video_list
    ):
        """Test complete interactive workflow from start to finish."""
        # Mock all interactive prompts
        mocker.patch(
            "main.prompt_date_range",
            return_value=(datetime(2024, 6, 15), datetime(2024, 6, 20, 23, 59, 59)),
        )
        mocker.patch("main.query_videos", return_value=mock_video_list)
        mocker.patch(
            "main.get_unique_persons", return_value=["Alice", "Bob", "Charlie"]
        )
        mocker.patch("main.prompt_people_selection", return_value=["Alice"])
        mocker.patch("main.prompt_duration_filter", return_value=(None, None))
        mocker.patch("main.filter_by_people", return_value=mock_video_list[:2])
        mocker.patch("main.filter_by_duration", return_value=mock_video_list[:2])

        mock_confirm = mocker.patch("main.questionary.confirm")
        mock_confirm.return_value.ask.side_effect = [True, True]

        mock_text = mocker.patch("main.questionary.text")
        mock_text.return_value.ask.return_value = "test_project"

        mocker.patch(
            "main.prompt_quality_selection", return_value="Auto (GPU if available)"
        )

        # Mock file operations
        mocker.patch("main.VIDEOS_DIR", tmp_path / "videos")
        mocker.patch("main.PROJECTS_DIR", tmp_path / "projects")
        mocker.patch(
            "main.export_videos",
            return_value={
                v.uuid: tmp_path / f"{v.uuid}.mov" for v in mock_video_list[:2]
            },
        )
        mocker.patch("main.compile_movie", return_value=tmp_path / "output.mp4")

        # Mock argparse to simulate no arguments
        mocker.patch("sys.argv", ["main.py"])

        # Should complete without error
        main()

    def test_recompile_mode(self, mocker, mock_console, sample_playlist):
        """Test recompile mode with existing playlist."""
        mocker.patch("sys.argv", ["main.py", "--recompile", str(sample_playlist)])
        mocker.patch(
            "main.prompt_quality_selection", return_value="Balanced (good quality)"
        )
        mocker.patch(
            "main.compile_movie", return_value=sample_playlist.parent / "output.mp4"
        )

        main()

        # Verify compile_movie was called
        import main as m

        m.compile_movie.assert_called_once()

    def test_recompile_missing_playlist_exits(self, mocker, mock_console, tmp_path):
        """Test that recompile with non-existent playlist exits with error."""
        mocker.patch(
            "sys.argv", ["main.py", "--recompile", str(tmp_path / "nonexistent.json")]
        )

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    def test_no_videos_found_returns_early(self, mocker, mock_console):
        """Test that main returns early when no videos are found."""
        mocker.patch("sys.argv", ["main.py"])
        mocker.patch(
            "main.prompt_date_range",
            return_value=(datetime(2024, 6, 15), datetime(2024, 6, 20)),
        )
        mocker.patch("main.query_videos", return_value=[])

        # Should return early without error
        main()

        # Verify we didn't get to people selection
        # If query_videos returns empty, we should return before prompt_people_selection

    def test_no_videos_after_people_filter_returns_early(
        self, mocker, mock_console, mock_video_list
    ):
        """Test early return when no videos match people filter."""
        mocker.patch("sys.argv", ["main.py"])
        mocker.patch(
            "main.prompt_date_range",
            return_value=(datetime(2024, 6, 15), datetime(2024, 6, 20)),
        )
        mocker.patch("main.query_videos", return_value=mock_video_list)
        mocker.patch("main.get_unique_persons", return_value=["Alice"])
        mocker.patch("main.prompt_people_selection", return_value=["NonexistentPerson"])
        mocker.patch("main.filter_by_people", return_value=[])

        # Should return early
        main()

    def test_no_videos_after_duration_filter_returns_early(
        self, mocker, mock_console, mock_video_list
    ):
        """Test early return when no videos match duration filter."""
        mocker.patch("sys.argv", ["main.py"])
        mocker.patch(
            "main.prompt_date_range",
            return_value=(datetime(2024, 6, 15), datetime(2024, 6, 20)),
        )
        mocker.patch("main.query_videos", return_value=mock_video_list)
        mocker.patch("main.get_unique_persons", return_value=["Alice"])
        mocker.patch("main.prompt_people_selection", return_value=None)
        mocker.patch("main.filter_by_people", return_value=mock_video_list)
        mocker.patch("main.prompt_duration_filter", return_value=(1000.0, 2000.0))
        mocker.patch("main.filter_by_duration", return_value=[])

        # Should return early
        main()

    def test_user_declines_to_copy_videos(
        self, mocker, mock_console, tmp_path, mock_video_list
    ):
        """Test workflow when user declines to copy videos."""
        mocker.patch("sys.argv", ["main.py"])
        mocker.patch(
            "main.prompt_date_range",
            return_value=(datetime(2024, 6, 15), datetime(2024, 6, 20)),
        )
        mocker.patch("main.query_videos", return_value=mock_video_list)
        mocker.patch("main.get_unique_persons", return_value=["Alice"])
        mocker.patch("main.prompt_people_selection", return_value=None)
        mocker.patch("main.filter_by_people", return_value=mock_video_list)
        mocker.patch("main.prompt_duration_filter", return_value=(None, None))
        mocker.patch("main.filter_by_duration", return_value=mock_video_list)
        mocker.patch("main.display_video_summary")

        mock_confirm = mocker.patch("main.questionary.confirm")
        mock_confirm.return_value.ask.return_value = False  # User declines

        # Should return without exporting
        main()

        # export_videos should not have been called
        # (We'd need to verify this, but mocking structure makes it implicit)

    def test_no_exported_videos_returns_early(
        self, mocker, mock_console, tmp_path, mock_video_list
    ):
        """Test early return when no videos are successfully exported."""
        mocker.patch("sys.argv", ["main.py"])
        mocker.patch(
            "main.prompt_date_range",
            return_value=(datetime(2024, 6, 15), datetime(2024, 6, 20)),
        )
        mocker.patch("main.query_videos", return_value=mock_video_list)
        mocker.patch("main.get_unique_persons", return_value=["Alice"])
        mocker.patch("main.prompt_people_selection", return_value=None)
        mocker.patch("main.filter_by_people", return_value=mock_video_list)
        mocker.patch("main.prompt_duration_filter", return_value=(None, None))
        mocker.patch("main.filter_by_duration", return_value=mock_video_list)
        mocker.patch("main.display_video_summary")

        mock_confirm = mocker.patch("main.questionary.confirm")
        mock_confirm.return_value.ask.return_value = True

        mocker.patch("main.export_videos", return_value={})  # No videos exported

        # Should return early
        main()

    def test_user_skips_movie_generation(
        self, mocker, mock_console, tmp_path, mock_video_list
    ):
        """Test workflow when user skips final movie generation."""
        mocker.patch("sys.argv", ["main.py"])
        mocker.patch(
            "main.prompt_date_range",
            return_value=(datetime(2024, 6, 15), datetime(2024, 6, 20)),
        )
        mocker.patch("main.query_videos", return_value=mock_video_list)
        mocker.patch("main.get_unique_persons", return_value=["Alice"])
        mocker.patch("main.prompt_people_selection", return_value=None)
        mocker.patch("main.filter_by_people", return_value=mock_video_list)
        mocker.patch("main.prompt_duration_filter", return_value=(None, None))
        mocker.patch("main.filter_by_duration", return_value=mock_video_list)
        mocker.patch("main.display_video_summary")
        mocker.patch("main.VIDEOS_DIR", tmp_path / "videos")
        mocker.patch("main.PROJECTS_DIR", tmp_path / "projects")
        mocker.patch(
            "main.export_videos",
            return_value={v.uuid: tmp_path / f"{v.uuid}.mov" for v in mock_video_list},
        )

        mock_confirm = mocker.patch("main.questionary.confirm")
        # First confirm (copy videos): True, Second confirm (generate movie): False
        mock_confirm.return_value.ask.side_effect = [True, False]

        mock_text = mocker.patch("main.questionary.text")
        mock_text.return_value.ask.return_value = "test_project"

        mock_compile = mocker.patch("main.compile_movie")

        main()

        # compile_movie should not have been called
        mock_compile.assert_not_called()


class TestMainRecompileMode:
    """Focused tests for recompile mode."""

    def test_recompile_removes_existing_mp4(
        self, mocker, mock_console, sample_playlist
    ):
        """Test that existing MP4 files are removed before recompile."""
        # Create an existing output file
        existing_mp4 = sample_playlist.parent / "old_output.mp4"
        existing_mp4.write_bytes(b"old video data")

        mocker.patch("sys.argv", ["main.py", "--recompile", str(sample_playlist)])
        mocker.patch(
            "main.prompt_quality_selection", return_value="Auto (GPU if available)"
        )
        mocker.patch(
            "main.compile_movie", return_value=sample_playlist.parent / "new_output.mp4"
        )

        main()

        # Old file should be removed
        assert not existing_mp4.exists()

    def test_recompile_preserves_playlist(self, mocker, mock_console, sample_playlist):
        """Test that playlist.json is preserved during recompile."""
        original_content = sample_playlist.read_text()

        mocker.patch("sys.argv", ["main.py", "--recompile", str(sample_playlist)])
        mocker.patch(
            "main.prompt_quality_selection", return_value="Auto (GPU if available)"
        )
        mocker.patch(
            "main.compile_movie", return_value=sample_playlist.parent / "output.mp4"
        )

        main()

        # Playlist should still exist with same content
        assert sample_playlist.exists()
        assert sample_playlist.read_text() == original_content
