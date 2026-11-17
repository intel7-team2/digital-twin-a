"""Start the local simulation controller, then open Factory I/O if necessary."""
import ctypes
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent


def status():
    try:
        with urlopen('http://127.0.0.1:8765/', timeout=1) as response:
            value = json.load(response)
            return value if 'simulation_running' in value and 'memory' in value else None
    except (OSError, ValueError):
        return None


def main():
    if status() is None:
        pythonw = Path(sys.executable).with_name('pythonw.exe')
        log = open(HERE / 'softplc.log', 'a', encoding='utf-8')
        subprocess.Popen([str(pythonw if pythonw.exists() else sys.executable),
                          str(HERE / 'softplc.py')], cwd=HERE,
                         stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
        for _ in range(50):
            if status() is not None:
                break
            time.sleep(.1)
        else:
            raise RuntimeError('Soft PLC did not start. See plc/softplc.log (port 502).')
    # Existing Factory I/O is already configured. Avoid opening a second instance.
    running = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Factory IO.exe', '/NH'],
                             capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW).stdout
    if b'Factory IO.exe' not in running:
        exe = Path(r'D:\programs\factoryIO\Factory IO.exe')
        if not exe.exists():
            raise FileNotFoundError(f'Factory I/O not found: {exe}')
        subprocess.Popen([str(exe)], cwd=exe.parent)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        ctypes.windll.user32.MessageBoxW(None, str(error), 'Line start failed', 0x10)
        raise
