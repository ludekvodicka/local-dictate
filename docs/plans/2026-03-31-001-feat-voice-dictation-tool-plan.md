---
title: Local Voice Dictation Tool
type: feat
status: active
date: 2026-03-31
deepened: 2026-03-31
origin: conversation (no brainstorm doc)
---

# Local Voice Dictation Tool

## Overview
Build a local voice-to-text dictation tool for Windows that captures speech via a global hotkey, transcribes it using Parakeet v3 (local ASR), optionally cleans up filler words with a small local LLM, and pastes the result into the active application.

## Problem Frame
Commercial tools (SuperWhisper $10/mo, Wispr Flow $10/mo) solve this well but cost money and send data to the cloud. The community has proven that a fully local pipeline (Parakeet + small LLM) achieves comparable quality in ~600ms. We have the hardware (GTX 1080, 8GB VRAM) to run this.

## Requirements Trace
- R1. Press-and-hold hotkey to record, release to transcribe
- R2. Transcribe speech locally using Parakeet v3 (no cloud, no cost)
- R3. Remove filler words (um, uh, like) via local LLM cleanup
- R4. Auto-paste transcribed text into the currently active application
- R5. Work globally — any app, any text field
- R6. Total latency under 1 second for 2-3 sentences
- R7. Run as a background console process on Windows

## Scope Boundaries
- No GUI / system tray (MVP) — console app only
- No streaming/real-time transcription — process after recording stops
- No meeting recording — short dictation clips only (up to ~30 seconds)
- No multi-language detection — single language at a time (configurable)
- No custom vocabulary training — use model as-is
- No Electron/desktop app wrapper

## Context & Research

### Relevant Code and Patterns
- Project directory: `Q:\ApplicationsAi\temporaryVoiceTool` (empty, greenfield)
- See `docs/research.md` for full research findings

### Technology Choices

| Component | Library | Version | Why |
|---|---|---|---|
| ASR engine | `onnx-asr` | 0.11.0 | Pure Python, supports Parakeet v3, Python 3.14, GPU via onnxruntime |
| ASR model | Parakeet TDT 0.6B v3 | - | 10x faster than Whisper, better accuracy, auto-downloads from HuggingFace |
| Audio capture | `sounddevice` | latest | Cross-platform, reliable on Windows, records to numpy array |
| Hotkey | `keyboard` | latest | Global hotkeys on Windows, no admin needed for most keys |
| LLM cleanup | Ollama HTTP API | - | Local Qwen 2.5 1.5B, simple REST call |
| Clipboard | `pyperclip` | latest | Read/write clipboard cross-platform |
| Key simulation | `keyboard` | latest | Simulate Ctrl+V paste |
| Config | JSON file | - | Simple, no extra dependency |

### Institutional Learnings
- Community reports Parakeet + Qwen 2.5 1.5B pipeline runs in ~600ms on Apple Silicon
- On GTX 1080 (CUDA) expect similar or faster for ASR, LLM cleanup comparable via Ollama
- CPU fallback for Parakeet is still usable (~0.15x real-time = 1.5s for 10s audio)

## Key Technical Decisions

- **onnx-asr over sherpa-onnx**: Simpler API, pure Python, no platform-specific wheels needed, same Parakeet model support. Accepts numpy arrays directly (`model.recognize(waveform, sample_rate=16000)`), supports `providers` parameter for GPU selection, has built-in VAD for long audio.
- **Ollama over direct llama.cpp**: Ollama manages models, provides simple HTTP API, user can install other models too
- **keyboard lib over pynput**: Better Windows support for global hotkeys, can both listen and simulate keypresses. Supports `suppress=True` to prevent hotkey from reaching the active app (critical: Ctrl+Space would otherwise insert a space). Callbacks run in a separate thread automatically.
- **Hold-to-record over toggle**: More natural UX (like walkie-talkie), prevents accidental long recordings
- **Console app over GUI**: Fastest path to working tool, system tray can be added later with `pystray`
- **Numpy arrays over temp WAV files**: onnx-asr accepts numpy arrays directly — no disk I/O needed, reduces latency
- **Thread-safe queue for audio**: sounddevice callback runs in a PortAudio thread, keyboard events in another thread. Use `queue.Queue` to safely pass audio chunks from the sounddevice callback to the main processing thread.

## Open Questions

### Resolved During Planning
- **Python 3.14 compatibility?** Yes — onnx-asr supports 3.10-3.14, sherpa-onnx has 3.14 wheels
- **GTX 1080 VRAM sufficient?** Yes — Parakeet ~2GB + Qwen 1.5B ~1.5GB = ~3.5GB of 8GB
- **onnx-asr GPU support?** Yes — install with `[gpu]` extra, uses onnxruntime-gpu

