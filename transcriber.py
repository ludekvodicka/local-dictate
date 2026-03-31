"""Speech-to-text module — Parakeet v3 or Whisper via onnx-asr."""

import time

import numpy as np

_model = None
_model_name = None
_language = None


def load_model(model_name="nemo-parakeet-tdt-0.6b-v3", language=None, use_gpu=True):
    """Load an ASR model. Downloads from HuggingFace on first run.

    Models:
        - "nemo-parakeet-tdt-0.6b-v3" — fast, good for English/European (auto-detects language)
        - "onnx-community/whisper-large-v3-turbo" — best multilingual quality, slower (~1.6GB)
        - "onnx-community/whisper-small" — good balance of speed and multilingual quality (~460MB)
        - "whisper-base" — smallest/fastest Whisper (~140MB)

    Language: only used for Whisper models (e.g. "cs" for Czech). Parakeet auto-detects.
    """
    global _model, _model_name, _language
    import warnings
    import onnx_asr

    _model_name = model_name
    _language = language

    if use_gpu:
        try:
            import onnxruntime
            available = onnxruntime.get_available_providers()
            if "CUDAExecutionProvider" in available:
                _model = onnx_asr.load_model(
                    model_name,
                    providers=[("CUDAExecutionProvider", {})],
                )
                print(f"  ASR model loaded: {model_name} (GPU/CUDA)")
                return
            else:
                print("  CUDA not available, using CPU")
        except Exception as e:
            print(f"  GPU check failed ({e}), using CPU")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        _model = onnx_asr.load_model(model_name)
    print(f"  ASR model loaded: {model_name} (CPU)")


def transcribe(audio, sample_rate=16000):
    """Transcribe a numpy audio array to text. Returns (text, elapsed_seconds)."""
    if _model is None:
        raise RuntimeError("Model not loaded. Call load_model() first.")

    start = time.perf_counter()

    # Pass language for Whisper models (Parakeet auto-detects)
    kwargs = {"sample_rate": sample_rate}
    if _language and "whisper" in (_model_name or "").lower():
        kwargs["language"] = _language

    result = _model.recognize(audio, **kwargs)
    elapsed = time.perf_counter() - start

    # onnx-asr may return a string or a result object
    text = str(result).strip() if result else ""
    return text, elapsed


def warm_up(sample_rate=16000):
    """Run a dummy transcription to warm up the ONNX session."""
    silence = np.zeros(sample_rate, dtype=np.float32)  # 1 second of silence
    transcribe(silence, sample_rate)
    print("  ASR warm-up complete")


if __name__ == "__main__":
    print("Loading model...")
    load_model()
    print("Warming up...")
    warm_up()

    print("\nTest: transcribing 1s of silence...")
    silence = np.zeros(16000, dtype=np.float32)
    text, elapsed = transcribe(silence)
    print(f"  Result: '{text}' ({elapsed:.3f}s)")
