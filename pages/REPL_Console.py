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

# Persistent storage for code and output (survives page switching)
if "repl_code" not in st.session_state:
    st.session_state.repl_code = "# Write your MicroPython code here\nprint('Hello from NanoPD!')\n"

if "repl_code_editor" not in st.session_state:
    st.session_state.repl_code_editor = st.session_state.repl_code

if "repl_output" not in st.session_state:
    st.session_state.repl_output = ""

if "repl_timeout" not in st.session_state:
    st.session_state.repl_timeout = 30

if "is_running" not in st.session_state:
    st.session_state.is_running = False


# ─── Helper Functions ───────────────────────────────────────────────────────
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


# ─── Callbacks ──────────────────────────────────────────────────────────────
def handle_save():
    # Read the latest content from the widget key before it disappears
    content = st.session_state.get("repl_code_editor", st.session_state.repl_code)
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
                loaded = f.read()
            # Write to the persistent state AND the widget key
            st.session_state.repl_code = loaded
            st.session_state.repl_code_editor = loaded
            st.toast(f"Loaded {os.path.basename(file_path)}", icon="✅")
        except Exception as e:
            st.toast(f"Failed to load: {e}", icon="❌")
    else:
        st.toast("Load cancelled.", icon="ℹ️")

def handle_clear():
    st.session_state.repl_output = ""

def handle_run_toggle():
    st.session_state.is_running = not st.session_state.is_running

def sync_code_to_state():
    """Syncs the widget key back to the persistent state on every edit."""
    st.session_state.repl_code = st.session_state.repl_code_editor

def sync_from_num():
    st.session_state.repl_timeout = st.session_state.timeout_num

def sync_from_slider():
    st.session_state.repl_timeout = st.session_state.timeout_slider


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

code_font = st.session_state.ui_cfg.get("code_font", "Consolas, Monaco, monospace")
code_size = st.session_state.ui_cfg.get("code_size", "14px")
code_lh = st.session_state.ui_cfg.get("code_lh", "1.3")

st.markdown(f"""
    <style>
        section[data-testid="stMain"] > div {{
            padding-bottom: 20px !important;
        }}
        .main > div.block-container {{
            padding-bottom: 20px !important;
        }}
        div[data-testid="block-container"] {{
            padding-bottom: 20px !important;
        }}
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


# ─── MAIN LAYOUT ────────────────────────────────────────────────────────────
col_code, col_output = st.columns([1, 1])

with col_code:
    # Action Buttons container (A)
    with st.container(border=True):
        ab1, ab2, ab3, ab4 = st.columns(4)
        with ab1:
            if not st.session_state.is_running:
                st.button(
                    "🚀 Run REPL", width="stretch", type="primary",
                    disabled=not device_ready,
                    help=None if device_ready else "Device not ready",
                    on_click=handle_run_toggle
                )
            else:
                st.button(
                    "🛑 Stop REPL", width="stretch", type="secondary",
                    on_click=handle_run_toggle
                )
        with ab2:
            st.button("💾 Save to Local", width="stretch", on_click=handle_save)
        with ab3:
            st.button("📂 Load Local File", width="stretch", on_click=handle_load)
        with ab4:
            st.button("🗑️ Clear Output", width="stretch", on_click=handle_clear)

        # Timeout Configuration
        st.markdown('<p class="metric-label" style="margin:8px 0 0 0">TIMEOUT (SECONDS)</p>', unsafe_allow_html=True)
        t_col1, t_col2 = st.columns([1, 1.8])
        with t_col1:
            st.number_input(
                "Timeout Number",
                min_value=1, max_value=3600, step=1,
                label_visibility="collapsed",
                key="timeout_num",
                value=st.session_state.repl_timeout,
                on_change=sync_from_num
            )
        with t_col2:
            st.slider(
                "Timeout Slider",
                min_value=1, max_value=600, step=1,
                label_visibility="collapsed",
                key="timeout_slider",
                value=min(st.session_state.repl_timeout, 600),
                on_change=sync_from_slider
            )

    # Coding container (B) with border
    with st.container(height=678, border=True):
        st.markdown(
            '<p class="metric-label" style="margin:0 0 12px 0">CODING</p>',
            unsafe_allow_html=True
        )
        st.text_area(
            "Code Editor",
            height=615,
            label_visibility="collapsed",
            key="repl_code_editor",
            on_change=sync_code_to_state
        )

with col_output:
    with st.container(height=852, border=True):
        st.markdown(
            '<p class="metric-label" style="margin:0 0 12px 0">MCU OUTPUT</p>',
            unsafe_allow_html=True
        )
        output_placeholder = st.empty()
        output_placeholder.code(
            st.session_state.repl_output if st.session_state.repl_output else "(waiting for execution...)",
            language="text",
            height=785
        )


# ─── NON-BLOCKING EXECUTION ENGINE ─────────────────────────────────────────
if st.session_state.is_running:
    code_to_run = st.session_state.repl_code.strip()
    timeout_val = st.session_state.repl_timeout

    if not code_to_run:
        st.toast("No code to run.", icon="⚠️")
        st.session_state.is_running = False
        st.rerun()

    timestamp = time.strftime("%H:%M:%S")
    st.session_state.repl_output += f"[{timestamp}] >> Run\n"
    output_placeholder.code(st.session_state.repl_output, language="text", height=785)

    cmd = [sys.executable, "-m", "mpremote", "exec", code_to_run]
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            creationflags=CREATIONFLAGS
        )

        start_time = time.time()
        import threading
        import queue

        q = queue.Queue()

        def enqueue_output(out, prefix):
            for line in iter(out.readline, ''):
                q.put((prefix, line))
            out.close()

        t_out = threading.Thread(target=enqueue_output, args=(proc.stdout, "<<"), daemon=True)
        t_err = threading.Thread(target=enqueue_output, args=(proc.stderr, "[stderr]"), daemon=True)
        t_out.start()
        t_err.start()

        while True:
            updated = False
            while not q.empty():
                try:
                    prefix, line = q.get_nowait()
                    st.session_state.repl_output += f"{prefix} {line}"
                    updated = True
                except queue.Empty:
                    break
            
            if updated:
                output_placeholder.code(st.session_state.repl_output, language="text", height=785)

            if proc.poll() is not None:
                t_out.join(timeout=0.1)
                t_err.join(timeout=0.1)
                while not q.empty():
                    try:
                        prefix, line = q.get_nowait()
                        st.session_state.repl_output += f"{prefix} {line}"
                    except queue.Empty:
                        break
                break

            if (time.time() - start_time) > timeout_val:
                st.session_state.repl_output += f"\n[TIMEOUT] Connection closed after {timeout_val}s (Script may still be running on MCU)\n"
                proc.terminate()
                break

            time.sleep(0.05)

    except Exception as e:
        st.session_state.repl_output += f"[error] Process failed: {str(e)}\n"

    st.session_state.is_running = False
    st.rerun()
