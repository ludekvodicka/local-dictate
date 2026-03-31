"""Speech-to-text module — supports onnx-asr, faster-whisper, and whisper.cpp engines.

Model format: [engine:]model_name
  - onnx-asr (default):   nemo-parakeet-tdt-0.6b-v3, onnx-community/whisper-large-v3-turbo, etc.
  - faster-whisper:        faster:large-v3, faster:medium, faster:small, faster:base
  - whisper.cpp:           cpp:large-v3, cpp:medium, cpp:small, cpp:base
"""

import os
import subprocess
import tempfile
import time

import numpy as np

_engine = None  # "onnx", "faster", "cpp"
_model = None
_model_name = None
_language = None

# whisper.cpp model file paths (GGML format)
_CPP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "whisper-cpp")
_CPP_CLI = os.path.join(_CPP_DIR, "Release", "whisper-cli.exe")
_CPP_MODELS_DIR = os.path.join(_CPP_DIR, "models")

# Map short names to HuggingFace GGML model URLs
_CPP_MODEL_MAP = {
    "base": "ggml-base.bin",
    "small": "ggml-small.bin",
    "medium": "ggml-medium.bin",
    "large-v3": "ggml-large-v3.bin",
    "large-v3-turbo": "ggml-large-v3-turbo.bin",
}


def _parse_model_spec(model_spec):
    """Parse 'engine:model' format. Returns (engine, model_name)."""
    if model_spec.startswith("faster:"):
        return "faster", model_spec[7:]
    elif model_spec.startswith("cpp:"):
        return "cpp", model_spec[4:]
    elif model_spec.startswith("cloud:"):
        return "cloud", model_spec[6:]
    else:
        return "onnx", model_spec


def _load_onnx(model_name, use_gpu):
    """Load model via onnx-asr."""
    global _model
    import warnings
    import onnx_asr

    if use_gpu:
        try:
            import onnxruntime
            onnxruntime.set_default_logger_severity(3)
            available = onnxruntime.get_available_providers()
            for provider, label in [
                ("CUDAExecutionProvider", "GPU/CUDA"),
                ("DmlExecutionProvider", "GPU/DirectML"),
            ]:
                if provider in available:
                    try:
                        _model = onnx_asr.load_model(model_name, providers=[(provider, {})])
                        # Quick test to verify GPU actually works with this model
                        import numpy as np
                        _model.recognize(np.zeros(16000, dtype=np.float32), sample_rate=16000)
                        print(f"  ASR: {model_name} (onnx-asr, {label})")
                        return
                    except Exception as e:
                        print(f"  {label} failed for this model, trying next...")
                        _model = None
            print("  No working GPU provider, using CPU")
        except Exception as e:
            print(f"  GPU failed ({e}), using CPU")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        _model = onnx_asr.load_model(model_name)
    print(f"  ASR: {model_name} (onnx-asr, CPU)")


def _load_faster(model_name, use_gpu):
    """Load model via faster-whisper."""
    global _model
    from faster_whisper import WhisperModel

    # faster-whisper uses CTranslate2 — CPU on GTX 1080 (cuDNN 9 doesn't support CC 6.1)
    device = "cpu"
    compute_type = "int8"
    print(f"  ASR: {model_name} (faster-whisper, CPU/int8)")

    _model = WhisperModel(model_name, device=device, compute_type=compute_type)


def _load_cpp(model_name, use_gpu):
    """Ensure whisper.cpp model is downloaded."""
    global _model
    os.makedirs(_CPP_MODELS_DIR, exist_ok=True)

    ggml_file = _CPP_MODEL_MAP.get(model_name, f"ggml-{model_name}.bin")
    model_path = os.path.join(_CPP_MODELS_DIR, ggml_file)

    if not os.path.exists(model_path):
        url = f"https://huggingface.co/ggerganov/whisper.cpp/resolve/main/{ggml_file}"
        print(f"  Downloading {ggml_file}...")
        import requests
        r = requests.get(url, stream=True)
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        with open(model_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192 * 16):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    print(f"\r  Downloading {ggml_file}... {pct}%", end="", flush=True)
        print()

    _model = model_path
    print(f"  ASR: {model_name} (whisper.cpp, CPU)")


