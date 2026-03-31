"""LLM cleanup module — filler word removal via Ollama."""

import time

import requests

_DEFAULT_PROMPT = (
    "Clean up this dictated text. Remove filler words (um, uh, like, you know, so, basically). "
    "Fix minor grammar. Keep the meaning exactly the same. Output only the cleaned text, nothing else."
)


def is_ollama_available(base_url="http://localhost:11434"):
    """Check if Ollama is running."""
    try:
        r = requests.get(f"{base_url}/api/tags", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def cleanup_text(text, model="qwen2.5:1.5b", base_url="http://localhost:11434",
                 timeout=5, system_prompt=_DEFAULT_PROMPT):
    """Clean up dictated text using Ollama LLM. Returns (cleaned_text, elapsed_seconds).

    On failure (Ollama down, timeout, error), returns the original text unchanged.
    """
    if not text or not text.strip():
        return text, 0

    start = time.perf_counter()

    try:
        response = requests.post(
            f"{base_url}/api/generate",
            json={
                "model": model,
                "prompt": text,
                "system": system_prompt,
                "stream": False,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        result = response.json().get("response", "").strip()
        elapsed = time.perf_counter() - start

        # If the LLM returned empty, keep original
        if not result:
            return text, elapsed

        return result, elapsed

    except Exception as e:
        elapsed = time.perf_counter() - start
        print(f"  Cleanup skipped ({e})")
        return text, elapsed


if __name__ == "__main__":
    if is_ollama_available():
        print("Ollama is running. Testing cleanup...")
        samples = [
            "Um so I was like thinking about uh the project and basically we need to um fix the login",
            "Hello world this is a clean sentence",
            "So basically uh you know what I mean like it's pretty obvious",
        ]
        for sample in samples:
            cleaned, elapsed = cleanup_text(sample)
            print(f"\n  Input:   {sample}")
            print(f"  Output:  {cleaned}")
            print(f"  Time:    {elapsed:.3f}s")
    else:
        print("Ollama not running. Cleanup will be skipped at runtime.")
        print("Install: https://ollama.com/download/windows")
        print("Then: ollama pull qwen2.5:1.5b")
