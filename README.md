# local-dictate

A local voice-to-text dictation tool for Windows. Hold a hotkey, speak, release — your words are transcribed and pasted into the active application. Fully local, no cloud services required.

Built as an open-source alternative to [SuperWhisper](https://superwhisper.com/) and [Wispr Flow](https://wisprflow.ai/).

## How it works

```
[Hold Ctrl+Space] → [Record audio] → [ASR transcription] → [LLM cleanup] → [Paste into active app]
                     microphone        Whisper/Parakeet       filler removal    Ctrl+V simulation
                                       ~0.2-2s (GPU/CPU)     ~0.4s (optional)
```

1. **Hold** the hotkey (default: `Ctrl+Space`) — recording starts
2. **Speak** naturally into your microphone
3. **Release** the hotkey — audio is transcribed locally
4. **Text appears** in whatever app has focus (editor, browser, chat, etc.)

The console shows timing for each step:
```
Recording... 2.1s
  -> "your transcribed text here" [rec 2.1s | asr 0.34s | cleanup 0.42s | total 0.76s]
```

## Features

- **Fully local** — no cloud, no API keys, no subscription, no data leaves your machine
- **Global hotkey** — works in any application (browser, editor, chat, terminal)
- **Hold-to-record** — natural walkie-talkie UX, prevents accidental recordings
- **100+ languages** — Whisper supports Czech, English, German, French, and many more
- **Filler word removal** — optional LLM cleanup removes "um", "uh", "like", etc.
- **Auto-paste** — transcription is automatically pasted into the active window
- **Configurable** — hotkey, model, language, cleanup prompt — all via `config.json`

## Requirements

- Windows 10/11
- Python 3.10+ (tested with 3.14)
- Microphone
- ~2GB disk space (for ASR model download)
- NVIDIA GPU optional (see [CPU vs GPU](#cpu-vs-gpu) below)

## Installation

### 1. Clone and install dependencies

```bash
git clone https://github.com/ludekvodicka/local-dictate.git
cd local-dictate
pip install -r requirements.txt
```

### 2. Install Ollama (optional — for filler word cleanup)

Download from https://ollama.com/download/windows, then:

```bash
ollama pull qwen2.5:1.5b
```

Without Ollama the tool still works — it just skips the cleanup step and pastes raw transcription.

### 3. Run

```bash
python main.py
```

Or double-click `start.bat`.

On first run, the ASR model (~1.6GB for Whisper large-v3-turbo) downloads automatically from HuggingFace.

## CPU vs GPU

The tool works on both CPU and GPU. Here's what to expect:

### CPU (default, no extra setup)

| Model | Size | Speed (3s clip) | Quality |
|---|---|---|---|
| `whisper-base` | ~140MB | ~1-2s | decent |
| `onnx-community/whisper-small` | ~460MB | ~2-4s | good |
| `nemo-parakeet-tdt-0.6b-v3` | ~1.2GB | ~0.5-1s | great (English), good (European) |
| `onnx-community/whisper-large-v3-turbo` | ~1.6GB | ~5-10s | best multilingual |

**Recommendation for CPU:** Use `whisper-small` or `parakeet` for acceptable speed. `whisper-large-v3-turbo` is accurate but slow on CPU.

### GPU acceleration options

The tool auto-detects and uses the best available provider (CUDA > DirectML > CPU).

#### Speed comparison (whisper-large-v3-turbo, 3s clip)

| Provider | Speed | Setup complexity |
|---|---|---|
| CPU | ~5-10s | None |
| **DirectML** | **~1-3s** | Easy — just install one pip package |
| **CUDA** | **~0.3-0.5s** | Requires CUDA 12.x + cuDNN 9.x |

#### Option A: DirectML (easy, any DirectX 12 GPU)

Works with NVIDIA, AMD, and Intel GPUs. No CUDA installation needed.

```bash
pip uninstall onnxruntime
pip install onnxruntime-directml
```

#### Option B: CUDA (fastest, NVIDIA only)

Requires [CUDA Toolkit 12.x](https://developer.nvidia.com/cuda-12-8-0-download-archive) and [cuDNN 9.x](https://developer.nvidia.com/cudnn-downloads). Note: CUDA 13.x is **not yet supported** by onnxruntime.

**Important:** cuDNN 9.11+ requires **compute capability 7.5+** (Turing architecture or newer). Older GPUs like GTX 1080 (Pascal, CC 6.1) are **not supported** — use DirectML instead.

| Architecture | Compute Capability | Example GPUs | CUDA + cuDNN 9 |
|---|---|---|---|
| Pascal | 6.1 | GTX 1060, 1070, 1080 | Not supported |
| Turing | **7.5** | **GTX 1650/1660, RTX 2060** | **Minimum supported** |
| Ampere | 8.6 | RTX 3060, 3070, 3080 | Supported |
| Ada Lovelace | 8.9 | RTX 4060, 4070, 4080 | Supported |

```bash
pip uninstall onnxruntime
pip install onnxruntime-gpu
```

#### Model speed comparison (GPU)

| Model | DirectML (3s clip) | CUDA (3s clip) | Notes |
|---|---|---|---|
| `whisper-base` | ~0.3-0.5s | ~0.1s | fastest |
| `onnx-community/whisper-small` | ~0.5-1s | ~0.1-0.2s | good balance |
| `nemo-parakeet-tdt-0.6b-v3` | ~0.3-0.5s | ~0.1s | fastest ASR model |
| `onnx-community/whisper-large-v3-turbo` | ~1-3s | ~0.3-0.5s | best multilingual quality |

**Recommendation:** Use DirectML for quick setup. Use CUDA for best performance if you have CUDA 12.x installed.

### GPU VRAM requirements

| Component | VRAM |
|---|---|
| Whisper large-v3-turbo | ~3GB |
| Parakeet v3 | ~2GB |
| Ollama Qwen 2.5 1.5B | ~1.5GB |
| **Total (max)** | **~4.5GB** |

A GTX 1080 (8GB) or better handles everything comfortably.

## Configuration

Edit `config.json` to customize:

```json
{
  "hotkey": "ctrl+space",
  "microphone": null,
  "asr_model": "onnx-community/whisper-large-v3-turbo",
  "language": "cs",
  "sample_rate": 16000,
  "min_recording_seconds": 0.3,
  "cleanup_enabled": true,
  "ollama_url": "http://localhost:11434",
  "ollama_model": "qwen2.5:1.5b",
  "ollama_timeout": 5,
  "cleanup_prompt": "Clean up this dictated text. Remove filler words..."
}
```

| Setting | Default | Description |
|---|---|---|
| `hotkey` | `ctrl+space` | Key combination to hold for recording |
| `microphone` | `null` | Audio input device number (`null` = system default). Run `list-microphones.bat` to see available devices. |
| `asr_model` | `onnx-community/whisper-large-v3-turbo` | ASR model (see table below) |
| `language` | `cs` | Language code (`en`, `cs`, `de`, `fr`, etc.). Used by Whisper models. Parakeet auto-detects. |
| `sample_rate` | `16000` | Audio sample rate in Hz |
| `min_recording_seconds` | `0.3` | Minimum recording duration (shorter clips are ignored) |
| `cleanup_enabled` | `true` | Enable/disable LLM filler word removal |
| `ollama_url` | `http://localhost:11434` | Ollama API endpoint |
| `ollama_model` | `qwen2.5:1.5b` | Ollama model for text cleanup |
| `ollama_timeout` | `5` | Seconds to wait for cleanup response |
| `cleanup_prompt` | (see config) | System prompt for the cleanup LLM |

### Microphone selection

Run `list-microphones.bat` (or `python main.py --mics`) to see available input devices:

```
Available microphones:
  0: Microsoft Sound Mapper - Input (default)
  1: Microphone (Lenovo Performance Audio)
  2: Microphone (Logitech StreamCam)
```

Set the device number in `config.json`:
```json
"microphone": 2
```

### Three ASR engines

The tool supports three speech recognition engines. Each can be selected via command line or bat file:

**onnx-asr** — GPU-accelerated via DirectML/CUDA, uses ONNX Runtime:
```
python main.py onnx-community/whisper-large-v3-turbo
python main.py nemo-parakeet-tdt-0.6b-v3
```

**faster-whisper** — CPU-optimized via CTranslate2 with int8 quantization:
```
python main.py faster:medium
python main.py faster:large-v3
```

**whisper.cpp** — C++ optimized CPU inference (auto-downloads GGML models):
```
python main.py cpp:medium
python main.py cpp:large-v3
```

### Available models and bat files

| Bat file | Engine | Model | Speed | Quality |
|---|---|---|---|---|
| `start-parakeet.bat` | onnx-asr | Parakeet v3 | very fast (GPU) | good (European) |
| `start-whisper-base.bat` | onnx-asr | Whisper base | fast (GPU) | decent |
| `start-whisper-small.bat` | onnx-asr | Whisper small | medium (GPU) | good |
| `start-whisper-medium.bat` | onnx-asr | Whisper medium | slow (GPU) | better |
| `start-whisper-large-turbo.bat` | onnx-asr | Whisper large-v3-turbo | medium (GPU) | great |
| `start-whisper-large.bat` | onnx-asr | Whisper large-v3 | slow (GPU) | best |
| `start-faster-base.bat` | faster-whisper | Whisper base | fast (CPU) | decent |
| `start-faster-small.bat` | faster-whisper | Whisper small | fast (CPU) | good |
| `start-faster-medium.bat` | faster-whisper | Whisper medium | medium (CPU) | better |
| `start-faster-large-turbo.bat` | faster-whisper | Whisper large-v3-turbo | medium (CPU) | great |
| `start-faster-large.bat` | faster-whisper | Whisper large-v3 | slow (CPU) | best |
| `start-cpp-base.bat` | whisper.cpp | Whisper base | fast (CPU) | decent |
| `start-cpp-small.bat` | whisper.cpp | Whisper small | fast (CPU) | good |
| `start-cpp-medium.bat` | whisper.cpp | Whisper medium | medium (CPU) | better |
| `start-cpp-large-turbo.bat` | whisper.cpp | Whisper large-v3-turbo | medium (CPU) | great |
| `start-cpp-large.bat` | whisper.cpp | Whisper large-v3 | slow (CPU) | best |

`list-microphones.bat` — list available audio input devices

## Architecture

```
main.py          — orchestrator, startup, hotkey loop, CLI args
recorder.py      — audio capture via sounddevice, hold-to-record via keyboard
transcriber.py   — multi-engine ASR (onnx-asr, faster-whisper, whisper.cpp)
cleanup.py       — filler word removal via Ollama HTTP API
output.py        — clipboard + simulated Ctrl+V paste
config.json      — user settings
whisper-cpp/     — whisper.cpp binary + GGML models (auto-downloaded)
start-*.bat      — launcher scripts for each engine/model combination
```

### Pipeline

```
                    ┌─────────────┐
                    │  keyboard   │  Global hotkey hook
                    │  library    │  (Ctrl+Space)
                    └──────┬──────┘
                           │ key down/up events
                    ┌──────▼──────┐
                    │ sounddevice │  PortAudio recording
                    │  16kHz mono │  float32 numpy array
                    └──────┬──────┘
                           │ audio array
                    ┌──────▼──────┐
                    │ transcriber │  onnx-asr (GPU/DirectML)
                    │             │  faster-whisper (CPU/int8)
                    │             │  whisper.cpp (CPU/C++)
                    └──────┬──────┘
                           │ raw text
                    ┌──────▼──────┐
                    │   Ollama    │  Qwen 2.5 1.5B (optional)
                    │  HTTP API   │  filler word removal
                    └──────┬──────┘
                           │ cleaned text
                    ┌──────▼──────┐
                    │  pyperclip  │  Clipboard + Ctrl+V
                    │  + keyboard │  into active window
                    └─────────────┘
```

## Troubleshooting

| Problem | Solution |
|---|---|
| No audio recorded | Run `list-microphones.bat` and set `microphone` in config.json |
| Hotkey not working | Try running as administrator, or change hotkey in config.json |
| Slow first transcription | Normal — ONNX session warm-up. Subsequent ones are faster |
| Antivirus warning | `keyboard` library uses low-level hooks — known false positive, add exclusion |
| Wrong language detected | Set `language` in config.json (e.g. `"en"`, `"cs"`) and use a Whisper model |
| Cleanup not working | Check Ollama is running (`ollama serve`), model is pulled (`ollama pull qwen2.5:1.5b`) |
| CUDA not detected | Install CUDA Toolkit 12.x and `pip install onnxruntime-gpu` |

## Credits

Inspired by [SuperWhisper](https://superwhisper.com/), [Wispr Flow](https://wisprflow.ai/), and the [OpenWhispr](https://github.com/OpenWhispr/openwhispr) project.

Powered by:
- [OpenAI Whisper](https://github.com/openai/whisper) / [NVIDIA Parakeet](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3) for speech recognition
- [onnx-asr](https://github.com/istupakov/onnx-asr) for ONNX inference
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) for CTranslate2 inference
- [whisper.cpp](https://github.com/ggml-org/whisper.cpp) for C++ inference
- [Ollama](https://ollama.com/) + [Qwen 2.5](https://ollama.com/library/qwen2.5) for text cleanup

## License

MIT
