"""Orchestrate full job: story/script beats → Wan clips → VO/captions → film."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

_ROOT = Path(__file__).resolve().parent.parent
_SIDECAR = _ROOT / "sidecar"
for p in (_ROOT, _SIDECAR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from config import app_paths, get_settings  # noqa: E402
from pipeline.script_gen import generate_script  # noqa: E402
from pipeline.wan_gen import generate_clip  # noqa: E402
from pipeline.tts import synthesize  # noqa: E402
from pipeline.captions import beats_to_ass, beats_to_srt  # noqa: E402
from pipeline.assemble import assemble_video  # noqa: E402
from pipeline.thumbnail import make_thumbnail  # noqa: E402


def _slug(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower()).strip("-")
    return s[:40] or "video"


def run_pipeline(
    job_id: str,
    topic: str,
    niche: str = "general facts",
    duration: str = "short",
    voice: str = "default",
    mock: bool = True,
    mode: str = "explainer",
    emit: Callable[..., None] | None = None,
) -> dict[str, Any]:
    def _emit(stage: str, progress: float, message: str, **kw: Any) -> None:
        if emit:
            emit(stage, progress, message, **kw)

    paths = app_paths()
    settings = get_settings()
    mock = mock or settings.mock_wan

    job_dir = paths["jobs"] / job_id
    clips_dir = job_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    _emit("script", 0.05, f"Generating {mode} script…")
    script = generate_script(topic, niche, duration, mode=mode)
    (job_dir / "script.json").write_text(json.dumps(script, indent=2))
    beats = script["beats"]
    _emit("script", 0.15, f"Script ready: {len(beats)} beats — {script['title']}")

    full_text = " ".join(b["narration"] for b in beats)
    _emit("tts", 0.2, "Generating voiceover…")
    audio_path = synthesize(
        full_text, job_dir / "voiceover.wav", paths["tts"], voice=voice, emit=_emit
    )

    try:
        import wave

        with wave.open(str(audio_path), "r") as w:
            audio_dur = w.getnframes() / float(w.getframerate())
        total_beat = sum(float(b.get("duration_s", 3.5)) for b in beats) or 1.0
        scale = audio_dur / total_beat
        for b in beats:
            b["duration_s"] = max(1.5, float(b.get("duration_s", 3.5)) * scale)
    except Exception:
        pass

    clip_paths: list[Path] = []
    n = len(beats)
    for i, beat in enumerate(beats):
        prog = 0.25 + 0.45 * (i / max(n, 1))
        _emit("wan", prog, f"Wan clip {i + 1}/{n}…")
        out = clips_dir / f"clip_{i:02d}.mp4"
        generate_clip(
            keywords=beat.get("visual_keywords", [topic]),
            out_path=out,
            model_dir=paths["wan"],
            duration_s=float(beat.get("duration_s", 3.0)),
            mock=mock,
            emit=_emit,
        )
        clip_paths.append(out)

    _emit("captions", 0.75, "Writing captions…")
    ass_path = beats_to_ass(beats, job_dir / "captions.ass")
    srt_path = beats_to_srt(beats, job_dir / "captions.srt")

    _emit("assemble", 0.8, "Assembling final video…")
    final_name = f"{job_id}_{_slug(topic)}.mp4"
    final_path = paths["output"] / final_name
    assemble_video(clip_paths, audio_path, ass_path, final_path, emit=_emit)

    _emit("thumbnail", 0.95, "Creating thumbnail…")
    thumb = make_thumbnail(script["title"], paths["output"] / f"{job_id}_thumb.jpg")

    result = {
        "video": str(final_path),
        "thumbnail": str(thumb),
        "script": str(job_dir / "script.json"),
        "srt": str(srt_path),
        "title": script["title"],
        "description": script.get("description", ""),
        "tags": script.get("tags", []),
        "mode": script.get("mode", mode),
    }
    (job_dir / "result.json").write_text(json.dumps(result, indent=2))
    _emit("done", 1.0, "Complete", output=result)
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run AutoReel pipeline")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--niche", default="interesting facts")
    parser.add_argument("--duration", default="short", choices=["short", "medium", "long"])
    parser.add_argument("--job-id", default="cli001")
    parser.add_argument("--mock-wan", action="store_true", default=True)
    parser.add_argument("--mode", default="explainer",
                        choices=["animated_short", "explainer"])
    args = parser.parse_args()

    def print_emit(stage, prog, msg, **kw):
        print(f"[{stage}] {prog:.0%} {msg}")

    out = run_pipeline(
        job_id=args.job_id,
        topic=args.topic,
        niche=args.niche,
        duration=args.duration,
        mock=args.mock_wan,
        mode=args.mode,
        emit=print_emit,
    )
    print(json.dumps(out, indent=2))
