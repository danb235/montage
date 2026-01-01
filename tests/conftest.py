"""Shared fixtures for Montage test suite."""

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from unittest.mock import MagicMock

import pytest

# Mock osxphotos before importing main (for environments without osxphotos installed)
if "osxphotos" not in sys.modules:
    sys.modules["osxphotos"] = MagicMock()


@dataclass
class MockExifInfo:
    """Mock exif_info for video objects."""

    duration: float


@dataclass
class MockPlace:
    """Mock place info for video objects."""

    name: str | None


def create_mock_video(
    uuid: str = "test-uuid-001",
    date: datetime | None = None,
    duration: float = 30.0,
    persons: list[str] | None = None,
    width: int = 1920,
    height: int = 1080,
    original_filename: str = "test_video.mov",
    original_filesize: int = 1024 * 1024 * 100,  # 100 MB
    intrash: bool = False,
    ismissing: bool = False,
    place_name: str | None = None,
    path: str | None = "/path/to/video.mov",
) -> MagicMock:
    """Factory for creating mock osxphotos video objects."""
    video = MagicMock()
    video.uuid = uuid
    video.date = date or datetime(2024, 6, 15, 10, 30, 0)
    video.persons = persons if persons is not None else []
    video.width = width
    video.height = height
    video.original_filename = original_filename
    video.original_filesize = original_filesize
    video.intrash = intrash
    video.ismissing = ismissing
    video.exif_info = MockExifInfo(duration=duration)
    video.place = MockPlace(name=place_name) if place_name else None
    video.path = path  # Path to video file for playback
    return video


@pytest.fixture
def mock_video():
    """Single mock video for simple tests."""
    return create_mock_video()


@pytest.fixture
def mock_video_portrait():
    """Portrait video (taller than wide)."""
    return create_mock_video(width=1080, height=1920)


@pytest.fixture
def mock_video_landscape():
    """Landscape video (wider than tall)."""
    return create_mock_video(width=1920, height=1080)


@pytest.fixture
def mock_video_list():
    """List of diverse mock videos for filter testing."""
    return [
        create_mock_video(
            uuid="video-001",
            date=datetime(2024, 6, 15, 10, 0),
            duration=30.0,
            persons=["Alice", "Bob"],
            width=1920,
            height=1080,
            original_filesize=50 * 1024 * 1024,
            place_name="New York, NY",
        ),
        create_mock_video(
            uuid="video-002",
            date=datetime(2024, 6, 15, 14, 0),
            duration=120.0,
            persons=["Alice"],
            width=1080,
            height=1920,  # Portrait
            original_filesize=100 * 1024 * 1024,
            place_name="Los Angeles, CA",
        ),
        create_mock_video(
            uuid="video-003",
            date=datetime(2024, 6, 16, 9, 0),
            duration=5.0,
            persons=["Charlie"],
            width=1920,
            height=1080,
            original_filesize=10 * 1024 * 1024,
        ),
        create_mock_video(
            uuid="video-004",
            date=datetime(2024, 6, 16, 12, 0),
            duration=60.0,
            persons=["_UNKNOWN_PERSON_1"],  # Should be filtered out
            width=1920,
            height=1080,
            original_filesize=60 * 1024 * 1024,
        ),
        create_mock_video(
            uuid="video-005",
            date=datetime(2024, 6, 17, 8, 0),
            duration=45.0,
            persons=[],  # No persons
            width=1920,
            height=1080,
            original_filesize=45 * 1024 * 1024,
        ),
    ]


@pytest.fixture
def mock_console(mocker):
    """Mock rich console to prevent output during tests."""
    return mocker.patch("main.console")


@pytest.fixture
def hevc_videotoolbox_settings():
    """Expected settings for HEVC VideoToolbox encoder."""
    return {
        "quality_flag": "-q:v",
        "quality_values": {"high": "50", "balanced": "60", "fast": "70"},
        "extra_args": ["-allow_sw", "1"],
        "pix_fmt": "yuv420p",
    }


@pytest.fixture
def h264_videotoolbox_settings():
    """Expected settings for H.264 VideoToolbox encoder."""
    return {
        "quality_flag": "-q:v",
        "quality_values": {"high": "50", "balanced": "60", "fast": "70"},
        "extra_args": ["-allow_sw", "1"],
        "pix_fmt": "yuv420p",
    }


