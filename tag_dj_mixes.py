#!/usr/bin/env python3
import argparse
import re
from collections import defaultdict
from pathlib import Path
from mutagen.id3 import ID3, ID3NoHeaderError, TIT2, TPE1, TPE2, TALB, TDRC, TRCK, APIC
from mutagen.mp4 import MP4, MP4Cover


# Matches: "[Artist/]Album/RawTitle"
PATH_PATTERN = re.compile(r"^(?:(?P<artist>[^/]+)/)?(?P<album>[^/]+)/(?P<raw_title>[^/]+)$")

DATE_PAT = r"\d{4}-\d{2}-\d{2}|\d{4}-\d{2}|\d{8}|\d{4}"

# Leading date: "2025-11-01 Title", "20240208 - Title", "2025 Title"
LEADING_DATE = re.compile(
    rf"^(?P<date>{DATE_PAT})(?:\s*-\s*|\s+)(?P<title>.+)$"
)

# Trailing date: "Title 2025-05-31", "Title - 2025", "Title (2025)", "Title [2025-05-31]"
TRAILING_DATE = re.compile(
    rf"^(?P<title>.+?)(?:(?:\s*-\s*|\s+)(?P<d1>{DATE_PAT})|\s*(?:-\s*)?[\(\[](?P<d2>{DATE_PAT})[\)\]])$"
)

SUPPORTED_EXTS = {".mp3", ".m4a"}


def parse_title_and_date(raw_title: str) -> tuple[str, str | None]:
    raw_date = None
    title = raw_title

    if m := LEADING_DATE.match(raw_title):
        raw_date, title = m.group("date"), m.group("title")
    elif m := TRAILING_DATE.match(raw_title):
        title = m.group("title")
        raw_date = m.group("d1") or m.group("d2")

    if raw_date and len(raw_date) == 8 and raw_date.isdigit():
        raw_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"

    return title.strip(), raw_date


def find_cover(audio_path: Path) -> Path | None:
    stem_lower = audio_path.stem.lower()
    valid_exts = {".jpg", ".jpeg", ".png"}
    folder_names = {"cover.jpg", "cover.png", "folder.jpg", "folder.png"}

    # 1. Per-mix artwork (case-insensitive)
    for f in audio_path.parent.iterdir():
        if f.is_file() and f.suffix.lower() in valid_exts and f.stem.lower() == stem_lower:
            return f

    # 2. Album or Artist folder artwork (case-insensitive)
    for folder in (audio_path.parent, audio_path.parent.parent):
        for f in folder.iterdir():
            if f.is_file() and f.name.lower() in folder_names:
                return f
    return None


def tag_mp3(path: Path, artist: str, album: str, title: str, date: str | None, track_num: int | None, cover: Path | None):
    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        tags = ID3()

    tags["TPE1"] = TPE1(encoding=3, text=artist)
    tags["TPE2"] = TPE2(encoding=3, text=artist)
    tags["TALB"] = TALB(encoding=3, text=album)
    tags["TIT2"] = TIT2(encoding=3, text=title)

    if date:
        tags["TDRC"] = TDRC(encoding=3, text=date)

    if track_num is not None:
        tags["TRCK"] = TRCK(encoding=3, text=str(track_num))

    if cover:
        mime = "image/png" if cover.suffix.lower() == ".png" else "image/jpeg"
        tags.delall("APIC")
        tags.add(APIC(
            encoding=3,
            mime=mime,
            type=3,
            desc="Cover",
            data=cover.read_bytes()
        ))

    tags.update_to_v23()
    tags.save(path, v2_version=3)


def tag_m4a(path: Path, artist: str, album: str, title: str, date: str | None, track_num: int | None, cover: Path | None):
    audio = MP4(path)
    if audio.tags is None:
        audio.add_tags()

    audio.tags["\xa9ART"] = [artist]  # Artist
    audio.tags["aART"] = [artist]     # Album Artist
    audio.tags["\xa9alb"] = [album]   # Album
    audio.tags["\xa9nam"] = [title]   # Title

    if date:
        audio.tags["\xa9day"] = [date]

    if track_num is not None:
        audio.tags["trkn"] = [(track_num, 0)]

    if cover:
        img_fmt = MP4Cover.FORMAT_PNG if cover.suffix.lower() == ".png" else MP4Cover.FORMAT_JPEG
        audio.tags["covr"] = [MP4Cover(cover.read_bytes(), imageformat=img_fmt)]

    audio.save()


def process_library(root: Path, dry_run: bool = True, set_track_numbers: bool = False, exclude_va: bool = True):
    folders: dict[Path, list[Path]] = defaultdict(list)
    for f in root.rglob("*"):
        if exclude_va:
            if (f.parent.name.strip().lower() == "various artists"
                or f.parent.parent.name.strip().lower() == "various artists"
            ):
                continue
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS:
            folders[f.parent].append(f)

    for folder in sorted(folders.keys()):
        file_list = sorted(folders[folder], key=lambda p: p.name.lower())

        for track_idx, audio_file in enumerate(file_list, start=1):
            rel_no_ext = audio_file.relative_to(root).with_suffix("").as_posix()
            match = PATH_PATTERN.match(rel_no_ext)

            if not match:
                print(f"[SKIP] No pattern match: {rel_no_ext}{audio_file.suffix}")
                continue

            data = match.groupdict()
            artist = data["artist"] or root.name
            album = data["album"]
            title, date = parse_title_and_date(data["raw_title"])

            # Fallback: extract date from album folder name if not found in track title
            if not date:
                _, date = parse_title_and_date(album)

            cover = find_cover(audio_file)
            track_num = track_idx if set_track_numbers else None

            track_info = f", Track='{track_num}'" if track_num is not None else ""
            run_type = "DRY-RUN" if dry_run else "UPDATE"
            print(
                f"[{run_type}] {rel_no_ext}{audio_file.suffix} ->\n\tArtist={artist!r}\n\tAlbum={album!r}\n\t"
                f"Date={date!r}\n\tTitle={title!r}{track_info}\n\tCover={cover.name if cover else 'None'}\n"
            )

            if dry_run:
                continue

            if audio_file.suffix.lower() == ".mp3":
                tag_mp3(audio_file, artist, album, title, date, track_num, cover)
            elif audio_file.suffix.lower() == ".m4a":
                tag_m4a(audio_file, artist, album, title, date, track_num, cover)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tag DJ mixes (.mp3/.m4a) from path and embed cover art.")
    parser.add_argument("directory", type=Path, help="Path to 'DJ Sets' or an Artist folder")
    parser.add_argument("-t", "--track-numbers", action="store_true", help="Assign sequential track numbers per folder")
    parser.add_argument("--apply", action="store_true", help="Write tags (default is dry-run)")
    parser.add_argument("--include-va", action="store_true", help="Include folder Various Artists")
    args = parser.parse_args()

    process_library(
        args.directory.resolve(),
        dry_run=not args.apply,
        set_track_numbers=args.track_numbers,
        exclude_va=not args.include_va
    )
