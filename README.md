<div align="center">

# 🎸 Guitar-to-Doom Controller Pro

**Играй в Doom на гитаре. Серьёзно.**

[![](https://img.shields.io/badge/v2.1.0-0099CC?style=flat-square)](https://github.com/elementalmasterpotap/guitar-to-doom/releases)
[![](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![](https://img.shields.io/badge/Windows-0078D6?style=flat-square&logo=windows&logoColor=white)](https://github.com/elementalmasterpotap/guitar-to-doom)
[![](https://img.shields.io/badge/GZDoom-v4.14.2-FF6600?style=flat-square)](https://zdoom.org/downloads)
[![](https://img.shields.io/badge/license-MIT-22AA44?style=flat-square)](LICENSE)
[![](https://img.shields.io/badge/Telegram-channel-26A5E4?style=flat-square&logo=telegram&logoColor=white)](https://t.me/potap_attic)

<details>
<summary>🇬🇧 English</summary>

**Turn your guitar into a Doom controller.**
Every string maps to a key. Palm mute switches weapons. GUI launcher picks the game.

## What's inside

### 🎮 Built by the author
| Feature | What it does |
|---------|-------------|
| **YIN Pitch Detection** | Pure Python, no aubio — sub-12ms latency, works on any Python version |
| **Palm Mute Detection** | Volume spike without pitch → next weapon (`]`). Works mid-riff. |
| **GUI Launcher** | Frameless EXE, animated VU meter, pick game + instrument, hit Play |
| **WinMM Fallback** | ctypes-based backend — zero extra dependencies, Python 3.15+ compatible |
| **Interactive Tutorial** | Step-by-step calibration for both guitar and bass |
| **Noise Gate + Smoothing** | No false triggers, stable pitch recognition under real playing conditions |

### 🌍 Community & upstream (bundled, not authored here)
| Source | What it brings |
|--------|---------------|
| **GZDoom v4.14.2** *([ZDoom team](https://zdoom.org))* | Vulkan renderer, widescreen support, ZScript modding, full WAD ecosystem |
| **IDKFA Soundtrack v2** *([Andrew Hulshult](https://www.moddb.com/downloads/idkfa-soundtrack-wad-only-version))* | Metal/rock music replacement — replaces original MIDI with real recorded tracks. 90MB of pure upgrade. |
| **NeuralUpscale2x v1.0** *(community mod)* | AI-upscaled textures at 2×. Sharper details, pixel-faithful aesthetic preserved. |

## Controls — Guitar (6 strings)
| String | Hz | Key | Action |
|--------|----|-----|--------|
| E (6th) | ~82 Hz | W | Move forward |
| A (5th) | ~110 Hz | S | Move backward |
| D (4th) | ~147 Hz | A | Strafe left |
| G (3rd) | ~196 Hz | D | Strafe right |
| B (2nd) | ~247 Hz | ← | Turn left |
| e (1st) | ~330 Hz | → | Turn right |
| Soft hit (with string) | — | Space | Use / open door |
| Hard hit (with string) | — | Ctrl | Fire |
| **Palm mute** | — | ] | Next weapon |
| ESC | — | — | **PANIC STOP** |

## Controls — Bass (4 strings)
| String | Hz | Key | Action |
|--------|----|-----|--------|
| E (4th) | ~41 Hz | W | Move forward |
| A (3rd) | ~55 Hz | S | Move backward |
| D (2nd) | ~73 Hz | A | Strafe left |
| G (1st) | ~98 Hz | D | Strafe right |
| Soft hit | — | Space | Use |
| Hard hit | — | Ctrl | Fire |
| **Palm mute** | — | ] | Next weapon |
| ESC | — | — | **PANIC STOP** |

## Bundled games
| BAT file | Game |
|----------|------|
| `Play The Ultimate DOOM (Vulkan).bat` | Doom 1 (4 episodes) |
| `Play DOOM II (Vulkan).bat` | Doom 2 + NRFTL + Master Levels |
| `Play SIGIL (Vulkan).bat` | SIGIL (by Romero) |
| `Play TNT Evilution (Vulkan).bat` | Final Doom: TNT |
| `Play The Plutonia Experiment (Vulkan).bat` | Final Doom: Plutonia |
| `Play No Rest for the Living (Vulkan).bat` | NRFTL (Xbox exclusive) |
| `Play Master Levels (Vulkan).bat` | Master Levels |

## Installation
```bash
pip install -r requirements.txt
python guitar_to_doom.py
```
Or just run `GuitarDoomLauncher.exe` — pick game, pick instrument, hit Play.

## Calibration
Edit the **CONFIG** section in `guitar_to_doom.py`:
```python
NOISE_GATE_THRESHOLD = 0.015    # noise floor (0.001–0.1)
VELOCITY_SPIKE_THRESHOLD = 0.08 # fire sensitivity
PITCH_SMOOTHING_WINDOW = 4      # pitch stability (2–8)
```
Full guide → [CALIBRATION.md](CALIBRATION.md)

## Requirements
- Windows 10/11
- Python 3.8+ (WinMM fallback covers any version including 3.15+)
- Guitar / bass + audio interface or Jack→USB adapter
- GZDoom v4.14.2 (included)

## License
MIT — rock and roll never dies 🤘

</details>

<details open>
<summary>🇷🇺 Русский</summary>

**Гитара → контроллер для Doom.**
Каждая струна — клавиша. Palm mute меняет оружие. GUI лаунчер выбирает игру.

## Что внутри

### 🎮 Авторские фишки
| Фишка | Что делает |
|-------|-----------|
| **YIN Pitch Detection** | Pure Python, без aubio — задержка <12мс, любая версия Python |
| **Palm Mute Detection** | Volume spike без pitch → смена оружия (`]`). Работает прямо во время риффа. |
| **GUI Лаунчер** | Frameless EXE, анимированный VU-метр, выбор игры и инструмента |
| **WinMM Fallback** | ctypes-бэкенд без зависимостей — работает на Python 3.15+ |
| **Интерактивный туториал** | Пошаговое обучение для гитары и баса |
| **Noise Gate + Smoothing** | Нет ложных срабатываний, стабильный pitch при реальной игре |

### 🌍 Улучшения от сообщества (включены, не авторские)
| Источник | Что даёт |
|----------|---------|
| **GZDoom v4.14.2** *([ZDoom team](https://zdoom.org))* | Vulkan рендерер, widescreen, ZScript, полная экосистема модов |
| **IDKFA Soundtrack v2** *([Andrew Hulshult](https://www.moddb.com/downloads/idkfa-soundtrack-wad-only-version))* | Метал/рок вместо стандартного MIDI — реальные записанные треки, 90MB живой музыки |
| **NeuralUpscale2x v1.0** *(community mod)* | Нейросетевой апскейл текстур 2× — чётче, но пиксельность сохранена |

## Управление — Электрогитара (6 струн)
| Струна | Гц | Клавиша | Действие |
|--------|-----|---------|----------|
| E (6-я) | ~82 Hz | W | Вперёд |
| A (5-я) | ~110 Hz | S | Назад |
| D (4-я) | ~147 Hz | A | Влево |
| G (3-я) | ~196 Hz | D | Вправо |
| B (2-я) | ~247 Hz | ← | Поворот влево |
| e (1-я) | ~330 Hz | → | Поворот вправо |
| Слабый удар (со струной) | — | Space | Использовать / открыть |
| Сильный удар (со струной) | — | Ctrl | Выстрел |
| **Palm mute** | — | ] | Следующее оружие |
| ESC | — | — | **ПАНИКА / СТОП** |

> **Palm mute** — приглуши струны ладонью и ударь. Volume spike есть, pitch нет → `]`.

## Управление — Бас-гитара (4 струны)
| Струна | Гц | Клавиша | Действие |
|--------|-----|---------|----------|
| E (4-я) | ~41 Hz | W | Вперёд |
| A (3-я) | ~55 Hz | S | Назад |
| D (2-я) | ~73 Hz | A | Влево |
| G (1-я) | ~98 Hz | D | Вправо |
| Слабый удар | — | Space | Использовать |
| Сильный удар | — | Ctrl | Выстрел |
| **Palm mute** | — | ] | Следующее оружие |
| ESC | — | — | **ПАНИКА / СТОП** |

## Игры в комплекте
| BAT-файл | Игра |
|----------|------|
| `Play The Ultimate DOOM (Vulkan).bat` | Doom 1 (4 эпизода) |
| `Play DOOM II (Vulkan).bat` | Doom 2 + NRFTL + Master Levels |
| `Play SIGIL (Vulkan).bat` | SIGIL (от Ромеро) |
| `Play TNT Evilution (Vulkan).bat` | Final Doom: TNT |
| `Play The Plutonia Experiment (Vulkan).bat` | Final Doom: Plutonia |
| `Play No Rest for the Living (Vulkan).bat` | NRFTL (Xbox-эксклюзив) |
| `Play Master Levels (Vulkan).bat` | Master Levels |

## Сетап GZDoom

GZDoom v4.14.2 настроен под Vulkan:

| Параметр | Значение |
|----------|---------|
| Backend | Vulkan (`vid_preferbackend=1`) |
| Разрешение | 2752×1152, Fullscreen |
| Фильтрация | Anisotropic 16x |
| SSAO | Включено |
| Звук | OpenAL, 48kHz, 128 каналов |
| Язык | Русский |

```batch
:: Структура запуска
gzdoom.exe ^
  -config gzdoom.ini ^
  -savedir save ^
  -iwad iwads\doom2.wad ^
  -file mods\audio\IDKFAv2.wad ^
  -file mods\graphics\NeuralUpscale2x_v1.0.pk3
```

## Установка
```bash
pip install -r requirements.txt
python guitar_to_doom.py
```
Или запусти `GuitarDoomLauncher.exe` — выбери игру и инструмент, нажми Play.

## Калибровка

Открой `guitar_to_doom.py`, секция **КОНФИГУРАЦИЯ**:
```python
NOISE_GATE_THRESHOLD = 0.015    # порог шума (0.001–0.1)
VELOCITY_SPIKE_THRESHOLD = 0.08 # чувствительность выстрела
PITCH_SMOOTHING_WINDOW = 4      # сглаживание pitch (2–8)
```
Подробно → [CALIBRATION.md](CALIBRATION.md)

## Архитектура
```
Гитара → Аудиоинтерфейс → sounddevice → YIN Pitch Detection
                                               │
                            ┌──────────────────┴──────────────────┐
                            │  Noise Gate (NOISE_GATE_THRESHOLD)   │
                            │  Pitch Smoothing (SMOOTHING_WINDOW)  │
                            │  Velocity / Palm Mute Detection      │
                            └──────────────────┬──────────────────┘
                                               │
                                     pydirectinput → GZDoom
```

## Зависимости
| Библиотека | Зачем |
|-----------|-------|
| **sounddevice** | Аудио ввод в реальном времени |
| **pydirectinput** | Имитация нажатий DirectInput |
| **numpy** | Обработка аудиосигнала |
| **pygetwindow** | Определение активного окна |
| **keyboard** | Глобальный хук клавиатуры |

## Troubleshooting
| Проблема | Решение |
|----------|---------|
| Ложные срабатывания | Увеличь `NOISE_GATE_THRESHOLD` |
| Большая задержка | Уменьши `BLOCK_SIZE` |
| Скрипт не реагирует | Проверь входное устройство в настройках Windows |
| Не работает в GZDoom | Добавь название окна в `TARGET_WINDOW_TITLES` |

## Лицензия
MIT — рок-н-ролл никогда не умрёт 🤘

</details>

</div>