@pytest.fixture
def libx265_settings():
    """Expected settings for libx265 CPU encoder."""
    return {
        "quality_flag": "-crf",
        "quality_values": {"high": "20", "balanced": "22", "fast": "24"},
        "presets": {"high": "slow", "balanced": "medium", "fast": "fast"},
        "extra_args": [],
        "pix_fmt": "yuv420p10le",
    }


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory structure."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def sample_playlist(tmp_path):
    """Create a sample playlist.json for testing."""
    playlist_data = {
        "created": "2024-06-15T12:00:00",
        "project_name": "test_project",
        "filters": {
            "start_date": "2024-06-15T00:00:00",
            "end_date": "2024-06-15T23:59:59",
            "people": ["Alice"],
            "min_duration": None,
            "max_duration": None,
        },
        "videos": [
            {
                "uuid": "test-uuid-001",
                "date": "2024-06-15T10:30:00",
                "duration": 30.0,
                "filename": "test_video.mov",
                "persons": ["Alice"],
                "is_portrait": False,
                "width": 1920,
                "height": 1080,
                "path": "/path/to/video.mov",
            }
        ],
    }

    project_dir = tmp_path / "projects" / "test_project"
    project_dir.mkdir(parents=True)
    playlist_path = project_dir / "playlist.json"
    playlist_path.write_text(json.dumps(playlist_data, indent=2))

    return playlist_path


@pytest.fixture
def sample_playlist_multiple_videos(tmp_path):
    """Create a playlist with multiple videos for transition testing."""
    playlist_data = {
        "created": "2024-06-15T12:00:00",
        "project_name": "test_project",
        "filters": {
            "start_date": "2024-06-15T00:00:00",
            "end_date": "2024-06-17T23:59:59",
            "people": None,
            "min_duration": None,
            "max_duration": None,
        },
        "videos": [
            {
                "uuid": "video-001",
                "date": "2024-06-15T10:00:00",
                "duration": 30.0,
                "filename": "video1.mov",
                "persons": ["Alice"],
                "is_portrait": False,
                "width": 1920,
                "height": 1080,
                "path": "/path/to/video1.mov",
            },
            {
                "uuid": "video-002",
                "date": "2024-06-16T10:00:00",
                "duration": 45.0,
                "filename": "video2.mov",
                "persons": ["Bob"],
                "is_portrait": True,
                "width": 1080,
                "height": 1920,
                "path": "/path/to/video2.mov",
            },
            {
                "uuid": "video-003",
                "date": "2024-06-17T10:00:00",
                "duration": 60.0,
                "filename": "video3.mov",
                "persons": ["Charlie"],
                "is_portrait": False,
                "width": 1920,
                "height": 1080,
                "path": "/path/to/video3.mov",
            },
        ],
    }

    project_dir = tmp_path / "projects" / "multi_video_project"
    project_dir.mkdir(parents=True)
    playlist_path = project_dir / "playlist.json"
    playlist_path.write_text(json.dumps(playlist_data, indent=2))

    return playlist_path


# Make create_mock_video available as a fixture too
@pytest.fixture
def video_factory():
    """Provide the create_mock_video factory function as a fixture."""
    return create_mock_video


# =============================================================================
# Interactive Video Selection Fixtures
# =============================================================================


@pytest.fixture
def mock_video_with_path():
    """Video with a valid path for playback testing."""
    return create_mock_video(
        uuid="playable-001",
        path="/path/to/playable_video.mov",
        ismissing=False,
    )


@pytest.fixture
def mock_video_icloud_only():
    """Video that is in iCloud only (no local path)."""
    return create_mock_video(
        uuid="icloud-001",
        path=None,
        ismissing=True,
    )


@pytest.fixture
def mock_videos_mixed():
    """Mix of playable and iCloud-only videos for selection testing."""
    return [
        create_mock_video(
            uuid="local-001",
            date=datetime(2024, 6, 15, 10, 0),
            path="/path/to/local1.mov",
            ismissing=False,
            persons=["Alice"],
        ),
        create_mock_video(
            uuid="local-002",
            date=datetime(2024, 6, 15, 14, 0),
            path="/path/to/local2.mov",
            ismissing=False,
            persons=["Bob"],
        ),
        create_mock_video(
            uuid="icloud-001",
            date=datetime(2024, 6, 16, 9, 0),
            path=None,
            ismissing=True,
            persons=["Charlie"],
        ),
    ]


@pytest.fixture
def mock_mpv_unavailable(mocker):
    """Mock mpv as unavailable (shutil.which returns None)."""
    mocker.patch("main._check_mpv_available", return_value=False)


@pytest.fixture
def mock_mpv_available(mocker):
    """Mock mpv as available with subprocess."""
    mocker.patch("main._check_mpv_available", return_value=True)
    # Mock subprocess.Popen to return a mock process
    mock_process = MagicMock()
    mock_process.terminate = MagicMock()
    mock_process.wait = MagicMock()
    mocker.patch("subprocess.Popen", return_value=mock_process)
    return mock_process
