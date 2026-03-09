"""
Guitar-to-Doom: Интерактивное обучение управлению
Поддерживает гитару (по умолчанию) и бас-гитару (--bass).

Запуск:
    python guitar_tutorial.py          # гитара
    python guitar_tutorial.py --bass   # бас-гитара
"""

import sys
import argparse
import time
import math
import struct
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

# ==================== КОНФИГ ====================

SAMPLE_RATE  = 44100
BLOCK_SIZE   = 512
CHANNELS     = 1

NOISE_GATE_THRESHOLD          = 0.015
PITCH_SMOOTHING_WINDOW        = 4
VELOCITY_SPIKE_USE_THRESHOLD  = 0.05
VELOCITY_SPIKE_FIRE_THRESHOLD = 0.10

STRING_RANGES = {
    'guitar': {
        'E': (75,  95),   # 6-я: E2 ~82 Hz
        'A': (100, 120),  # 5-я: A2 ~110 Hz
        'D': (135, 155),  # 4-я: D3 ~147 Hz
        'G': (185, 205),  # 3-я: G3 ~196 Hz
        'B': (240, 260),  # 2-я: B3 ~247 Hz
        'e': (320, 340),  # 1-я: E4 ~330 Hz
    },
    'bass': {
        'E': (38, 48),    # 4-я: E1 ~41 Hz
        'A': (52, 62),    # 3-я: A1 ~55 Hz
        'D': (70, 80),    # 2-я: D2 ~73 Hz
        'G': (95, 105),   # 1-я: G2 ~98 Hz
    },
}

KEY_INFO = {
    'guitar': {
        'E': ('W',     'Вперёд'),
        'A': ('S',     'Назад'),
        'D': ('A',     'Стрейф влево'),
        'G': ('D',     'Стрейф вправо'),
        'B': ('Left',  'Поворот влево'),
        'e': ('Right', 'Поворот вправо'),
    },
    'bass': {
        'E': ('W', 'Вперёд'),
        'A': ('S', 'Назад'),
        'D': ('A', 'Стрейф влево'),
        'G': ('D', 'Стрейф вправо'),
    },
}

# ==================== УРОКИ ====================

LESSONS_GUITAR = [
    {'title': 'Урок 1 — Вперёд',          'desc': 'Сыграй 6-ю струну (E) — самую толстую.',      'goal_type': 'string', 'goal': 'E', 'count': 3},
    {'title': 'Урок 2 — Назад',            'desc': 'Сыграй 5-ю струну (A).',                      'goal_type': 'string', 'goal': 'A', 'count': 3},
    {'title': 'Урок 3 — Стрейф влево',    'desc': 'Сыграй 4-ю струну (D).',                      'goal_type': 'string', 'goal': 'D', 'count': 3},
    {'title': 'Урок 4 — Стрейф вправо',   'desc': 'Сыграй 3-ю струну (G).',                      'goal_type': 'string', 'goal': 'G', 'count': 3},
    {'title': 'Урок 5 — Поворот влево',   'desc': 'Сыграй 2-ю струну (B). Тонкая, у края.',     'goal_type': 'string', 'goal': 'B', 'count': 3},
    {'title': 'Урок 6 — Поворот вправо',  'desc': 'Сыграй 1-ю струну (e) — самую тонкую.',       'goal_type': 'string', 'goal': 'e', 'count': 3},
    {'title': 'Урок 7 — Использовать',    'desc': 'Слабый шлепок ладонью по струнам.',            'hint':  'Мягко, не сильно', 'goal_type': 'spike',  'goal': 'use',  'count': 3},
    {'title': 'Урок 8 — Выстрел',         'desc': 'Сильный резкий удар по струнам.',              'hint':  'Сильнее чем для Space', 'goal_type': 'spike',  'goal': 'fire', 'count': 3},
    {'title': 'Урок 9 — Смена оружия',   'desc': 'Palm mute: заглуши струны ладонью и ударь.',   'hint':  'Рука на струнах, затем удар — нет звука, но есть движение', 'goal_type': 'mute', 'count': 3},
    {'title': 'Урок 10 — Финальный тест', 'desc': 'Сыграй по порядку: E → G → B → e',            'hint':  'По одной, чётко', 'goal_type': 'sequence', 'goal': ['E', 'G', 'B', 'e'], 'count': 1},
]

