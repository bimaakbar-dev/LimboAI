"""Informasi sistem dan perintah aman yang diizinkan."""
from __future__ import annotations

import ctypes
import os
import platform
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path
from typing import Any


class MemoryStatusEx(ctypes.Structure):
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


def _powershell(command: str, timeout: int = 20) -> str:
    for _ in range(2):
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True, text=True, timeout=timeout,
            )
            output = result.stdout.strip() or result.stderr.strip()
            if output:
                return output
        except (OSError, subprocess.SubprocessError) as exc:
            return f"(gagal: {exc})"
    return ""


def _field(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}\s*:\s*(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else "-"


class SystemTools:
    SAFE_COMMANDS = {
        "python", "py", "git", "tasklist", "systeminfo",
        "ipconfig", "ping", "where", "whoami",
    }

    def __init__(self, config: dict):
        self.cfg = config
        self._spec_cache: dict[str, Any] | None = None

    @staticmethod
    def _ok(message: str, **data: Any) -> dict:
        return {"ok": True, "message": message, "data": data}

    @staticmethod
    def _fail(message: str) -> dict:
        return {"ok": False, "message": message}

    def get_specs(self) -> dict:
        if self._spec_cache is not None:
            return self._ok(self._format_specs(self._spec_cache), **self._spec_cache)

        status = MemoryStatusEx()
        status.dwLength = ctypes.sizeof(MemoryStatusEx)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))

        cpu_text = _powershell(
            "Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, "
            "NumberOfLogicalProcessors, MaxClockSpeed | Format-List"
        )
        gpu_text = _powershell(
            "Get-CimInstance Win32_VideoController | Select-Object -First 1 Name, AdapterRAM | Format-List"
        )
        os_text = _powershell(
            "Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, OSArchitecture | Format-List"
        )
        disk = shutil.disk_usage(Path(os.getcwd()).anchor or "C:\\")

        specs = {
            "cpu": _field(cpu_text, "Name"),
            "cores": _field(cpu_text, "NumberOfCores"),
            "threads": _field(cpu_text, "NumberOfLogicalProcessors"),
            "ram_gb": round(status.ullTotalPhys / (1024 ** 3), 2),
            "ram_free_gb": round(status.ullAvailPhys / (1024 ** 3), 2),
            "gpu": _field(gpu_text, "Name"),
            "gpu_vram_gb": round(
                int(_field(gpu_text, "AdapterRAM").split()[0]) / (1024 ** 3), 2
            ) if _field(gpu_text, "AdapterRAM").split() and _field(gpu_text, "AdapterRAM").split()[0].isdigit() else "-",
            "os": _field(os_text, "Caption"),
            "os_arch": _field(os_text, "OSArchitecture"),
            "disk_total_gb": round(disk.total / (1024 ** 3), 1),
            "disk_free_gb": round(disk.free / (1024 ** 3), 1),
        }
        if specs["cpu"] == "-":
            specs["cpu"] = platform.processor() or "unknown"
        self._spec_cache = specs
        return self._ok(self._format_specs(specs), **specs)

    @staticmethod
    def _format_specs(specs: dict[str, Any]) -> str:
        return (
            f"CPU     : {specs['cpu']} ({specs['cores']} core / {specs['threads']} thread)\n"
            f"RAM     : {specs['ram_gb']} GB (kosong {specs['ram_free_gb']} GB)\n"
            f"GPU     : {specs['gpu']} ({specs['gpu_vram_gb']} GB VRAM)\n"
            f"OS      : {specs['os']} {specs['os_arch']}\n"
            f"Disk    : {specs['disk_total_gb']} GB total, {specs['disk_free_gb']} GB kosong"
        )

    def disk_usage(self, path: str = "C:\\") -> dict:
        target = Path(path)
        if not target.exists():
            return self._fail(f"Path tidak ditemukan: {target}")
        usage = shutil.disk_usage(str(target))
        return self._ok(
            f"{target}: total {usage.total / (1024**3):.1f} GB, "
            f"terpakai {usage.used / (1024**3):.1f} GB, "
            f"kosong {usage.free / (1024**3):.1f} GB",
            total_gb=round(usage.total / (1024**3), 1),
            free_gb=round(usage.free / (1024**3), 1),
        )

    def processes(self, limit: int | None = None) -> dict:
        limit = int(limit or self.cfg.get("limits", {}).get("process_limit", 15))
        output = _powershell(
            f"Get-Process | Sort-Object CPU -Descending | Select-Object -First {limit} "
            "Name, Id, CPU | Format-Table -AutoSize | Out-String -Width 160"
        )
        return self._ok(f"Proses dengan CPU tertinggi:\n{output}", output=output)

    def internet_check(self) -> dict:
        try:
            with urllib.request.urlopen("https://www.google.com", timeout=3) as response:
                online = response.status == 200
            return self._ok("Internet: tersedia." if online else "Internet: tidak tersedia.", online=online)
        except Exception as exc:
            return self._ok(f"Internet: tidak tersedia ({exc}).", online=False)

    def run_command(self, argv: list[str], confirm: bool = False) -> dict:
        if not argv:
            return self._fail("Perintah kosong.")
        program = Path(argv[0]).name.lower()
        if program not in self.SAFE_COMMANDS:
            return self._fail(
                f"Perintah '{program}' tidak ada dalam daftar yang diizinkan. "
                f"Yang diizinkan: {', '.join(sorted(self.SAFE_COMMANDS))}."
            )
        if self.cfg.get("confirm_destructive", True) and confirm is not True:
            return {
                "ok": False,
                "need_confirmation": True,
                "message": f"Rencana menjalankan: {' '.join(argv)}\nKetik 'konfirmasi' untuk melanjutkan.",
            }
        try:
            result = subprocess.run(argv, capture_output=True, text=True, timeout=60, shell=False)
            output = (result.stdout or "") + (result.stderr or "")
            return self._ok(
                output.strip() or f"Perintah selesai (exit {result.returncode}).",
                returncode=result.returncode, output=output,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return self._fail(str(exc))
