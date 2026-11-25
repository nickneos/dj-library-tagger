#!/usr/bin/env python3
import argparse
import re
from collections import defaultdict
from pathlib import Path
from mutagen.id3 import ID3, ID3NoHeaderError, TIT2, TPE1, TPE2, TALB, TDRC, TRCK, APIC
from mutagen.mp4 import MP4, MP4Cover

SUPPORTED_EXTS = {".mp3", ".m4a"}


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


def update_coverart(root: Path, dry_run: bool = True):
    files = sorted(
        f for f in root.rglob("*")
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS
    )

    for audio_file in files:
        rel_path = audio_file.relative_to(root)
        ext = audio_file.suffix.lower()

        cover = find_cover(audio_file)

        if dry_run:
            print(f"[DRY-RUN] {rel_path} -> Cover={cover.name if cover else 'None'}")
            continue

        if ext == ".mp3":

            if cover:
                try:
                    tags = ID3(audio_file)
                except ID3NoHeaderError:
                    tags = ID3()   
                
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
                tags.save(audio_file, v2_version=3)

        elif ext == ".m4a":

            if cover:
                audio = MP4(audio_file)
                if audio.tags is None:
                    audio.add_tags()
                
                img_fmt = MP4Cover.FORMAT_PNG if cover.suffix.lower() == ".png" else MP4Cover.FORMAT_JPEG
                audio.tags["covr"] = [MP4Cover(cover.read_bytes(), imageformat=img_fmt)]

                audio.save()

        print(f"[UPDATED] {rel_path} -> Cover={cover.name if cover else 'None'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tag DJ mixes (.mp3/.m4a) from path and embed cover art.")
    parser.add_argument("directory", type=Path, help="Path to 'DJ Sets' or an Artist folder")
    parser.add_argument("--apply", action="store_true", help="Write tags (default is dry-run)")
    args = parser.parse_args()

    update_coverart(args.directory.resolve(), dry_run=not args.apply)

