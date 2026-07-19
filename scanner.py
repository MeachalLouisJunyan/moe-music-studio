#!/usr/bin/env python3
"""Directory scanner — discovers audio files and extracts metadata."""

import os
import subprocess
import sys
from pathlib import Path

SUPPORTED_EXTS = {
    ".flac", ".wav", ".wave", ".aiff", ".aif", ".aifc",
    ".alac", ".ape", ".wv", ".tta",
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


# Keep ffmpeg/ffprobe from flashing console windows when running
# as a windowed (no-console) frozen app on Windows.
SUBPROCESS_FLAGS = (
    {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
)


def _bundle_dirs():
    """Directories where a bundled ffmpeg may live when frozen by PyInstaller."""
    dirs = []
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        dirs += [exe_dir, exe_dir / "_internal"]
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            dirs.append(Path(meipass))
    return dirs


_ffmpeg_cache = None


def find_ffmpeg():
    global _ffmpeg_cache
    if _ffmpeg_cache is not None:
        return _ffmpeg_cache or None

    exe_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    for d in _bundle_dirs():
        p = d / exe_name
        if p.is_file():
            _ffmpeg_cache = str(p)
            return _ffmpeg_cache
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True,
                       timeout=5, **SUBPROCESS_FLAGS)
        _ffmpeg_cache = "ffmpeg"
        return _ffmpeg_cache
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass
    candidates = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\tools\ffmpeg\bin\ffmpeg.exe",
        "/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg",
    ]
    for p in candidates:
        if Path(p).is_file():
            _ffmpeg_cache = p
            return _ffmpeg_cache
    _ffmpeg_cache = ""
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


_ffprobe_cache = None


def _find_ffprobe():
    global _ffprobe_cache
    if _ffprobe_cache is not None:
        return _ffprobe_cache or None

    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        _ffprobe_cache = ""
        return None
    if ffmpeg_path == "ffmpeg":
        _ffprobe_cache = "ffprobe"
    else:
        p = Path(ffmpeg_path)
        sibling = p.with_name(p.name.replace("ffmpeg", "ffprobe"))
        _ffprobe_cache = str(sibling) if sibling.is_file() else "ffprobe"
    return _ffprobe_cache


def probe_file(file_path):
    """Extract metadata from an audio file using ffprobe."""
    ffprobe = _find_ffprobe()
    if not ffprobe:
        return _parse_ffprobe_output("")

    try:
        result = subprocess.run(
            [ffprobe, "-v", "quiet", "-show_entries",
             "format=format_name,duration,bit_rate:"
             "stream=sample_rate,channels:"
             "format_tags=title,artist,album,genre,date",
             "-of", "default=noprint_wrappers=1",
             str(file_path)],
            capture_output=True, text=True, timeout=10, **SUBPROCESS_FLAGS)
        return _parse_ffprobe_output(result.stdout)
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
