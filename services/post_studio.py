"""Make each X draft worth replying to, and give it a picture.

discussion_angle()  Asks DeepSeek for one clear, defensible stance on the post's
                    data plus one question, so the post has something to argue
                    about. Strict checks: short, calm, no advice, no hype words.
                    If anything fails, the original post is kept.
render_card()       Draws a 1200x675 image of the post (works with any format),
                    for attaching on X.
"""
from __future__ import annotations

import io
import re
import textwrap
from typing import List, Optional, Tuple

import requests

import config
from utils.logger import get_logger

logger = get_logger(__name__)

MAX_LEN = 280
DISCLAIMER = "Data, not advice."
BANNED = re.compile(
    r"🔥|🔴|🟢|🚨|💀|🚀|crash|dump|moon|explode|panic|fomo|bloodbath|squeeze|huge|massive|urgent|"
    r"act now|don't miss|\bbuy|\bsell|guarantee|https?://|#\w",
    re.IGNORECASE,
)

ANGLE_PROMPT = """You help a data analyst write posts on X that start honest debates.

Here is a data-based post draft:
---
{post}
---

Write exactly two lines:
Line 1: one clear opinion about what this data means (max 110 characters). Take a side that thoughtful people could disagree with. It must be defensible from the data shown.
Line 2: one short question that invites people to reply with their own view (max 70 characters).

Rules: no financial advice, never say buy or sell, no price predictions, no hype words, no emojis, no hashtags, no links, no quotation marks. Plain, calm English.
Output only the two lines."""


# ------------------------------ Discussion angle -------------------------
def _ask_deepseek(prompt: str) -> Optional[str]:
    key = getattr(config, "DEEPSEEK_API_KEY", None)
    if not key:
        return None
    from core.backends import DEEPSEEK_URL

    resp = requests.post(
        DEEPSEEK_URL,
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": getattr(config, "DEEPSEEK_MODEL", "deepseek-chat"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.8,
            "max_tokens": 120,
        },
        timeout=40,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def clean_angle(raw: Optional[str]) -> Optional[Tuple[str, str]]:
    """Validate the model's two lines. Returns (stance, question) or None."""
    if not raw:
        return None
    lines = [l.strip().strip('"').strip("“”").lstrip("-•1234567890.:) ").strip() for l in raw.splitlines()]
    lines = [l for l in lines if l and not l.lower().startswith(("line 1", "line 2"))]
    if len(lines) < 2:
        return None
    stance, question = lines[0], lines[1]
    if not question.endswith("?"):
        return None
    if len(stance) > 130 or len(question) > 90:
        return None
    if BANNED.search(stance) or BANNED.search(question):
        return None
    return stance, question


def apply_angle(text: str, angle: Tuple[str, str]) -> Optional[str]:
    """Replace the post's closing paragraph with the stance + question, keeping the disclaimer."""
    stance, question = angle
    paras = [p for p in text.split("\n\n") if p.strip()]
    if len(paras) < 2:
        return None
    body = paras[:-1]
    candidate = "\n\n".join(body + [stance, f"{question} (Data, not advice)"])
    if len(candidate) <= MAX_LEN:
        return candidate
    # Too long: drop the generic closing paragraph ("Not impossible...", "Trending measures...").
    if len(body) > 2:
        candidate = "\n\n".join(body[:-1] + [stance, f"{question} (Data, not advice)"])
        if len(candidate) <= MAX_LEN:
            return candidate
    return None


def add_discussion_angle(text: str, fmt: str) -> str:
    """Return a more debatable version of a data post, or the original if anything fails."""
    if fmt not in {"reality", "recovery", "dilution", "hype"}:
        return text  # takes and debate questions are already opinions
    try:
        angle = clean_angle(_ask_deepseek(ANGLE_PROMPT.format(post=text)))
    except Exception as e:
        logger.warning("Discussion angle unavailable: %s", e)
        return text
    if not angle:
        return text
    return apply_angle(text, angle) or text


# ------------------------------ Image card -------------------------------
W, H = 1200, 675
BG, FG, MUTED, ACCENT = (14, 15, 18), (236, 238, 242), (150, 158, 170), (90, 170, 255)
LABELS = {
    "reality": "REALITY CHECK", "recovery": "UNPOPULAR MATHS", "dilution": "HIDDEN SUPPLY",
    "hype": "HYPE VS DATA", "ai": "AGENTIC AI", "journey": "BUILD LOG", "governance": "HOT TAKE · DATA", "debate": "YOUR CALL",
}
FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans{}.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans{}.ttf",
]


def _font(size: int, bold: bool = False):
    from PIL import ImageFont

    for pattern in FONT_DIRS:
        path = pattern.format("-Bold" if bold else ("" if "dejavu" in pattern else "-Regular"))
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # very old Pillow
        return ImageFont.load_default()


def _wrap(draw, text: str, font, width: int) -> List[str]:
    out: List[str] = []
    for raw in text.split("\n"):
        if not raw.strip():
            out.append("")
            continue
        words, line = raw.split(" "), ""
        for w in words:
            trial = f"{line} {w}".strip()
            if draw.textlength(trial, font=font) <= width:
                line = trial
            else:
                if line:
                    out.append(line)
                line = w
        out.append(line)
    return out


def render_card(text: str, fmt: str = "reality", handle: Optional[str] = None) -> bytes:
    """A dark 1200x675 PNG of the post. Disclaimer goes in the footer."""
    from PIL import Image, ImageDraw

    body = text.replace("(Data, not advice)", "").replace(DISCLAIMER, "").strip()
    paras = [p.strip() for p in body.split("\n\n") if p.strip()]
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    margin, top, bottom = 70, 110, H - 80

    draw.text((margin, 50), LABELS.get(fmt, "UNCLE TONY"), font=_font(26, True), fill=ACCENT)

    # Shrink the text until every paragraph fits the box.
    for size in range(48, 21, -2):
        regular, bold = _font(size), _font(size, True)
        blocks = []
        for i, p in enumerate(paras):
            is_head, is_last = i == 0, i == len(paras) - 1 and len(paras) > 1
            is_stance = i == len(paras) - 2 and paras[-1].rstrip().endswith("?") and i > 0
            f = bold if (is_head or is_last or is_stance) else regular
            color = FG if (is_head or is_stance) else (ACCENT if is_last else FG if "•" in p or "$" in p else MUTED)
            blocks.append((_wrap(draw, p, f, W - 2 * margin), f, color))
        line_h = int(size * 1.3)
        total = sum(len(b[0]) * line_h for b in blocks) + (len(blocks) - 1) * int(size * 0.6)
        if total <= bottom - top:
            break

    y = top
    for lines, f, color in blocks:
        for line in lines:
            draw.text((margin, y), line, font=f, fill=color)
            y += line_h
        y += int(size * 0.6)

    draw.line([(margin, H - 70), (W - margin, H - 70)], fill=(45, 47, 55), width=2)
    small = _font(22)
    draw.text((margin, H - 55), f"Uncle Tony · {DISCLAIMER}", font=small, fill=MUTED)
    if handle:
        tag = handle if handle.startswith("@") else f"@{handle}"
        draw.text((W - margin - draw.textlength(tag, font=small), H - 55), tag, font=small, fill=MUTED)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
