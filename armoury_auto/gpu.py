"""GPU usage helpers: how busy the graphics engines are (Windows performance counters)
and which apps currently hold the NVIDIA dGPU (so Eco mode never yanks it from them)."""
import ctypes
import re
import subprocess
from collections import defaultdict
from ctypes import wintypes

_CREATE_NO_WINDOW = 0x08000000
_PDH_FMT_DOUBLE = 0x00000200
_PDH_MORE_DATA = 0x800007D2
_COUNTER_3D = r"\GPU Engine(*engtype_3D)\Utilization Percentage"

_pdh = ctypes.WinDLL("pdh")
for _fn in ("PdhOpenQueryW", "PdhAddEnglishCounterW", "PdhCollectQueryData", "PdhGetFormattedCounterArrayW"):
    getattr(_pdh, _fn).restype = wintypes.DWORD


class _PdhValue(ctypes.Structure):
    _fields_ = [("CStatus", wintypes.DWORD), ("doubleValue", ctypes.c_double)]


class _PdhItem(ctypes.Structure):
    _fields_ = [("szName", wintypes.LPWSTR), ("FmtValue", _PdhValue)]


class GpuLoad:
    """3D-engine utilization of the busiest GPU (the AMD iGPU while the dGPU is in Eco)."""

    def __init__(self):
        self._query = ctypes.c_void_p()
        self._counter = ctypes.c_void_p()
        _pdh.PdhOpenQueryW(None, None, ctypes.byref(self._query))
        _pdh.PdhAddEnglishCounterW(self._query, _COUNTER_3D, None, ctypes.byref(self._counter))
        _pdh.PdhCollectQueryData(self._query)

    def busiest_percent(self) -> float:
        _pdh.PdhCollectQueryData(self._query)
        size, count = wintypes.DWORD(0), wintypes.DWORD(0)
        if _pdh.PdhGetFormattedCounterArrayW(self._counter, _PDH_FMT_DOUBLE, ctypes.byref(size),
                                             ctypes.byref(count), None) != _PDH_MORE_DATA:
            return 0.0
        buf = (ctypes.c_byte * size.value)()
        if _pdh.PdhGetFormattedCounterArrayW(self._counter, _PDH_FMT_DOUBLE, ctypes.byref(size),
                                             ctypes.byref(count), buf) != 0:
            return 0.0
        items = ctypes.cast(buf, ctypes.POINTER(_PdhItem))
        per_gpu = defaultdict(float)
        for i in range(count.value):
            item = items[i]
            if item.FmtValue.CStatus <= 1:  # valid or new data
                luid = re.search(r"luid_(\w+?_\w+?)_", item.szName or "")
                per_gpu[luid.group(1) if luid else "?"] += item.FmtValue.doubleValue
        return min(100.0, max(per_gpu.values(), default=0.0))


def dgpu_apps() -> list[str]:
    """Process names using the NVIDIA GPU, per nvidia-smi ([] when the dGPU is off)."""
    try:
        out = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=15,
                             creationflags=_CREATE_NO_WINDOW).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    names = re.findall(r"^\|\s+\d+\s+\S+\s+\S+\s+\d+\s+[CG+]+\s+(.+?)\s{2,}\S+\s*\|$", out, re.M)
    return sorted({n.split("\\")[-1] for n in names})
