# Voice Dictation Tool — Setup

## Prerequisites

- Python 3.10+ (tested with 3.14)
- NVIDIA GPU (optional, for faster transcription)
- Microphone

## Installation

### 1. Install Python dependencies

```bash
cd Q:\ApplicationsAi\temporaryVoiceTool
pip install -r requirements.txt
```

For GPU acceleration (NVIDIA CUDA):
```bash
pip install onnx-asr[gpu,hub] sounddevice keyboard pyperclip numpy requests
```

### 2. Install Ollama (optional, for filler word cleanup)

Download from https://ollama.com/download/windows

Then pull the cleanup model:
```bash
ollama pull qwen2.5:1.5b
```

If Ollama is not installed, the tool still works — it just skips the filler word cleanup step.

### 3. First run — model download

On first run, the Parakeet v3 ASR model (~1.2GB) will be downloaded automatically from HuggingFace. This is a one-time download.

## Usage

```bash
python main.py
```

Hold **Ctrl+Space** to record, release to transcribe and paste.

Press **Ctrl+C** to exit.

## Configuration

Edit `config.json` to customize:

| Setting | Default | Description |
|---|---|---|
| `hotkey` | `ctrl+space` | Key combo to hold for recording |
| `language` | `en` | Transcription language |
| `cleanup_enabled` | `true` | Enable LLM filler word removal |
| `ollama_model` | `qwen2.5:1.5b` | Ollama model for cleanup |
| `ollama_timeout` | `5` | Seconds to wait for cleanup before skipping |

## Troubleshooting

- **No audio recorded:** Check your default microphone in Windows Sound settings
- **Hotkey not working:** Try running as administrator, or change the hotkey in config.json
- **Slow transcription:** First transcription is slower (model warm-up). Subsequent ones are faster.
- **Antivirus warning:** The `keyboard` library uses low-level hooks — this is a known false positive
