"""Assemble Wan clips + VO + captions into final MP4 via FFmpeg."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable, Optional

Emit = Optional[Callable[..., None]]


def assemble_video(
    clip_paths: list[Path],
    audio_path: Path,
    ass_path: Path,
    out_path: Path,
    emit: Emit = None,
) -> Path:
    if emit:
        emit("assemble", 0.1, "Concatenating clips…")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    work = out_path.parent / f".work_{out_path.stem}"
    work.mkdir(parents=True, exist_ok=True)
    concat_list = work / "concat.txt"
    lines = []
    for p in clip_paths:
        # Escape single quotes for ffmpeg concat demuxer
        esc = str(p.resolve()).replace("'", "'\\''")
        lines.append(f"file '{esc}'")
    concat_list.write_text("\n".join(lines) + "\n")

    silent_concat = work / "video_silent.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "24",
            str(silent_concat),
        ],
        check=True,
        capture_output=True,
    )

    if emit:
        emit("assemble", 0.5, "Muxing audio + burning captions…")

    # Escape ASS path for subtitles filter (Windows-ish + special chars)
    ass_esc = str(ass_path.resolve()).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")
    cmd = [
        "ffmpeg", "-y",
        "-i", str(silent_concat),
        "-i", str(audio_path),
        "-vf", f"ass={ass_esc}",
        "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        str(out_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError:
        # Fallback without ASS burn-in (some builds lack libass)
        if emit:
            emit("assemble", 0.7, "libass unavailable — muxing without burned captions")
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(silent_concat),
                "-i", str(audio_path),
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                str(out_path),
            ],
            check=True,
            capture_output=True,
        )

    if emit:
        emit("assemble", 1.0, f"Wrote {out_path.name}")
    return out_path
