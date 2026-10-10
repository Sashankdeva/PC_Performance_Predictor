"""Low-level control of the ASUS performance mode (the one Armoury Crate shows as
Silent / Performance / Turbo) and GPU mode (Eco / Standard / Ultimate) through the
ATK ACPI driver, plus the matching Windows power plans Armoury Crate creates for each mode."""
import ctypes
import re
import subprocess
import uuid
from ctypes import wintypes

# Firmware values for device 0x00120075 (same as Fn+F5 / Armoury Crate).
MODES = {"performance": 0, "turbo": 1, "silent": 2}

GPU_MODES = ("eco", "standard")

_DEVICE_PERFORMANCE_MODE = 0x00120075
_DEVICE_GPU_ECO = 0x00090020  # 1 = dGPU powered off
_DEVICE_GPU_MUX = 0x00090016  # 0 = Ultimate (dGPU drives the screen), 1 = Optimus
_METHOD_DEVS = 0x53564544  # "DEVS" - set device status
_METHOD_DSTS = 0x53545344  # "DSTS" - read device status
_IOCTL_ATK_ACPI = 0x0022240C
_INVALID_HANDLE = ctypes.c_void_p(-1).value
_CREATE_NO_WINDOW = 0x08000000

_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_k32.CreateFileW.restype = wintypes.HANDLE
_k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                             wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
_k32.DeviceIoControl.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                                 ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
_k32.LocalFree.argtypes = [ctypes.c_void_p]

_powrprof = ctypes.WinDLL("powrprof")
_powrprof.PowerGetActiveScheme.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
_powrprof.PowerSetActiveScheme.argtypes = [ctypes.c_void_p, ctypes.c_char_p]


class AsusAcpi:
    def __init__(self):
        self._handle = _k32.CreateFileW(r"\\.\ATKACPI", 0xC0000000, 3, None, 3, 0, None)
        if self._handle in (None, _INVALID_HANDLE):
            raise OSError(f"Cannot open ASUS ATK ACPI driver (error {ctypes.get_last_error()}). "
                          "Is 'ASUS System Control Interface' installed?")

    def _call(self, method: int, device: int, value: int = 0) -> int | None:
        args = device.to_bytes(4, "little") + value.to_bytes(4, "little")
        packet = method.to_bytes(4, "little") + len(args).to_bytes(4, "little") + args
        in_buf = ctypes.create_string_buffer(packet, len(packet))
        out_buf = ctypes.create_string_buffer(16)
        returned = wintypes.DWORD()
        ok = _k32.DeviceIoControl(self._handle, _IOCTL_ATK_ACPI, in_buf, len(packet),
                                  out_buf, len(out_buf), ctypes.byref(returned), None)
        return int.from_bytes(out_buf.raw[:4], "little") if ok else None

    def _set(self, device: int, value: int, what: str) -> None:
        if self._call(_METHOD_DEVS, device, value) != 1:
            raise OSError(f"ASUS driver rejected {what} (error {ctypes.get_last_error()})")

    def _get(self, device: int) -> int | None:
        status = self._call(_METHOD_DSTS, device)
        return status & 0xFFFF if status and status & 0x10000 else None  # 0x10000 = device present

    def set_mode(self, mode: str) -> None:
        self._set(_DEVICE_PERFORMANCE_MODE, MODES[mode], f"mode '{mode}'")

    def ultimate_mode(self) -> bool:
        """MUX routes the screen straight to the dGPU; Eco is impossible until a restart."""
        return self._get(_DEVICE_GPU_MUX) == 0

    def gpu_mode(self) -> str | None:
        """'ultimate', 'eco' or 'standard' (dGPU on, Optimus)."""
        if self.ultimate_mode():
            return "ultimate"
        eco = self._get(_DEVICE_GPU_ECO)
        return None if eco is None else ("eco" if eco == 1 else "standard")

    def set_gpu(self, mode: str) -> None:
        """'eco' turns the dGPU off, 'standard' turns it on. Takes a few seconds."""
        self._set(_DEVICE_GPU_ECO, 1 if mode == "eco" else 0, f"GPU mode '{mode}'")


class PowerPlans:
    """Maps modes to the Windows power plans Armoury Crate keeps in sync with them."""

    def __init__(self, plan_names: dict[str, str]):
        listing = subprocess.run(["powercfg", "/list"], capture_output=True, text=True,
                                 creationflags=_CREATE_NO_WINDOW).stdout
        by_name = {name.strip().lower(): guid.lower()
                   for guid, name in re.findall(r"([0-9a-fA-F-]{36})\s+\((.+?)\)", listing)}
        self.by_mode = {mode: by_name.get(name.lower()) for mode, name in plan_names.items()}

    def active(self) -> str | None:
        ptr = ctypes.c_void_p()
        if _powrprof.PowerGetActiveScheme(None, ctypes.byref(ptr)) != 0:
            return None
        guid = str(uuid.UUID(bytes_le=ctypes.string_at(ptr, 16)))
        _k32.LocalFree(ptr)
        return guid

    def set_active(self, guid: str) -> None:
        _powrprof.PowerSetActiveScheme(None, uuid.UUID(guid).bytes_le)

    def mode_of(self, guid: str | None) -> str | None:
        return next((mode for mode, g in self.by_mode.items() if g and g == guid), None)
