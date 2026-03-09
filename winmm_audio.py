"""
winmm_audio.py — Pure-Python аудио захват через Windows WinMM API (ctypes).
Fallback для Python 3.15+ где sounddevice/pyaudio не работают.

Совместимость: любой Python 3.x с ctypes, только Windows.
"""
import ctypes
import threading
import struct
import time
import sys

if sys.platform != 'win32':
    raise ImportError('winmm_audio: только Windows')

winmm = ctypes.windll.winmm

# ── WinMM константы ───────────────────────────────────────────────────────────
WAVE_FORMAT_PCM  = 1
WAVE_MAPPER      = 0xFFFFFFFF
MMSYSERR_NOERROR = 0
WHDR_DONE        = 0x00000001
WHDR_PREPARED    = 0x00000002
WHDR_INQUEUE     = 0x00000010
CALLBACK_NULL    = 0x00000000


# ── Структуры (x64 выравнивание) ──────────────────────────────────────────────

class WAVEFORMATEX(ctypes.Structure):
    _fields_ = [
        ('wFormatTag',      ctypes.c_uint16),   # WORD
        ('nChannels',       ctypes.c_uint16),   # WORD
        ('nSamplesPerSec',  ctypes.c_uint32),   # DWORD
        ('nAvgBytesPerSec', ctypes.c_uint32),   # DWORD
        ('nBlockAlign',     ctypes.c_uint16),   # WORD
        ('wBitsPerSample',  ctypes.c_uint16),   # WORD
        ('cbSize',          ctypes.c_uint16),   # WORD
    ]


class WAVEHDR(ctypes.Structure):
    # На x64: LPSTR=8б, DWORD=4б, DWORD_PTR=8б, pointer=8б
    _fields_ = [
        ('lpData',          ctypes.c_void_p),   # LPSTR   (8 байт)
        ('dwBufferLength',  ctypes.c_uint32),   # DWORD   (4 байта)
        ('dwBytesRecorded', ctypes.c_uint32),   # DWORD   (4 байта)
        ('dwUser',          ctypes.c_size_t),   # DWORD_PTR (8 байт)
        ('dwFlags',         ctypes.c_uint32),   # DWORD   (4 байта)
        ('dwLoops',         ctypes.c_uint32),   # DWORD   (4 байта)
        ('lpNext',          ctypes.c_void_p),   # pointer (8 байт)
        ('reserved',        ctypes.c_size_t),   # DWORD_PTR (8 байт)
    ]


# ── Основной класс ────────────────────────────────────────────────────────────

class WinMMStream:
    """
    Потоковый захват аудио через WinMM waveIn API.

    callback(samples: list[float]) — нормализованные PCM [-1.0, 1.0], mono,
    len(samples) == block_size. Вызывается из background-треда.
    """

    def __init__(self, sample_rate: int = 44100,
                 block_size: int = 512,
                 channels: int = 1,
                 callback=None):
        self.sample_rate = sample_rate
        self.block_size  = block_size
        self.channels    = channels
        self.callback    = callback

        self._hWaveIn  = ctypes.c_void_p(None)
        self._running  = False
        self._thread   = None
        # Удерживаем буферы чтобы GC не прибрал пока идёт запись
        self._raw_bufs = []
        self._headers  = []

    # ── context manager ──────────────────────────────────────────────────────

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()

    # ── публичный API ────────────────────────────────────────────────────────

    def start(self):
        fmt = self._make_format()
        h   = ctypes.c_void_p()

        ret = winmm.waveInOpen(
            ctypes.byref(h),
            WAVE_MAPPER,
            ctypes.byref(fmt),
            0, 0,
            CALLBACK_NULL,
        )
        if ret != MMSYSERR_NOERROR:
            raise OSError(f'waveInOpen завершился с кодом {ret}')
        self._hWaveIn = h

        self._running = True
        self._prepare_buffers(n=2)
        winmm.waveInStart(self._hWaveIn)

        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._hWaveIn.value:
            winmm.waveInStop(self._hWaveIn)
            winmm.waveInReset(self._hWaveIn)
            for hdr in self._headers:
                winmm.waveInUnprepareHeader(
                    self._hWaveIn,
                    ctypes.byref(hdr),
                    ctypes.sizeof(WAVEHDR),
                )
            winmm.waveInClose(self._hWaveIn)
            self._hWaveIn = ctypes.c_void_p(None)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._raw_bufs.clear()
        self._headers.clear()

    # ── внутренние ───────────────────────────────────────────────────────────

    def _make_format(self) -> WAVEFORMATEX:
        fmt                 = WAVEFORMATEX()
        fmt.wFormatTag      = WAVE_FORMAT_PCM
        fmt.nChannels       = self.channels
        fmt.nSamplesPerSec  = self.sample_rate
        fmt.wBitsPerSample  = 16                              # 16-bit PCM
        fmt.nBlockAlign     = self.channels * 2
        fmt.nAvgBytesPerSec = self.sample_rate * fmt.nBlockAlign
        fmt.cbSize          = 0
        return fmt

    def _prepare_buffers(self, n: int = 2):
        buf_bytes = self.block_size * self.channels * 2      # 16-bit = 2 байта/семпл

        for _ in range(n):
            raw = ctypes.create_string_buffer(buf_bytes)
            hdr = WAVEHDR()
            hdr.lpData          = ctypes.addressof(raw)
            hdr.dwBufferLength  = buf_bytes
            hdr.dwBytesRecorded = 0
            hdr.dwFlags         = 0

            self._raw_bufs.append(raw)
            self._headers.append(hdr)

            winmm.waveInPrepareHeader(
                self._hWaveIn,
                ctypes.byref(hdr),
                ctypes.sizeof(WAVEHDR),
            )
            winmm.waveInAddBuffer(
                self._hWaveIn,
                ctypes.byref(hdr),
                ctypes.sizeof(WAVEHDR),
            )

    def _requeue(self, idx: int):
        """Вернуть заполненный буфер обратно в очередь драйвера."""
        hdr = self._headers[idx]
        raw = self._raw_bufs[idx]

        # Сбрасываем флаги (кроме PREPARED — он уже выставлен PrepareHeader)
        hdr.dwFlags        = WHDR_PREPARED
        hdr.dwBytesRecorded = 0
        hdr.lpData         = ctypes.addressof(raw)
        hdr.dwBufferLength = len(raw)

        winmm.waveInAddBuffer(
            self._hWaveIn,
            ctypes.byref(hdr),
            ctypes.sizeof(WAVEHDR),
        )

    def _poll_loop(self):
        idx = 0
        while self._running:
            hdr = self._headers[idx]

            # Ждём WHDR_DONE — драйвер заполнил буфер
            while self._running and not (hdr.dwFlags & WHDR_DONE):
                time.sleep(0.001)

            if not self._running:
                break

            n_bytes = hdr.dwBytesRecorded
            if n_bytes > 0 and self.callback is not None:
                try:
                    raw      = self._raw_bufs[idx]
                    n_samp   = n_bytes // 2          # 16-bit PCM
                    ints     = struct.unpack_from(f'<{n_samp}h', raw.raw, 0)
                    samples  = [s / 32768.0 for s in ints]
                    self.callback(samples)
                except Exception:
                    pass  # не роняем поток из-за ошибки в callback

            self._requeue(idx)
            idx = (idx + 1) % len(self._headers)
