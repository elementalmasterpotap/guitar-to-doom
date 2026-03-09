# Guitar-to-Doom Controller Pro

## Install

Recommended on Windows:

```powershell
py -m pip install numpy sounddevice pydirectinput pygetwindow
py -m pip install aubio
```

If `aubio` fails to build from source on Windows, use a prebuilt environment:

```powershell
conda install -c conda-forge aubio
py -m pip install numpy sounddevice pydirectinput pygetwindow
```

## Run

```powershell
py .\tools\guitar_to_doom_controller_pro.py
```

## What it does

**Guitar (6 strings):**

| String | Hz | Key | Action |
|--------|----|-----|--------|
| E (6th) | ~82  | W     | Move forward |
| A (5th) | ~110 | S     | Move backward |
| D (4th) | ~147 | A     | Strafe left |
| G (3rd) | ~196 | D     | Strafe right |
| B (2nd) | ~247 | Left  | Turn left |
| e (1st) | ~330 | Right | Turn right |
| Light strum (string active) | — | Space | Use / open door |
| Hard strum (string active) | — | Ctrl | Fire weapon |
| **Palm mute** (no string) | — | ]  | Next weapon |

**Bass (4 strings):**

| String | Hz | Key | Action |
|--------|----|-----|--------|
| E (4th) | ~41 | W | Move forward |
| A (3rd) | ~55 | S | Move backward |
| D (2nd) | ~73 | A | Strafe left |
| G (1st) | ~98 | D | Strafe right |
| Light strum (string active) | — | Space | Use / open door |
| Hard strum (string active) | — | Ctrl | Fire weapon |
| **Palm mute** (no string) | — | ]  | Next weapon |

- Silence -> release all movement keys
- Sends keys only while a `GZDoom` / `Doom` window is focused
- `Esc` in the console stops the script and releases every held key
- **Palm mute**: mute strings with palm, then strike — volume spike without detectable pitch triggers `]`

## Calibration

1. Start with the guitar volume fully open and a clean DI signal.
2. If notes trigger while you are not touching the strings, raise `NOISE_GATE_RMS`.
3. If soft picking is ignored, lower `NOISE_GATE_RMS` a little.
4. If pitch jumps between wrong strings, raise `MIN_PITCH_CONFIDENCE` or lower `NOTE_TOLERANCE_CENTS`.
5. If movement feels sluggish, lower `HOLD_CONFIRM_FRAMES` from `2` to `1`.
6. If fire triggers too often, raise `ATTACK_RATIO`, `ATTACK_ABS_DELTA`, or `ATTACK_COOLDOWN_MS`.
7. For bass, keep `INSTRUMENT_MODE = "bass"` because it uses a longer aubio window for low `E1`.
8. For hot pickups or an active bass, you will usually need a higher `NOISE_GATE_RMS` than for passive single coils.

## Device selection

Set `LIST_AUDIO_DEVICES_ONLY = True` near the top of the script to print audio devices and exit. Then paste the required device index into `INPUT_DEVICE`.
