"""
launch.py — Port-aware Streamlit launcher for nanoPD.
Finds the first free port starting from 8501 and launches Streamlit there.
"""
import socket
import subprocess
import sys
import os


def find_free_port(start: int = 8501, end: int = 8510) -> int:
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("localhost", port))
                return port          # Port is free
            except OSError:
                continue            # Port is occupied, try next
    raise RuntimeError(f"No free port found between {start} and {end}.")


if __name__ == "__main__":
    port = find_free_port()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    streamlit_exe = os.path.join(script_dir, ".venv", "Scripts", "streamlit.exe")

    if not os.path.isfile(streamlit_exe):
        # Fallback: use python -m streamlit
        cmd = [sys.executable, "-m", "streamlit", "run", "main.py",
               "--server.port", str(port)]
    else:
        cmd = [streamlit_exe, "run", "main.py",
               "--server.port", str(port)]

    print(f"  >> Starting nanoPD on http://localhost:{port}")
    subprocess.run(cmd, cwd=script_dir)
