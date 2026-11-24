"""A different kind of daily X draft for each day of the week.

The goal: stop the scroll with a sharp, honest angle, never with hype or lies.
Opinions may be controversial; facts must be true, and nothing is buy/sell advice.

Crypto is one day in seven; the rest is agentic AI and the build journey,
told as human experience rather than as a product pitch.

    Mon  ai         Agentic AI, from first-hand experience building agents
    Tue  journey    Build log: a real moment from building Uncle Tony, and the lesson
    Wed  data       Crypto data post, rotating: reality -> recovery -> dilution -> hype
    Thu  ai         Agentic AI
    Fri  journey    Build log
    Sat  governance Data, privacy and governance
    Sun  debate     An "agree or disagree" question to start a conversation

Single data formats can still be asked for: /xpost reality | recovery | dilution | hype.
Data posts use one CoinGecko call. Takes rotate through a library without
repeating until every take has been used.

JOURNEY_POSTS must stay true: they describe things that really happened while
building this bot. Never add holdings, amounts, prices paid, IPs or keys.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)

MAX_LEN = 280
WEEKLY = ["ai", "journey", "data", "ai", "journey", "governance", "debate"]
DATA_ROTATION = ["reality", "recovery", "dilution", "hype"]
DATA_FORMATS = set(DATA_ROTATION)
FORMATS = set(WEEKLY) | DATA_FORMATS

STABLE_OR_WRAPPED = {
    "usdt", "usdc", "dai", "usde", "fdusd", "tusd", "usds", "pyusd", "busd", "usd1", "usdd", "gusd",
    "frax", "lusd", "usdp", "eurc", "wbtc", "weth", "steth", "wsteth", "weeth", "cbbtc", "reth",
    "wbeth", "rseth", "ezeth", "jitosol", "msol", "bsol", "susde", "lbtc", "solvbtc", "xaut", "paxg",
}

AI_TAKES = [
    "I gave my AI agent fewer permissions this month, not more.\n\nIt can read, draft and suggest. It can't act without me.\n\nThe most useful agent I've built is the one that knows its limits.",
    "Everyone demos agents doing things.\nNobody demos the agent saying \"I'm not sure, check this first.\"\n\nThat second one is the only kind I'd trust with anything that matters.",
    "My agent has a second agent whose only job is to criticise its work.\n\nWriter, critic, then me. The human always gets the last word.\n\nThat's not a limitation. That's the design.",
    "Agents don't remove work. They move it: from doing the task to checking the task.\n\nIf you hate checking, you'll hate agents.",
    "Before I automate anything I ask one question: what happens when this goes wrong at 3am while I'm asleep?\n\nIf I can't answer it, it doesn't get automated.",
    "An AI agent that can touch money needs the same rules as a new hire on day one: small limits, clear approvals, everything written down.\n\nTrust is earned in steps.",
    "Small, boring agents beat clever ones.\n\nMine checks data, writes a short note and waits for me. No drama. It just shows up every day.",
    "I watched one program pay another program for an answer this week. No account, no sign-up, a fraction of a cent.\n\nAgents paying agents is closer than most people think.",
    "The best prompt I've written for an agent wasn't clever. It was a list of things it must never do.\n\nGuardrails first, personality later.",
    "Unpopular opinion: most AI agents are just expensive notification spam.\n\nThe hard part isn't making an agent act. It's teaching it when to stay quiet.",
    "Ask an AI if your coin is undervalued and it'll agree.\nAsk why it's overvalued and it'll agree with that too.\n\nAI is a mirror, not an oracle. Build agents that check data, not ones that flatter you.",
    "The \"10-person billion-dollar company\" is the lottery version of AI.\n\nThe real version: one person saving 10 hours of boring work a week.\n\nLess exciting. Far more likely.",
    "Hot take: an AI agent that says \"do nothing today\" is worth more than one that hands you 10 trade ideas.\n\nRestraint is the feature nobody demos.",
    "Most \"AI trading bots\" are marketing excitement, not edge.\n\nIf it shows you an accuracy % but never its losing trades, you're reading an advert.",
    "Your feed isn't neutral. It's optimised for your attention, not your decisions.\n\nI build agents that work the other way: fewer, better facts.",
    "Unpopular opinion: prompts are not a moat.\n\nAnyone can copy your prompt. Nobody can copy two years of your data.",
    "AI won't take your job.\nA person with three boring, reliable agents might.\n\nReliable beats impressive every time.",
    "An agent that fails silently is worse than no agent at all.\n\nIf your bot can't tell you it's broken, you don't have automation. You have a liability.",
    "Free AI tools aren't free. You pay in API bills, rate limits or your data.\n\nKnow which one before you build on it.",
]

GOVERNANCE_TAKES = [
    "Everyone wants AI. Nobody wants to talk about where the data came from.\n\nThat's the next scandal, not the next breakthrough.",
    "\"Anonymised data\" is often one extra dataset away from identifying you.\n\nBefore cheering any data sale, ask: who audits the anonymisation?",
    "Governments releasing public data can fund innovation or break public trust.\n\nThe difference is transparency: who gets it, what for, and who checks.",
    "Unpopular opinion: privacy rules don't slow AI down.\n\nMessy, unlabelled, unconsented data does.",
    "If an AI can't tell you which source it used, \"evidence-based\" is just a nicer word for confident.",
    "Your data is someone's product.\n\nThe real question isn't whether it's used. It's whether you get a say and a share.",
    "Data governance sounds boring until a leak makes the news.\n\nThen everyone wishes they'd cared earlier.",
    "Companies keep data \"just in case\".\n\nEvery row you don't need is a liability you're storing for free.",
]

DEBATE_QUESTIONS = [
    "Agree or disagree:\n\nA coin that's down 90% from its high is more likely to fade away than to recover.",
    "Agree or disagree:\n\nMost people would end up with more money by doing nothing than by trading every week.",
    "Which do you trust most for money decisions?\n\n1. A YouTube analyst\n2. An AI chatbot\n3. Raw data\n\nPick one and say why.",
    "Agree or disagree:\n\nAI agents will make creators who only summarise the news irrelevant within two years.",
    "Be honest: have you ever made a money decision because a thumbnail scared you?",
    "Agree or disagree:\n\nIf you can't explain why you hold a coin in one sentence, you're gambling, not investing.",
    "Would you let an AI agent move your money if it showed you every reason first?\n\nYes or no, and why?",
    "Agree or disagree:\n\nFree AI tools are quietly training us to depend on them.",
    "Would you let an AI agent spend $10 a month on your behalf without asking each time?\n\nWhere's your line?",
    "Agree or disagree:\n\nThe skill that matters most in the AI era isn't coding. It's knowing what to check.",
    "Honest question for builders: what's the one thing you'd never let an AI agent do without your approval?",
]

JOURNEY_POSTS = [
    "I built a crypto bot whose main job is to keep me calm.\n\nNo alarm emojis, no hype words, no urgency. If a message could make me anxious or greedy, it gets rewritten.\n\nThe hardest feature wasn't code. It was tone.",
    "My local bank card was rejected by a cloud provider, so my bot ran on my laptop for weeks, on home internet that drops when it likes.\n\nBuilding from where you are is slower. It still counts.",
    "Today my bot drafted a post, a second AI scored it, and it rewrote itself until the score was good enough.\n\nThen it waited for me to tap Approve.\n\nThe goal isn't automation. It's automation that asks first.",
    "My bot can change exactly one thing on my exchange account: move an order I already placed to a higher price.\n\nOnly higher, never more than 30%, and only after I tap Confirm.\n\nNarrow permissions let me sleep.",
    "Every time someone says a coin will 10x, my bot writes the claim down.\n\nAfter 30 and 90 days it checks what actually happened.\n\nI don't need another opinion. I need a record of claims vs reality.",
    "This week a program I built got paid by another program for the first time. One cent, in test money.\n\nTiny. But watching a machine pay for an answer, with no account and no sign-up, changed how I think about the web.",
    "For a few hours two copies of my bot were running at once, on my laptop and on a server, fighting over the same messages.\n\nLesson: before adding features, know exactly where your software is running.",
    "I'm not a deep technical person. I built my bot with an AI pair-programmer, one plain-English question at a time.\n\nYou don't need to know everything. You need to keep asking the next question.",
    "My bot says good morning every day.\n\nNot to be cute. If it ever goes quiet, I know something broke before it costs me anything.\n\nSilence is the most dangerous bug.",
    "The most useful message my trading assistant sends is often: nothing to do today.\n\nIt took me a while to see that as a feature and not a failure.",
    "I asked my bot to stop calling losses red and gains green. Now it says unrealised, shows the facts and adds: no action needed unless it fits your plan.\n\nSame numbers. Calmer decisions.",
]

LIBRARIES = {"ai": AI_TAKES, "governance": GOVERNANCE_TAKES, "debate": DEBATE_QUESTIONS, "journey": JOURNEY_POSTS}


# ------------------------------ Helpers ----------------------------------
def format_for_day(weekday: int) -> str:
    return WEEKLY[weekday % 7]


def next_data_format(state: Dict) -> str:
    """The crypto day rotates through the data formats."""
    idx = (int(state.get("data_idx", -1)) + 1) % len(DATA_ROTATION)
    state["data_idx"] = idx
    return DATA_ROTATION[idx]


def _usd(v: float) -> str:
    from services.reality_check import _usd as fmt

    return fmt(v)


def _top_coins() -> List[Dict]:
    from services.market_service import COINGECKO_BASE_URL, _fetch_json

    coins = _fetch_json(
        f"{COINGECKO_BASE_URL}/coins/markets",
        params={"vs_currency": "usd", "order": "market_cap_desc", "per_page": 100, "page": 1,
                "price_change_percentage": "7d"},
    )
    return [c for c in coins or [] if _is_real_coin(c)]


def _is_real_coin(c: Dict) -> bool:
    sym = str(c.get("symbol", "")).lower()
    name = str(c.get("name", "")).lower()
    if sym in STABLE_OR_WRAPPED or "wrapped" in name or "staked" in name or "bridged" in name:
        return False
    return bool(c.get("current_price"))


def _not_recent(coins: List[Dict], recent: set) -> List[Dict]:
    fresh = [c for c in coins if c["symbol"].upper() not in recent]
    return fresh or coins


def next_take(fmt: str, state: Dict) -> str:
    """Rotate through a library without repeats until all have been used."""
    library = LIBRARIES[fmt]
    used = state.setdefault("used_takes", {}).setdefault(fmt, [])
    if len(used) >= len(library):
        used.clear()
    idx = next(i for i in range(len(library)) if i not in used)
    used.append(idx)
    return library[idx]


# ------------------------------ Data posts -------------------------------
def recovery_post(coins: List[Dict], recent: set) -> Optional[Dict]:
    """The coin furthest below its all-time high, and the rise it needs to get back."""
    pool = [c for c in coins if c.get("ath_change_percentage") is not None and c["ath_change_percentage"] < -50]
    if not pool:
        return None
    c = min(_not_recent(pool, recent), key=lambda c: c["ath_change_percentage"])
    drop = -c["ath_change_percentage"]
    need = (c["ath"] / c["current_price"] - 1) * 100
    sym = c["symbol"].upper()
    text = (
        f"Unpopular maths:\n\n"
        f"${sym} is {drop:.0f}% below its all-time high of {_usd(c['ath'])}.\n"
        f"To get back there, it needs +{need:,.0f}%.\n\n"
        f"Most people think a {drop:.0f}% drop needs a {drop:.0f}% rise. It needs {c['ath'] / c['current_price']:,.1f}x.\n"
        f"Losses are asymmetric. Respect the maths.\n\n"
        f"Data, not advice."
    )
    return {"text": text, "symbol": sym}


def dilution_post(coins: List[Dict], recent: set) -> Optional[Dict]:
    """The top-100 coin with the most supply still to be issued."""
    pool = []
    for c in coins:
        circ, mx = c.get("circulating_supply"), c.get("max_supply")
        if circ and mx and mx > circ * 1.2:
            pool.append((mx / circ, c))
    if not pool:
        return None
    fresh = [p for p in pool if p[1]["symbol"].upper() not in recent] or pool
    ratio, c = max(fresh, key=lambda p: p[0])
    sym = c["symbol"].upper()
    in_circ = 100 / ratio
    full_price = c["market_cap"] / c["max_supply"] if c.get("market_cap") else None
    text = (
        f"Nobody talks about this:\n\n"
        f"Only {in_circ:.0f}% of ${sym}'s max supply is in circulation.\n"
        f"Up to {(ratio - 1) * 100:,.0f}% more coins can still be issued.\n"
    )
    if full_price:
        text += f"Same market cap at full supply = {_usd(full_price)} a coin (today {_usd(c['current_price'])}).\n"
    text += "\nPrice is per coin. Supply matters.\n\nData, not advice."
    return {"text": text, "symbol": sym}


def hype_post(coins: List[Dict], trending: List[str], recent: set) -> Optional[Dict]:
    """The most-talked-about coin, and what it actually did this week."""
    by_sym = {c["symbol"].upper(): c for c in coins}
    picks = [s for s in trending if s in by_sym] or []
    if not picks:
        return None
    sym = next((s for s in picks if s not in recent), picks[0])
    c = by_sym[sym]
    week = c.get("price_change_percentage_7d_in_currency")
    week_line = f"7-day move: {week:+.1f}%" if week is not None else "7-day move: n/a"
    text = (
        f"Everyone is talking about ${sym} this week.\n\n"
        f"{week_line}\n"
        f"Market cap rank: #{c.get('market_cap_rank', '?')}\n"
        f"Below its all-time high by {-c.get('ath_change_percentage', 0):.0f}%\n\n"
        f"Trending measures attention, not value.\n"
        f"Which one are you following?\n\n"
        f"Data, not advice."
    )
    return {"text": text, "symbol": sym}


# ------------------------------ Entry point ------------------------------
def build_mixed_post(fmt: str, state: Dict, recent: set, trending: Optional[List[str]] = None) -> Optional[Dict]:
    """Return {'text', 'symbol'?} for a non-Reality-Check format, or None."""
    if fmt in LIBRARIES:
        return {"text": next_take(fmt, state)[:MAX_LEN]}
    coins = _top_coins()
    if fmt == "recovery":
        post = recovery_post(coins, recent)
    elif fmt == "dilution":
        post = dilution_post(coins, recent)
    elif fmt == "hype":
        post = hype_post(coins, trending or [], recent)
    else:
        return None
    if post:
        post["text"] = post["text"][:MAX_LEN]
    return post
