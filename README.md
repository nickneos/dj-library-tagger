# dj-library-tagger

Lightweight, dependency-free CLI tools for batch-tagging `.mp3` and `.m4a` audio libraries directly on a Linux server using `python3-mutagen`. Designed to run locally over SSH so large audio files are updated directly on disk without slow SMB network transfers.

---

## Scripts Overview

| Script | Purpose |
| :--- | :--- |
| **`tag_dj_mixes.py`** | Extracts `Artist`, `Album Artist`, `Album`, `Title`, `Year`, and `Date` from folder/file paths and embeds cover art for DJ mixes. |
| **`tag_compilations.py`** | Recursively tags compilation albums with `Album Artist`, `RELEASETYPE`, and the `Compilation` flag while preserving existing track metadata and artwork. |

---

## Requirements

- Python 3.10+
- `python3-mutagen`

Install on Debian / Ubuntu:

```bash
sudo apt update
sudo apt install --no-install-recommends python3-mutagen
```

Make both scripts executable:

```bash
chmod +x tag_dj_mixes.py tag_compilations.py
```

---

## 1. `tag_dj_mixes.py` — DJ Mix Tagger & Cover Art Embedder

### Features
- **Multi-format support:** Handles both `.mp3` (UTF-16 ID3v2.3) and `.m4a` (MP4 atoms).
- **Path-based metadata extraction:** Populates `Artist`, `Album Artist`, `Album`, `Title`, `Year`, and `Date` from your directory structure.
- **Flexible date parsing:** Extracts leading and trailing dates (`YYYY-MM-DD`, `YYYYMMDD`, `YYYY-MM`, `YYYY`, plus `(2025)` and `[2025-11-30]`) into metadata date/year fields while cleaning the title.
- **Smart cover art embedding:** Case-insensitive matching for `.jpg`, `.jpeg`, and `.png` artwork, replacing existing cover art cleanly to prevent duplicate images.
- **Optional sequential track numbering:** Assigns plain track numbers (`1`, `2`, `3`, ...) per folder in alphanumeric order via `-t` / `--track-numbers`.
- **Safe dry-run mode:** Previews changes without modifying files unless `--apply` is passed.

### Expected Folder Structure
Works whether pointed at your root `DJ Sets/` directory or directly at a specific artist's folder (e.g., `DJ Neos/`):

```text
DJ Sets/
└── DJ Neos/                        # -> Artist & Album Artist
    ├── cover.jpg                   # -> Fallback artwork for all albums
    ├── DJ Mixes/                   # -> Album
    │   ├── cover.png               # -> Album-level artwork
    │   ├── 20240208 - Urban Mix.mp3
    │   ├── Dance Mix 20250531.m4a
    │   ├── Dance Mix 20250531.png  # -> Mix-specific artwork (highest priority)
    │   └── Summer Mix (2025).mp3
    └── Gigs/                       # -> Album
        └── 2025-11-01 Claire and Will.mp3
```

### Supported Date Formats

| Filename Example | Extracted `Title` | Extracted `Date` |
| :--- | :--- | :--- |
| `2025-11-01 Claire and Will.mp3` | `Claire and Will` | `2025-11-01` |
| `20240208 - Urban Mix.mp3` | `Urban Mix` | `2024-02-08` |
| `Dance Mix 20250531.m4a` | `Dance Mix` | `2025-05-31` |
| `Dance Mix - 2025-05-31.mp3` | `Dance Mix` | `2025-05-31` |
| `Summer Mix (2025).mp3` | `Summer Mix` | `2025` |
| `Club Classics [2025-11-30].m4a` | `Club Classics` | `2025-11-30` |
| `Club Classics 2024.mp3` | `Club Classics` | `2024` |
| `80s Mix #1.mp3` | `80s Mix #1` | *(None)* |

### Cover Art Lookup Priority (Case-Insensitive)
1. `<Mix Filename>.jpg` / `.jpeg` / `.png` in the same folder
2. `cover.jpg` / `cover.png` / `folder.jpg` / `folder.png` in the **Album** folder
3. `cover.jpg` / `cover.png` / `folder.jpg` / `folder.png` in the **Artist** folder

### Usage

```bash
# 1. Dry-run preview (default)
./tag_dj_mixes.py "DJ Neos/"

# 2. Apply tags and cover art
./tag_dj_mixes.py "DJ Neos/" --apply

# 3. Apply tags, cover art, and sequential track numbers (1, 2, 3...)
./tag_dj_mixes.py "DJ Neos/" -t --apply
```

### CLI Options (`tag_dj_mixes.py`)

| Flag | Description |
| :--- | :--- |
| `directory` | Path to the root `DJ Sets` directory or an individual `Artist` folder. |
| `-t`, `--track-numbers` | Assign sequential track numbers (`1`, `2`, `3`...) per folder alphanumerically. |
| `--apply` | Write tags and artwork to files (omitting this runs a safe dry-run). |
| `--include-va` | Include **various artists** folder during scan. By default, ommiting this excludes audio in a **various artists** folder.  |
| `-h`, `--help` | Show help message and exit. |

---

## 2. `tag_compilations.py` — Compilation Album Tagger

### Features
- **Preserves existing track metadata:** Keeps individual track artists, titles, album names, track numbers, and cover art intact.
- **Standard compilation tags:** Writes:
  - `Album Artist` (`TPE2` / `aART`) → `Various Artists`
  - `RELEASETYPE` (`TXXX:RELEASETYPE` / `----:com.apple.iTunes:RELEASETYPE`) → `album;compilation`
  - `Compilation` flag (`TCMP=1` / `cpil=True`)
- **Recursive processing:** Scans all nested album subfolders under a target compilations directory.
- **Safe dry-run mode:** Previews all changes unless `--apply` is passed.

### Usage

```bash
# 1. Dry-run preview across all nested compilation folders
./tag_compilations.py "/path/to/Compilations"

# 2. Apply compilation tags to all nested MP3/M4A files
./tag_compilations.py "/path/to/Compilations" --apply

# 3. Optional: specify a custom Album Artist or Release Type
./tag_compilations.py "/path/to/Compilations" -a "Ministry of Sound" -r "album;compilation" --apply
```

### CLI Options (`tag_compilations.py`)

| Flag | Description |
| :--- | :--- |
| `directory` | Root folder containing compilation albums. |
| `-a`, `--artist` | Album Artist value to write (default: `Various Artists`). |
| `-r`, `--release-type` | `RELEASETYPE` value to write (default: `album;compilation`). |
| `--apply` | Write changes to disk (omitting this runs a safe dry-run). |
| `-h`, `--help` | Show help message and exit. |

---

## Verifying Written Tags

Inspect the resulting metadata on any file using tools included with `python3-mutagen`:

```bash
# Inspect an MP3 file
mid3v2 -l "DJ Neos/Gigs/2025-11-01 Claire and Will.mp3"

# Inspect an M4A (or MP3) file
mutagen-inspect "DJ Neos/DJ Mixes/Dance Mix 20250531.m4a"
```
