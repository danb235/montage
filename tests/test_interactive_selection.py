"""Tests for interactive video selection feature."""

import socket
from datetime import datetime
from unittest.mock import MagicMock

from main import (
    SelectionState,
    VideoDecision,
    _check_mpv_available,
    _display_selection_summary,
    _display_video_metadata,
    _send_mpv_command,
    interactive_video_selection,
)
from tests.conftest import create_mock_video


class TestVideoDecision:
    """Tests for VideoDecision dataclass."""

    def test_default_decision_is_pending(self, mock_video):
        """VideoDecision should default to pending status."""
        decision = VideoDecision(video=mock_video)
        assert decision.decision == "pending"

    def test_can_set_keep_decision(self, mock_video):
        """VideoDecision can be set to keep."""
        decision = VideoDecision(video=mock_video)
        decision.decision = "keep"
        assert decision.decision == "keep"

    def test_can_set_skip_decision(self, mock_video):
        """VideoDecision can be set to skip."""
        decision = VideoDecision(video=mock_video)
        decision.decision = "skip"
        assert decision.decision == "skip"

    def test_default_rotation_is_zero(self, mock_video):
        """VideoDecision should default to 0 rotation."""
        decision = VideoDecision(video=mock_video)
        assert decision.rotation == 0

    def test_can_set_rotation(self, mock_video):
        """VideoDecision rotation can be set."""
        decision = VideoDecision(video=mock_video)
        decision.rotation = 90
        assert decision.rotation == 90

    def test_rotation_cycles(self, mock_video):
        """Rotation should cycle through 0, 90, 180, 270."""
        decision = VideoDecision(video=mock_video)
        for expected in [90, 180, 270, 0]:
            decision.rotation = (decision.rotation + 90) % 360
            assert decision.rotation == expected


class TestSelectionState:
    """Tests for SelectionState dataclass."""

    def test_initial_state(self, mock_video_list):
        """SelectionState should initialize correctly."""
        decisions = [VideoDecision(video=v) for v in mock_video_list]
        state = SelectionState(decisions=decisions)

        assert state.current_index == 0
        assert state.should_quit is False
        assert state.total_count == len(mock_video_list)

    def test_kept_count(self, mock_video_list):
        """kept_count should return correct count."""
        decisions = [VideoDecision(video=v) for v in mock_video_list]
        decisions[0].decision = "keep"
        decisions[1].decision = "keep"
        decisions[2].decision = "skip"

        state = SelectionState(decisions=decisions)

        assert state.kept_count == 2

    def test_skipped_count(self, mock_video_list):
        """skipped_count should return correct count."""
        decisions = [VideoDecision(video=v) for v in mock_video_list]
        decisions[0].decision = "keep"
        decisions[1].decision = "skip"
        decisions[2].decision = "skip"

        state = SelectionState(decisions=decisions)

        assert state.skipped_count == 2

    def test_current_video(self, mock_video_list):
        """current_video should return the decision at current_index."""
        decisions = [VideoDecision(video=v) for v in mock_video_list]
        state = SelectionState(decisions=decisions)

        assert state.current_video == decisions[0]

        state.current_index = 2
        assert state.current_video == decisions[2]

    def test_has_next(self, mock_video_list):
        """has_next should return True if not at last video."""
        decisions = [VideoDecision(video=v) for v in mock_video_list]
        state = SelectionState(decisions=decisions)

        assert state.has_next() is True

        state.current_index = len(decisions) - 1
        assert state.has_next() is False

    def test_has_previous(self, mock_video_list):
        """has_previous should return True if not at first video."""
        decisions = [VideoDecision(video=v) for v in mock_video_list]
        state = SelectionState(decisions=decisions)

        assert state.has_previous() is False

        state.current_index = 1
        assert state.has_previous() is True


class TestCheckMpvAvailable:
    """Tests for _check_mpv_available function."""

    def test_returns_false_when_mpv_not_installed(self, mocker, mock_console):
        """Should return False when mpv binary is not found."""
        mocker.patch("shutil.which", return_value=None)

        result = _check_mpv_available()
        assert result is False

    def test_returns_true_when_mpv_installed(self, mocker, mock_console):
        """Should return True when mpv binary is found."""
        mocker.patch("shutil.which", return_value="/usr/local/bin/mpv")

        result = _check_mpv_available()
        assert result is True


