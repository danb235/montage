# Montage

**Create beautiful video compilations from your Apple Photos library with a single command.**

Montage is a command-line tool for macOS that queries your Photos app, lets you filter videos by date, people, and duration, then compiles them into a polished movie with smooth transitions—all without leaving your terminal.

![macOS](https://img.shields.io/badge/platform-macOS-blue) ![Python 3.11](https://img.shields.io/badge/python-3.11-green)

---

## Features

- **Date Range Filtering** — Select videos from specific time periods (holidays, vacations, monthly highlights)
- **People Filtering** — Leverage Photos' face recognition to include only videos featuring specific people
- **Duration Filtering** — Exclude clips that are too short or too long
- **Automatic Transitions** — 1-second fade transitions between clips with audio crossfade
- **Smart Aspect Ratio Handling** — Portrait videos get a blurred background; landscape videos are letterboxed
- **Hardware Acceleration** — Uses GPU encoding when available (VideoToolbox on Mac)
- **Recompile Support** — Change quality settings without re-exporting from Photos
- **Project Organization** — Saves projects with metadata for future editing

---

## Quick Start

### Prerequisites

- **macOS** (required — uses Apple Photos integration)
- **Python 3.11**
- **ffmpeg** (for video encoding)

### Installation

```bash
# Install ffmpeg (if not already installed)
brew install ffmpeg

# Clone the repository
git clone https://github.com/danb235/montage.git
cd montage

# Create virtual environment with Python 3.11
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### First Run

```bash
python main.py
```

That's it! The interactive prompts will guide you through creating your first compilation.

---

## Usage Examples

### Example 1: Monthly Family Compilation

Create a compilation of all videos from December 2025:

```
$ python main.py

📅 Enter start date (YYYY-MM-DD): 2025-12-01
📅 Enter end date (YYYY-MM-DD): 2025-12-31

Found 47 videos from this period.

👥 Select people to include:
  ◉ All (include all videos)
  ○ Casey
  ○ Jessica
  ○ Grandma

> Selected: All

⏱️  Minimum duration (seconds, or Enter to skip):
⏱️  Maximum duration (seconds, or Enter to skip):

┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Date               ┃ Duration ┃ People            ┃ Size       ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ 2025-12-01 09:15   │ 0:32     │ Casey             │ 45.2 MB    │
│ 2025-12-03 14:22   │ 1:15     │ Casey, Jessica    │ 98.1 MB    │
│ 2025-12-07 18:45   │ 0:18     │                   │ 22.4 MB    │
│ ...                │ ...      │ ...               │ ...        │
└────────────────────┴──────────┴───────────────────┴────────────┘

📊 Total: 47 videos | 2.3 GB | ~18 minutes of footage

📁 Project name [december-2025]:

✅ Proceed with export? [Y/n]: y

Exporting videos... ━━━━━━━━━━━━━━━━━━━━ 100% 47/47

🎬 Select quality:
  ◉ Auto (GPU if available)
  ○ High (best quality, slower)
  ○ Balanced
  ○ Fast (preview)

Compiling... ━━━━━━━━━━━━━━━━━━━━ 100%

✅ Created: projects/december-2025/output.mp4 (186 MB)
```

### Example 2: Compilation Featuring Specific People

Make a highlight reel of just your kids from the past 3 months:

```
$ python main.py

📅 Enter start date (YYYY-MM-DD): 2025-10-01
📅 Enter end date (YYYY-MM-DD): 2025-12-31

Found 156 videos from this period.

👥 Select people to include:
  ○ All (include all videos)
  ◉ Casey
  ◉ Emma
  ○ Jessica
  ○ Mike

> Selected: Casey, Emma

Filtering... Found 43 videos featuring Casey or Emma.
```

### Example 3: Filter by Duration

Exclude very short clips (under 5 seconds) and very long recordings (over 2 minutes):

```
$ python main.py

📅 Enter start date (YYYY-MM-DD): 2025-12-01
📅 Enter end date (YYYY-MM-DD): 2025-12-31

Found 47 videos from this period.

👥 Select people to include:
> Selected: All

⏱️  Minimum duration (seconds, or Enter to skip): 5
⏱️  Maximum duration (seconds, or Enter to skip): 120

Filtering by duration... 31 videos remaining.
```

### Example 4: Recompile with Different Quality

Already created a project but want better quality? Recompile without re-exporting:

```
$ python main.py --recompile projects/december-2025/playlist.json

📂 Loaded project: december-2025
   47 videos | Last compiled: 2025-12-20

🎬 Select quality:
  ○ Auto (GPU if available)
  ◉ High (best quality, slower)    <-- Choose higher quality
  ○ Balanced
  ○ Fast (preview)

Compiling with high quality... ━━━━━━━━━━━━━━━━━━━━ 100%

✅ Created: projects/december-2025/output.mp4 (312 MB)
```

Shorthand:
```bash
python main.py -r projects/december-2025/playlist.json
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

| Setting   | Description                          | Use Case                    |
|-----------|--------------------------------------|-----------------------------|
| **Auto**  | Uses GPU if available, else balanced | Default, recommended        |
| **High**  | Best quality, slower encoding        | Final exports, archival     |
| **Balanced** | Good quality, reasonable speed    | Everyday use                |
| **Fast**  | Quick encode, lower quality          | Previews, drafts            |

### Hardware Acceleration

Montage automatically detects and uses the best available encoder:

| Platform | Preferred Encoder       | Fallback        |
|----------|-------------------------|-----------------|
| macOS    | VideoToolbox (GPU)      | libx265 (CPU)   |
| Windows  | NVENC / QuickSync / AMF | libx265 (CPU)   |
| Linux    | NVENC / VAAPI           | libx265 (CPU)   |

---

## Project Structure

```
montage/
├── main.py              # Main script
├── videos/              # Cached exports from Photos (auto-created)
│   ├── <uuid>.mov
│   └── ...
└── projects/            # Your compilation projects (auto-created)
    └── december-2025/
        ├── playlist.json   # Video list + metadata
        └── output.mp4      # Final compiled video
```

### The playlist.json File

Each project saves a `playlist.json` containing:
- List of video UUIDs and file paths
- Original filter settings (dates, people, duration)
- Video metadata (duration, dimensions, people detected)

This allows you to recompile with different quality settings without re-querying Photos.

---

## Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| macOS       | 10.15+  | Required for Photos integration |
| Python      | 3.11    | Specified in `.python-version` |
| ffmpeg      | 4.0+    | Install via `brew install ffmpeg` |

### Python Dependencies

Installed automatically from `requirements.txt`:
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
