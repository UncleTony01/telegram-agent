from core.backends import HermesBackendFactory


def generate_reply(prompt, history=None):
    backend = HermesBackendFactory.create()
    return backend.generate(prompt, history)
