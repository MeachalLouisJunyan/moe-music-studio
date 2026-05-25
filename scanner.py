#!/usr/bin/env python3
"""Directory scanner — discovers audio files and extracts metadata."""

import os
import subprocess
from pathlib import Path

SUPPORTED_EXTS = {
    ".flac", ".wav", ".wave", ".aiff", ".aif", ".aifc",
    ".alac", ".ape", ".wv", ".tta", ".m4a",
    ".dsf", ".dff",
    ".mp3", ".mp2", ".mp1",
    ".aac", ".m4a", ".m4b", ".m4p", ".m4r", ".3gp", ".3g2",
    ".ogg", ".oga", ".ogv", ".ogx", ".spx", ".opus",
    ".wma", ".asf", ".wmv",
    ".ac3", ".eac3", ".dts", ".mka",
    ".ra", ".rm", ".ram",
    ".amr", ".awb",
    ".au", ".snd",
    ".caf",
    ".voc",
    ".mid", ".midi", ".rmi",
    ".aa", ".aax",
    ".raw", ".pcm",
}


def find_ffmpeg():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return "ffmpeg"
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    candidates = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\tools\ffmpeg\bin\ffmpeg.exe",
        "/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg",
    ]
    for p in candidates:
        if Path(p).is_file():
            return p
    return None


def _parse_ffprobe_output(raw):
    result = {"title": "", "artist": "", "album": "", "genre": "",
              "year": 0, "duration": 0.0, "format": "",
              "bitrate": 0, "sample_rate": 0, "channels": 0}
    for line in raw.splitlines():
        line = line.strip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        if key == "title":
            result["title"] = val
        elif key == "artist":
            result["artist"] = val
        elif key == "album":
            result["album"] = val
        elif key == "genre":
            result["genre"] = val
        elif key == "date" or key == "year":
            try:
                result["year"] = int(val[:4])
            except ValueError:
                pass
        elif key == "duration":
            try:
                result["duration"] = float(val)
            except ValueError:
                pass
        elif key == "format_name":
            result["format"] = val.split(",")[0].strip()
        elif key == "bit_rate":
            try:
                result["bitrate"] = int(float(val) / 1000)
            except ValueError:
                pass
        elif key == "sample_rate":
            try:
                result["sample_rate"] = int(val)
            except ValueError:
                pass
        elif key == "channels":
            try:
                result["channels"] = int(val)
            except ValueError:
                pass
    return result


def probe_file(file_path):
    """Extract metadata from an audio file using ffprobe."""
    ffprobe = None
    ffmpeg_path = find_ffmpeg()
    if ffmpeg_path:
        ffprobe = ffmpeg_path.replace("ffmpeg", "ffprobe")
        if not Path(ffprobe).is_file():
            ffprobe = "ffprobe"

    if not ffprobe:
        return _parse_ffprobe_output("")

    try:
        result = subprocess.run(
            [ffprobe, "-v", "quiet", "-show_entries",
             "format=format_name,duration,bit_rate:format_tags=title,artist,"
             "album,genre,date",
             "-of", "default=noprint_wrappers=1",
             str(file_path)],
            capture_output=True, text=True, timeout=30)
        meta = _parse_ffprobe_output(result.stdout)

        # Get stream info for channels/sample_rate
        r2 = subprocess.run(
            [ffprobe, "-v", "quiet", "-select_streams", "a:0",
             "-show_entries", "stream=sample_rate,channels",
             "-of", "default=noprint_wrappers=1",
             str(file_path)],
            capture_output=True, text=True, timeout=30)
        for line in r2.stdout.splitlines():
            line = line.strip()
            if line.startswith("sample_rate="):
                try:
                    meta["sample_rate"] = int(line.split("=", 1)[1])
                except ValueError:
                    pass
            elif line.startswith("channels="):
                try:
                    meta["channels"] = int(line.split("=", 1)[1])
                except ValueError:
                    pass

        return meta
    except Exception:
        return _parse_ffprobe_output("")


def scan_directory(root_dir, progress_callback=None):
    """Recursively find all audio files in a directory and probe metadata."""
    root = Path(root_dir)
    results = []
    all_files = []

    for dirpath, _, fnames in os.walk(root):
        for fn in fnames:
            fp = Path(dirpath) / fn
            if fp.suffix.lower() in SUPPORTED_EXTS:
                all_files.append(fp)

    total = len(all_files)
    for i, fp in enumerate(all_files):
        meta = probe_file(fp)
        meta["file_path"] = str(fp.resolve())
        if not meta["format"]:
            meta["format"] = fp.suffix.lstrip(".").upper()
        results.append(meta)

        if progress_callback:
            progress_callback(i + 1, total, fp.name)

    return results


def quick_scan(root_dir):
    """Fast scan without metadata probing — just find file paths."""
    root = Path(root_dir)
    files = []
    for dirpath, _, fnames in os.walk(root):
        for fn in fnames:
            fp = Path(dirpath) / fn
            if fp.suffix.lower() in SUPPORTED_EXTS:
                files.append(str(fp.resolve()))
    return sorted(files, key=str.lower)
