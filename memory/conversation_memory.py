from collections import defaultdict, deque

MEMORY_SIZE = 10

memory = defaultdict(lambda: deque(maxlen=MEMORY_SIZE))


def add_message(chat_id, role, content):
    memory[chat_id].append(
        {
            "role": role,
            "content": content,
        }
    )

    print(f"\nAdded {role}: {content}")
    print(memory[chat_id])


def get_history(chat_id):
    print("\nCurrent history:")
    print(memory[chat_id])
    return list(memory[chat_id])


def clear_history(chat_id):
    memory[chat_id].clear()
    print("\nMemory cleared!")
    print(memory[chat_id])
