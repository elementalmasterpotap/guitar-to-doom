"""Guitar-to-Doom Controller Pro — установщик зависимостей"""

import subprocess
import sys
import os

# ── Зависимости которые всегда ставятся ─────────────────────
BASE_PACKAGES = [
    ('pydirectinput', 'pydirectinput'),
    ('pygetwindow',   'pygetwindow'),
    ('keyboard',      'keyboard'),
]

# Пакеты требующие рабочего cffi/numpy (весь audio стек)
AUDIO_PACKAGES = [
    ('numpy',       'numpy'),
    ('sounddevice', 'sounddevice'),
]


def check_python():
    v = sys.version_info
    print(f'Python {v.major}.{v.minor}.{v.micro}  [{sys.executable}]')
    if v.major < 3 or (v.major == 3 and v.minor < 8):
        print('[ERROR] Нужен Python 3.8+')
        sys.exit(1)
    print('[OK] Python OK')


def audio_supported():
    """Возвращает (поддерживается: bool, причина: str)"""
    import re
    v = sys.version_info

    # 1) Runtime API (Python 3.12+): самый надёжный способ
    is_freethreading = False
    if hasattr(sys, '_is_gil_enabled'):
        try:
            is_freethreading = not sys._is_gil_enabled()
        except Exception:
            pass

    # 2) По имени exe: python3.13t.exe, python3.15t.exe → ищем \d+t на конце
    if not is_freethreading:
        exe_stem = re.sub(r'\.exe$', '', os.path.basename(sys.executable).lower())
        is_freethreading = bool(re.search(r'\d+t$', exe_stem))

    # 3) По строке версии (запасной вариант)
    if not is_freethreading:
        is_freethreading = 'free-threading' in sys.version.lower()

    if is_freethreading:
        return False, 'free-threading сборка — numpy/sounddevice/cffi не имеют wheels'
    if v >= (3, 14):
        return False, (
            f'Python {v.major}.{v.minor} — numpy и sounddevice '
            f'не поддерживают эту версию (нужен 3.8–3.13)'
        )
    return True, ''


def upgrade_pip():
    print('\n[0/?] Обновление pip...')
    r = subprocess.run(
        [sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip', '-q'],
        capture_output=True, text=True
    )
    if r.returncode != 0 and 'externally-managed' in r.stderr:
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip', '-q',
             '--break-system-packages'],
            capture_output=True
        )


def install_packages(packages):
    total = len(packages)
    for i, (pkg, _) in enumerate(packages, 1):
        print(f'[{i}/{total}] {pkg}...', end=' ', flush=True)
        r = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', pkg, '-q'],
            capture_output=True, text=True
        )
        # PEP 668: externally-managed-environment → retry с --break-system-packages
        if r.returncode != 0 and 'externally-managed' in r.stderr:
            r = subprocess.run(
                [sys.executable, '-m', 'pip', 'install', pkg, '-q',
                 '--break-system-packages'],
                capture_output=True, text=True
            )
        if r.returncode != 0:
            print(f'WARNING: {r.stderr.strip()[:80]}')
        else:
            print('OK')


def verify(packages):
    print('\nПроверка импортов:')
    failed = []
    for pkg, import_name in packages:
        try:
            __import__(import_name)
            print(f'  [OK] {pkg}')
        except ImportError:
            print(f'  [FAIL] {pkg}')
            failed.append(pkg)
    return failed


def main():
    print('=' * 58)
    print('  Guitar-to-Doom Controller Pro')
    print('  Установщик зависимостей')
    print('=' * 58)
    print()
    check_python()

    audio_ok, audio_reason = audio_supported()

    if audio_ok:
        packages = AUDIO_PACKAGES + BASE_PACKAGES
        print('[INFO] numpy + sounddevice: будут установлены')
    else:
        packages = BASE_PACKAGES
        print(f'[SKIP] numpy + sounddevice: {audio_reason}')
        print()
        print('╔══════════════════════════════════════════════════════╗')
        print('║  numpy/sounddevice не поддерживают эту версию Python.║')
        print('║  Аудио будет захватываться через встроенный WinMM.   ║')
        print('║  Гитарный контроллер РАБОТАЕТ на любом Python.       ║')
        print('╚══════════════════════════════════════════════════════╝')
        print()

    upgrade_pip()
    print()
    install_packages(packages)
    print()
    print('=' * 58)
    failed = verify(packages)

    if failed:
        print(f'\n[WARNING] Не установлены: {", ".join(failed)}')
    else:
        if audio_ok:
            print('\nВсе зависимости установлены!')
        else:
            print('\npydirectinput / pygetwindow / keyboard — OK')
            print('[!] Аудио через WinMM (ctypes). Гитарный контроллер готов к работе.')
        print()
        print('Запуск:')
        print('  Guitar_Doom_II.bat       - Doom II с гитарным управлением')
        print('  Guitar_Ultimate_Doom.bat - Ultimate Doom')
        print('  Guitar_Tutorial.bat      - Обучение управлению гитарой')

    print()
    input('Enter для выхода...')


if __name__ == '__main__':
    main()
