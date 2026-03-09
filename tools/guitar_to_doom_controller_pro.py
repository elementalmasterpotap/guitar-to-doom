#!/usr/bin/env python3
"""Guitar-to-Doom Controller Pro.

Real-time audio bridge that maps guitar/bass pitch and attack to keyboard
input for GZDoom on Windows.
"""

from __future__ import annotations

import math
import queue
import statistics
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional

import aubio
import msvcrt
import numpy as np
import pygetwindow as gw
import pydirectinput
import sounddevice as sd


# -----------------------------
# User-tunable configuration
# -----------------------------
INSTRUMENT_MODE = "guitar"  # "guitar" or "bass"
PROMPT_FOR_MODE = False
INPUT_DEVICE = None  # int device index or exact device name; None -> default
INPUT_CHANNELS = 1
SAMPLE_RATE = 48_000
FIRE_KEY = "space"  # "space" or "ctrlleft"
TARGET_WINDOW_TOKENS = ("gzdoom", "doom")
LIST_AUDIO_DEVICES_ONLY = False

# Signal thresholds.
NOISE_GATE_RMS = 0.012
MIN_PITCH_CONFIDENCE = 0.72
NOTE_TOLERANCE_CENTS = 90.0
HOLD_CONFIRM_FRAMES = 2
SILENCE_RELEASE_FRAMES = 3
DISPLAY_HZ = 20

# Attack / trigger behavior.
ATTACK_RATIO = 1.85
ATTACK_ABS_DELTA = 0.015
ATTACK_COOLDOWN_MS = 140
ENVELOPE_SMOOTHING = 0.18

# Pitch detector settings. Bass gets a longer window for low E1.
MODE_CONFIG = {
    "guitar": {
        "blocksize": 256,
        "winsize": 2048,
        "notes": {
            "E2": {"hz": 82.41, "move": "w"},
            "A2": {"hz": 110.00, "move": "s"},
            "D3": {"hz": 146.83, "move": "a"},
            "G3": {"hz": 196.00, "move": "d"},
        },
    },
    "bass": {
        "blocksize": 256,
        "winsize": 4096,
        "notes": {
            "E1": {"hz": 41.20, "move": "w"},
            "A1": {"hz": 55.00, "move": "s"},
            "D2": {"hz": 73.42, "move": "a"},
            "G2": {"hz": 98.00, "move": "d"},
        },
    },
}


@dataclass(frozen=True)
class NoteCandidate:
    name: str
    frequency_hz: float
    move_key: str
    cents_error: float


@dataclass
class FrameStatus:
    rms: float = 0.0
    pitch_hz: float = 0.0
    note_name: str = "--"
    move_key: str = "-"
    confidence: float = 0.0
    focus_ok: bool = False
    fired: bool = False


