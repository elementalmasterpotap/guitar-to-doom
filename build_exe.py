"""
build_exe.py — компилирует launcher.py в одиночный .exe через PyInstaller.
Автоматически выбирает Python 3.12 если текущий Python 3.14+ (PyInstaller не поддерживает).
Запуск: python build_exe.py
"""
import subprocess, sys, os, shutil

# PyInstaller поддерживает Python 3.8–3.13. Для 3.14+ ищем 3.12.
def _find_build_python():
    v = sys.version_info
    if v < (3, 14):
        return sys.executable
    candidates = [
        r"C:\Users\Eleme\.local\bin\python3.12.exe",
        r"C:\Python312\python.exe",
        r"C:\Python311\python.exe",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    # Попробовать в PATH
    for name in ("python3.12", "python3.11"):
        r = subprocess.run(["where", name], capture_output=True, text=True)
        if r.returncode == 0:
            return r.stdout.strip().splitlines()[0]
    print(f"[WARN] Python {v.major}.{v.minor} не поддерживается PyInstaller.")
    print("       Установи Python 3.12 или запусти build_exe.py через python3.12.")
    return sys.executable  # попытка всё равно

BUILD_PY = _find_build_python()

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
BUILD= os.path.join(ROOT, "build_tmp")
SPEC = os.path.join(ROOT, "launcher.spec")

def pip(*args):
    r = subprocess.run([BUILD_PY, "-m", "pip", "install", *args, "-q"],
                       capture_output=True, text=True)
    if r.returncode != 0 and "externally-managed" in r.stderr:
        subprocess.run([BUILD_PY, "-m", "pip", "install", *args, "-q",
                        "--break-system-packages"], capture_output=True)

def ensure_pyinstaller():
    r = subprocess.run([BUILD_PY, "-c", "import PyInstaller"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        print("[OK] PyInstaller найден")
    else:
        print("[..] Устанавливаю PyInstaller + pywin32-ctypes...")
        pip("pyinstaller", "pywin32-ctypes")
        print("[OK] Установлено")

def build():
    ensure_pyinstaller()
    print("[..] Сборка EXE...")

    v = subprocess.run([BUILD_PY, "--version"], capture_output=True, text=True).stdout.strip()
    print(f"[..] Используется {BUILD_PY} ({v})")

    cmd = [
        BUILD_PY, "-m", "PyInstaller",
        "--onefile",                         # один файл
        "--windowed",                        # без консольного окна
        "--name", "GuitarDoomLauncher",
        "--distpath", DIST,
        "--workpath", BUILD,
        "--specpath", ROOT,
        "--hidden-import", "tkinter",
        "--hidden-import", "tkinter.ttk",
        "--hidden-import", "ctypes.wintypes",
        "--add-data", f"{os.path.join(ROOT,'winmm_audio.py')};.",
        os.path.join(ROOT, "launcher.py"),
    ]

    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print("[ERROR] PyInstaller завершился с ошибкой")
        sys.exit(1)

    exe_src = os.path.join(DIST, "GuitarDoomLauncher.exe")
    exe_dst = os.path.join(ROOT, "GuitarDoomLauncher.exe")

    if os.path.exists(exe_src):
        shutil.copy2(exe_src, exe_dst)
        size_mb = os.path.getsize(exe_dst) / 1024 / 1024
        print(f"\n[OK] EXE готов: GuitarDoomLauncher.exe ({size_mb:.1f} MB)")
        print(f"     Путь: {exe_dst}")

        # Чистим временные файлы PyInstaller
        for p in [DIST, BUILD, SPEC]:
            try:
                if os.path.isdir(p):  shutil.rmtree(p, ignore_errors=True)
                elif os.path.isfile(p): os.remove(p)
            except Exception:
                pass
        print("[OK] Временные файлы удалены")
    else:
        print("[ERROR] EXE не найден после сборки")
        sys.exit(1)

if __name__ == "__main__":
    build()
    input("\nEnter для выхода...")
