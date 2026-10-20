"""Runtime environment detection and conservative desktop adaptation.

Detection is best-effort and uses only the Python standard library so the
application can start offline on modest Windows PCs.
"""
from __future__ import annotations

import os
import platform
import struct
import sys
from typing import Dict, Optional, Tuple


def _windows_version() -> Tuple[str, str, str]:
    """Return (friendly name, version, build) using the native Windows version."""
    version = platform.version()
    build = ""
    try:
        import ctypes
        from ctypes import wintypes

        class OSVERSIONINFOEXW(ctypes.Structure):
            _fields_ = [
                ("dwOSVersionInfoSize", wintypes.DWORD),
                ("dwMajorVersion", wintypes.DWORD),
                ("dwMinorVersion", wintypes.DWORD),
                ("dwBuildNumber", wintypes.DWORD),
                ("dwPlatformId", wintypes.DWORD),
                ("szCSDVersion", wintypes.WCHAR * 128),
                ("wServicePackMajor", wintypes.WORD),
                ("wServicePackMinor", wintypes.WORD),
                ("wSuiteMask", wintypes.WORD),
                ("wProductType", wintypes.BYTE),
                ("wReserved", wintypes.BYTE),
            ]

        info = OSVERSIONINFOEXW()
        info.dwOSVersionInfoSize = ctypes.sizeof(info)
        rtl_get_version = ctypes.windll.ntdll.RtlGetVersion
        rtl_get_version.argtypes = [ctypes.POINTER(OSVERSIONINFOEXW)]
        rtl_get_version.restype = wintypes.DWORD
        if rtl_get_version(ctypes.byref(info)) == 0:
            version = "{}.{}.{}".format(
                info.dwMajorVersion, info.dwMinorVersion, info.dwBuildNumber
            )
            build = str(info.dwBuildNumber)
            major, minor = info.dwMajorVersion, info.dwMinorVersion
            if major == 10 and info.dwBuildNumber >= 22000:
                name = "Windows 11"
            elif major == 10:
                name = "Windows 10"
            elif major == 6 and minor == 3:
                name = "Windows 8.1"
            elif major == 6 and minor == 2:
                name = "Windows 8"
            elif major == 6 and minor == 1:
                name = "Windows 7"
            elif major == 6 and minor == 0:
                name = "Windows Vista"
            else:
                name = "Windows"
            return name, version, build
    except (AttributeError, ImportError, OSError, TypeError, ValueError):
        pass

    name = platform.system() or "Unknown"
    if sys.platform == "win32":
        name = "Windows"
    return name, version or "unknown", build


def detect_device() -> Dict[str, object]:
    """Describe the current device without collecting identifying information."""
    system = platform.system() or "Unknown"
    version = platform.version() or "unknown"
    build = ""
    if sys.platform == "win32":
        system, version, build = _windows_version()

    try:
        memory_bytes = None
        if sys.platform == "win32":
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                memory_bytes = int(status.ullTotalPhys)
        else:
            pages = os.sysconf("SC_PHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            memory_bytes = int(pages * page_size)
    except (AttributeError, OSError, ValueError, TypeError):
        memory_bytes = None

    cpu_count = os.cpu_count() or 1
    memory_gb = round(memory_bytes / (1024 ** 3), 1) if memory_bytes else None
    low_memory = memory_bytes is not None and memory_bytes <= 4 * (1024 ** 3)
    low_cpu = cpu_count <= 2
    profile = "hemat" if low_memory or low_cpu else "standar"
    return {
        "os_name": system,
        "os_version": version,
        "os_build": build,
        "architecture": platform.machine() or ("64-bit" if sys.maxsize > 2 ** 32 else "32-bit"),
        "process_bits": struct.calcsize("P") * 8,
        "cpu_count": cpu_count,
        "memory_bytes": memory_bytes,
        "memory_gb": memory_gb,
        "profile": profile,
    }


def configure_window_for_device(root, device: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    """Fit the initial window to available screen space and modest hardware."""
    info = device or detect_device()
    try:
        root.update_idletasks()
        screen_width = max(800, int(root.winfo_screenwidth()))
        screen_height = max(600, int(root.winfo_screenheight()))
        width = min(1120, screen_width - 40)
        height = min(720, screen_height - 70)
        if info.get("profile") == "hemat":
            width = min(width, 1000)
            height = min(height, 680)
        width = max(800, width)
        height = max(540, height)
        root.geometry("{}x{}+{}+{}".format(
            width, height, max(0, (screen_width - width) // 2),
            max(0, (screen_height - height) // 2)
        ))
        root.minsize(min(860, width), min(560, height))
        try:
            scaling = float(root.tk.call("tk", "scaling"))
            root.tk.call("tk", "scaling", min(1.25, max(0.9, scaling)))
        except (AttributeError, TypeError, ValueError):
            pass
    except (AttributeError, TypeError, ValueError):
        pass
    return info


__all__ = ["configure_window_for_device", "detect_device"]
