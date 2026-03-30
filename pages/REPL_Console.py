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

# Persistent storage for page navigation (Streamlit clears widget keys on page exit)
if "repl_code_storage" not in st.session_state:
    st.session_state.repl_code_storage = "# Write your MicroPython code here\nprint('Hello from NanoPD!')\n"

if "repl_output_storage" not in st.session_state:
    st.session_state.repl_output_storage = ""

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


# ─── Callbacks (Handle state & blocking IO) ─────────────
def sync_code_storage():
    """Sync the widget state back to persistent storage."""
    st.session_state.repl_code_storage = st.session_state.repl_code_editor

def handle_save():
    content = st.session_state.repl_code_storage
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
                st.session_state.repl_code_storage = f.read()
            st.toast(f"Loaded {os.path.basename(file_path)}", icon="✅")
        except Exception as e:
            st.toast(f"Failed to load: {e}", icon="❌")
    else:
        st.toast("Load cancelled.", icon="ℹ️")

def handle_clear():
    st.session_state.repl_output_storage = ""

def handle_run_toggle():
    # Toggle state - script body handles the actual process management
    st.session_state.is_running = not st.session_state.is_running


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
        
        # Timeout Configuration Columns
        st.markdown('<p class="metric-label" style="margin:8px 0 0 0">TIMEOUT (SECONDS)</p>', unsafe_allow_html=True)
        
        # Synchronization logic
        def sync_from_num():
            st.session_state.repl_timeout = st.session_state.timeout_num
        
        def sync_from_slider():
            st.session_state.repl_timeout = st.session_state.timeout_slider

        t_col1, t_col2 = st.columns([1, 1.8])
        with t_col1:
            # Side-by-side Number Input
            st.number_input(
                "Timeout Number",
                min_value=1, max_value=3600, step=1,
                label_visibility="collapsed",
                key="timeout_num",
                value=st.session_state.get("repl_timeout", 30),
                on_change=sync_from_num
            )
        with t_col2:
            # Side-by-side Slider
            st.slider(
                "Timeout Slider",
                min_value=1, max_value=600, step=1,
                label_visibility="collapsed",
                key="timeout_slider",
                value=st.session_state.get("repl_timeout", 30),
                on_change=sync_from_slider
            )

    # Coding container
    with st.container(height=714, border=True):
        st.markdown(
            '<p class="metric-label" style="margin:0 0 12px 0">CODING</p>',
            unsafe_allow_html=True
        )
        st.text_area(
            "Code Editor",
            value=st.session_state.repl_code_storage,
            height=630, # Reduced to ensure container border visibility
            label_visibility="collapsed",
            key="repl_code_editor",
            on_change=sync_code_storage
        )

# ─── NON-BLOCKING EXECUTION ENGINE ───────────────────────────────────────── (In the output column)
with col_output:
    output_container = st.container(height=852, border=True)
    with output_container:
        st.markdown(
            '<p class="metric-label" style="margin:0 0 12px 0">MCU OUTPUT</p>',
            unsafe_allow_html=True
        )
        
        # This area will display the output code block
        # We use a placeholder that will be updated in a loop if running
        output_placeholder = st.empty()

        # Render the current buffer immediately
        output_placeholder.code(
            st.session_state.repl_output_storage if st.session_state.repl_output_storage else "(waiting for execution...)",
            language="text"
        )

# ─── RUN ENGINE (Executed if is_running was just set to True) ─────────────
if st.session_state.is_running:
    code_to_run = st.session_state.repl_code_editor.strip()
    timeout_val = st.session_state.repl_timeout
    
    if not code_to_run:
        st.toast("No code to run.", icon="⚠️")
        st.session_state.is_running = False
        st.rerun()

    timestamp = time.strftime("%H:%M:%S")
    st.session_state.repl_output_storage += f"[{timestamp}] >> Run\n"
    
    # Refresh the display with the new header
    output_placeholder.code(st.session_state.repl_output_storage, language="text")

    # Start Popen process
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
        
        # Poll the process
        while True:
            # Check if finished
            if proc.poll() is not None:
                # Get remaining output
                remaining_stdout, remaining_stderr = proc.communicate()
                if remaining_stdout:
                    for l in remaining_stdout.splitlines():
                        st.session_state.repl_output_storage += f"<< {l}\n"
                if remaining_stderr:
                    for l in remaining_stderr.splitlines():
                        st.session_state.repl_output_storage += f"[stderr] {l}\n"
                break

            # Non-blocking read of stdout
            import selectors
            sel = selectors.DefaultSelector()
            sel.register(proc.stdout, selectors.EVENT_READ)
            sel.register(proc.stderr, selectors.EVENT_READ)
            
            events = sel.select(timeout=0.1)
            for key, mask in events:
                line = key.fileobj.readline()
                if line:
                    prefix = "<<" if key.fileobj is proc.stdout else "[stderr]"
                    st.session_state.repl_output_storage += f"{prefix} {line}"
                    # Update live display
                    output_placeholder.code(st.session_state.repl_output_storage, language="text")

            # Check timeout
            if (time.time() - start_time) > timeout_val:
                st.session_state.repl_output_storage += f"\n[TIMEOUT] Connection closed after {timeout_val}s (Script may still be running on MCU)\n"
                proc.terminate()
                break

            # Small sleep to yield to UI/OS
            time.sleep(0.1)

    except Exception as e:
        st.session_state.repl_output_storage += f"[error] Process failed: {str(e)}\n"
    
    # Mark as finished
    st.session_state.is_running = False
    st.rerun() # Refresh to reset buttons