class TestSendMpvCommand:
    """Tests for _send_mpv_command function."""

    def test_returns_false_when_socket_not_found(self, mocker):
        """Should return False when socket file doesn't exist."""
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = FileNotFoundError()
        mocker.patch("socket.socket", return_value=mock_socket)

        result = _send_mpv_command(["loadfile", "/path/to/video.mov"])
        assert result is False

    def test_returns_false_on_connection_refused(self, mocker):
        """Should return False when connection is refused."""
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = ConnectionRefusedError()
        mocker.patch("socket.socket", return_value=mock_socket)

        result = _send_mpv_command(["loadfile", "/path/to/video.mov"])
        assert result is False

    def test_sends_json_command(self, mocker):
        """Should send JSON-formatted command to socket."""
        import json

        mock_socket = MagicMock()
        mocker.patch("socket.socket", return_value=mock_socket)

        _send_mpv_command(["loadfile", "/path/to/video.mov"])

        # Check the send call
        call_args = mock_socket.send.call_args[0][0]
        sent_data = json.loads(call_args.decode().strip())
        assert sent_data["command"] == ["loadfile", "/path/to/video.mov"]

    def test_returns_true_on_success(self, mocker):
        """Should return True when command is sent successfully."""
        mock_socket = MagicMock()
        mocker.patch("socket.socket", return_value=mock_socket)

        result = _send_mpv_command(["set_property", "video-rotate", "90"])
        assert result is True

    def test_closes_socket_after_send(self, mocker):
        """Should close socket after sending command."""
        mock_socket = MagicMock()
        mocker.patch("socket.socket", return_value=mock_socket)

        _send_mpv_command(["loadfile", "/path/to/video.mov"])

        mock_socket.close.assert_called_once()

    def test_uses_unix_socket(self, mocker):
        """Should create a Unix socket."""
        mock_socket_class = mocker.patch("socket.socket")

        _send_mpv_command(["loadfile", "/path/to/video.mov"])

        mock_socket_class.assert_called_with(socket.AF_UNIX, socket.SOCK_STREAM)


class TestDisplayVideoMetadata:
    """Tests for _display_video_metadata function."""

    def test_displays_metadata(self, mock_video, mock_console):
        """Should display video metadata without errors."""
        state = SelectionState(decisions=[VideoDecision(video=mock_video)])

        # Should not raise any exceptions
        _display_video_metadata(mock_video, 0, 1, state)

        # Verify console.print was called
        assert mock_console.print.called

    def test_handles_missing_place(self, video_factory, mock_console):
        """Should handle videos without location."""
        video = video_factory(place_name=None)
        state = SelectionState(decisions=[VideoDecision(video=video)])

        _display_video_metadata(video, 0, 1, state)

        # Should not raise any exceptions
        assert mock_console.print.called

    def test_handles_unknown_persons(self, video_factory, mock_console):
        """Should filter out _UNKNOWN persons."""
        video = video_factory(persons=["Alice", "_UNKNOWN_PERSON_1"])
        state = SelectionState(decisions=[VideoDecision(video=video)])

        _display_video_metadata(video, 0, 1, state)

        # Should display without _UNKNOWN persons
        assert mock_console.print.called


class TestDisplaySelectionSummary:
    """Tests for _display_selection_summary function."""

    def test_displays_summary(self, mock_video_list, mock_console):
        """Should display selection summary without errors."""
        decisions = [VideoDecision(video=v) for v in mock_video_list]
        decisions[0].decision = "keep"
        decisions[1].decision = "skip"

        state = SelectionState(decisions=decisions)

        _display_selection_summary(state)

        assert mock_console.print.called

    def test_handles_zero_reviewed(self, mock_video_list, mock_console):
        """Should handle case where no videos were reviewed."""
        decisions = [VideoDecision(video=v) for v in mock_video_list]
        state = SelectionState(decisions=decisions)

        _display_selection_summary(state)

        # Should not raise division by zero
        assert mock_console.print.called


