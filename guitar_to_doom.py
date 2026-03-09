"""
Guitar-to-Doom Controller Pro
Мост между гитарой/басом и GZDoom через аудио-анализ

Требования:
    pip install sounddevice pydirectinput pygetwindow keyboard
    numpy опционален — работает и без него

Использование:
    python guitar_to_doom.py           # гитара (по умолчанию)
    python guitar_to_doom.py --bass    # бас-гитара
"""

import sys
import argparse
import time
import threading
import math
import struct
import pydirectinput
import pygetwindow as gw
import keyboard
from pitch_utils import PitchDetector
from collections import deque

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

try:
    import sounddevice as sd
    _HAS_SD = True
except ImportError:
    _HAS_SD = False

try:
    from winmm_audio import WinMMStream
    _HAS_WINMM = True
except (ImportError, OSError):
    _HAS_WINMM = False

if not _HAS_SD and not _HAS_WINMM:
    print('[ERROR] Нет доступной библиотеки аудио.')
    print('        Установи sounddevice (Python 3.8–3.13) или убедись что winmm_audio.py есть рядом.')
    sys.exit(1)

# ==================== КОНФИГУРАЦИЯ ====================

# Выбор режима: 'guitar' или 'bass'
INSTRUMENT_MODE = 'guitar'  # Измените на 'bass' для бас-гитары

# Параметры аудио
SAMPLE_RATE = 44100
BLOCK_SIZE = 512  # Меньше = меньше задержка, но больше CPU
CHANNELS = 1

# Noise Gate (порог громкости, ниже которого сигнал игнорируется)
# Диапазон: 0.001 - 0.1 (настройте под свой звукосниматель)
NOISE_GATE_THRESHOLD = 0.015

# Pitch Smoothing (количество предыдущих значений для усреднения)
PITCH_SMOOTHING_WINDOW = 4

# Velocity Spike Detection (два уровня: слабый удар = использовать, сильный = огонь)
VELOCITY_SPIKE_USE_THRESHOLD  = 0.05   # Слабый удар  → Space (открыть дверь)
VELOCITY_SPIKE_FIRE_THRESHOLD = 0.10   # Сильный удар → CTRL  (выстрел)

# Минимальная длительность ноты (в блоках) для срабатывания
NOTE_HOLD_MIN_BLOCKS = 2

# Частотные диапазоны струн (Гц)
STRING_RANGES = {
    'guitar': {
        'E': (75, 95),    # 6-я струна: E2 ~82.41 Hz
        'A': (100, 120),  # 5-я струна: A2 ~110.00 Hz
        'D': (135, 155),  # 4-я струна: D3 ~146.83 Hz
        'G': (185, 205),  # 3-я струна: G3 ~196.00 Hz
        'B': (240, 260),  # 2-я струна: B3 ~246.94 Hz
        'e': (320, 340),  # 1-я струна: E4 ~329.63 Hz
    },
    'bass': {
        'E': (38, 48),    # 4-я струна: E1 ~41.20 Hz
        'A': (52, 62),    # 3-я струна: A1 ~55.00 Hz
        'D': (70, 80),    # 2-я струна: D2 ~73.42 Hz
        'G': (95, 105),   # 1-я струна: G2 ~98.00 Hz
    }
}

# Маппинг струн на клавиши
KEY_MAPPING = {
    'E': 'w',      # Вперёд
    'A': 's',      # Назад
    'D': 'a',      # Стрейф влево
    'G': 'd',      # Стрейф вправо
    'B': 'left',   # Поворот влево
    'e': 'right',  # Поворот вправо
}

# Клавиши действий
ACTION_KEY  = 'ctrl'   # Сильный удар (со струной) → выстрел
USE_KEY     = 'space'  # Слабый удар  (со струной) → использовать/открыть
WEAPON_KEY  = ']'      # Приглушённый стрем (без струны) → следующее оружие

# Окна, для которых активен скрипт
TARGET_WINDOW_TITLES = ['gzdoom', 'doom', 'gzdoom.exe', 'doom 2', 'doom ii', 'ultimate doom', 'heretic', 'hexen']

# ==================== ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ====================

running = True
panic_pressed = False
active_keys = set()
pitch_history = deque(maxlen=PITCH_SMOOTHING_WINDOW)
volume_history = deque(maxlen=5)
last_velocity = 0.0
note_hold_counter = {}
current_note = None
attack_cooldown = 0
pitch_detector = None

# ==================== ФУНКЦИИ ОБРАБОТКИ ====================

def get_active_string(freq):
    """Определяет, какая струна играется по частоте"""
    if freq <= 0:
        return None

    ranges = STRING_RANGES.get(INSTRUMENT_MODE, STRING_RANGES['guitar'])

    for string_name, (min_freq, max_freq) in ranges.items():
        if min_freq <= freq <= max_freq:
            return string_name

    return None

