import pytest

from services import post_studio as ps

POST = (
    "Someone will tell you $AVAX can 10x.\nHere's what that really means:\n\n"
    "• Price: $6.68 → $66.80\n• Market cap: $2.98B → $29.8B (#12)\n\n"
    "Not impossible. Just know what you're betting on.\n\n"
    "Would you take that bet? (Data, not advice)"
)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(ps.requests, "post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network")))


def test_clean_angle_accepts_two_calm_lines():
    raw = "1. A 10x here needs more new money than most of the market holds.\n2. Where would that money come from?"
    assert ps.clean_angle(raw) == (
        "A 10x here needs more new money than most of the market holds.",
        "Where would that money come from?",
    )


@pytest.mark.parametrize("raw", [
    None, "", "only one line",
    "This coin will moon soon.\nReady?",
    "Time to buy before it's too late.\nAre you in?",
    "A calm stance.\nNot a question",
    "x" * 140 + "\nWhy?",
])
def test_clean_angle_rejects_bad_output(raw):
    assert ps.clean_angle(raw) is None


def test_apply_angle_replaces_closer_and_keeps_disclaimer():
    out = ps.apply_angle(POST, ("A 10x needs new money the size of a top-12 coin.", "Where does it come from?"))
    assert out.startswith("Someone will tell you $AVAX")
    assert "Where does it come from? (Data, not advice)" in out
    assert "Would you take that bet?" not in out
    assert len(out) <= 280


def test_add_angle_keeps_original_on_failure(monkeypatch):
    monkeypatch.setattr(ps, "_ask_deepseek", lambda p: "nonsense")
    assert ps.add_discussion_angle(POST, "reality") == POST
    monkeypatch.setattr(ps, "_ask_deepseek", lambda p: (_ for _ in ()).throw(RuntimeError("down")))
    assert ps.add_discussion_angle(POST, "reality") == POST


def test_add_angle_used_when_valid_and_skipped_for_takes(monkeypatch):
    monkeypatch.setattr(ps, "_ask_deepseek", lambda p: "Most 10x calls ignore where the money comes from.\nWho funds it?")
    out = ps.add_discussion_angle(POST, "reality")
    assert "Most 10x calls ignore where the money comes from." in out and out.endswith("(Data, not advice)")
    assert ps.add_discussion_angle("A hot take.", "ai") == "A hot take."


def test_no_key_means_no_call(monkeypatch):
    monkeypatch.setattr(ps.config, "DEEPSEEK_API_KEY", None, raising=False)
    assert ps._ask_deepseek("hi") is None


@pytest.mark.parametrize("fmt", ["reality", "recovery", "dilution", "hype", "ai", "governance", "debate"])
def test_render_card_is_png_of_right_size(fmt):
    from io import BytesIO

    from PIL import Image

    png = ps.render_card(POST, fmt, handle="AnthonyMuthoka5")
    img = Image.open(BytesIO(png))
    assert img.size == (1200, 675) and img.format == "PNG"
