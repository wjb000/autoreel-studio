"""Generate scripts: animated short films (story beats) or explainer / facts."""
from __future__ import annotations

import json
from typing import Any


DURATION_BEATS = {
    "short": 5,    # ~30–45s
    "medium": 8,   # ~60–90s
    "long": 12,    # ~2–3 min
}

# Content modes (first-class)
MODE_ANIMATED_SHORT = "animated_short"
MODE_EXPLAINER = "explainer"


def _template_explainer(topic: str, niche: str, n_beats: int) -> dict[str, Any]:
    """Faceless facts / explainer script (works offline / without LLM)."""
    hooks = [
        f"Did you know this about {topic}?",
        f"Here's what most people get wrong about {topic}.",
        f"Three surprising facts about {topic} you need to hear.",
    ]
    title = f"{topic.title()} — Explained in Under a Minute"
    beats = []
    for i in range(n_beats):
        if i == 0:
            text = hooks[i % len(hooks)]
            keywords = [topic, "mystery", "question mark", "cinematic"]
        elif i == n_beats - 1:
            text = f"Follow for more {niche} — and tell us what surprised you most."
            keywords = ["subscribe", "glow", "abstract", "outro"]
        else:
            fact_n = i
            text = (
                f"Fact {fact_n}: {topic} connects to ideas most people never notice. "
                f"In the world of {niche}, this detail changes how you see everything."
            )
            keywords = [topic, niche.split()[0] if niche else "science", "motion", "macro"]
        beats.append(
            {
                "index": i,
                "narration": text,
                "visual_keywords": keywords,
                "duration_s": 3.0 if i == 0 else 4.0,
                "beat_type": "hook" if i == 0 else ("cta" if i == n_beats - 1 else "fact"),
            }
        )
    description = (
        f"{title}\n\n"
        f"Auto-generated faceless explainer about {topic} ({niche}).\n"
        f"#shorts #facts #{topic.replace(' ', '')}"
    )
    return {
        "title": title,
        "mode": MODE_EXPLAINER,
        "niche": niche,
        "topic": topic,
        "description": description,
        "tags": [niche, topic, "facts", "explainer", "shorts"],
        "beats": beats,
    }


def _template_animated_short(topic: str, niche: str, n_beats: int) -> dict[str, Any]:
    """Story-beat driven animated short film script → Wan clips → VO/captions → film."""
    # Arc labels scale with beat count
    if n_beats <= 5:
        arc = ["setup", "inciting", "rising", "climax", "resolution"]
    elif n_beats <= 8:
        arc = ["setup", "inciting", "rising", "midpoint", "complication", "climax", "falling", "resolution"]
    else:
        arc = (
            ["setup", "world", "inciting"]
            + [f"rising_{i}" for i in range(1, n_beats - 5)]
            + ["climax", "falling", "resolution"]
        )
        arc = (arc + ["beat"] * n_beats)[:n_beats]

    title = f"{topic.title()} — Animated Short"
    style = niche or "cinematic animation"
    beats = []
    for i in range(n_beats):
        role = arc[i] if i < len(arc) else f"beat_{i}"
        if i == 0:
            text = f"In a world shaped by {topic}, everything begins with a quiet moment."
            keywords = [topic, style, "establishing shot", "cinematic lighting", "wide"]
        elif "climax" in role:
            text = f"Everything collides — {topic} forces a choice that cannot be undone."
            keywords = [topic, "dramatic", "dynamic motion", "high contrast", style]
        elif "resolution" in role or i == n_beats - 1:
            text = f"Silence returns. The story of {topic} leaves a spark that lingers."
            keywords = [topic, "soft light", "closing shot", "emotional", style]
        elif "inciting" in role:
            text = f"Then something changes — a spark tied to {topic} breaks the calm."
            keywords = [topic, "sudden motion", "story beat", style]
        else:
            text = (
                f"Along the path, {topic} reveals a new layer. "
                f"In this {style} short, the next beat tightens the thread."
            )
            keywords = [topic, style, "character moment", "animated", "depth of field"]
        beats.append(
            {
                "index": i,
                "narration": text,
                "visual_keywords": keywords,
                "duration_s": 3.5 if i == 0 else 4.5,
                "beat_type": role,
                "story_role": role,
            }
        )
    description = (
        f"{title}\n\n"
        f"Animated short film about {topic} ({style}).\n"
        f"Story beats → AI clips → voice + captions.\n"
        f"#animatedshort #ai #shorts #{topic.replace(' ', '')}"
    )
    return {
        "title": title,
        "mode": MODE_ANIMATED_SHORT,
        "niche": niche,
        "topic": topic,
        "description": description,
        "tags": [niche, topic, "animated", "shortfilm", "ai", "shorts"],
        "beats": beats,
    }


def _try_ollama(topic: str, niche: str, n_beats: int, mode: str) -> dict[str, Any] | None:
    try:
        import httpx

        if mode == MODE_ANIMATED_SHORT:
            prompt = (
                f"Write an animated short-film story script about '{topic}' "
                f"in visual style '{niche}'. Return ONLY JSON with keys: title, description, "
                f"tags (array), beats (array of {{narration, visual_keywords (3-6 words), "
                f"duration_s, story_role}}). Exactly {n_beats} beats covering setup → climax → "
                f"resolution. Narration should feel cinematic VO, 1-2 sentences each."
            )
        else:
            prompt = (
                f"Write a faceless YouTube Shorts script about '{topic}' in the niche '{niche}'. "
                f"Return ONLY JSON with keys: title, description, tags (array), beats (array of "
                f"{{narration, visual_keywords (3-5 words), duration_s}}). Exactly {n_beats} beats. "
                f"Each narration 1-2 sentences. Style: punchy facts explainer."
            )
        r = httpx.post(
            "http://127.0.0.1:11434/api/generate",
            json={"model": "llama3.2", "prompt": prompt, "stream": False, "format": "json"},
            timeout=60.0,
        )
        if r.status_code != 200:
            return None
        data = json.loads(r.json().get("response", "{}"))
        if "beats" not in data:
            return None
        data["topic"] = topic
        data["niche"] = niche
        data["mode"] = mode
        for i, b in enumerate(data["beats"]):
            b["index"] = i
            b.setdefault("duration_s", 3.5)
            b.setdefault("visual_keywords", [topic])
            if mode == MODE_ANIMATED_SHORT:
                b.setdefault("story_role", b.get("beat_type", f"beat_{i}"))
                b.setdefault("beat_type", b["story_role"])
        return data
    except Exception:
        return None


def generate_script(
    topic: str,
    niche: str = "general facts",
    duration: str = "short",
    mode: str = MODE_EXPLAINER,
) -> dict[str, Any]:
    n = DURATION_BEATS.get(duration, 5)
    mode = (mode or MODE_EXPLAINER).strip().lower().replace("-", "_").replace(" ", "_")
    if mode in ("animated", "film", "short_film", "animated_short_film"):
        mode = MODE_ANIMATED_SHORT
    if mode in ("facts", "explainer_facts", "faceless"):
        mode = MODE_EXPLAINER
    if mode not in (MODE_ANIMATED_SHORT, MODE_EXPLAINER):
        mode = MODE_EXPLAINER

    result = _try_ollama(topic, niche, n, mode)
    if result:
        return result
    if mode == MODE_ANIMATED_SHORT:
        return _template_animated_short(topic, niche, n)
    return _template_explainer(topic, niche, n)