### Deferred to Implementation
- **Does onnxruntime-gpu work with Python 3.14 on Windows?** Will test during Unit 1 setup; CPU fallback available. Also try DirectML provider as alternative.
- **Best hotkey?** Will default to Ctrl+Space, make configurable. Alternative: use a less common key like ScrollLock or a function key to avoid conflicts.
- **Ollama GPU memory conflict with Parakeet?** Ollama on GPU uses ~1.5GB + Parakeet ~2GB = 3.5GB of 8GB. Should be fine. If not, Ollama can use CPU (`CUDA_VISIBLE_DEVICES="" ollama serve`).
- **sounddevice on Python 3.14?** Likely works (uses PortAudio via ctypes/cffi). Test in Unit 1. Fallback: `pyaudio` or raw `wave` + `subprocess` calling `ffmpeg`.
- **keyboard lib on Python 3.14?** Pure Python + ctypes on Windows, no compiled extensions — should work. Test in Unit 1.

## Implementation Units

- [ ] **Unit 1: Project Setup & Dependencies**
  **Goal:** Working Python environment with all dependencies installed, config file structure
  **Requirements:** Foundation for all other units
  **Dependencies:** None
  **Files:**
  - Create: `requirements.txt`
  - Create: `config.json` (hotkey, language, model, ollama settings)
  - Create: `setup.md` (installation instructions for prerequisites)
  **Approach:**
  - Create `requirements.txt` with: `onnx-asr[cpu,hub]`, `sounddevice`, `keyboard`, `pyperclip`, `numpy`, `requests`
  - GPU variant: `onnx-asr[gpu,hub]` (separate instructions)
  - `config.json` with defaults: hotkey=`ctrl+space`, language=`en`, cleanup_enabled=`true`, ollama_model=`qwen2.5:1.5b`, ollama_url=`http://localhost:11434`
  - `setup.md`: install Python, install Ollama, `ollama pull qwen2.5:1.5b`, pip install
  **Verification:** `pip install -r requirements.txt` succeeds, `python -c "import onnx_asr, sounddevice, keyboard, pyperclip"` works

- [ ] **Unit 2: Audio Recording Module**
  **Goal:** Record audio from microphone while hotkey is held, return numpy array
  **Requirements:** R1
  **Dependencies:** Unit 1
  **Files:**
  - Create: `recorder.py`
  **Approach:**
  - Use `sounddevice.InputStream` with callback to accumulate audio chunks into a `queue.Queue`
  - Sample rate: 16000 Hz (what Parakeet expects), mono, float32 (onnx-asr expects float32)
  - `keyboard.on_press_key` / `keyboard.on_release_key` for hold-to-record with `suppress=True` to prevent key reaching active app
  - On key press: start recording, print visual indicator ("Recording...")
  - On key release: stop recording, drain queue into single numpy array, return it
  - No temp WAV file needed — onnx-asr accepts numpy arrays directly
  - Add minimum recording duration (0.3s) to avoid accidental taps
  - **Threading model:** keyboard callbacks run in keyboard's listener thread. sounddevice callback runs in PortAudio thread. Both write to shared state protected by `threading.Event` flags. Main thread polls/waits for recording-complete event.
  - **Key repeat handling:** On Windows, holding a key generates repeated key-down events. Use a flag to ignore repeats after first press.
  **Test scenarios:**
  - Hold key 1s, release → returns numpy array of ~16000 float32 samples
  - Tap key quickly (<0.3s) → ignored, no transcription triggered
  - Hold key 30s → works (within onnx-asr 20-30s limit)
  - Key repeat events on Windows → handled, don't start multiple recordings
  - Multiple rapid hold-release cycles → each produces separate transcription
  **Verification:** Run standalone, hold hotkey, speak, print array shape and duration

- [ ] **Unit 3: Speech-to-Text Module**
  **Goal:** Transcribe numpy audio array to text using Parakeet v3 locally
  **Requirements:** R2, R6
  **Dependencies:** Unit 1
  **Files:**
  - Create: `transcriber.py`
  **Approach:**
  - Load model once at startup: `onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v3")`
  - Model auto-downloads from HuggingFace on first run (~1.2GB)
  - For GPU: `onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v3", providers=[("CUDAExecutionProvider", {})])`
  - For int8 quantized (smaller/faster): `onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v3", quantization="int8")`
  - Transcribe numpy array: `result = model.recognize(waveform, sample_rate=16000)`
  - GPU detection: try CUDA provider first, catch error and fall back to CPU
  - Cache model instance at module level — never reload between transcriptions
  - For clips >20s, chain with VAD: `vad = onnx_asr.load_vad("silero"); model = model.with_vad(vad)`
  **Test scenarios:**
  - 3-second English speech numpy array → accurate text in <500ms
  - Silence → empty string (Parakeet handles this well, no hallucinations)
  - 20-second clip → transcribes correctly (may need VAD)
  - Background noise → reasonable transcription
  - GPU unavailable → falls back to CPU gracefully
  **Verification:** Run standalone, record 3s of speech, pass numpy array, print transcription and timing