def smooth_pitch(new_pitch):
    """Сглаживание pitch значений"""
    pitch_history.append(new_pitch)
    if len(pitch_history) >= 2:
        # Медианный фильтр для удаления выбросов
        sorted_pitches = sorted(pitch_history)
        return sorted_pitches[len(sorted_pitches) // 2]
    return new_pitch

def detect_velocity_spike(current_volume):
    """Обнаружение резкой атаки: 'fire', 'use' или False"""
    global last_velocity, attack_cooldown

    if attack_cooldown > 0:
        attack_cooldown -= 1
        return False

    velocity = current_volume - last_velocity
    last_velocity = current_volume

    if current_volume > NOISE_GATE_THRESHOLD * 2:
        if velocity > VELOCITY_SPIKE_FIRE_THRESHOLD:
            attack_cooldown = 8
            return 'fire'
        elif velocity > VELOCITY_SPIKE_USE_THRESHOLD:
            attack_cooldown = 8
            return 'use'

    return False

def is_target_window_active():
    """Проверяет, активно ли окно GZDoom"""
    try:
        active_window = gw.getActiveWindow()
        if active_window is None:
            return False

        window_title = active_window.title.lower()
        return any(target in window_title for target in TARGET_WINDOW_TITLES)
    except Exception:
        return False

def press_key(key):
    """Нажимает клавишу (только если окно GZDoom активно)"""
    if is_target_window_active() and key not in active_keys:
        pydirectinput.keyDown(key)
        active_keys.add(key)

def release_key(key):
    """Отпускает клавишу"""
    if key in active_keys:
        pydirectinput.keyUp(key)
        active_keys.discard(key)

def release_all_keys():
    """Отпускает все активные клавиши (Panic Button)"""
    for key in list(active_keys):
        pydirectinput.keyUp(key)
    active_keys.clear()
    print("\n[!] PANIC: Все клавиши отпущены!")

def visualize_volume(volume, max_bars=30):
    """Создает ASCII шкалу громкости"""
    normalized = min(volume * 50, max_bars)
    bars = int(normalized)
    return '█' * bars + '░' * (max_bars - bars)

def get_note_name(freq):
    """Преобразует частоту в ноту"""
    if freq <= 0:
        return "---"

    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    semitones = 12 * math.log2(freq / 440.0)
    note_index = int(round(semitones)) % 12
    octave = int(math.floor(semitones / 12)) + 4
    return f"{note_names[note_index]}{octave}"

# ==================== ОБРАБОТКА АУДИО ====================

def _process_samples(samples):
    """Ядро обработки: samples = list[float] mono, нормализованные [-1, 1]"""
    global current_note, panic_pressed

    if panic_pressed or not running:
        return

    rms_val = math.sqrt(sum(x * x for x in samples) / max(len(samples), 1))

    volume_history.append(rms_val)
    avg_volume = sum(volume_history) / len(volume_history) if volume_history else 0.0

    # Noise Gate
    if avg_volume < NOISE_GATE_THRESHOLD:
        if active_keys:
            release_all_keys()
        current_note = None
        update_display(0, 0, "SILENCE")
        return

    # Pitch Detection
    detected_pitch = pitch_detector(samples)[0]
    smoothed_pitch = smooth_pitch(detected_pitch)

    detected_string = get_active_string(smoothed_pitch)
    spike = detect_velocity_spike(avg_volume)

    note_name = get_note_name(smoothed_pitch)
    status_text = f"{detected_string or '---'} | {note_name}" if detected_string else note_name
    update_display(avg_volume, smoothed_pitch, status_text)

    if is_target_window_active():
        if spike and detected_string:
            # Струна звучит — fire/use в зависимости от силы удара
            if spike == 'fire':
                pydirectinput.keyDown(ACTION_KEY)
                pydirectinput.keyUp(ACTION_KEY)
                print(f"  [FIRE!]", end='')
            elif spike == 'use':
                pydirectinput.keyDown(USE_KEY)
                pydirectinput.keyUp(USE_KEY)
                print(f"  [USE!]", end='')
        elif spike and not detected_string:
            # Приглушённый стрем (palm mute) — смена оружия
            pydirectinput.keyDown(WEAPON_KEY)
            pydirectinput.keyUp(WEAPON_KEY)
            print(f"  [WEAPON]", end='')

        if detected_string:
            target_key = KEY_MAPPING.get(detected_string)
            if target_key:
                for key in list(active_keys):
                    if key != ACTION_KEY and key != target_key:
                        release_key(key)
                press_key(target_key)
                current_note = detected_string
        else:
            for key in list(active_keys):
                if key != ACTION_KEY:
                    release_key(key)
    else:
        if active_keys:
            release_all_keys()


def audio_callback(indata, frames, time_info, status):
    """Callback для sounddevice (InputStream / RawInputStream)"""
    if status:
        print(f"Audio Status: {status}", file=sys.stderr)

    if _HAS_NUMPY and hasattr(indata, 'shape'):
        samples = list(indata[:, 0].astype(float))
    else:
        n_floats = len(indata) // 4
        samples = list(struct.unpack(f'{n_floats}f', indata))

    _process_samples(samples)


def winmm_callback(samples):
    """Callback для WinMMStream (уже list[float])"""
    _process_samples(samples)

def update_display(volume, freq, status_text):
    """Обновляет консольное отображение"""
    vol_bar = visualize_volume(volume)
    freq_text = f"{freq:6.1f} Hz" if freq > 0 else "   --- Hz"

    print(f"\r[{vol_bar}] {freq_text} | {status_text:12} | Keys: {','.join(active_keys) or '-':10}", end='', flush=True)

# ==================== PANIC BUTTON HANDLER ====================

def on_panic_press(e):
    """Обработчик Panic Button"""
    global panic_pressed, running
    panic_pressed = True
    running = False
    release_all_keys()
    print("\n[!] PANIC BUTTON НАЖАТ! Скрипт остановлен.")
    sys.exit(0)

# ==================== ИНИЦИАЛИЗАЦИЯ ====================

def initialize():
    """Инициализация детекторов"""
    global pitch_detector

    print("=" * 60)
    print("  Guitar-to-Doom Controller Pro")
    print("=" * 60)
    print(f"Режим: {INSTRUMENT_MODE.upper()}")
    print(f"Sample Rate: {SAMPLE_RATE} Hz")
    print(f"Block Size: {BLOCK_SIZE} samples ({BLOCK_SIZE/SAMPLE_RATE*1000:.1f} ms)")
    print(f"Noise Gate: {NOISE_GATE_THRESHOLD}")
    _audio_backend = 'sounddevice' if _HAS_SD else 'WinMM (ctypes fallback)'
    print(f"Pitch Engine:  {'numpy (fast)' if _HAS_NUMPY else 'pure Python'}")
    print(f"Audio Backend: {_audio_backend}")
    print("-" * 60)
    print("Настройка:")

    pitch_detector = PitchDetector(sample_rate=SAMPLE_RATE)

    print("  ✓ Pitch detector готов (YIN)")
    print("-" * 60)
    print("Управление:")
    print("  E струна → W          (Вперёд)")
    print("  A струна → S          (Назад)")
    print("  D струна → A          (Стрейф влево)")
    print("  G струна → D          (Стрейф вправо)")
    print("  B струна → Left       (Поворот влево)")
    print("  e струна → Right      (Поворот вправо)")
    print("  Слабый удар  (со струной) → Space  (Использовать/открыть)")
    print("  Сильный удар (со струной) → CTRL   (Выстрел)")
    print("  Palm mute / глушение     → ]      (Следующее оружие)")
    print("  ESC → PANIC BUTTON                (Стоп)")
    print("=" * 60)
    print("Ждём окно GZDoom... Начинайте играть!")
    print()

def main():
    """Главная функция"""
    global running, INSTRUMENT_MODE

    parser = argparse.ArgumentParser(description='Guitar/Bass-to-Doom Controller')
    parser.add_argument('--bass', action='store_true', help='Режим бас-гитары (E1 A1 D2 G2)')
    args = parser.parse_args()
    if args.bass:
        INSTRUMENT_MODE = 'bass'

    initialize()

    # Регистрируем Panic Button
    keyboard.on_press_key('esc', on_panic_press)

    try:
        if _HAS_SD:
            # sounddevice — предпочтительный бэкенд (Python 3.8–3.13)
            stream_cls   = sd.InputStream  if _HAS_NUMPY else sd.RawInputStream
            stream_dtype = np.float32      if _HAS_NUMPY else 'float32'
            with stream_cls(
                samplerate=SAMPLE_RATE,
                blocksize=BLOCK_SIZE,
                channels=CHANNELS,
                dtype=stream_dtype,
                callback=audio_callback,
            ):
                while running:
                    time.sleep(0.01)
        else:
            # WinMM ctypes fallback — любой Python, только Windows
            with WinMMStream(
                sample_rate=SAMPLE_RATE,
                block_size=BLOCK_SIZE,
                channels=CHANNELS,
                callback=winmm_callback,
            ):
                while running:
                    time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n[!] Прерывание пользователем")

    except Exception as e:
        print(f"\n[ERROR] {e}")

    finally:
        running = False
        release_all_keys()
        print("\nСкрипт завершён. Все клавиши отпущены.")

if __name__ == "__main__":
    main()
