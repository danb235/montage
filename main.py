#!/usr/bin/env python3
"""
Video Compiler - Create compilation videos from macOS Photos library.

This tool queries videos from the Photos app using osxphotos, allows interactive
filtering by date, people, and duration, then compiles selected videos into a
single movie using ffmpeg.

Usage:
    python main.py                    # Interactive mode - create new project
    python main.py --recompile <path> # Recompile existing playlist
"""

import argparse
import json
import platform
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import osxphotos
import questionary
from rich.console import Console
from rich.progress import (
    Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn,
    TimeElapsedColumn, TimeRemainingColumn
)
from rich.table import Table

# Constants
VIDEOS_DIR = Path("videos")
PROJECTS_DIR = Path("projects")
TARGET_WIDTH = 1920
TARGET_HEIGHT = 1080
TARGET_FPS = 30
TRANSITION_DURATION = 1  # seconds

# Human-readable encoder names for user feedback
ENCODER_NAMES = {
    "hevc_videotoolbox": "Apple VideoToolbox (Metal GPU)",
    "hevc_nvenc": "NVIDIA NVENC (CUDA GPU)",
    "hevc_amf": "AMD AMF (GPU)",
    "hevc_vaapi": "VA-API (GPU)",
    "hevc_qsv": "Intel Quick Sync (GPU)",
    "libx265": "x265 (CPU)",
}

# Encoder cache to avoid repeated tests
_encoder_cache: dict[str, tuple] = {}

console = Console()