LESSONS_BASS = [
    {'title': 'Урок 1 — Вперёд',          'desc': 'Сыграй 4-ю струну (E1) — самую толстую.',     'goal_type': 'string', 'goal': 'E', 'count': 3},
    {'title': 'Урок 2 — Назад',            'desc': 'Сыграй 3-ю струну (A1).',                     'goal_type': 'string', 'goal': 'A', 'count': 3},
    {'title': 'Урок 3 — Стрейф влево',    'desc': 'Сыграй 2-ю струну (D2).',                     'goal_type': 'string', 'goal': 'D', 'count': 3},
    {'title': 'Урок 4 — Стрейф вправо',   'desc': 'Сыграй 1-ю струну (G2) — самую тонкую.',      'goal_type': 'string', 'goal': 'G', 'count': 3},
    {'title': 'Урок 5 — Использовать',    'desc': 'Слабый шлепок ладонью по струнам.',            'hint':  'Мягко, не сильно', 'goal_type': 'spike',  'goal': 'use',  'count': 3},
    {'title': 'Урок 6 — Выстрел',         'desc': 'Сильный резкий удар по струнам.',              'hint':  'Сильнее чем для Space', 'goal_type': 'spike',  'goal': 'fire', 'count': 3},
    {'title': 'Урок 7 — Смена оружия',   'desc': 'Palm mute: заглуши струны ладонью и ударь.',   'hint':  'Рука на струнах, затем удар — нет звука, но есть движение', 'goal_type': 'mute', 'count': 3},
    {'title': 'Урок 8 — Финальный тест',  'desc': 'Сыграй по порядку: E → A → D → G',            'hint':  'По одной, чётко', 'goal_type': 'sequence', 'goal': ['E', 'A', 'D', 'G'], 'count': 1},
]

# ==================== СОСТОЯНИЕ ====================

pitch_history   = deque(maxlen=PITCH_SMOOTHING_WINDOW)
volume_history  = deque(maxlen=5)
last_velocity   = 0.0
attack_cooldown = 0

detected_string = None
detected_spike  = None
detected_mute   = False
current_volume  = 0.0
current_freq    = 0.0

pitch_detector  = None
running         = True
MODE            = 'guitar'

# ==================== АУДИО ====================

