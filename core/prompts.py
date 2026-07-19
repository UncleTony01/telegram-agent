def build_prompt(user_message, history=None):
    system_instruction = (
        "You are Uncle Tony, a helpful crypto assistant. "
        "Treat this as a fresh, stateless request. "
        "Do not use any hidden memory, prior session context, or previous chat state. "
        "Use only the conversation history provided below and the current user message. "
        "If the answer is not present in those inputs, say that you do not know.\n\n"
        "IMPORTANT: When explaining trade recommendations, opportunity scores, or expected edge, "
        "only use the deterministic analysis provided in the context. Do not invent or speculate. "
        "Explain WHY a recommendation was chosen, WHY an opportunity score is high or low, "
        "and WHY expected edge is positive, neutral, or negative based on the actual indicators."
    )

    conversation = ""
    if history:
        for message in history:
            conversation += f"{message['role'].capitalize()}: {message['content']}\n"

    if conversation:
        return (
            f"{system_instruction}\n\n"
            f"Conversation history:\n{conversation}\n\n"
            f"Current user message: {user_message}\n\n"
            "Answer:"
        )

    return (
        f"{system_instruction}\n\n"
        f"Current user message: {user_message}\n\n"
        "Answer:"
    )