class DoomControllerBridge:
    def __init__(self, mode: str) -> None:
        if mode not in MODE_CONFIG:
            raise ValueError(f"Unsupported mode: {mode}")

        self.mode = mode
        self.mode_cfg = MODE_CONFIG[mode]
        self.notes = self.mode_cfg["notes"]
        self.blocksize = self.mode_cfg["blocksize"]
        self.winsize = self.mode_cfg["winsize"]

        self.audio_queue: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=16)
        self.stop_event = threading.Event()
        self.status = FrameStatus()
        self.last_display = 0.0

        self.pending_note: Optional[str] = None
        self.pending_count = 0
        self.active_move_key: Optional[str] = None
        self.recent_pitches: Deque[float] = deque(maxlen=5)
        self.recent_note_names: Deque[str] = deque(maxlen=5)
        self.silence_counter = 0

        self.rms_ema = 0.0
        self.last_fire_at = 0.0
        self.held_keys: set[str] = set()

        self.pitch_detector = aubio.pitch(
            "yinfast",
            self.winsize,
            self.blocksize,
            SAMPLE_RATE,
        )
        self.pitch_detector.set_unit("Hz")
        self.pitch_detector.set_tolerance(0.8)
        self.pitch_detector.set_silence(-40)

        pydirectinput.FAILSAFE = False
        pydirectinput.PAUSE = 0

    def list_audio_devices(self) -> None:
        print(sd.query_devices())

    def get_active_window_title(self) -> str:
        try:
            window = gw.getActiveWindow()
            if window and window.title:
                return window.title
        except Exception:
            pass
        return ""

    def is_target_window_active(self) -> bool:
        title = self.get_active_window_title().lower()
        return any(token in title for token in TARGET_WINDOW_TOKENS)

    def audio_callback(self, indata, frames, time_info, status) -> None:
        del frames, time_info
        if status:
            # Keep running, but surface backend problems in the console.
            print(f"\n[audio] {status}", flush=True)

        audio = np.asarray(indata, dtype=np.float32)
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)
        else:
            audio = audio.reshape(-1)

        try:
            self.audio_queue.put_nowait(audio.copy())
        except queue.Full:
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self.audio_queue.put_nowait(audio.copy())
            except queue.Full:
                pass

    def release_all(self) -> None:
        for key in tuple(self.held_keys):
            try:
                pydirectinput.keyUp(key)
            finally:
                self.held_keys.discard(key)
        self.active_move_key = None

    def set_move_key(self, target_key: Optional[str]) -> None:
        if target_key == self.active_move_key:
            return

        for key in ("w", "a", "s", "d"):
            if key in self.held_keys and key != target_key:
                pydirectinput.keyUp(key)
                self.held_keys.discard(key)

        if target_key and target_key not in self.held_keys:
            pydirectinput.keyDown(target_key)
            self.held_keys.add(target_key)

        self.active_move_key = target_key

    def fire(self) -> bool:
        now = time.monotonic()
        if (now - self.last_fire_at) * 1000.0 < ATTACK_COOLDOWN_MS:
            return False
        if not self.is_target_window_active():
            return False

        pydirectinput.press(FIRE_KEY)
        self.last_fire_at = now
        return True

    def classify_pitch(self, hz: float) -> Optional[NoteCandidate]:
        if not math.isfinite(hz) or hz <= 0:
            return None

        best_name = None
        best_data = None
        best_cents = None
        for note_name, data in self.notes.items():
            cents = 1200.0 * math.log2(hz / data["hz"])
            if best_cents is None or abs(cents) < abs(best_cents):
                best_name = note_name
                best_data = data
                best_cents = cents

        if best_name is None or best_data is None or best_cents is None:
            return None
        if abs(best_cents) > NOTE_TOLERANCE_CENTS:
            return None

        return NoteCandidate(
            name=best_name,
            frequency_hz=best_data["hz"],
            move_key=best_data["move"],
            cents_error=best_cents,
        )

    def smooth_pitch(self, note_name: str, hz: float) -> float:
        self.recent_note_names.append(note_name)
        self.recent_pitches.append(hz)
        matching = [
            pitch
            for name, pitch in zip(self.recent_note_names, self.recent_pitches)
            if name == note_name
        ]
        if not matching:
            return hz
        return float(statistics.median(matching))

    def detect_attack(self, rms: float) -> bool:
        previous_ema = self.rms_ema
        if self.rms_ema == 0.0:
            self.rms_ema = rms
        else:
            self.rms_ema = (
                ENVELOPE_SMOOTHING * rms
                + (1.0 - ENVELOPE_SMOOTHING) * self.rms_ema
            )

        if rms < max(NOISE_GATE_RMS * 1.15, 0.001):
            return False

        delta = rms - previous_ema
        return rms > previous_ema * ATTACK_RATIO and delta > ATTACK_ABS_DELTA

    def handle_pitch_candidate(
        self,
        candidate: Optional[NoteCandidate],
        detected_hz: float,
        confidence: float,
        rms: float,
    ) -> None:
        focus_ok = self.is_target_window_active()
        fired = self.detect_attack(rms)

        if fired:
            fired = self.fire()

        if candidate is None:
            self.pending_note = None
            self.pending_count = 0
            self.silence_counter += 1
            if self.silence_counter >= SILENCE_RELEASE_FRAMES or not focus_ok:
                self.release_all()
            self.status = FrameStatus(
                rms=rms,
                pitch_hz=detected_hz,
                note_name="--",
                move_key="-",
                confidence=confidence,
                focus_ok=focus_ok,
                fired=fired,
            )
            return

        self.silence_counter = 0
        if candidate.name == self.pending_note:
            self.pending_count += 1
        else:
            self.pending_note = candidate.name
            self.pending_count = 1

        smooth_hz = self.smooth_pitch(candidate.name, detected_hz)
        resolved_key = self.active_move_key or "-"
        if self.pending_count >= HOLD_CONFIRM_FRAMES and focus_ok:
            self.set_move_key(candidate.move_key)
            resolved_key = candidate.move_key.upper()
        elif not focus_ok:
            self.release_all()
            resolved_key = "-"

        self.status = FrameStatus(
            rms=rms,
            pitch_hz=smooth_hz,
            note_name=candidate.name,
            move_key=resolved_key,
            confidence=confidence,
            focus_ok=focus_ok,
            fired=fired,
        )

    def process_block(self, audio: np.ndarray) -> None:
        rms = float(np.sqrt(np.mean(np.square(audio), dtype=np.float64)))
        detected_hz = 0.0
        confidence = 0.0
        candidate = None

        if rms >= NOISE_GATE_RMS:
            detected_hz = float(self.pitch_detector(audio)[0])
            confidence = float(self.pitch_detector.get_confidence())
            if confidence >= MIN_PITCH_CONFIDENCE:
                candidate = self.classify_pitch(detected_hz)

        self.handle_pitch_candidate(candidate, detected_hz, confidence, rms)

    def panic_pressed(self) -> bool:
        if not msvcrt.kbhit():
            return False

        ch = msvcrt.getwch()
        return ch == "\x1b"

    def volume_bar(self, rms: float, width: int = 30) -> str:
        normalized = min(max(rms / max(NOISE_GATE_RMS * 4.0, 0.001), 0.0), 1.0)
        filled = int(round(normalized * width))
        return "#" * filled + "-" * (width - filled)

    def print_status(self) -> None:
        now = time.monotonic()
        if now - self.last_display < 1.0 / DISPLAY_HZ:
            return

        self.last_display = now
        bar = self.volume_bar(self.status.rms)
        note = self.status.note_name
        pitch = f"{self.status.pitch_hz:6.1f} Hz" if self.status.pitch_hz else "   --.- Hz"
        conf = f"{self.status.confidence:0.2f}"
        focus = "ON " if self.status.focus_ok else "OFF"
        fire = "YES" if self.status.fired else " no"
        line = (
            f"\rVOL [{bar}] {self.status.rms:0.4f} | "
            f"NOTE {note:>3} | PITCH {pitch} | "
            f"MOVE {self.status.move_key:>2} | "
            f"CONF {conf} | FOCUS {focus} | FIRE {fire} | "
            f"Esc = panic"
        )
        print(line, end="", flush=True)

    def run(self) -> None:
        print(
            "Guitar-to-Doom Controller Pro\n"
            f"Mode: {self.mode} | Device: {INPUT_DEVICE if INPUT_DEVICE is not None else 'default'}\n"
            f"Noise gate: {NOISE_GATE_RMS:.4f} | Pitch confidence: {MIN_PITCH_CONFIDENCE:.2f}\n"
            f"Fire key: {FIRE_KEY} | Target windows: {', '.join(TARGET_WINDOW_TOKENS)}\n"
            "Use open strings for the cleanest control. Press Esc in this console to panic-stop.\n"
        )

        with sd.InputStream(
            device=INPUT_DEVICE,
            channels=INPUT_CHANNELS,
            samplerate=SAMPLE_RATE,
            blocksize=self.blocksize,
            dtype="float32",
            latency="low",
            callback=self.audio_callback,
        ):
            while not self.stop_event.is_set():
                if self.panic_pressed():
                    print("\nPanic stop requested.", flush=True)
                    self.stop_event.set()
                    break

                try:
                    block = self.audio_queue.get(timeout=0.1)
                except queue.Empty:
                    if not self.is_target_window_active():
                        self.release_all()
                    continue

                self.process_block(block)
                if not self.status.focus_ok:
                    self.release_all()
                self.print_status()

        self.release_all()
        print("\nStopped cleanly.", flush=True)


def choose_mode() -> str:
    if not PROMPT_FOR_MODE:
        return INSTRUMENT_MODE.lower().strip()

    raw = input("Select mode [guitar/bass] (default: guitar): ").strip().lower()
    return raw if raw in MODE_CONFIG else "guitar"


def main() -> None:
    mode = choose_mode()
    bridge = DoomControllerBridge(mode)

    if LIST_AUDIO_DEVICES_ONLY:
        bridge.list_audio_devices()
        return

    try:
        bridge.run()
    except KeyboardInterrupt:
        bridge.release_all()
        print("\nInterrupted by user.", flush=True)
    finally:
        bridge.release_all()


if __name__ == "__main__":
    main()
