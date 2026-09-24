"""Wan 2.1 text-to-video clip generation with --mock-wan fallback."""
from __future__ import annotations

import math
import subprocess
from pathlib import Path
from typing import Callable, Optional

import numpy as np

Emit = Optional[Callable[..., None]]


def _device():
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"


def _mock_clip(out_path: Path, keywords: list[str], duration_s: float = 3.0, fps: int = 12) -> Path:
    """Generate a colorful procedural motion clip via numpy + ffmpeg (no Wan weights)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    w, h = 854, 480
    n_frames = max(8, int(duration_s * fps))
    # Hash keywords to colors
    seed = sum(ord(c) for c in " ".join(keywords)) % 997
    rng = np.random.default_rng(seed)
    base = rng.integers(40, 200, size=3).astype(np.float32)

    raw = out_path.with_suffix(".raw")
    with open(raw, "wb") as f:
        for i in range(n_frames):
            t = i / max(n_frames - 1, 1)
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            wave = np.sin((xx / w * 6 + t * 4) * math.pi) * 40
            wave2 = np.cos((yy / h * 4 - t * 3) * math.pi) * 30
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            for c in range(3):
                channel = base[c] + wave * (0.5 + c * 0.2) + wave2 * (0.3 + c * 0.1)
                channel = np.clip(channel + 20 * math.sin(t * math.pi * 2 + c), 0, 255)
                frame[:, :, c] = channel.astype(np.uint8)
            # Center label bar
            frame[h // 2 - 20 : h // 2 + 20, :] = (frame[h // 2 - 20 : h // 2 + 20, :] // 2)
            f.write(frame.tobytes())

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{w}x{h}", "-r", str(fps),
        "-i", str(raw),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    raw.unlink(missing_ok=True)
    return out_path


def _real_wan_clip(
    prompt: str,
    out_path: Path,
    model_dir: Path,
    duration_s: float = 3.0,
) -> Path:
    """Generate with Diffusers WanPipeline when torch + weights available."""
    import torch
    from diffusers import WanPipeline
    from diffusers.utils import export_to_video

    device = _device()
    dtype = torch.float16 if device in ("cuda", "mps") else torch.float32
    pipe = WanPipeline.from_pretrained(str(model_dir), torch_dtype=dtype)
    pipe.to(device)
    # Short clip @ ~480p — keep frames modest for consumer GPUs
    num_frames = max(17, int(duration_s * 8))  # Wan often uses low fps internally
    result = pipe(
        prompt=prompt,
        negative_prompt="blurry, low quality, text, watermark",
        num_frames=num_frames,
        height=480,
        width=832,
        guidance_scale=5.0,
    )
    frames = result.frames[0]
    export_to_video(frames, str(out_path), fps=8)
    return out_path


def generate_clip(
    keywords: list[str],
    out_path: Path,
    model_dir: Path,
    duration_s: float = 3.0,
    mock: bool = True,
    emit: Emit = None,
) -> Path:
    prompt = ", ".join(keywords) + ", cinematic b-roll, high detail"
    if emit:
        emit("wan", 0.0, f"Generating clip: {prompt[:60]}…")

    ready = (model_dir / ".ready").exists()
    stub = (model_dir / "MODEL_STUB.txt").exists()
    use_mock = mock or stub or not ready

    if use_mock:
        return _mock_clip(out_path, keywords, duration_s)

    try:
        return _real_wan_clip(prompt, out_path, model_dir, duration_s)
    except Exception as e:
        if emit:
            emit("wan", 0.0, f"Wan failed ({e}); falling back to mock clip")
        return _mock_clip(out_path, keywords, duration_s)