def smooth_pitch(v):
    pitch_history.append(v)
    if len(pitch_history) >= 2:
        return sorted(pitch_history)[len(pitch_history) // 2]
    return v

def get_string(freq):
    if freq <= 0:
        return None
    for name, (lo, hi) in STRING_RANGES[MODE].items():
        if lo <= freq <= hi:
            return name
    return None

def detect_spike(volume):
    global last_velocity, attack_cooldown
    if attack_cooldown > 0:
        attack_cooldown -= 1
        return None
    delta = volume - last_velocity
    last_velocity = volume
    if volume > NOISE_GATE_THRESHOLD * 2:
        if delta > VELOCITY_SPIKE_FIRE_THRESHOLD:
            attack_cooldown = 8
            return 'fire'
        elif delta > VELOCITY_SPIKE_USE_THRESHOLD:
            attack_cooldown = 8
            return 'use'
    return None

def _process_samples(samples):
    global detected_string, detected_spike, detected_mute, current_volume, current_freq

    rms = math.sqrt(sum(x * x for x in samples) / max(len(samples), 1))

    volume_history.append(rms)
    avg = sum(volume_history) / len(volume_history) if volume_history else 0.0
    current_volume = avg

    spike = detect_spike(avg)

    if avg < NOISE_GATE_THRESHOLD:
        detected_string = None
        current_freq    = 0.0
        return

    freq = float(pitch_detector(samples)[0])
    freq = smooth_pitch(freq)
    current_freq    = freq
    detected_string = get_string(freq)

    # Классифицируем спайк: со струной → use/fire, без струны → palm mute
    if spike:
        if detected_string:
            detected_spike = spike
        else:
            detected_mute = True


def audio_callback(indata, frames, time_info, status):
    """Callback для sounddevice"""
    if _HAS_NUMPY and hasattr(indata, 'shape'):
        samples = list(indata[:, 0].astype(float))
    else:
        n_floats = len(indata) // 4
        samples = list(struct.unpack(f'{n_floats}f', indata))
    _process_samples(samples)


def winmm_callback(samples):
    """Callback для WinMMStream"""
    _process_samples(samples)

# ==================== ОТОБРАЖЕНИЕ ====================

RESET  = '\033[0m'
BOLD   = '\033[1m'
DIM    = '\033[2m'
GREEN  = '\033[92m'
CYAN   = '\033[96m'
YELLOW = '\033[93m'
RED    = '\033[91m'

def bar(volume, width=28):
    filled = min(int(volume * 50 * width / 30), width)
    return '█' * filled + '░' * (width - filled)

def print_schema():
    print(f"{CYAN}{'─'*56}{RESET}")
    if MODE == 'guitar':
        print(f"{BOLD}  Схема управления — Гитара (6 струн){RESET}")
        print(f"{CYAN}{'─'*56}{RESET}")
        rows = [
            ('E (6-я)', '82 Hz',  'W',     'Вперёд'),
            ('A (5-я)', '110 Hz', 'S',     'Назад'),
            ('D (4-я)', '147 Hz', 'A',     'Стрейф влево'),
            ('G (3-я)', '196 Hz', 'D',     'Стрейф вправо'),
            ('B (2-я)', '247 Hz', 'Left',  'Поворот влево'),
            ('e (1-я)', '330 Hz', 'Right', 'Поворот вправо'),
        ]
    else:
        print(f"{BOLD}  Схема управления — Бас-гитара (4 струны){RESET}")
        print(f"{CYAN}{'─'*56}{RESET}")
        rows = [
            ('E (4-я)', '41 Hz',  'W', 'Вперёд'),
            ('A (3-я)', '55 Hz',  'S', 'Назад'),
            ('D (2-я)', '73 Hz',  'A', 'Стрейф влево'),
            ('G (1-я)', '98 Hz',  'D', 'Стрейф вправо'),
        ]
    for name, freq, key, action in rows:
        print(f"  {YELLOW}{name:8}{RESET} {DIM}{freq:7}{RESET}  →  {GREEN}{key:6}{RESET}  {action}")
    print()
    print(f"  {YELLOW}Слабый удар{RESET}   (со струной)  →  {GREEN}Space{RESET}   Использовать/открыть")
    print(f"  {YELLOW}Сильный удар{RESET}  (со струной)  →  {GREEN}CTRL {RESET}   Выстрел")
    print(f"  {YELLOW}Palm mute{RESET}     (без струны)  →  {GREEN}]    {RESET}   Следующее оружие")
    print(f"{CYAN}{'─'*56}{RESET}")

# ==================== ЛОГИКА УРОКОВ ====================

def wait_for_string(target, count):
    hits, last_hit = 0, None
    while hits < count and running:
        s = detected_string
        if s and s != last_hit:
            last_hit = s
            if s == target:
                hits += 1
                print(f"\r  {GREEN}[{'●'*hits}{'○'*(count-hits)}]{RESET} Струна {s}! +{hits}          ", end='', flush=True)
            else:
                info = KEY_INFO[MODE].get(s, ('?', '?'))
                print(f"\r  [{'●'*hits}{'○'*(count-hits)}] Струна {s} ({info[1]}) — нужна {target}   ", end='', flush=True)
        elif not s and last_hit:
            last_hit = None
        freq_str = f"{current_freq:6.1f} Hz" if current_freq > 0 else "  тишина "
        print(f"\r  [{'●'*hits}{'○'*(count-hits)}] {bar(current_volume)} {freq_str}  ", end='', flush=True)
        time.sleep(0.05)
    return hits >= count

def wait_for_spike(target, count):
    global detected_spike
    hits = 0
    while hits < count and running:
        spike = detected_spike
        detected_spike = None
        if spike == target:
            hits += 1
            label = 'Space' if target == 'use' else 'CTRL'
            print(f"\r  {GREEN}[{'●'*hits}{'○'*(count-hits)}]{RESET} {label}! +{hits}              ", end='', flush=True)
        elif spike and spike != target:
            wrong = 'слишком сильно (это CTRL)' if target == 'use' else 'слишком слабо (это Space)'
            print(f"\r  [{'●'*hits}{'○'*(count-hits)}] {wrong}         ", end='', flush=True)
        print(f"\r  [{'●'*hits}{'○'*(count-hits)}] {bar(current_volume)}  ", end='', flush=True)
        time.sleep(0.05)
    return hits >= count

def wait_for_mute(count):
    global detected_mute
    hits = 0
    while hits < count and running:
        if detected_mute:
            detected_mute = False
            hits += 1
            print(f"\r  {GREEN}[{'●'*hits}{'○'*(count-hits)}]{RESET} Palm mute! ] +{hits}              ", end='', flush=True)
        print(f"\r  [{'●'*hits}{'○'*(count-hits)}] {bar(current_volume)}  заглуши и ударь...  ", end='', flush=True)
        time.sleep(0.05)
    return hits >= count


def wait_for_sequence(sequence):
    global detected_string
    idx, last_hit = 0, None
    while idx < len(sequence) and running:
        target = sequence[idx]
        progress = '  '.join(
            f"{GREEN}{n}{RESET}" if i < idx else
            (f"{YELLOW}[{n}]{RESET}" if i == idx else f"{DIM}{n}{RESET}")
            for i, n in enumerate(sequence)
        )
        s = detected_string
        if s and s != last_hit:
            last_hit = s
            if s == target:
                idx += 1
                time.sleep(0.3)
            elif idx > 0:
                print(f"\r  {RED}Неверно ({s} вместо {target}) — сначала{RESET}          ", end='', flush=True)
                time.sleep(0.8)
                idx = 0
        elif not s and last_hit:
            last_hit = None
        freq_str = f"{current_freq:6.1f} Hz" if current_freq > 0 else "  тишина "
        print(f"\r  {progress}   {bar(current_volume)} {freq_str}  ", end='', flush=True)
        time.sleep(0.05)
    return idx >= len(sequence)

def run_lesson(lesson):
    print(f"\n{BOLD}{CYAN}{'═'*56}{RESET}")
    print(f"  {BOLD}{lesson['title']}{RESET}")
    print(f"{CYAN}{'═'*56}{RESET}")
    print(f"  {lesson['desc']}")
    if lesson.get('hint'):
        print(f"  {DIM}({lesson['hint']}){RESET}")
    print()

    gtype  = lesson['goal_type']
    target = lesson['goal']
    count  = lesson.get('count', 3)

    if gtype == 'string':
        key, action = KEY_INFO[MODE][target]
        print(f"  Цель: {YELLOW}{target} струна{RESET} → {GREEN}{key} ({action}){RESET}   ×{count}\n")
        ok = wait_for_string(target, count)

    elif gtype == 'spike':
        label = 'слабый удар → Space' if target == 'use' else 'сильный удар → CTRL'
        print(f"  Цель: {YELLOW}{label}{RESET}   ×{count}\n")
        ok = wait_for_spike(target, count)

    elif gtype == 'mute':
        print(f"  Цель: {YELLOW}palm mute → ] (смена оружия){RESET}   ×{count}\n")
        ok = wait_for_mute(count)

    elif gtype == 'sequence':
        print(f"  Последовательность: {YELLOW}{' → '.join(target)}{RESET}\n")
        ok = wait_for_sequence(target)

    print()
    if ok:
        print(f"  {GREEN}{BOLD}Урок пройден!{RESET}")
    time.sleep(1)
    return ok

# ==================== MAIN ====================

def main():
    global pitch_detector, running, MODE

    parser = argparse.ArgumentParser(description='Guitar/Bass-to-Doom Tutorial')
    parser.add_argument('--bass', action='store_true', help='Режим бас-гитары')
    args = parser.parse_args()
    if args.bass:
        MODE = 'bass'

    lessons = LESSONS_BASS if MODE == 'bass' else LESSONS_GUITAR
    mode_label = 'Бас-гитара' if MODE == 'bass' else 'Гитара'

    print(f"\n{BOLD}{CYAN}{'═'*56}{RESET}")
    print(f"  {BOLD}Guitar-to-Doom: Обучение — {mode_label}{RESET}")
    _audio_backend = 'sounddevice' if _HAS_SD else 'WinMM (ctypes fallback)'
    print(f"  Pitch Engine:  {'numpy (fast)' if _HAS_NUMPY else 'pure Python'}")
    print(f"  Audio Backend: {_audio_backend}")
    print(f"{CYAN}{'═'*56}{RESET}\n")
    print_schema()
    print()
    print(f"  {DIM}Подключи инструмент через аудиоинтерфейс.{RESET}")
    print(f"  {DIM}Enter — начать обучение...{RESET}")
    input()

    pitch_detector = PitchDetector(sample_rate=SAMPLE_RATE)

    if not _HAS_SD and not _HAS_WINMM:
        print('[ERROR] Нет доступной библиотеки аудио.')
        sys.exit(1)

    def _make_stream():
        if _HAS_SD:
            stream_cls   = sd.InputStream  if _HAS_NUMPY else sd.RawInputStream
            stream_dtype = np.float32      if _HAS_NUMPY else 'float32'
            return stream_cls(
                samplerate=SAMPLE_RATE,
                blocksize=BLOCK_SIZE,
                channels=CHANNELS,
                dtype=stream_dtype,
                callback=audio_callback,
            )
        else:
            return WinMMStream(
                sample_rate=SAMPLE_RATE,
                block_size=BLOCK_SIZE,
                channels=CHANNELS,
                callback=winmm_callback,
            )

    passed = 0
    with _make_stream():
        for i, lesson in enumerate(lessons):
            ok = run_lesson(lesson)
            if ok:
                passed += 1
            if i < len(lessons) - 1:
                print(f"\n  {DIM}Enter → следующий урок   Ctrl+C = выход{RESET}")
                try:
                    input()
                except KeyboardInterrupt:
                    break

    running = False
    total = len(lessons)

    print(f"\n{CYAN}{'═'*56}{RESET}")
    print(f"  {BOLD}Обучение завершено — {mode_label}{RESET}")
    print(f"  Пройдено: {GREEN}{passed}{RESET} / {total}")
    if passed == total:
        print(f"\n  {GREEN}{BOLD}Нат20! Полное управление освоено. Запускай Doom.{RESET}")
    elif passed >= total - 2:
        print(f"\n  {YELLOW}Почти всё — можно играть!{RESET}")
    else:
        print(f"\n  {DIM}Попробуй ещё раз.{RESET}")
    print(f"{CYAN}{'═'*56}{RESET}\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{DIM}Прервано.{RESET}")