- [ ] **Unit 4: LLM Cleanup Module**
  **Goal:** Remove filler words and lightly format transcribed text using local LLM
  **Requirements:** R3, R6
  **Dependencies:** Unit 1 (Ollama installed separately)
  **Files:**
  - Create: `cleanup.py`
  **Approach:**
  - HTTP POST to Ollama API: `POST http://localhost:11434/api/generate`
  - Model: `qwen2.5:1.5b`
  - System prompt: "Clean up this dictated text. Remove filler words (um, uh, like, you know, so, basically). Fix minor grammar. Keep the meaning exactly the same. Output only the cleaned text, nothing else."
  - Set `stream: false` for simplicity
  - Timeout: 5 seconds (if Ollama is slow/down, return raw text)
  - Graceful degradation: if Ollama not running, skip cleanup and use raw transcription
  **Test scenarios:**
  - "Um so I was like thinking about uh the project" → "I was thinking about the project"
  - Clean text → returned unchanged
  - Ollama down → raw transcription returned (no crash)
  - Very long text → still cleaned within timeout
  **Verification:** Run standalone with sample dirty text, verify cleanup quality and latency

- [ ] **Unit 5: Output Module**
  **Goal:** Paste transcribed text into the currently active application
  **Requirements:** R4, R5
  **Dependencies:** Unit 1
  **Files:**
  - Create: `output.py`
  **Approach:**
  - Save current clipboard content (to restore after paste). Note: `pyperclip.paste()` only handles text; if clipboard has an image/file, save/restore will lose it. Accept this limitation for MVP.
  - Copy transcription to clipboard via `pyperclip.copy(text)`
  - Small delay (50-100ms) via `time.sleep(0.05)` to ensure clipboard is set
  - Simulate Ctrl+V via `keyboard.send('ctrl+v')` — this works globally because `keyboard` uses low-level Windows hooks, so the keystroke goes to whatever window has focus
  - Small delay (100ms) then restore original clipboard text
  - **Focus concern:** The console window running our tool does NOT steal focus because we never create a GUI window. The `keyboard` library works in the background. When user releases the hotkey, the target app still has focus.
  - **Edge case:** If user clicks on our console window during recording, the paste target changes. This is acceptable for MVP — user should keep focus on target app.
  **Test scenarios:**
  - Text pasted into Notepad
  - Text pasted into browser text field
  - Text pasted into VS Code
  - Text pasted into terminal (some terminals intercept Ctrl+V differently)
  - Original clipboard text preserved after paste
  - Empty transcription → nothing pasted (skip)
  **Verification:** Run standalone, open Notepad, verify text appears and clipboard is restored

- [ ] **Unit 6: Main Orchestrator**
  **Goal:** Wire all modules together into a working dictation tool
  **Requirements:** R1-R7
  **Dependencies:** Units 2-5
  **Files:**
  - Create: `main.py`
  **Approach:**
  - On startup: load config, load Parakeet model (warm up ~2-5s), check Ollama availability via HTTP ping
  - Print status: "Voice Tool ready. Hold Ctrl+Space to dictate. Ctrl+C to exit."
  - **Threading model:**
    - Main thread: waits on `threading.Event` for recording-complete, then runs transcribe → cleanup → paste sequentially
    - Keyboard thread (managed by `keyboard` lib): sets recording-start/stop events
    - PortAudio thread (managed by `sounddevice`): pushes audio chunks to `queue.Queue`
    - No custom threads needed — just coordination via Event + Queue
  - Pipeline per dictation: wait for hotkey → record → transcribe → cleanup → paste
  - Print each step with timing: `[recording 2.1s] [transcribe 0.15s] [cleanup 0.42s] → pasted`
  - Handle Ctrl+C via `signal.signal(SIGINT, ...)` or try/except KeyboardInterrupt
  - Error handling: catch and log errors per-transcription, don't crash the loop
  - **Startup warm-up:** Do a dummy transcription of silence to warm up ONNX session (first inference is slow)
  **Patterns to follow:**
  - Keep main.py thin — just orchestration, no business logic
  - Each module exposes simple functions (no classes needed for MVP)
  **Test scenarios:**
  - Full flow: hold key → speak → text appears in Notepad
  - Full flow: dictate into browser, VS Code, Slack
  - Rapid successive dictations (hold → release → hold → release) work without state corruption
  - Error in one transcription doesn't crash the tool
  - Ctrl+C exits cleanly, releases keyboard hooks
  - First transcription after startup is not significantly slower (warm-up works)
  - Ollama down → tool still works, just no cleanup
  **Verification:** Run tool, dictate into 3+ different apps, verify text accuracy and measure end-to-end latency

