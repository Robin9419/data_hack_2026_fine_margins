"""Run both development servers and stop their process groups together (Linux/macOS)."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    python = ROOT / "backend/.venv/bin/python"
    if not python.exists() or not (ROOT / "frontend/node_modules/.bin/vite").exists():
        sys.exit("Dependencies are missing. Run make install first.")

    processes = []

    def stop(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop)
    try:
        processes.append(subprocess.Popen(
            [str(python), "-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"],
            cwd=ROOT / "backend", start_new_session=True))
        processes.append(subprocess.Popen(
            ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173", "--strictPort"],
            cwd=ROOT / "frontend", start_new_session=True))
        print("App: http://localhost:5173 | API: http://localhost:8000/docs\nCtrl+C stops both servers.", flush=True)
        while all(p.poll() is None for p in processes):
            time.sleep(0.2)
        return next(p.returncode or 1 for p in processes if p.poll() is not None)
    except KeyboardInterrupt:
        return 0
    finally:
        for p in processes:
            try:
                os.killpg(p.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        for p in processes:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(p.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                p.wait()


if __name__ == "__main__":
    sys.exit(main())
