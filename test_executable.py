"""Launch only this build; never click Save or mutate client settings."""
import ctypes
from ctypes import wintypes
from pathlib import Path
import subprocess
import time

exe = Path(__file__).resolve().parent / "dist" / "AntaresIntelligentTool.exe"
user32 = ctypes.WinDLL("user32", use_last_error=True)
callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.IsHungAppWindow.argtypes = [wintypes.HWND]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
proc = subprocess.Popen([str(exe)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print(f"Started build pid={proc.pid}", flush=True)
try:
    found = []
    @callback_type
    def inspect(hwnd, unused):
        title = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, title, len(title))
        if title.value == "Antares Intelligent配置工具":
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            found.append((pid.value, not user32.IsHungAppWindow(hwnd), hwnd))
        return True
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        user32.EnumWindows(inspect, 0)
        if found:
            break
        if proc.poll() is not None:
            raise RuntimeError(f"EXE exited before opening its window: {proc.returncode}")
        time.sleep(0.5)
    assert found and all(responsive for _, responsive, _ in found), "No responsive application window appeared within 25 seconds"
    print(f"PASS: packaged EXE opens a responsive application window; size={exe.stat().st_size:,} bytes", flush=True)
finally:
    for _, _, hwnd in found:
        user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE, just like closing the window.
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], stdin=subprocess.DEVNULL, timeout=10, check=True)
        proc.wait(timeout=30)
    print("PASS: test application closed without saving configuration", flush=True)
