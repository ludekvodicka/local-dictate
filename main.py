"""Voice Dictation Tool — hold hotkey to record, transcribe, clean up, and paste."""

import json
import sys
import time

import recorder
import transcriber
import cleanup
import output


def load_config():
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("Warning: config.json not found, using defaults")
        return {}


def main():
    config = load_config()
    hotkey = config.get("hotkey", "ctrl+space")
    sample_rate = config.get("sample_rate", 16000)
    min_duration = config.get("min_recording_seconds", 0.3)
    cleanup_enabled = config.get("cleanup_enabled", True)
    ollama_url = config.get("ollama_url", "http://localhost:11434")
    ollama_model = config.get("ollama_model", "qwen2.5:1.5b")
    ollama_timeout = config.get("ollama_timeout", 5)
    cleanup_prompt = config.get("cleanup_prompt", cleanup._DEFAULT_PROMPT)

    asr_model = config.get("asr_model", "nemo-parakeet-tdt-0.6b-v3")
    language = config.get("language", None)

    # Command-line override: python main.py <model>
    if len(sys.argv) > 1:
        asr_model = sys.argv[1]

    print("=" * 50)
    print("  Voice Dictation Tool")
    print("=" * 50)

    # Load ASR model
    print(f"\nLoading ASR model: {asr_model}...")
    transcriber.load_model(model_name=asr_model, language=language, use_gpu=True)

    # Warm up ASR (first inference is slow)
    print("Warming up ASR...")
    transcriber.warm_up(sample_rate)

    # Check Ollama
    if cleanup_enabled:
        if cleanup.is_ollama_available(ollama_url):
            print(f"Ollama ready (model: {ollama_model})")
        else:
            print("Ollama not available — cleanup will be skipped")
            cleanup_enabled = False

    print(f"\nReady! Hold [{hotkey}] to dictate, release to transcribe.")
    print("Press Ctrl+C to exit.\n")

    rec = recorder.Recorder(sample_rate=sample_rate, hotkey=hotkey)

    while True:
        try:
            # Wait for recording
            audio, duration = rec.wait_and_record()

            if audio is None or duration < min_duration:
                if audio is not None:
                    print(f"  Too short ({duration:.1f}s), skipping")
                continue

            # Transcribe
            text, asr_time = transcriber.transcribe(audio, sample_rate)

            if not text.strip():
                print(f"  (silence) [{asr_time:.2f}s]")
                continue

            # Cleanup
            cleanup_time = 0
            if cleanup_enabled:
                text, cleanup_time = cleanup.cleanup_text(
                    text,
                    model=ollama_model,
                    base_url=ollama_url,
                    timeout=ollama_timeout,
                    system_prompt=cleanup_prompt,
                )

            # Paste
            output.paste_text(text)

            # Report
            total = asr_time + cleanup_time
            parts = [f"rec {duration:.1f}s", f"asr {asr_time:.2f}s"]
            if cleanup_enabled:
                parts.append(f"cleanup {cleanup_time:.2f}s")
            print(f"  -> \"{text}\" [{' | '.join(parts)} | total {total:.2f}s]")

        except KeyboardInterrupt:
            print("\n\nExiting. Bye!")
            sys.exit(0)
        except Exception as e:
            print(f"  Error: {e}")
            continue


if __name__ == "__main__":
    main()