def _load_cloud(model_name, use_gpu):
    """Load cloud model via Vercel AI Gateway."""
    global _model

    # Load API key from .env file
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    api_key = None
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("AI_GATEWAY_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
    if not api_key:
        api_key = os.environ.get("AI_GATEWAY_API_KEY")
    if not api_key:
        raise RuntimeError("AI_GATEWAY_API_KEY not found in .env or environment")

    _model = {
        "api_key": api_key,
        "base_url": "https://ai-gateway.vercel.sh/v1",
        "model": model_name,
    }
    print(f"  ASR: {model_name} (Vercel AI Gateway)")


def load_model(model_name="nemo-parakeet-tdt-0.6b-v3", language=None, use_gpu=True):
    """Load an ASR model.

    Model format: [engine:]model_name
      onnx-asr:        nemo-parakeet-tdt-0.6b-v3, onnx-community/whisper-large-v3-turbo, etc.
      faster-whisper:   faster:large-v3, faster:medium, faster:small
      whisper.cpp:      cpp:large-v3, cpp:medium, cpp:small
      cloud (Vercel):   cloud:openai/whisper-1, cloud:groq/whisper-large-v3, etc.
    """
    global _engine, _model_name, _language

    engine, name = _parse_model_spec(model_name)
    _engine = engine
    _model_name = name
    _language = language

    if engine == "onnx":
        _load_onnx(name, use_gpu)
    elif engine == "faster":
        _load_faster(name, use_gpu)
    elif engine == "cpp":
        _load_cpp(name, use_gpu)
    elif engine == "cloud":
        _load_cloud(name, use_gpu)


def _transcribe_onnx(audio, sample_rate):
    kwargs = {"sample_rate": sample_rate}
    if _language and "whisper" in (_model_name or "").lower():
        kwargs["language"] = _language
    result = _model.recognize(audio, **kwargs)
    return str(result).strip() if result else ""


def _transcribe_faster(audio, sample_rate):
    segments, _ = _model.transcribe(
        audio,
        language=_language,
        beam_size=1,
        vad_filter=False,
    )
    return " ".join(seg.text.strip() for seg in segments)


def _transcribe_cloud(audio, sample_rate):
    """Transcribe via Vercel AI Gateway using chat completions with audio input.

    Uses data:audio/wav;base64 in image_url content block — supported by Gemini models.
    """
    import base64
    import io
    import requests
    import soundfile as sf

    # Write audio to in-memory WAV
    buf = io.BytesIO()
    sf.write(buf, audio, sample_rate, format="WAV")
    audio_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    lang_hint = f" The audio is in {_language} language." if _language else ""

    payload = {
        "model": _model["model"],
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Transcribe this audio exactly as spoken. Output only the transcription text, nothing else. Do not add any commentary or explanation.{lang_hint}",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:audio/wav;base64,{audio_b64}",
                        },
                    },
                ],
            }
        ],
    }

    response = requests.post(
        f"{_model['base_url']}/chat/completions",
        headers={
            "Authorization": f"Bearer {_model['api_key']}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()
    return result["choices"][0]["message"]["content"].strip()


def _transcribe_cpp(audio, sample_rate):
    # whisper.cpp needs a WAV file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name
        # Write WAV with soundfile - whisper.cpp expects 16kHz mono
        import soundfile as sf
        sf.write(tmp_path, audio, sample_rate)

    try:
        cmd = [
            _CPP_CLI,
            "-m", _model,  # model path
            "-f", tmp_path,
            "--no-timestamps",
            "--no-prints",
        ]
        if _language:
            cmd.extend(["-l", _language])

        result = subprocess.run(cmd, capture_output=True, timeout=120)
        return result.stdout.decode("utf-8", errors="replace").strip()
    finally:
        os.unlink(tmp_path)


def transcribe(audio, sample_rate=16000):
    """Transcribe a numpy audio array to text. Returns (text, elapsed_seconds)."""
    if _model is None:
        raise RuntimeError("Model not loaded. Call load_model() first.")

    start = time.perf_counter()

    if _engine == "onnx":
        text = _transcribe_onnx(audio, sample_rate)
    elif _engine == "faster":
        text = _transcribe_faster(audio, sample_rate)
    elif _engine == "cpp":
        text = _transcribe_cpp(audio, sample_rate)
    elif _engine == "cloud":
        text = _transcribe_cloud(audio, sample_rate)
    else:
        text = ""

    elapsed = time.perf_counter() - start
    return text, elapsed


def warm_up(sample_rate=16000):
    """Run a dummy transcription to warm up the engine."""
    if _engine in ("cpp", "cloud"):
        # whisper.cpp and cloud don't need warm-up
        print(f"  ASR ready (no warm-up needed for {_engine})")
        return
    silence = np.zeros(sample_rate, dtype=np.float32)
    transcribe(silence, sample_rate)
    print("  ASR warm-up complete")


if __name__ == "__main__":
    import sys
    model = sys.argv[1] if len(sys.argv) > 1 else "nemo-parakeet-tdt-0.6b-v3"
    print(f"Loading: {model}")
    load_model(model, language="cs")
    print("Warming up...")
    warm_up()
    print("\nTest: 1s silence...")
    text, elapsed = transcribe(np.zeros(16000, dtype=np.float32))
    print(f"  Result: '{text}' ({elapsed:.3f}s)")
