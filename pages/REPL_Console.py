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

if "repl_code" not in st.session_state:
    st.session_state.repl_code = "# Write your MicroPython code here\nprint('Hello from NanoPD!')\n"

if "repl_output" not in st.session_state:
    st.session_state.repl_output = ""

if "repl_running" not in st.session_state:
    st.session_state.repl_running = False


# ─── Helper Functions ───────────────────────────────────────────────────────
def run_mpremote(args, timeout=20.0, soft_reset=False):
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
        except subprocess.TimeoutExpired:
            return -1, "", "Timeout: MCU did not respond."
        except Exception as e:
            return -2, "", str(e)

    return -3, "", "Failed to enter Raw REPL after retries."


def execute_code(code: str):
    """Send code to the MCU via mpremote exec and return formatted output."""
    timestamp = time.strftime("%H:%M:%S")
    header = f"[{timestamp}] >>> Run\n"

    rc, stdout, stderr = run_mpremote(["exec", code], timeout=30.0)

    output_parts = [header]
    if stdout.strip():
        output_parts.append(stdout.rstrip("\n"))
    if stderr.strip():
        output_parts.append(f"[stderr] {stderr.rstrip()}")
    if rc != 0 and not stderr.strip():
        output_parts.append(f"[error] Exit code: {rc}")
    if rc == 0 and not stdout.strip() and not stderr.strip():
        output_parts.append("(no output)")

    return "\n".join(output_parts) + "\n"


def load_file_dialog():
    """Opens a native file dialog and returns the selected file path."""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
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
            run_clicked = st.button(
                "🚀 Run Code", width="stretch",
                disabled=not device_ready,
                help=None if device_ready else "Device not ready"
            )
        with ab2:
            save_clicked = st.button("💾 Save to Local", width="stretch")
        with ab3:
            load_clicked = st.button("📂 Load Local File", width="stretch")
        with ab4:
            clear_clicked = st.button("🗑️ Clear Output", width="stretch")

    # Coding container
    with st.container(height=764, border=True):
        st.markdown(
            '<p class="metric-label" style="margin:0 0 12px 0">CODING</p>',
            unsafe_allow_html=True
        )

        new_code = st.text_area(
            "Code Editor",
            value=st.session_state.repl_code,
            height=700,
            label_visibility="collapsed",
            key="repl_code_editor"
        )
        # Sync editor content back to session state
        st.session_state.repl_code = new_code

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


# ─── Button Actions (processed after layout rendering) ─────────────────────
if run_clicked:
    code_to_run = st.session_state.repl_code.strip()
    if code_to_run:
        result = execute_code(code_to_run)
        st.session_state.repl_output += result
        st.rerun()
    else:
        st.toast("No code to run.", icon="⚠️")

if save_clicked:
    saved_path = save_file_dialog(st.session_state.repl_code)
    if saved_path:
        st.toast(f"Saved to {os.path.basename(saved_path)}", icon="✅")
    else:
        st.toast("Save cancelled.", icon="ℹ️")

if load_clicked:
    file_path = load_file_dialog()
    if file_path:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                st.session_state.repl_code = f.read()
            st.toast(f"Loaded {os.path.basename(file_path)}", icon="✅")
            st.rerun()
        except Exception as e:
            st.toast(f"Failed to load: {e}", icon="❌")
    else:
        st.toast("Load cancelled.", icon="ℹ️")

if clear_clicked:
    st.session_state.repl_output = ""
    st.rerun()