## File Structure (Final)

```
Q:\ApplicationsAi\temporaryVoiceTool\
├── main.py              # Entry point & orchestrator
├── recorder.py          # Audio capture (hold-to-record)
├── transcriber.py       # Parakeet v3 via onnx-asr
├── cleanup.py           # LLM filler-word removal via Ollama
├── output.py            # Clipboard + paste
├── config.json          # User settings
├── requirements.txt     # Python dependencies
├── setup.md             # Installation instructions
└── docs/
    ├── research.md
    └── plans/
        └── 2026-03-31-001-feat-voice-dictation-tool-plan.md
```

## System-Wide Impact
- **Global hotkey**: `keyboard` library uses low-level Windows hooks (SetWindowsHookEx). With `suppress=True`, the hotkey is consumed and doesn't reach other apps. No admin elevation needed for most keys. May conflict with other global hotkey tools using the same key combo.
- **Clipboard**: Temporarily overwrites clipboard during paste — mitigated by save/restore of text content. Non-text clipboard content (images, files) will be lost during the brief paste window (~150ms).
- **GPU memory**: Parakeet model stays loaded in VRAM — ~2GB persistent usage. This is fine on 8GB GTX 1080, but may affect other GPU-intensive apps running simultaneously.
- **Ollama**: Separate process, needs to be running — graceful fallback if not. Ollama keeps models loaded in memory by default (configurable via `OLLAMA_KEEP_ALIVE`). Qwen 2.5 1.5B uses ~1.5GB RAM/VRAM.
- **No admin required**: Neither `keyboard` nor `sounddevice` need admin on Windows for standard usage.
- **Antivirus**: Low-level keyboard hooks may trigger antivirus warnings. This is a known false positive with the `keyboard` library.

## Risks & Dependencies

| Risk | Severity | Impact | Mitigation |
|---|---|---|---|
| Python 3.14 package incompatibility | **High** | sounddevice, keyboard, or onnx-asr may not have 3.14 wheels | Test early in Unit 1. If fails: install Python 3.12 side-by-side, use it for this project only |
| onnxruntime-gpu not working with GTX 1080 (CC 6.1) | Medium | No GPU acceleration for ASR | CPU fallback is still fast (~0.15x real-time). Also try DirectML as alternative provider |
| Ollama not installed | Low | No filler word cleanup | Graceful skip — return raw transcription. Document installation in setup.md |
| Hotkey conflicts with other apps | Low | Dictation doesn't trigger | Make hotkey configurable in config.json |
| Long Ollama latency on CPU-only machines | Medium | Total pipeline >1s, breaks R6 | Make cleanup optional/configurable. User has GPU so Ollama can use it |
| Model first-download (~1.2GB) | Low | Bad first-run experience | Document in setup.md, onnx-asr shows HuggingFace download progress automatically |
| Windows key repeat events | Medium | Multiple recordings start from single hold | Track key state with flag, ignore repeated key-down after first |
| Antivirus blocks keyboard hooks | Low | Tool can't detect hotkey | Document as known issue, add exclusion instructions |
| Clipboard non-text content lost | Low | User loses copied image/file during paste | Document limitation. Only ~150ms window. Future: use win32clipboard for full save/restore |
| onnxruntime 1.24.1 compatibility issue | Medium | onnx-asr docs warn about this version | Pin onnxruntime version in requirements.txt if needed |

## Future Enhancements (Out of Scope for MVP)
- System tray icon with `pystray` (minimize to tray, visual recording indicator)
- Custom vocabulary / prompt for domain-specific terms
- Sound feedback (beep on start/stop recording)
- Multi-language auto-detection
- Streaming transcription (show partial results while speaking)
- History log of all transcriptions
- Different modes (raw, cleaned, formatted, translated)

## Sources & References
- Research: `docs/research.md`
- onnx-asr: https://github.com/istupakov/onnx-asr
- Parakeet v3: https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3
- Ollama API: https://github.com/ollama/ollama/blob/main/docs/api.md
- Community validation: Telegram discussion (2026-03-30/31)
