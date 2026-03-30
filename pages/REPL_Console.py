import streamlit as st
import os
import sys
import subprocess
import time
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from utils.style_utils import apply_global_css
from utils.config_utils import load_ui_config
from utils.mount_utils import is_mounted, is_rp2350_connected, CREATIONFLAGS

# ─── Session State Initialization ───────────────────────────────────────────
if "ui_cfg" not in st.session_state:
    st.session_state.ui_cfg = load_ui_config()

# Source of truth for the editor content
if "repl_code_editor" not in st.session_state:
    st.session_state.repl_code_editor = "# Write your MicroPython code here\nprint('Hello from NanoPD!')\n"

if "repl_output" not in st.session_state:
    st.session_state.repl_output = ""

if "repl_running" not in st.session_state:
    st.session_state.repl_running = False

if "repl_timeout" not in st.session_state:
    st.session_state.repl_timeout = 30.0


# ─── Helper Functions ───────────────────────────────────────────────────────
def run_mpremote(args, timeout=30.0, soft_reset=False):
    """Executes mpremote with a retry loop for Raw REPL entry."""
    if soft_reset:
        subprocess.run(
            [sys.executable, "-m", "mpremote", "soft-reset"],
            capture_output=True, creationflags=CREATIONFLAGS
        )
        time.sleep(0.5)

    cmd = [sys.executable, "-m", "mpremote"] + args
    max_retries = 3

    for attempt in range(max_retries):
        try:
            res = subprocess.run(
                cmd, capture_output=True, timeout=timeout,
                creationflags=CREATIONFLAGS
            )
            stdout = res.stdout.decode('utf-8', errors='replace')
            stderr = res.stderr.decode('utf-8', errors='replace')

            if ("could not enter raw repl" in stderr.lower()
                    or "failed to access" in stderr.lower()):
                time.sleep(1.0)
                continue

            return res.returncode, stdout, stderr
        except subprocess.TimeoutExpired as e:
            # Handle timeout by capturing partial output
            stdout = e.stdout.decode('utf-8', errors='replace') if e.stdout else ""
            stderr = e.stderr.decode('utf-8', errors='replace') if e.stderr else ""
            return -1, stdout, stderr
        except Exception as e:
            return -2, "", str(e)

    return -3, "", "Failed to enter Raw REPL after retries."


def execute_code(code: str, timeout: float):
    """Send code to the MCU via mpremote exec and return formatted output."""
    timestamp = time.strftime("%H:%M:%S")
    # >> prefix for host commands
    header = f"[{timestamp}] >> Run\n"

    rc, stdout, stderr = run_mpremote(["exec", code], timeout=timeout)

    output_parts = [header]
    
    # << prefix for MCU output lines
    if stdout.strip():
        for line in stdout.splitlines():
            output_parts.append(f"<< {line}")
            
    if stderr.strip():
        for line in stderr.splitlines():
            output_parts.append(f"[stderr] {line}")
            
    if rc == -1:
        output_parts.append(f"\n[TIMEOUT] Connection closed after {timeout}s (Script may still be running on MCU)")
    elif rc != 0 and not stderr.strip():
        output_parts.append(f"[error] Exit code: {rc}")
    elif rc == 0 and not stdout.strip() and not stderr.strip():
        output_parts.append("<< (no output)")

    return "\n".join(output_parts) + "\n"


def load_file_dialog():
    """Opens a native file dialog and returns the selected file path."""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    root.lift()
    root.focus_force()
    selected_file = filedialog.askopenfilename(
        title="Select MicroPython File",
        filetypes=[("Python Files", "*.py"), ("All Files", "*.*")]
    )
    root.destroy()
    return selected_file


def save_file_dialog(content: str):
    """Opens a native save dialog and writes content to the selected path."""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    root.lift()
    root.focus_force()
    selected_file = filedialog.asksaveasfilename(
        title="Save MicroPython File",
        defaultextension=".py",
        filetypes=[("Python Files", "*.py"), ("All Files", "*.*")]
    )
    root.destroy()
    if selected_file:
        try:
            with open(selected_file, "w", encoding="utf-8") as f:
                f.write(content)
            return selected_file
        except Exception:
            return None
    return None


