"""Output module — clipboard + paste into active application."""

import time

import pyperclip


def paste_text(text):
    """Copy text to clipboard and simulate Ctrl+V to paste into the active window.

    Saves and restores the previous clipboard text content.
    Non-text clipboard content (images, files) will be lost.
    """
    import keyboard

    if not text or not text.strip():
        return

    # Save current clipboard text
    try:
        original = pyperclip.paste()
    except Exception:
        original = None

    # Copy our text and paste
    pyperclip.copy(text)
    time.sleep(0.05)  # ensure clipboard is set
    keyboard.send("ctrl+v")
    time.sleep(0.1)  # ensure paste completes

    # Restore original clipboard
    if original is not None:
        try:
            pyperclip.copy(original)
        except Exception:
            pass


if __name__ == "__main__":
    print("Test: Will paste 'Hello from Voice Tool!' in 3 seconds.")
    print("Switch to a text editor now...")
    time.sleep(3)
    paste_text("Hello from Voice Tool!")
    print("Done! Check your text editor.")
