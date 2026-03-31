"""Audio recording module — hold-to-record via global hotkey."""

import queue
import threading

import numpy as np
import sounddevice as sd


class Recorder:
    def __init__(self, sample_rate=16000, hotkey="ctrl+space", device=None):
        self.sample_rate = sample_rate
        self.hotkey = hotkey
        self.device = device
        self._audio_queue = queue.Queue()
        self._is_recording = False
        self._is_pressed = False
        self._recording_started = threading.Event()
        self._recording_done = threading.Event()
        self._stream = None
        self._hooked = False

    def _audio_callback(self, indata, frames, time_info, status):
        if self._is_recording:
            self._audio_queue.put(indata.copy())

    def _on_key_event(self, event):
        import keyboard as kb

        parts = self.hotkey.lower().split("+")
        key = parts[-1]
        modifiers = parts[:-1]

        if event.name != key:
            # Stop recording if a modifier is released while recording
            if self._is_pressed and event.event_type == "up" and event.name in modifiers:
                self._is_pressed = False
                self._is_recording = False
                self._recording_done.set()
            return

        if event.event_type == "down":
            for mod in modifiers:
                if not kb.is_pressed(mod):
                    return
            if self._is_pressed:
                return  # ignore Windows key repeat
            self._is_pressed = True
            self._is_recording = True
            self._recording_done.clear()
            self._audio_queue = queue.Queue()
            self._recording_started.set()
            print("  Recording...", end="", flush=True)
        elif event.event_type == "up":
            if not self._is_pressed:
                return
            self._is_pressed = False
            self._is_recording = False
            self._recording_done.set()

    def start(self):
        """Start persistent keyboard hook and audio stream. Call once."""
        import keyboard

        if not self._hooked:
            keyboard.hook(self._on_key_event)
            self._hooked = True

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            callback=self._audio_callback,
            blocksize=1024,
            device=self.device,
        )
        self._stream.start()

    def stop(self):
        """Stop and clean up."""
        import keyboard

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if self._hooked:
            keyboard.unhook_all()
            self._hooked = False

    def wait_and_record(self):
        """Block until hotkey is pressed and released. Returns (numpy_array, duration_seconds) or (None, 0)."""
        self._recording_started.clear()
        self._recording_done.clear()
        self._is_pressed = False
        self._is_recording = False

        # Wait for recording to start (key press)
        self._recording_started.wait()

        # Wait for recording to end (key release)
        self._recording_done.wait()

        # Drain the queue into a single array
        chunks = []
        while not self._audio_queue.empty():
            chunks.append(self._audio_queue.get())

        if not chunks:
            print(" (empty)", flush=True)
            return None, 0

        audio = np.concatenate(chunks, axis=0).flatten()
        duration = len(audio) / self.sample_rate

        print(f" {duration:.1f}s", flush=True)
        return audio, duration


if __name__ == "__main__":
    print(f"Test: Hold Ctrl+Space to record, release to stop. Ctrl+C to exit.")
    rec = Recorder()
    rec.start()
    try:
        while True:
            audio, duration = rec.wait_and_record()
            if audio is not None and duration >= 0.3:
                print(f"  Got {len(audio)} samples ({duration:.1f}s)")
            elif audio is not None:
                print(f"  Too short ({duration:.1f}s)")
    except KeyboardInterrupt:
        print("\nExiting.")
    finally:
        rec.stop()