# ─── Callbacks (Handle state BEFORE UI rendering) ─────────────
def handle_run():
    code = st.session_state.repl_code_editor.strip()
    timeout = st.session_state.repl_timeout
    if code:
        result = execute_code(code, timeout)
        st.session_state.repl_output += result
    else:
        st.toast("No code to run.", icon="⚠️")

def handle_save():
    content = st.session_state.repl_code_editor
    saved_path = save_file_dialog(content)
    if saved_path:
        st.toast(f"Saved to {os.path.basename(saved_path)}", icon="✅")
    else:
        st.toast("Save cancelled.", icon="ℹ️")

def handle_load():
    file_path = load_file_dialog()
    if file_path:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                st.session_state.repl_code_editor = content
            st.toast(f"Loaded {os.path.basename(file_path)}", icon="✅")
        except Exception as e:
            st.toast(f"Failed to load: {e}", icon="❌")
    else:
        st.toast("Load cancelled.", icon="ℹ️")

def handle_clear():
    st.session_state.repl_output = ""


# ─── Apply Global CSS ───────────────────────────────────────────────────────
apply_global_css(
    title_size=st.session_state.ui_cfg.get("title_size", "1.5rem"),
    label_size=st.session_state.ui_cfg.get("label_size", "0.875rem"),
    info_size=st.session_state.ui_cfg.get("info_size", "1.0rem"),
    code_font=st.session_state.ui_cfg.get("code_font", "Consolas, Monaco, monospace"),
    code_size=st.session_state.ui_cfg.get("code_size", "14px"),
    code_lh=st.session_state.ui_cfg.get("code_lh", "1.3"),
    is_mcu_page=True
)

# Page-specific CSS overrides
code_font = st.session_state.ui_cfg.get("code_font", "Consolas, Monaco, monospace")
code_size = st.session_state.ui_cfg.get("code_size", "14px")
code_lh = st.session_state.ui_cfg.get("code_lh", "1.3")

st.markdown(f"""
    <style>
        /* Reduce Streamlit's large default bottom padding on the main content area */
        section[data-testid="stMain"] > div {{
            padding-bottom: 20px !important;
        }}
        .main > div.block-container {{
            padding-bottom: 20px !important;
        }}
        div[data-testid="block-container"] {{
            padding-bottom: 20px !important;
        }}

        /* Output terminal styling */
        .repl-output-block pre code {{
            font-family: {code_font} !important;
            font-size: {code_size} !important;
            line-height: {code_lh} !important;
        }}
    </style>
""", unsafe_allow_html=True)


# ─── Device Status Check ────────────────────────────────────────────────────
mounted = is_mounted()
connected = is_rp2350_connected()
device_ready = connected and not mounted


# ─── MAIN LAYOUT — Two columns matching UI calibration sandbox ──────────────
col_code, col_output = st.columns([1, 1])

with col_code:
    # Action Buttons container (A)
    with st.container(border=True):
        ab1, ab2, ab3, ab4 = st.columns(4)
        with ab1:
            st.button(
                "🚀 Run Code", width="stretch",
                disabled=not device_ready,
                help=None if device_ready else "Device not ready",
                on_click=handle_run
            )
        with ab2:
            st.button("💾 Save to Local", width="stretch", on_click=handle_save)
        with ab3:
            st.button("📂 Load Local File", width="stretch", on_click=handle_load)
        with ab4:
            st.button("🗑️ Clear Output", width="stretch", on_click=handle_clear)
        
        # Timeout Configuration
        st.number_input(
            "Timeout (seconds)",
            min_value=1.0,
            max_value=3600.0,
            step=1.0,
            key="repl_timeout",
            help="Maximum time to wait for a script to finish before timing out host-side."
        )

    # Coding container
    with st.container(height=714, border=True):
        st.markdown(
            '<p class="metric-label" style="margin:0 0 12px 0">CODING</p>',
            unsafe_allow_html=True
        )

        st.text_area(
            "Code Editor",
            height=650,
            label_visibility="collapsed",
            key="repl_code_editor"
        )

with col_output:
    with st.container(height=852, border=True):
        st.markdown(
            '<p class="metric-label" style="margin:0 0 12px 0">MCU OUTPUT</p>',
            unsafe_allow_html=True
        )

        st.code(
            st.session_state.repl_output if st.session_state.repl_output else "(waiting for execution...)",
            language="text",
            height=785
        )
