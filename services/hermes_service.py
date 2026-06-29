from core.ai import generate_reply


def ask_hermes(prompt, history=None):
    try:
        return generate_reply(prompt, history)
    except Exception as e:
        return f"Error: {e}"
