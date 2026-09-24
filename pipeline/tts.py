"""TTS via kokoro-onnx when available, else espeak/ffmpeg sine fallback."""
from __future__ import annotations

import shutil
import subprocess
import wave
from pathlib import Path
from typing import Callable, Optional

import numpy as np

Emit = Optional[Callable[..., None]]


def _ffmpeg_tone_with_silence(out_wav: Path, duration_s: float, text: str) -> Path:
    """Placeholder VO: soft tone whose length approximates speech (~14 chars/sec)."""
    chars = max(len(text), 10)
    dur = max(duration_s, chars / 14.0)
    # Generate quiet modulated tone as stand-in
    sr = 24000
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    # Amplitude envelope like speech syllables
    env = 0.15 * (0.5 + 0.5 * np.sin(2 * np.pi * 3 * t))
    audio = (env * np.sin(2 * np.pi * 180 * t) * 32767).astype(np.int16)
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_wav), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(audio.tobytes())
    return out_wav


def _espeak(text: str, out_wav: Path) -> Path | None:
    if not shutil.which("espeak") and not shutil.which("espeak-ng"):
        return None
    bin_name = "espeak-ng" if shutil.which("espeak-ng") else "espeak"
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [bin_name, "-w", str(out_wav), text],
            check=True,
            capture_output=True,
        )
        return out_wav
    except Exception:
        return None


def _kokoro(text: str, out_wav: Path, model_dir: Path, voice: str = "af_sarah") -> Path | None:
    try:
        from kokoro_onnx import Kokoro

        # Typical layout after download
        onnx = next(model_dir.glob("**/*.onnx"), None)
        voices = next(model_dir.glob("**/voices*.bin"), None) or next(
            model_dir.glob("**/voices*.npz"), None
        )
        if not onnx:
            return None
        kokoro = Kokoro(str(onnx), str(voices) if voices else "")
        samples, sample_rate = kokoro.create(text, voice=voice, speed=1.0)
        import soundfile as sf

        out_wav.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_wav), samples, sample_rate)
        return out_wav
    except Exception:
        return None


def synthesize(
    text: str,
    out_wav: Path,
    model_dir: Path,
    voice: str = "default",
    emit: Emit = None,
) -> Path:
    if emit:
        emit("tts", 0.0, f"Synthesizing VO ({len(text)} chars)…")
    path = _kokoro(text, out_wav, model_dir, voice=voice if voice != "default" else "af_sarah")
    if path:
        return path
    path = _espeak(text, out_wav)
    if path:
        return path
    return _ffmpeg_tone_with_silence(out_wav, 3.0, text)