def _test_encoder(encoder: str, timeout: int = 10) -> bool:
    """Test if an encoder is available by attempting a 1-second encode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_output = Path(tmpdir) / "test.mp4"

        # Generate test pattern and encode
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30",
            "-c:v", encoder,
            "-t", "1",
            str(test_output)
        ]

        # Add encoder-specific flags
        if encoder == "hevc_videotoolbox":
            cmd.insert(-1, "-allow_sw")
            cmd.insert(-1, "0")  # Require hardware, don't allow software fallback

        try:
            subprocess.run(cmd, capture_output=True, timeout=timeout, check=True)
            return test_output.exists() and test_output.stat().st_size > 0
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return False


def _get_encoder_settings(encoder: str) -> dict:
    """Get optimal settings for each encoder type."""
    if encoder == "hevc_videotoolbox":
        return {
            "quality_flag": "-q:v",
            "quality_values": {"high": "50", "balanced": "60", "fast": "70"},
            "extra_args": ["-allow_sw", "1"],
            "pix_fmt": "yuv420p",  # VideoToolbox doesn't support 10-bit
        }
    elif encoder == "hevc_nvenc":
        return {
            "quality_flag": "-cq",
            "quality_values": {"high": "20", "balanced": "24", "fast": "28"},
            "extra_args": ["-preset", "p4", "-tune", "hq"],
            "pix_fmt": "yuv420p",
        }
    elif encoder == "hevc_amf":
        return {
            "quality_flag": "-qp_i",
            "quality_values": {"high": "20", "balanced": "24", "fast": "28"},
            "extra_args": ["-quality", "quality"],
            "pix_fmt": "yuv420p",
        }
    elif encoder == "hevc_vaapi":
        return {
            "quality_flag": "-qp",
            "quality_values": {"high": "20", "balanced": "24", "fast": "28"},
            "extra_args": ["-vaapi_device", "/dev/dri/renderD128"],
            "pix_fmt": "vaapi",
        }
    elif encoder == "hevc_qsv":
        return {
            "quality_flag": "-global_quality",
            "quality_values": {"high": "20", "balanced": "25", "fast": "30"},
            "extra_args": [],
            "pix_fmt": "yuv420p",
        }
    else:  # libx265 (CPU fallback)
        return {
            "quality_flag": "-crf",
            "quality_values": {"high": "20", "balanced": "22", "fast": "24"},
            "presets": {"high": "slow", "balanced": "medium", "fast": "fast"},
            "extra_args": [],
            "pix_fmt": "yuv420p10le",  # CPU supports 10-bit
        }


def detect_best_encoder(codec: str = "hevc") -> tuple[str, dict, list[str]]:
    """
    Detect the best available encoder for the current platform.
    Returns (encoder_name, encoder_settings, tested_encoders).

    Tests hardware encoders in priority order, falls back to CPU.
    Results are cached for the session.
    """
    cache_key = f"{platform.system()}_{codec}"
    if cache_key in _encoder_cache:
        return _encoder_cache[cache_key]

    system = platform.system()
    tested = []  # Track what we tested for user feedback

    # Define encoder priority by platform
    if system == "Darwin":  # macOS
        hw_encoders = ["hevc_videotoolbox"]
    elif system == "Windows":
        hw_encoders = ["hevc_nvenc", "hevc_qsv", "hevc_amf"]
    else:  # Linux
        hw_encoders = ["hevc_nvenc", "hevc_vaapi"]

    # Test each hardware encoder
    for encoder in hw_encoders:
        tested.append(encoder)
        if _test_encoder(encoder):
            result = (encoder, _get_encoder_settings(encoder), tested)
            _encoder_cache[cache_key] = result
            return result

    # Fallback to CPU
    result = ("libx265", _get_encoder_settings("libx265"), tested)
    _encoder_cache[cache_key] = result
    return result


def format_size(size_bytes: int) -> str:
    """Format bytes to human readable size."""
    if size_bytes is None:
        return "Unknown"
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def format_duration(seconds: float) -> str:
    """Format seconds to human readable duration."""
    if seconds is None:
        return "Unknown"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.0f}s"


def generate_output_filename(start_date: datetime, end_date: datetime, people: list[str] | None) -> str:
    """
    Generate sortable output filename from date range and people.

    Format: YYYY.MM.DD.to.YYYY.MM.DD.Person1.Person2.mp4
    Single day: YYYY.MM.DD.Person1.mp4
    """
    # Format dates as YYYY.MM.DD for sortability
    start_str = start_date.strftime("%Y.%m.%d")
    end_str = end_date.strftime("%Y.%m.%d")

    # Check if same day (comparing just the date portion)
    same_day = start_date.date() == end_date.date()

    # Build date part
    if same_day:
        date_part = start_str
    else:
        date_part = f"{start_str}.to.{end_str}"

    # Format people (replace spaces with dots, join with dots)
    if people:
        people_part = ".".join(p.replace(" ", ".") for p in people)
    else:
        people_part = "All"

    return f"{date_part}.{people_part}.mp4"


def validate_date(date_str: str) -> bool:
    """Validate date string format."""
    if not date_str:
        return False
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def prompt_date_range() -> tuple[datetime, datetime]:
    """Prompt user for start and end dates."""
    console.print("\n[bold]Step 1: Select Date Range[/bold]")

    start_str = questionary.text(
        "Start date (YYYY-MM-DD):",
        validate=lambda x: validate_date(x) or "Please enter a valid date (YYYY-MM-DD)"
    ).ask()

    if start_str is None:
        sys.exit(0)

    end_str = questionary.text(
        "End date (YYYY-MM-DD):",
        validate=lambda x: validate_date(x) or "Please enter a valid date (YYYY-MM-DD)"
    ).ask()

    if end_str is None:
        sys.exit(0)

    start_date = datetime.strptime(start_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59)

    return start_date, end_date


def query_videos(start_date: datetime, end_date: datetime) -> list:
    """Query videos from Photos library within date range."""
    console.print("\n[dim]Loading Photos library...[/dim]")

    photosdb = osxphotos.PhotosDB()

    # Query all movies in date range
    photos = photosdb.photos(
        movies=True,
        images=False,
        from_date=start_date,
        to_date=end_date
    )

    # Filter to only include non-trashed videos
    videos = [p for p in photos if not p.intrash]

    console.print(f"[green]Found {len(videos)} videos in date range[/green]")
    return videos


def get_unique_persons(videos: list) -> list[str]:
    """Get unique named persons from video list."""
    persons = set()
    for v in videos:
        for person in v.persons:
            # Filter out unknown persons
            if person and not person.startswith("_UNKNOWN"):
                persons.add(person)
    return sorted(persons)


def prompt_people_selection(persons: list[str]) -> list[str] | None:
    """Prompt user to select people to include."""
    console.print("\n[bold]Step 2: Select People[/bold]")

    if not persons:
        console.print("[yellow]No named persons found in videos[/yellow]")
        return None

    choices = [{"name": "ALL (include all videos)", "value": "ALL"}]
    choices.extend([{"name": p, "value": p} for p in persons])

    selected = questionary.checkbox(
        "Select people to include (space to select, enter to confirm):",
        choices=[c["name"] for c in choices]
    ).ask()

    if selected is None:
        sys.exit(0)

    if not selected or "ALL (include all videos)" in selected:
        console.print("[dim]Including all videos[/dim]")
        return None

    console.print(f"[dim]Filtering to: {', '.join(selected)}[/dim]")
    return selected


def filter_by_people(videos: list, selected_people: list[str]) -> list:
    """Filter videos to only include those with selected people."""
    if selected_people is None:
        return videos

    filtered = []
    for v in videos:
        if any(person in v.persons for person in selected_people):
            filtered.append(v)

    return filtered


def prompt_quality_selection() -> str:
    """Prompt user for encoding quality preset."""
    quality = questionary.select(
        "Encoding quality:",
        choices=[
            "Auto (GPU if available)",
            "High (best quality, slower)",
            "Balanced (good quality)",
            "Fast (preview quality)",
        ],
        default="Auto (GPU if available)"
    ).ask()

    if quality is None:
        sys.exit(0)

    return quality


def prompt_duration_filter() -> tuple[float | None, float | None]:
    """Prompt user for min/max video duration."""
    console.print("\n[bold]Step 3: Duration Filter[/bold]")

    min_str = questionary.text(
        "Minimum duration in seconds (press Enter for no minimum):",
        default=""
    ).ask()

    if min_str is None:
        sys.exit(0)

    max_str = questionary.text(
        "Maximum duration in seconds (press Enter for no maximum):",
        default=""
    ).ask()

    if max_str is None:
        sys.exit(0)

    min_dur = float(min_str) if min_str else None
    max_dur = float(max_str) if max_str else None

    if min_dur or max_dur:
        parts = []
        if min_dur:
            parts.append(f"min: {min_dur}s")
        if max_dur:
            parts.append(f"max: {max_dur}s")
        console.print(f"[dim]Duration filter: {', '.join(parts)}[/dim]")
    else:
        console.print("[dim]No duration filter applied[/dim]")

    return min_dur, max_dur


def filter_by_duration(videos: list, min_dur: float | None, max_dur: float | None) -> list:
    """Filter videos by duration."""
    if min_dur is None and max_dur is None:
        return videos

    filtered = []
    for v in videos:
        duration = v.exif_info.duration if v.exif_info else None
        if duration is None:
            continue

        if min_dur is not None and duration < min_dur:
            continue
        if max_dur is not None and duration > max_dur:
            continue

        filtered.append(v)

    return filtered


def display_video_summary(videos: list) -> None:
    """Display summary table of selected videos."""
    console.print("\n[bold]Step 4: Review Selection[/bold]\n")

    table = Table(title="Selected Videos", show_lines=False)
    table.add_column("#", style="dim", width=4)
    table.add_column("Date", style="cyan", width=18)
    table.add_column("Duration", style="green", width=10)
    table.add_column("People", style="yellow", width=25)
    table.add_column("Location", style="blue", width=30)
    table.add_column("Size", style="magenta", width=10)

    total_size = 0
    total_duration = 0

    sorted_videos = sorted(videos, key=lambda x: x.date)

    for i, v in enumerate(sorted_videos, 1):
        duration = v.exif_info.duration if v.exif_info else 0
        size = v.original_filesize or 0

        people = ", ".join(p for p in v.persons[:3] if not p.startswith("_UNKNOWN"))
        if len(v.persons) > 3:
            people += "..."

        location = ""
        if v.place:
            location = v.place.name or ""
            if len(location) > 28:
                location = location[:25] + "..."

        table.add_row(
            str(i),
            v.date.strftime("%Y-%m-%d %H:%M"),
            format_duration(duration),
            people or "-",
            location or "-",
            format_size(size)
        )

        total_size += size
        total_duration += duration or 0

    console.print(table)

    # Calculate estimated output duration (with transitions)
    num_transitions = max(0, len(videos) - 1)
    output_duration = total_duration - (num_transitions * TRANSITION_DURATION)

    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  Total videos: {len(videos)}")
    console.print(f"  Total size: {format_size(total_size)}")
    console.print(f"  Total duration: {format_duration(total_duration)}")
    console.print(f"  Estimated output: {format_duration(output_duration)} (with {num_transitions} transitions)")

    # Check for iCloud-only videos
    missing_count = sum(1 for v in videos if v.ismissing)
    if missing_count > 0:
        console.print(f"\n[yellow]Note: {missing_count} videos are in iCloud and will be downloaded[/yellow]")


def export_videos(videos: list) -> dict[str, Path]:
    """Export videos to local cache, skip if already exists."""
    VIDEOS_DIR.mkdir(exist_ok=True)

    exported = {}
    sorted_videos = sorted(videos, key=lambda x: x.date)

    console.print("\n[bold]Step 5: Exporting Videos[/bold]\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Exporting...", total=len(sorted_videos))

        for v in sorted_videos:
            dest_path = VIDEOS_DIR / f"{v.uuid}.mov"

            if dest_path.exists():
                progress.update(task, advance=1, description=f"[dim]Cached: {v.original_filename}[/dim]")
                exported[v.uuid] = dest_path
                continue

            progress.update(task, description=f"Exporting: {v.original_filename}")

            try:
                # Use osxphotos export - this handles iCloud download
                results = v.export(
                    str(VIDEOS_DIR),
                    use_photos_export=True,
                    timeout=300  # 5 minute timeout for large files
                )

                if results:
                    # Rename to UUID-based name
                    exported_path = Path(results[0])
                    exported_path.rename(dest_path)
                    exported[v.uuid] = dest_path
                else:
                    console.print(f"[red]Failed to export: {v.original_filename}[/red]")
            except Exception as e:
                console.print(f"[red]Error exporting {v.original_filename}: {e}[/red]")

            progress.update(task, advance=1)

    console.print(f"\n[green]Exported {len(exported)} videos to {VIDEOS_DIR}[/green]")
    return exported


def create_playlist(videos: list, project_name: str, filters: dict, exported: dict[str, Path]) -> Path:
    """Create playlist JSON for the project."""
    projects_dir = PROJECTS_DIR / project_name
    projects_dir.mkdir(parents=True, exist_ok=True)

    sorted_videos = sorted(videos, key=lambda x: x.date)

    playlist = {
        "created": datetime.now().isoformat(),
        "project_name": project_name,
        "filters": filters,
        "videos": []
    }

    for v in sorted_videos:
        if v.uuid not in exported:
            continue

        duration = v.exif_info.duration if v.exif_info else 0
        is_portrait = v.height > v.width if v.height and v.width else False

        playlist["videos"].append({
            "uuid": v.uuid,
            "date": v.date.isoformat(),
            "duration": duration,
            "filename": v.original_filename,
            "persons": v.persons,
            "is_portrait": is_portrait,
            "width": v.width,
            "height": v.height,
            "path": str(exported[v.uuid].absolute())
        })

    playlist_path = projects_dir / "playlist.json"
    playlist_path.write_text(json.dumps(playlist, indent=2))

    console.print(f"\n[green]Created playlist: {playlist_path}[/green]")
    return playlist_path


def build_portrait_filter(input_idx: int) -> str:
    """Build ffmpeg filter for portrait video with blurred pillarbox."""
    return (
        f"[{input_idx}:v]split[{input_idx}orig][{input_idx}copy];"
        f"[{input_idx}copy]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={TARGET_WIDTH}:{TARGET_HEIGHT},gblur=sigma=50[{input_idx}blur];"
        f"[{input_idx}blur][{input_idx}orig]overlay=(W-w)/2:(H-h)/2,"
        f"setsar=1,fps={TARGET_FPS},settb=AVTB[v{input_idx}]"
    )


def build_landscape_filter(input_idx: int) -> str:
    """Build ffmpeg filter for landscape video (scale and pad)."""
    return (
        f"[{input_idx}:v]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={TARGET_WIDTH}:{TARGET_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
        f"setsar=1,fps={TARGET_FPS},settb=AVTB[v{input_idx}]"
    )


def compile_movie(playlist_path: Path, quality: str = "Auto (GPU if available)") -> Path:
    """Compile videos into a single movie using ffmpeg."""
    console.print("\n[bold]Step 7: Compiling Movie[/bold]\n")

    # Detect encoder and determine settings
    if quality == "Auto (GPU if available)":
        console.print("[dim]Detecting available encoders...[/dim]")
        encoder, enc_settings, tested = detect_best_encoder()
        quality_tier = "balanced"

        encoder_name = ENCODER_NAMES.get(encoder, encoder)

        if encoder == "libx265":
            # CPU fallback - explain why
            failed_encoders = [ENCODER_NAMES.get(e, e) for e in tested]
            console.print(f"[yellow]No GPU encoder available[/yellow]")
            console.print(f"[dim]Tested: {', '.join(failed_encoders)}[/dim]")
            console.print(f"[dim]This may be due to missing drivers, unsupported hardware,[/dim]")
            console.print(f"[dim]or FFmpeg compiled without hardware encoder support.[/dim]")
            console.print(f"[cyan]Using: {encoder_name} (slower but works everywhere)[/cyan]")
        else:
            # GPU encoder found
            console.print(f"[green]GPU encoder detected![/green]")
            console.print(f"[cyan]Using: {encoder_name}[/cyan]")
    else:
        # Manual quality selection - use CPU encoder
        encoder = "libx265"
        enc_settings = _get_encoder_settings("libx265")
        quality_tier = {
            "High (best quality, slower)": "high",
            "Balanced (good quality)": "balanced",
            "Fast (preview quality)": "fast",
        }.get(quality, "balanced")
        console.print(f"[cyan]Using: {ENCODER_NAMES.get(encoder, encoder)} ({quality_tier})[/cyan]")

    console.print()  # Blank line before progress info

    with open(playlist_path) as f:
        playlist = json.load(f)

    videos = playlist["videos"]
    if not videos:
        console.print("[red]No videos in playlist[/red]")
        return None

    # Calculate total duration for progress tracking
    total_duration = sum(v["duration"] for v in videos)
    if len(videos) > 1:
        total_duration -= (len(videos) - 1) * TRANSITION_DURATION

    project_dir = playlist_path.parent

    # Generate descriptive filename from playlist metadata
    filters = playlist["filters"]
    start_date = datetime.fromisoformat(filters["start_date"])
    end_date = datetime.fromisoformat(filters["end_date"])
    people = filters.get("people")

    output_filename = generate_output_filename(start_date, end_date, people)
    output_path = project_dir / output_filename

    # Build ffmpeg command
    inputs = []
    filter_parts = []

    # Add input files and normalize filters
    for i, v in enumerate(videos):
        inputs.extend(["-i", v["path"]])

        if v["is_portrait"]:
            filter_parts.append(build_portrait_filter(i))
        else:
            filter_parts.append(build_landscape_filter(i))

        # Audio normalization
        filter_parts.append(f"[{i}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[a{i}]")

    # Build xfade chain for video
    if len(videos) == 1:
        # Single video - just use normalized output
        filter_parts.append(f"[v0]null[vout]")
        filter_parts.append(f"[a0]anull[aout]")
    else:
        # Multiple videos - chain xfade transitions
        cumulative_duration = 0

        for i in range(len(videos) - 1):
            if i == 0:
                v_in1 = f"[v{i}]"
                a_in1 = f"[a{i}]"
            else:
                v_in1 = f"[vt{i-1}]"
                a_in1 = f"[at{i-1}]"

            v_in2 = f"[v{i+1}]"
            a_in2 = f"[a{i+1}]"

            # Calculate offset: cumulative duration minus transitions already applied
            offset = cumulative_duration + videos[i]["duration"] - TRANSITION_DURATION
            cumulative_duration = offset

            if i == len(videos) - 2:
                v_out = "[vout]"
                a_out = "[aout]"
            else:
                v_out = f"[vt{i}]"
                a_out = f"[at{i}]"

            filter_parts.append(
                f"{v_in1}{v_in2}xfade=transition=fade:duration={TRANSITION_DURATION}:offset={offset:.3f}{v_out}"
            )
            filter_parts.append(
                f"{a_in1}{a_in2}acrossfade=d={TRANSITION_DURATION}:c1=tri:c2=tri{a_out}"
            )

    filter_complex = ";".join(filter_parts)

    # Build encoder-specific command
    cmd = ["ffmpeg", "-y"]
    cmd.extend(inputs)
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", encoder,
        "-pix_fmt", enc_settings["pix_fmt"],
        enc_settings["quality_flag"], enc_settings["quality_values"][quality_tier],
    ])

    # Add encoder-specific extra args
    cmd.extend(enc_settings.get("extra_args", []))

    # Add preset for CPU encoder (libx265 only)
    if encoder == "libx265" and "presets" in enc_settings:
        cmd.extend(["-preset", enc_settings["presets"][quality_tier]])
        if quality_tier == "high":
            cmd.extend(["-tune", "fastdecode", "-x265-params", "aq-mode=3"])

    cmd.extend([
        "-tag:v", "hvc1",  # For Apple compatibility
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(output_path)
    ])

    # Show command info
    console.print("[dim]Running ffmpeg...[/dim]")
    console.print(f"[dim]Output: {output_path}[/dim]")
    console.print(f"[dim]Estimated duration: {format_duration(total_duration)}[/dim]\n")

    try:
        # Run ffmpeg with progress bar
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )

        # Use Rich progress bar instead of raw ffmpeg output
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Encoding...", total=total_duration)

            for line in process.stdout:
                # Parse time=HH:MM:SS.ms from ffmpeg output
                if "time=" in line:
                    time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})', line)
                    if time_match:
                        h, m, s, ms = map(int, time_match.groups())
                        current_seconds = h * 3600 + m * 60 + s + ms / 100
                        progress.update(task, completed=min(current_seconds, total_duration))

        process.wait()

        if process.returncode == 0:
            console.print(f"\n[bold green]Movie created successfully: {output_path}[/bold green]")

            # Show file size
            if output_path.exists():
                size = output_path.stat().st_size
                console.print(f"[dim]Output size: {format_size(size)}[/dim]")

            return output_path
        else:
            console.print(f"\n[red]ffmpeg failed with return code {process.returncode}[/red]")
            return None

    except FileNotFoundError:
        console.print("[red]ffmpeg not found. Please install with: brew install ffmpeg[/red]")
        return None
    except Exception as e:
        console.print(f"[red]Error running ffmpeg: {e}[/red]")
        return None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Video Compiler")
    parser.add_argument(
        "--recompile", "-r",
        type=str,
        metavar="PLAYLIST",
        help="Recompile from existing playlist.json file"
    )
    args = parser.parse_args()

    # Handle recompile mode
    if args.recompile:
        playlist_path = Path(args.recompile)
        if not playlist_path.exists():
            console.print(f"[red]Playlist not found: {playlist_path}[/red]")
            sys.exit(1)

        console.print(f"\n[bold cyan]Recompiling: {playlist_path.parent.name}[/bold cyan]\n")

        # Delete existing output files (could have descriptive name)
        existing_outputs = list(playlist_path.parent.glob("*.mp4"))
        for old_output in existing_outputs:
            old_output.unlink()
            console.print(f"[dim]Removed existing {old_output.name}[/dim]")

        # Prompt for quality selection
        quality = prompt_quality_selection()
        compile_movie(playlist_path, quality)
        return

    console.print("\n[bold cyan]Video Compiler[/bold cyan]")
    console.print("[dim]Create compilation videos from your Photos library[/dim]\n")

    # Step 1: Date range
    start_date, end_date = prompt_date_range()

    # Step 2: Query videos
    videos = query_videos(start_date, end_date)

    if not videos:
        console.print("[yellow]No videos found in the specified date range[/yellow]")
        return

    # Step 3: People selection
    persons = get_unique_persons(videos)
    selected_people = prompt_people_selection(persons)
    videos = filter_by_people(videos, selected_people)

    if not videos:
        console.print("[yellow]No videos match the selected people filter[/yellow]")
        return

    # Step 4: Duration filter
    min_dur, max_dur = prompt_duration_filter()
    videos = filter_by_duration(videos, min_dur, max_dur)

    if not videos:
        console.print("[yellow]No videos match the duration filter[/yellow]")
        return

    # Step 5: Display summary
    display_video_summary(videos)

    # Confirm to proceed
    if not questionary.confirm("\nProceed to copy videos?", default=True).ask():
        console.print("[dim]Cancelled[/dim]")
        return

    # Step 6: Export videos
    exported = export_videos(videos)

    if not exported:
        console.print("[red]No videos were exported[/red]")
        return

    # Step 7: Create playlist
    console.print("\n[bold]Step 6: Create Project[/bold]")

    # Generate default project name using same sortable format as output filename
    default_name = generate_output_filename(start_date, end_date, selected_people)
    default_name = default_name.removesuffix(".mp4")  # Remove .mp4 extension for folder name

    project_name = questionary.text(
        "Project name:",
        default=default_name,
        validate=lambda x: bool(x.strip()) or "Please enter a project name"
    ).ask()

    if not project_name:
        console.print("[dim]Cancelled[/dim]")
        return

    filters = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "people": selected_people,
        "min_duration": min_dur,
        "max_duration": max_dur
    }

    playlist_path = create_playlist(videos, project_name, filters, exported)

    # Step 8: Compile movie
    if questionary.confirm("\nGenerate final movie now?", default=True).ask():
        # Prompt for quality selection
        quality = prompt_quality_selection()
        output_path = compile_movie(playlist_path, quality)

        if output_path:
            console.print(f"\n[bold green]Done![/bold green]")
            console.print(f"[dim]Project folder: {playlist_path.parent}[/dim]")
    else:
        console.print(f"\n[dim]Playlist saved. Run later with the playlist file.[/dim]")
        console.print(f"[dim]Project folder: {playlist_path.parent}[/dim]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[dim]Cancelled[/dim]")
        sys.exit(0)
