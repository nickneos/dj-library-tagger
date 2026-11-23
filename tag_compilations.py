#!/usr/bin/env python3
import argparse
from pathlib import Path
from mutagen.id3 import ID3, ID3NoHeaderError, TPE2, TCMP, TXXX
from mutagen.mp4 import MP4, MP4FreeForm


SUPPORTED_EXTS = {".mp3", ".m4a"}


def update_compilations(root: Path, album_artist: str, release_type: str, dry_run: bool = True):
    files = sorted(
        f for f in root.rglob("*")
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS
    )

    for audio_file in files:
        rel_path = audio_file.relative_to(root)
        ext = audio_file.suffix.lower()

        if dry_run:
            print(
                f"[DRY-RUN] {rel_path} -> Album Artist={album_artist!r}, "
                f"RELEASETYPE={release_type!r}, Compilation=True"
            )
            continue

        if ext == ".mp3":
            try:
                tags = ID3(audio_file)
            except ID3NoHeaderError:
                tags = ID3()

            tags["TPE2"] = TPE2(encoding=3, text=album_artist)
            tags["TCMP"] = TCMP(encoding=3, text="1")
            tags["TXXX:RELEASETYPE"] = TXXX(
                encoding=3,
                desc="RELEASETYPE",
                text=release_type,
            )
            tags.update_to_v23()
            tags.save(audio_file, v2_version=3)

        elif ext == ".m4a":
            audio = MP4(audio_file)
            if audio.tags is None:
                audio.add_tags()

            audio.tags["aART"] = [album_artist]
            audio.tags["cpil"] = True
            audio.tags["----:com.apple.iTunes:RELEASETYPE"] = [
                MP4FreeForm(release_type.encode("utf-8"))
            ]
            audio.save()

        print(
            f"[UPDATED] {rel_path} -> Album Artist={album_artist!r}, "
            f"RELEASETYPE={release_type!r}, Compilation=True"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Set Album Artist, RELEASETYPE, and Compilation flag recursively."
    )
    parser.add_argument("directory", type=Path, help="Root folder of compilation albums")
    parser.add_argument(
        "-a", "--artist",
        default="Various Artists",
        help="Album Artist value (default: 'Various Artists')",
    )
    parser.add_argument(
        "-r", "--release-type",
        default="album;compilation",
        help="RELEASETYPE value (default: 'album;compilation')",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes to disk (default is dry-run)",
    )
    args = parser.parse_args()

    update_compilations(
        args.directory.resolve(),
        args.artist,
        args.release_type,
        dry_run=not args.apply,
    )
