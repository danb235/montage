"""Tests for encoder settings and filter building functions."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from main import (
    TARGET_FPS,
    TARGET_HEIGHT,
    TARGET_WIDTH,
    _get_encoder_settings,
    build_landscape_filter,
    build_portrait_filter,
)


class TestGetEncoderSettings:
    """Tests for _get_encoder_settings() function."""

    def test_hevc_videotoolbox_settings(self, hevc_videotoolbox_settings):
        settings = _get_encoder_settings("hevc_videotoolbox")
        assert settings == hevc_videotoolbox_settings

    def test_hevc_videotoolbox_quality_flag(self):
        settings = _get_encoder_settings("hevc_videotoolbox")
        assert settings["quality_flag"] == "-q:v"

    def test_hevc_videotoolbox_has_allow_sw(self):
        settings = _get_encoder_settings("hevc_videotoolbox")
        assert "-allow_sw" in settings["extra_args"]
        assert "1" in settings["extra_args"]

    def test_h264_videotoolbox_settings(self, h264_videotoolbox_settings):
        settings = _get_encoder_settings("h264_videotoolbox")
        assert settings == h264_videotoolbox_settings

    def test_h264_videotoolbox_quality_flag(self):
        settings = _get_encoder_settings("h264_videotoolbox")
        assert settings["quality_flag"] == "-q:v"

    def test_h264_videotoolbox_pix_fmt(self):
        settings = _get_encoder_settings("h264_videotoolbox")
        assert settings["pix_fmt"] == "yuv420p"

    def test_libx265_settings(self, libx265_settings):
        settings = _get_encoder_settings("libx265")
        assert settings == libx265_settings

    def test_libx265_has_crf_flag(self):
        settings = _get_encoder_settings("libx265")
        assert settings["quality_flag"] == "-crf"

    def test_libx265_has_presets(self):
        settings = _get_encoder_settings("libx265")
        assert "presets" in settings
        assert "high" in settings["presets"]
        assert "balanced" in settings["presets"]
        assert "fast" in settings["presets"]

    def test_libx265_10bit_pixel_format(self):
        settings = _get_encoder_settings("libx265")
        assert settings["pix_fmt"] == "yuv420p10le"

    def test_libx265_no_extra_args(self):
        settings = _get_encoder_settings("libx265")
        assert settings["extra_args"] == []

    def test_unknown_encoder_falls_back_to_libx265(self):
        """Unknown encoders should return libx265 settings (else branch)."""
        settings = _get_encoder_settings("unknown_encoder")
        assert settings["quality_flag"] == "-crf"
        assert "presets" in settings

    def test_all_encoders_have_quality_tiers(self):
        """All encoders must have high, balanced, and fast quality values."""
        for encoder in ["hevc_videotoolbox", "h264_videotoolbox", "libx265"]:
            settings = _get_encoder_settings(encoder)
            assert "high" in settings["quality_values"]
            assert "balanced" in settings["quality_values"]
            assert "fast" in settings["quality_values"]

    def test_all_encoders_have_pix_fmt(self):
        """All encoders must specify pixel format."""
        for encoder in ["hevc_videotoolbox", "h264_videotoolbox", "libx265"]:
            settings = _get_encoder_settings(encoder)
            assert "pix_fmt" in settings
            assert settings["pix_fmt"] is not None


class TestBuildPortraitFilter:
    """Tests for build_portrait_filter() function."""

    def test_filter_contains_split(self):
        filter_str = build_portrait_filter(0)
        assert "[0:v]split" in filter_str

    def test_filter_contains_blur(self):
        filter_str = build_portrait_filter(0)
        assert "gblur=sigma=50" in filter_str

    def test_filter_contains_overlay(self):
        filter_str = build_portrait_filter(0)
        assert "overlay=" in filter_str

    def test_filter_output_label(self):
        filter_str = build_portrait_filter(0)
        assert "[v0]" in filter_str

    def test_input_index_0(self):
        filter_str = build_portrait_filter(0)
        assert "[0:v]split" in filter_str
        assert "[0orig]" in filter_str
        assert "[0copy]" in filter_str

    def test_input_index_5(self):
        filter_str = build_portrait_filter(5)
        assert "[5:v]split" in filter_str
        assert "[5orig]" in filter_str
        assert "[5copy]" in filter_str
        assert "[v5]" in filter_str

    def test_input_index_10(self):
        filter_str = build_portrait_filter(10)
        assert "[10:v]split" in filter_str
        assert "[10orig]" in filter_str
        assert "[v10]" in filter_str

    def test_target_width_in_filter(self):
        filter_str = build_portrait_filter(0)
        assert str(TARGET_WIDTH) in filter_str

    def test_target_height_in_filter(self):
        filter_str = build_portrait_filter(0)
        assert str(TARGET_HEIGHT) in filter_str

    def test_fps_in_filter(self):
        filter_str = build_portrait_filter(0)
        assert f"fps={TARGET_FPS}" in filter_str

    def test_setsar_in_filter(self):
        """Verify sample aspect ratio is set to 1."""
        filter_str = build_portrait_filter(0)
        assert "setsar=1" in filter_str

    def test_settb_in_filter(self):
        """Verify timebase is set."""
        filter_str = build_portrait_filter(0)
        assert "settb=AVTB" in filter_str

    def test_no_rotation_by_default(self):
        """Filter should not include transpose when rotation is 0."""
        filter_str = build_portrait_filter(0)
        assert "transpose" not in filter_str

    def test_rotation_90_degrees(self):
        """Filter should include transpose=1 for 90 degree rotation."""
        filter_str = build_portrait_filter(0, rotation=90)
        assert "transpose=1" in filter_str

    def test_rotation_180_degrees(self):
        """Filter should include double transpose for 180 degree rotation."""
        filter_str = build_portrait_filter(0, rotation=180)
        assert "transpose=1,transpose=1" in filter_str

    def test_rotation_270_degrees(self):
        """Filter should include transpose=2 for 270 degree rotation."""
        filter_str = build_portrait_filter(0, rotation=270)
        assert "transpose=2" in filter_str

    def test_rotation_applied_before_split(self):
        """Rotation filter should be applied before split operation."""
        filter_str = build_portrait_filter(0, rotation=90)
        transpose_pos = filter_str.find("transpose=1")
        split_pos = filter_str.find("split")
        assert transpose_pos < split_pos


class TestBuildLandscapeFilter:
    """Tests for build_landscape_filter() function."""

    def test_filter_contains_scale(self):
        filter_str = build_landscape_filter(0)
        assert "[0:v]scale=" in filter_str

    def test_filter_contains_pad(self):
        filter_str = build_landscape_filter(0)
        assert "pad=" in filter_str

    def test_filter_output_label(self):
        filter_str = build_landscape_filter(0)
        assert "[v0]" in filter_str

    def test_input_index_3(self):
        filter_str = build_landscape_filter(3)
        assert "[3:v]scale=" in filter_str
        assert "[v3]" in filter_str

    def test_input_index_7(self):
        filter_str = build_landscape_filter(7)
        assert "[7:v]scale=" in filter_str
        assert "[v7]" in filter_str

    def test_target_width_in_filter(self):
        filter_str = build_landscape_filter(0)
        assert str(TARGET_WIDTH) in filter_str

    def test_target_height_in_filter(self):
        filter_str = build_landscape_filter(0)
        assert str(TARGET_HEIGHT) in filter_str

    def test_black_padding(self):
        filter_str = build_landscape_filter(0)
        assert ":black" in filter_str

    def test_fps_in_filter(self):
        filter_str = build_landscape_filter(0)
        assert f"fps={TARGET_FPS}" in filter_str

    def test_setsar_in_filter(self):
        """Verify sample aspect ratio is set to 1."""
        filter_str = build_landscape_filter(0)
        assert "setsar=1" in filter_str

    def test_force_original_aspect_ratio(self):
        filter_str = build_landscape_filter(0)
        assert "force_original_aspect_ratio=decrease" in filter_str

    def test_settb_in_filter(self):
        """Verify timebase is set."""
        filter_str = build_landscape_filter(0)
        assert "settb=AVTB" in filter_str

    def test_no_rotation_by_default(self):
        """Filter should not include transpose when rotation is 0."""
        filter_str = build_landscape_filter(0)
        assert "transpose" not in filter_str

    def test_rotation_90_degrees(self):
        """Filter should include transpose=1 for 90 degree rotation."""
        filter_str = build_landscape_filter(0, rotation=90)
        assert "transpose=1" in filter_str

    def test_rotation_180_degrees(self):
        """Filter should include double transpose for 180 degree rotation."""
        filter_str = build_landscape_filter(0, rotation=180)
        assert "transpose=1,transpose=1" in filter_str

    def test_rotation_270_degrees(self):
        """Filter should include transpose=2 for 270 degree rotation."""
        filter_str = build_landscape_filter(0, rotation=270)
        assert "transpose=2" in filter_str

    def test_rotation_applied_before_scale(self):
        """Rotation filter should be applied before scale operation."""
        filter_str = build_landscape_filter(0, rotation=90)
        transpose_pos = filter_str.find("transpose=1")
        scale_pos = filter_str.find("scale=")
        assert transpose_pos < scale_pos
