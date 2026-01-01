# Montage

**Create beautiful video compilations from your Apple Photos library with a single command.**

Montage is a command-line tool for macOS that queries your Photos app, lets you filter videos by date, people, and duration, then compiles them into a polished movie with smooth transitions—all without leaving your terminal.

![macOS](https://img.shields.io/badge/platform-macOS-blue) ![Python 3.11](https://img.shields.io/badge/python-3.11-green)

---

## Features

- **Date Range Filtering** — Select videos from specific time periods (holidays, vacations, monthly highlights)
- **People Filtering** — Leverage Photos' face recognition to include only videos featuring specific people
- **Duration Filtering** — Exclude clips that are too short or too long
- **Interactive Video Preview** — Watch each video and swipe right to keep or left to skip (Tinder-style)
- **Video Rotation** — Fix sideways videos during preview; rotation is applied in final compilation
- **Automatic Transitions** — 1-second fade transitions between clips with audio crossfade
- **Smart Aspect Ratio Handling** — Portrait videos get a blurred background; landscape videos are letterboxed
- **Hardware Acceleration** — Uses GPU encoding when available (VideoToolbox on Mac)
- **Recompile Support** — Change quality settings without re-exporting from Photos
- **Project Organization** — Saves projects with metadata for future editing

---

## Quick Start

### Prerequisites

- **macOS** (required — uses Apple Photos integration)
- **uv** (Python package manager — handles Python version automatically)
- **ffmpeg** (for video encoding)
- **mpv** (optional — for interactive video preview)

### Installation

```bash
# Install uv, ffmpeg, and mpv
brew install uv ffmpeg mpv

# Clone the repository
git clone https://github.com/danb235/montage.git
cd montage

# Run! (uv automatically installs Python 3.11 and all dependencies)
uv run montage
```

That's it! No need to manually create virtual environments or install Python — **uv handles everything automatically**.

### Alternative: Manual Setup

If you prefer traditional pip:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
python main.py
```

---

## Usage Examples

### Example 1: Monthly Family Compilation

Create a compilation of all videos from December 2025:

```
$ uv run montage

Start date (YYYY-MM-DD): 2025-12-01
End date (YYYY-MM-DD): 2025-12-31

Found 47 videos in date range

Select people to include (space to select, enter to confirm):
  ○ ALL (include all videos)
  ○ Casey
  ○ Jessica
  ○ Grandma

> Including all videos

Minimum duration in seconds (press Enter for no minimum):
Maximum duration in seconds (press Enter for no maximum):

┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Date               ┃ Duration ┃ People            ┃ Size       ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ 2025-12-01 09:15   │ 0:32     │ Casey             │ 45.2 MB    │
│ 2025-12-03 14:22   │ 1:15     │ Casey, Jessica    │ 98.1 MB    │
│ 2025-12-07 18:45   │ 0:18     │                   │ 22.4 MB    │
│ ...                │ ...      │ ...               │ ...        │
└────────────────────┴──────────┴───────────────────┴────────────┘

Summary:
  Total videos: 47
  Total size: 2.3 GB
  Total duration: ~18 minutes
  Estimated output: ~17 minutes (with 46 transitions)

Project name: [2025.12.01.to.2025.12.31.All]

Proceed to copy videos? [Y/n]: y

Exporting... ━━━━━━━━━━━━━━━━━━━━ 100% 47/47

Generate final movie now? [Y/n]: y

Encoding quality:
  > GPU - Balanced (fast, smaller files)
    GPU - High (fast, good quality)
    GPU - Fast (fastest, preview quality)
    ──────────────
    CPU - Balanced (moderate speed)
    CPU - High (slow, best quality)
    CPU - Fast (faster, lower quality)

Encoding... ━━━━━━━━━━━━━━━━━━━━ 100%

Movie created successfully: projects/2025.12.01.to.2025.12.31.All/2025.12.01.to.2025.12.31.All.mp4
Output size: 186 MB
```

### Example 2: Compilation Featuring Specific People

Make a highlight reel of just your kids from the past 3 months:

```
$ uv run montage

Start date (YYYY-MM-DD): 2025-10-01
End date (YYYY-MM-DD): 2025-12-31

Found 156 videos in date range

Select people to include (space to select, enter to confirm):
  ○ ALL (include all videos)
  ◉ Casey
  ◉ Emma
  ○ Jessica
  ○ Mike

> Filtering to: Casey, Emma

Found 43 videos featuring Casey or Emma.
```

### Example 3: Filter by Duration

Exclude very short clips (under 5 seconds) and very long recordings (over 2 minutes):

```
$ uv run montage

Start date (YYYY-MM-DD): 2025-12-01
End date (YYYY-MM-DD): 2025-12-31

Found 47 videos in date range

Select people to include (space to select, enter to confirm):
> Including all videos

Minimum duration in seconds (press Enter for no minimum): 5
Maximum duration in seconds (press Enter for no maximum): 120

Duration filter: min: 5s, max: 120s
31 videos remaining.
```

### Example 4: Interactive Video Preview (Tinder-style)

Don't want all 47 videos? Preview each one and decide what to keep:

```
$ uv run montage

Start date (YYYY-MM-DD): 2025-12-01
End date (YYYY-MM-DD): 2025-12-31

Found 47 videos in date range

...filters applied...

Summary:
  Total videos: 47
  Total size: 2.3 GB

Preview and select videos individually? [y/N]: y

Interactive Video Selection
Watch each video and decide to keep or skip

────────────────────────────────────────────────────────
Video 1 of 47                    Kept: 0 | Skipped: 0
────────────────────────────────────────────────────────
Date:       2025-12-01 09:15
Duration:   0:32
People:     Casey
Filename:   IMG_1234.MOV
Dimensions: 1920x1080
Size:       45.2 MB
────────────────────────────────────────────────────────
→/Enter: Keep   ←/Backspace: Skip   R: Rotate   U: Undo   Q: Quit

[mpv window opens with video playing]

✓ KEPT                           <- You pressed →

────────────────────────────────────────────────────────
Video 2 of 47                    Kept: 1 | Skipped: 0
...

════════════════════════════════════════════════════════
Selection Complete
════════════════════════════════════════════════════════
  Videos reviewed: 47
  Kept:            23 (49%)
  Skipped:         24 (51%)
════════════════════════════════════════════════════════

Updated Selection:
  Total videos: 23
  Total size: 1.1 GB

Proceed to copy videos? [Y/n]: y
```

**Keyboard controls during preview:**
| Key | Action |
|-----|--------|
| `→` or `Enter` | Keep video |
| `←` or `Backspace` | Skip video |
| `R` | Rotate video 90° (saved for final compilation) |
| `Space` | Pause/Resume playback (in mpv window) |
| `U` | Undo last decision |
| `Q` | Quit preview (asks about remaining) |

### Example 5: Recompile with Different Quality

Already created a project but want better quality? Recompile without re-exporting:

```
$ uv run montage --recompile projects/2025.12.01.to.2025.12.31.All/playlist.json

Recompiling: 2025.12.01.to.2025.12.31.All

Encoding quality:
  > GPU - High (fast, good quality)    <-- Choose higher quality
    GPU - Balanced (fast, smaller files)
    GPU - Fast (fastest, preview quality)
    ──────────────
    CPU - High (slow, best quality)
    CPU - Balanced (moderate speed)
    CPU - Fast (faster, lower quality)

Encoding... ━━━━━━━━━━━━━━━━━━━━ 100%

Movie created successfully: projects/2025.12.01.to.2025.12.31.All/2025.12.01.to.2025.12.31.All.mp4
Output size: 312 MB
```

Shorthand:
```bash
uv run montage -r projects/2025.12.01.to.2025.12.31.All/playlist.json
```

---

## How It Works

1. **Query Photos Library** — Uses [osxphotos](https://github.com/RhetTbull/osxphotos) to read your macOS Photos database
2. **Filter Videos** — Apply date range, people, and duration filters interactively
3. **Export to Cache** — Copies selected videos from Photos to a local `videos/` directory
4. **Create Project** — Saves metadata to `projects/<name>/playlist.json`
5. **Compile with ffmpeg** — Processes all clips with:
   - Standardized resolution (1080p @ 30fps)
   - Smart aspect ratio handling
   - 1-second fade transitions
   - Audio crossfading
   - Hardware-accelerated encoding

---

## Quality Settings

Montage offers both GPU and CPU encoding options:

### GPU Encoding (VideoToolbox)

| Setting   | Description                          | Use Case                    |
|-----------|--------------------------------------|-----------------------------|
| **GPU - High** | Best quality, fast encoding     | Final exports, archival     |
| **GPU - Balanced** | Good quality, smaller files | Everyday use (default)      |
| **GPU - Fast** | Quick encode, preview quality  | Previews, drafts            |

### CPU Encoding (libx265)

| Setting   | Description                          | Use Case                    |
|-----------|--------------------------------------|-----------------------------|
| **CPU - High** | Best quality, slow encoding     | Maximum quality, no GPU     |
| **CPU - Balanced** | Good quality, moderate speed | When GPU unavailable        |
| **CPU - Fast** | Faster encode, lower quality   | Quick drafts, no GPU        |

GPU options appear first when hardware encoding is available. If no GPU encoder is detected, GPU options are disabled and CPU options are shown as the default.

### Hardware Acceleration

Montage automatically detects and uses the best available encoder for your Mac:

| Encoder | Mac Support | Notes |
|---------|-------------|-------|
| VideoToolbox HEVC | 2017+ / Apple Silicon | Fastest, best quality |
| VideoToolbox H.264 | 2011+ | Fallback for older Macs |
| libx265 (CPU) | All Macs | Final fallback |

**Recommended:** Apple Silicon Macs (M1/M2/M3/M4) provide the best performance using the dedicated Media Engine.

---

## Project Structure

```
montage/
├── main.py              # Main script
├── videos/              # Cached exports from Photos (auto-created)
│   ├── <uuid>.mov
│   └── ...
└── projects/            # Your compilation projects (auto-created)
    └── 2025.12.01.to.2025.12.31.All/
        ├── playlist.json                    # Video list + metadata
        └── 2025.12.01.to.2025.12.31.All.mp4 # Final compiled video
```

### The playlist.json File

Each project saves a `playlist.json` containing:
- List of video UUIDs and file paths
- Original filter settings (dates, people, duration)
- Video metadata (duration, dimensions, people detected)
- Rotation settings for each video (if adjusted during preview)

This allows you to recompile with different quality settings without re-querying Photos.

---

## Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| macOS       | 10.15+  | Required for Photos integration |
| uv          | 0.4+    | Install via `brew install uv` |
| ffmpeg      | 4.3+    | Install via `brew install ffmpeg` |
| mpv         | 0.35+   | Install via `brew install mpv` (optional) |

Python 3.11 is automatically installed by uv when you run `uv run montage`.

### Python Dependencies

Managed automatically via `pyproject.toml` and `uv.lock`:
- `osxphotos` — Photos library access
- `questionary` — Interactive CLI prompts
- `rich` — Beautiful terminal output

---

## Troubleshooting

### "Photos library not found"

Ensure Photos.app has been opened at least once and has a library configured.

### "Permission denied" accessing Photos

Grant Terminal (or your terminal app) Full Disk Access:
1. Open **System Preferences → Security & Privacy → Privacy**
2. Select **Full Disk Access** from the left sidebar
3. Add your terminal application (Terminal.app, iTerm2, etc.)

### Videos showing as "missing" or failing to export

Some videos may be stored in iCloud. Ensure they're downloaded:
1. Open Photos.app
2. Select the video
3. Wait for download to complete (cloud icon disappears)

### Slow encoding

- Check if hardware acceleration is working: the tool will print which encoder it's using
- For faster previews, select "Fast" quality
- Close other applications using GPU resources

### "ffmpeg not found"

Install ffmpeg:
```bash
brew install ffmpeg
```

### Video preview not working / "mpv not available"

The interactive video preview requires mpv. Install it:
```bash
brew install mpv
```

If mpv is not installed, the preview feature is skipped and all filtered videos are included automatically.

### Video appears rotated/sideways

Some iPhone videos have rotation metadata that may display incorrectly. During interactive preview:
1. Press `R` to rotate the video 90°
2. Keep pressing `R` until it looks correct (cycles through 0°, 90°, 180°, 270°)
3. The rotation is saved and applied during final compilation

---

## License

MIT License

Copyright (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