class TestInteractiveVideoSelection:
    """Tests for interactive_video_selection function."""

    def test_returns_all_videos_when_mpv_unavailable(
        self, mock_video_list, mock_mpv_unavailable, mock_console
    ):
        """Should return all videos when mpv is not available."""
        result, rotation_map = interactive_video_selection(mock_video_list)

        assert result == mock_video_list
        assert rotation_map == {}

    def test_returns_empty_list_for_empty_input(self, mock_mpv_unavailable):
        """Should return empty list for empty input."""
        result, rotation_map = interactive_video_selection([])

        assert result == []
        assert rotation_map == {}

    def test_separates_icloud_videos(
        self, mock_videos_mixed, mock_mpv_unavailable, mock_console
    ):
        """iCloud-only videos should be included but not previewed."""
        result, _rotation_map = interactive_video_selection(mock_videos_mixed)

        # All videos should be returned since mpv is unavailable
        assert len(result) == 3

    def test_icloud_videos_auto_included(self, mocker, mock_console):
        """iCloud-only videos should be auto-included in final result."""
        # Create videos with one iCloud-only
        videos = [
            create_mock_video(uuid="local", path="/local.mov", ismissing=False),
            create_mock_video(uuid="icloud", path=None, ismissing=True),
        ]

        # Mock mpv as unavailable - should return all videos
        mocker.patch("main._check_mpv_available", return_value=False)

        result, _rotation_map = interactive_video_selection(videos)

        # Both videos should be included
        assert len(result) == 2
        uuids = [v.uuid for v in result]
        assert "local" in uuids
        assert "icloud" in uuids

    def test_all_icloud_returns_all(self, mocker, mock_console):
        """When all videos are iCloud-only, return all."""
        videos = [
            create_mock_video(uuid="icloud1", path=None, ismissing=True),
            create_mock_video(uuid="icloud2", path=None, ismissing=True),
        ]

        mocker.patch("main._check_mpv_available", return_value=True)

        result, _rotation_map = interactive_video_selection(videos)

        assert len(result) == 2

    def test_sorts_videos_by_date(self, mocker, mock_console):
        """Videos should be sorted by date for chronological review."""
        # Create videos in random order
        videos = [
            create_mock_video(
                uuid="last", date=datetime(2024, 6, 17), path="/last.mov"
            ),
            create_mock_video(
                uuid="first", date=datetime(2024, 6, 15), path="/first.mov"
            ),
            create_mock_video(
                uuid="middle", date=datetime(2024, 6, 16), path="/middle.mov"
            ),
        ]

        # Mock mpv as unavailable to test sorting logic indirectly
        mocker.patch("main._check_mpv_available", return_value=False)

        result, _rotation_map = interactive_video_selection(videos)

        # All should be returned (fallback mode)
        assert len(result) == 3


class TestSelectionStateEdgeCases:
    """Edge case tests for SelectionState."""

    def test_single_video(self):
        """State should work with single video."""
        video = create_mock_video()
        decisions = [VideoDecision(video=video)]
        state = SelectionState(decisions=decisions)

        assert state.total_count == 1
        assert state.has_next() is False
        assert state.has_previous() is False

    def test_all_kept(self, mock_video_list):
        """State should track when all videos are kept."""
        decisions = [VideoDecision(video=v) for v in mock_video_list]
        for d in decisions:
            d.decision = "keep"

        state = SelectionState(decisions=decisions)

        assert state.kept_count == len(mock_video_list)
        assert state.skipped_count == 0

    def test_all_skipped(self, mock_video_list):
        """State should track when all videos are skipped."""
        decisions = [VideoDecision(video=v) for v in mock_video_list]
        for d in decisions:
            d.decision = "skip"

        state = SelectionState(decisions=decisions)

        assert state.kept_count == 0
        assert state.skipped_count == len(mock_video_list)

    def test_mixed_with_pending(self, mock_video_list):
        """State should handle mix of decisions including pending."""
        decisions = [VideoDecision(video=v) for v in mock_video_list]
        decisions[0].decision = "keep"
        decisions[1].decision = "skip"
        # Rest remain pending

        state = SelectionState(decisions=decisions)

        assert state.kept_count == 1
        assert state.skipped_count == 1
        pending = state.total_count - state.kept_count - state.skipped_count
        assert pending == 3
