"""Audio recording module — hold-to-record via global hotkey."""

import queue
import threading
import time

import numpy as np
import sounddevice as sd


class Recorder:
    def __init__(self, sample_rate=16000, hotkey="ctrl+space", device=None):
        self.sample_rate = sample_rate
        self.hotkey = hotkey
        self.device = device
        self._audio_queue = queue.Queue()
        self._is_recording = False
        self._is_pressed = False  # track key state to ignore Windows key repeats
        self._recording_done = threading.Event()
        self._stream = None

    def _audio_callback(self, indata, frames, time_info, status):
        if self._is_recording:
            self._audio_queue.put(indata.copy())

    def _on_key_event(self, event):
        import keyboard as kb

        # Parse hotkey parts: e.g. "ctrl+space" -> modifiers=["ctrl"], key="space"
        parts = self.hotkey.lower().split("+")
        key = parts[-1]
        modifiers = parts[:-1]

        # Only react to the trigger key (e.g. "space")
        if event.name != key:
            # Also stop recording if a modifier is released while recording
            if self._is_pressed and event.event_type == "up" and event.name in modifiers:
                self._is_pressed = False
                self._is_recording = False
                self._recording_done.set()
            return

        if event.event_type == "down":
            # Check all modifiers are held — only required for starting
            for mod in modifiers:
                if not kb.is_pressed(mod):
                    return
            if self._is_pressed:
                return  # ignore Windows key repeat events
            self._is_pressed = True
            self._is_recording = True
            self._recording_done.clear()
            self._audio_queue = queue.Queue()  # clear any stale data
            print("  Recording...", end="", flush=True)
        elif event.event_type == "up":
            # On release, just check if we were recording — don't check modifiers
            if not self._is_pressed:
                return
            self._is_pressed = False
            self._is_recording = False
            self._recording_done.set()

    def wait_and_record(self):
        """Block until hotkey is pressed and released. Returns (numpy_array, duration_seconds) or (None, 0) if too short."""
        import keyboard

        self._recording_done.clear()
        self._is_pressed = False
        self._is_recording = False

        # Hook all keyboard events, filter in callback
        keyboard.hook(self._on_key_event)

        # Open audio stream
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            callback=self._audio_callback,
            blocksize=1024,
            device=self.device,
        )
        self._stream.start()

        try:
            # Wait for key press then release
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

        finally:
            self._stream.stop()
            self._stream.close()
            keyboard.unhook_all()


def record_once(sample_rate=16000, hotkey="ctrl+space", min_duration=0.3):
    """Convenience function: record once, return (audio_array, duration) or (None, 0) if too short."""
    rec = Recorder(sample_rate=sample_rate, hotkey=hotkey)
    audio, duration = rec.wait_and_record()
    if audio is not None and duration < min_duration:
        print(f"  Too short ({duration:.1f}s < {min_duration}s), skipping")
        return None, 0
    return audio, duration


if __name__ == "__main__":
    print(f"Test: Hold Ctrl+Space to record, release to stop. Ctrl+C to exit.")
    while True:
        try:
            audio, duration = record_once()
            if audio is not None:
                print(f"  Got {len(audio)} samples ({duration:.1f}s)")
        except KeyboardInterrupt:
            print("\nExiting.")
            break
