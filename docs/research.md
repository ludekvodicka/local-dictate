# Research — Voice Dictation Tool

## 2026-03-31: Initial Research

### Problem
Build a local voice-to-text dictation tool (like SuperWhisper/Wispr Flow) that runs on Windows with GTX 1080.

### Key Findings

#### ASR Engine: onnx-asr + Parakeet v3 (recommended)
- `onnx-asr` (v0.11.0) — lightweight pure Python package, supports Python 3.10-3.14
- Supports Parakeet TDT 0.6B v3 — 10x faster than Whisper, better accuracy (6.32% vs 7.44% WER)
- Install: `pip install onnx-asr[gpu,hub]` (GPU) or `pip install onnx-asr[cpu,hub]` (CPU)
- Usage: `model = onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v3"); result = model.recognize("file.wav")`
- Max audio length: 20-30 seconds per chunk (VAD available for longer)
- Note: onnxruntime 1.24.1 has known compatibility issues

#### Alternative: sherpa-onnx
- More feature-rich, has Windows wheels for Python 3.14
- No GPU-specific pip wheels (needs manual CUDA build)
- More complex API

#### LLM Cleanup: Ollama + Qwen 2.5 1.5B
- Community-validated: "Ghosty" reports ~600ms total pipeline on M2 Pro
- Cleanup is ~80% of total latency
- Removes filler words (um, uh, like), light formatting
- ~1.5GB VRAM quantized, fits alongside Parakeet on 8GB GPU
- Ollama not currently installed on user's machine

#### GPU Compatibility: GTX 1080 (8GB VRAM, Compute Capability 6.1)
- ONNX Runtime CUDA supports CC 6.1
- Parakeet v3 needs ~2GB VRAM
- Qwen 2.5 1.5B needs ~1.5GB VRAM (quantized)
- Total ~3.5GB of 8GB — plenty of headroom
- Fallback: CPU-only is still fast for Parakeet (~0.15x real-time)

#### User Environment
- Python 3.14.2 installed
- numpy 2.4.2 installed
- No Ollama, no CUDA toolkit (nvcc), nvidia-smi works
- OS: Windows 11 Pro

### Community Insights (from Telegram discussion)
- Kain: "Opus one shot it in ~10 mins" — very feasible project
- Ghosty: Parakeet + Qwen 2.5 1.5B cleanup "feels same as SuperWhisper"
- Hold-to-record (globe key / hotkey) + auto-paste is the standard UX
- Filler word removal is the key differentiator vs raw transcription
