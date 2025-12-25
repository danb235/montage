"""Tests for video filtering functions."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import os

# Import helper function - conftest.py is in the same directory
import sys

from main import filter_by_duration, filter_by_people, get_unique_persons

sys.path.insert(0, os.path.dirname(__file__))
from conftest import create_mock_video


class TestGetUniquePersons:
    """Tests for get_unique_persons() function."""

    def test_extracts_unique_persons(self, mock_video_list):
        persons = get_unique_persons(mock_video_list)

        assert "Alice" in persons
        assert "Bob" in persons
        assert "Charlie" in persons

    def test_excludes_unknown_persons(self, mock_video_list):
        persons = get_unique_persons(mock_video_list)

        assert "_UNKNOWN_PERSON_1" not in persons
        assert not any(p.startswith("_UNKNOWN") for p in persons)

    def test_returns_sorted_list(self, mock_video_list):
        persons = get_unique_persons(mock_video_list)

        assert persons == sorted(persons)

    def test_empty_video_list(self):
        persons = get_unique_persons([])
        assert persons == []

    def test_no_persons_in_videos(self):
        videos = [
            create_mock_video(uuid="v1", persons=[]),
            create_mock_video(uuid="v2", persons=[]),
        ]
        persons = get_unique_persons(videos)
        assert persons == []

    def test_deduplicates_persons(self):
        """Same person in multiple videos should only appear once."""
        videos = [
            create_mock_video(uuid="v1", persons=["Alice", "Bob"]),
            create_mock_video(uuid="v2", persons=["Alice", "Charlie"]),
            create_mock_video(uuid="v3", persons=["Alice"]),
        ]
        persons = get_unique_persons(videos)

        assert persons.count("Alice") == 1
        assert len(persons) == 3  # Alice, Bob, Charlie

    def test_filters_none_values(self):
        """None values in persons list should be filtered out."""
        video = create_mock_video(persons=[None, "Alice", None])
        persons = get_unique_persons([video])

        assert "Alice" in persons
        assert None not in persons

    def test_filters_empty_strings(self):
        """Empty strings in persons list should be filtered out."""
        video = create_mock_video(persons=["", "Alice", ""])
        persons = get_unique_persons([video])

        assert "Alice" in persons
        assert "" not in persons

    def test_case_sensitive(self):
        """Person names should be case-sensitive."""
        videos = [
            create_mock_video(uuid="v1", persons=["alice"]),
            create_mock_video(uuid="v2", persons=["Alice"]),
        ]
        persons = get_unique_persons(videos)

        assert "alice" in persons
        assert "Alice" in persons
        assert len(persons) == 2


class TestFilterByPeople:
    """Tests for filter_by_people() function."""

    def test_filters_to_selected_people(self, mock_video_list):
        filtered = filter_by_people(mock_video_list, ["Alice"])

        # Should include videos with Alice (video-001 and video-002)
        assert len(filtered) == 2
        for v in filtered:
            assert "Alice" in v.persons

    def test_none_selection_returns_all(self, mock_video_list):
        filtered = filter_by_people(mock_video_list, None)

        assert len(filtered) == len(mock_video_list)

    def test_multiple_people_selection_or_logic(self, mock_video_list):
        """Selecting multiple people should include videos with ANY of them."""
        filtered = filter_by_people(mock_video_list, ["Alice", "Charlie"])

        # Should include video-001 (Alice, Bob), video-002 (Alice), video-003 (Charlie)
        assert len(filtered) == 3
        uuids = {v.uuid for v in filtered}
        assert "video-001" in uuids
        assert "video-002" in uuids
        assert "video-003" in uuids

    def test_no_matches_returns_empty(self, mock_video_list):
        filtered = filter_by_people(mock_video_list, ["NonexistentPerson"])

        assert len(filtered) == 0

    def test_preserves_video_order(self, mock_video_list):
        filtered = filter_by_people(mock_video_list, ["Alice"])

        uuids = [v.uuid for v in filtered]
        # video-001 comes before video-002 in original list
        assert uuids.index("video-001") < uuids.index("video-002")

    def test_single_person_exact_match(self):
        videos = [
            create_mock_video(uuid="v1", persons=["Alice"]),
            create_mock_video(uuid="v2", persons=["Bob"]),
        ]
        filtered = filter_by_people(videos, ["Alice"])

        assert len(filtered) == 1
        assert filtered[0].uuid == "v1"

    def test_video_with_multiple_matching_people(self):
        """Video with multiple selected people should only be included once."""
        videos = [
            create_mock_video(uuid="v1", persons=["Alice", "Bob"]),
        ]
        filtered = filter_by_people(videos, ["Alice", "Bob"])

        assert len(filtered) == 1
        assert filtered[0].uuid == "v1"

    def test_empty_selection_treated_as_none(self):
        """Empty list should NOT be treated same as None - it should return nothing."""
        videos = [
            create_mock_video(uuid="v1", persons=["Alice"]),
        ]
        filtered = filter_by_people(videos, [])

        # Empty list means no people selected, so no filter is applied
        # Actually checking the implementation - empty list is truthy check
        # Let's verify actual behavior
        # Looking at the code: if selected_people is None: return videos
        # So empty list [] is not None, should filter
        # But then: if any(person in v.persons for person in selected_people)
        # With empty selected_people, any() returns False
        assert len(filtered) == 0


class TestFilterByDuration:
    """Tests for filter_by_duration() function."""

    def test_min_duration_filter(self, mock_video_list):
        filtered = filter_by_duration(mock_video_list, min_dur=30.0, max_dur=None)

        for v in filtered:
            assert v.exif_info.duration >= 30.0

    def test_max_duration_filter(self, mock_video_list):
        filtered = filter_by_duration(mock_video_list, min_dur=None, max_dur=60.0)

        for v in filtered:
            assert v.exif_info.duration <= 60.0

    def test_min_and_max_duration_filter(self, mock_video_list):
        filtered = filter_by_duration(mock_video_list, min_dur=20.0, max_dur=50.0)

        for v in filtered:
            assert 20.0 <= v.exif_info.duration <= 50.0

    def test_no_filter_returns_all(self, mock_video_list):
        filtered = filter_by_duration(mock_video_list, min_dur=None, max_dur=None)

        assert len(filtered) == len(mock_video_list)

    def test_no_matches_returns_empty(self, mock_video_list):
        filtered = filter_by_duration(mock_video_list, min_dur=1000.0, max_dur=2000.0)

        assert len(filtered) == 0

    def test_handles_missing_exif_info(self):
        """Videos without exif_info should be excluded."""
        video = create_mock_video()
        video.exif_info = None

        filtered = filter_by_duration([video], min_dur=10.0, max_dur=None)

        assert len(filtered) == 0

    def test_exact_min_boundary_included(self):
        """Video exactly at min boundary should be included."""
        video = create_mock_video(duration=30.0)

        filtered = filter_by_duration([video], min_dur=30.0, max_dur=None)

        assert len(filtered) == 1

    def test_exact_max_boundary_included(self):
        """Video exactly at max boundary should be included."""
        video = create_mock_video(duration=30.0)

        filtered = filter_by_duration([video], min_dur=None, max_dur=30.0)

        assert len(filtered) == 1

    def test_exact_both_boundaries(self):
        """Video exactly matching both min and max should be included."""
        video = create_mock_video(duration=30.0)

        filtered = filter_by_duration([video], min_dur=30.0, max_dur=30.0)

        assert len(filtered) == 1

    def test_just_below_min_excluded(self):
        """Video just below min should be excluded."""
        video = create_mock_video(duration=29.9)

        filtered = filter_by_duration([video], min_dur=30.0, max_dur=None)

        assert len(filtered) == 0

    def test_just_above_max_excluded(self):
        """Video just above max should be excluded."""
        video = create_mock_video(duration=30.1)

        filtered = filter_by_duration([video], min_dur=None, max_dur=30.0)

        assert len(filtered) == 0

    def test_preserves_order(self, mock_video_list):
        """Filtered results should maintain original order."""
        filtered = filter_by_duration(mock_video_list, min_dur=30.0, max_dur=None)

        # Get UUIDs in order
        uuids = [v.uuid for v in filtered]
        original_uuids = [
            v.uuid for v in mock_video_list if v.exif_info.duration >= 30.0
        ]

        assert uuids == original_uuids

    def test_zero_duration_handled(self):
        """Zero duration video should be filtered correctly."""
        video = create_mock_video(duration=0.0)

        # With min=0, should be included
        filtered = filter_by_duration([video], min_dur=0.0, max_dur=None)
        assert len(filtered) == 1

        # With min>0, should be excluded
        filtered = filter_by_duration([video], min_dur=1.0, max_dur=None)
        assert len(filtered) == 0

    def test_very_long_video(self):
        """Very long video should be handled correctly."""
        video = create_mock_video(duration=7200.0)  # 2 hours

        filtered = filter_by_duration([video], min_dur=3600.0, max_dur=None)
        assert len(filtered) == 1

        filtered = filter_by_duration([video], min_dur=None, max_dur=3600.0)
        assert len(filtered) == 0
