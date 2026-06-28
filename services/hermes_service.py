import subprocess

from config import HERMES_CMD


def ask_hermes(prompt):
    try:
        result = subprocess.run(
            [
                HERMES_CMD,
                "chat",
                "-q",
                prompt,
                "-Q",
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )

        output = result.stdout.strip()

        if not output:
            output = result.stderr.strip()

        if not output:
            output = "Hermes returned no output."

        return output

    except subprocess.TimeoutExpired:
        return "Hermes timed out."

    except Exception as e:
        return f"Error: {e}"
