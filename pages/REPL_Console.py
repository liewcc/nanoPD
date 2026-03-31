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
from streamlit_ace import st_ace

# ─── Session State Initialization ───────────────────────────────────────────
if "ui_cfg" not in st.session_state:
    st.session_state.ui_cfg = load_ui_config()

# Persistent storage for code and output (survives page switching)
if "repl_code" not in st.session_state:
    st.session_state.repl_code = "# Write your MicroPython code here\nprint('Hello from NanoPD!')\n"

if "repl_output" not in st.session_state:
    st.session_state.repl_output = ""

if "repl_timeout" not in st.session_state:
    st.session_state.repl_timeout = 30

if "is_running" not in st.session_state:
    st.session_state.is_running = False

if "ace_version" not in st.session_state:
    st.session_state.ace_version = 0


# ─── Helper Functions ───────────────────────────────────────────────────────
def load_file_dialog():
    """Opens a native file dialog via subprocess to avoid Tkinter threading crashes."""
    script = """
import tkinter as tk
from tkinter import filedialog
root = tk.Tk()
root.withdraw()
root.attributes('-topmost', True)
root.lift()
root.focus_force()
f = filedialog.askopenfilename(title="Select MicroPython File", filetypes=[("Python Files", "*.py"), ("All Files", "*.*")])
if f:
    print(f)
"""
    try:
        result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
        path = result.stdout.strip()
        return path if path else None
    except Exception:
        return None


def save_file_dialog(content: str):
    """Opens a native save dialog via subprocess and writes content to the selected path."""
    script = """
import tkinter as tk
from tkinter import filedialog
import sys

try:
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    root.lift()
    root.focus_force()
    f = filedialog.asksaveasfilename(title="Save MicroPython File", defaultextension=".py", filetypes=[("Python Files", "*.py"), ("All Files", "*.*")])
    if f:
        print(f)
    else:
        print("CANCELLED")
except Exception as e:
    print(f"TK_ERROR: {e}")
"""
    try:
        result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=60)
        out = result.stdout.strip()
        if out == "CANCELLED" or not out:
            return None, "File dialog was cancelled."
        if out.startswith("TK_ERROR:"):
            return None, f"Tkinter failed: {out}"
        if result.returncode != 0:
            return None, f"Subprocess failed: {result.stderr}"

        path = out.split("\n")[-1].strip()  # In case there's extra print lines
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return path, "Success"
        return None, "Unknown error during save."
    except subprocess.TimeoutExpired:
        return None, "Save dialog timed out!"
    except Exception as e:
        return None, str(e)


# ─── Callbacks ──────────────────────────────────────────────────────────────
def handle_save():
    # Read the latest content from the widget key before it disappears
    dynamic_key = f"repl_code_editor_{st.session_state.ace_version}"
    content = st.session_state.get(dynamic_key)
    
    # If the widget hasn't fully synced or returned None, use the persistent code state
    if content is None:
        content = st.session_state.get("repl_code", "")
        
    saved_path, err_msg = save_file_dialog(content)
    if saved_path:
        st.toast(f"Saved to {os.path.basename(saved_path)}", icon="✅")
    else:
        st.toast(f"Save failed/cancelled: {err_msg}", icon="⚠️")

def handle_load():
    file_path = load_file_dialog()
    if file_path:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                loaded = f.read()
            # Write to the persistent state and bump ace version to force re-render
            st.session_state.repl_code = loaded
            st.session_state.ace_version += 1
            st.toast(f"Loaded {os.path.basename(file_path)}", icon="✅")
        except Exception as e:
            st.toast(f"Failed to load: {e}", icon="❌")
    else:
        st.toast("Load cancelled.", icon="ℹ️")

def handle_clear():
    st.session_state.repl_output = ""

def handle_run_toggle():
    st.session_state.is_running = not st.session_state.is_running

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
        .repl-output-block pre code,
        div[data-testid="stTextArea"] textarea {{
            font-family: {code_font} !important;
            font-size: {code_size} !important;
            line-height: {code_lh} !important;
        }}

        /* ─── VIEWPORT BOTTOM PADDING ─── */
        /* Ensures exactly 20px (A) gap from the bottom of the browser viewport */
        section[data-testid="stMain"] > div {{
            padding-bottom: 20px !important;
        }}
        div[data-testid="block-container"] {{
            padding-bottom: 20px !important;
        }}

        /* Strip column wrapper spacing so static heights control the gap precisely */
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
            padding-bottom: 0 !important;
            margin-bottom: 0 !important;
        }}

        /* Hide unwanted vertical scrollbars on the main fixed-height containers */
        /* Targets the container wrappers without breaking the internal iframe/textarea scrolling */
        div[data-testid="stVerticalBlock"]:has(.layout-coding-marker),
        div[data-testid="stVerticalBlock"]:has(.layout-mcu-marker) {{
            overflow-y: hidden !important;
            scrollbar-width: none !important;
        }}
        div[data-testid="stVerticalBlock"]:has(.layout-coding-marker)::-webkit-scrollbar,
        div[data-testid="stVerticalBlock"]:has(.layout-mcu-marker)::-webkit-scrollbar {{
            display: none !important;
            width: 0 !important;
        }}

        /* LOCK internal dynamic components to prevent collapse during execution loop rerenders */
        div[data-testid="stVerticalBlock"]:has(.layout-mcu-marker) div[data-testid="stTextArea"] textarea {{
            height: 763px !important;
            resize: none !important;
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

    # Coding container (B) — height = VH(951) - top(278) - A(20) = 653px
    with st.container(height=653, border=True):
        st.markdown('<div class="layout-coding-marker" style="display:none;"></div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="metric-label" style="margin:0 0 12px 0">CODING</p>',
            unsafe_allow_html=True
        )
        ace_content = st_ace(
            value=st.session_state.repl_code,
            language="python",
            theme="tomorrow",
            show_gutter=True,
            show_print_margin=False,
            wrap=True,
            auto_update=True,
            height=568,
            font_size=14,
            key=f"repl_code_editor_{st.session_state.ace_version}"
        )
        # Sync ace editor content back to persistent state
        if ace_content is not None and ace_content != st.session_state.repl_code:
            st.session_state.repl_code = ace_content

with col_output:
    with st.container(height=843, border=True):  # height = VH(951) - top(88) - A(20) = 843px
        st.markdown('<div class="layout-mcu-marker" style="display:none;"></div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="metric-label" style="margin:0 0 12px 0">MCU OUTPUT</p>',
            unsafe_allow_html=True
        )
        output_placeholder = st.empty()
        output_placeholder.text_area(
            "MCU Output Logs",
            value=st.session_state.repl_output.rstrip('\n') if st.session_state.repl_output else "(waiting for execution...)",
            height=763,
            label_visibility="collapsed",
            disabled=False
        )

# ─── NON-BLOCKING EXECUTION ENGINE ─────────────────────────────────────────
if st.session_state.is_running:
    code_to_run = st.session_state.repl_code.strip()
    timeout_val = st.session_state.repl_timeout

    if not code_to_run:
        st.toast("No code to run.", icon="⚠️")
        st.session_state.is_running = False
        st.rerun()

    st.session_state.repl_output += ">> Run\n"
    init_display_lines = st.session_state.repl_output.splitlines()[-42:]
    output_placeholder.text_area(
        "MCU Output Logs",
        value="\n".join(init_display_lines),
        height=763,
        label_visibility="collapsed",
        disabled=False,
        key="mcu_run_init"
    )

    cmd = [sys.executable, "-m", "mpremote", "exec", code_to_run]
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
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

        loop_counter = 0
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
                # Keep exactly ~42 lines (a very safe fit for 763px height).
                # This guarantees the text bounds will NEVER overflow the container and spawn a native scrollbar,
                # ensuring that remounting via key doesn't reset the viewport to hide the latest bottom lines.
                display_lines = st.session_state.repl_output.splitlines()[-42:]
                output_placeholder.text_area(
                    "MCU Output Logs",
                    value="\n".join(display_lines),
                    height=763,
                    label_visibility="collapsed",
                    disabled=False,
                    key=f"mcu_loop_{loop_counter}"
                )
                loop_counter += 1

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
                st.session_state.repl_output += f"\n>> [TIMEOUT] Connection closed after {timeout_val}s (Script may still be running on MCU)\n"
                proc.terminate()
                break

            time.sleep(0.05)

    except Exception as e:
        st.session_state.repl_output += f"[error] Process failed: {str(e)}\n"

    st.session_state.is_running = False
    st.rerun()

# ─── AUTO-SCROLL POST-EXECUTION ─────────────────────────────────────────────
if not st.session_state.is_running and st.session_state.repl_output:
    import streamlit.components.v1 as components
    components.html(
        f"""
        <!-- Force Re-evaluation: {time.time()} -->
        <script>
        function scrollToBottom() {{
            var parentDoc = window.parent.document;
            var markers = parentDoc.querySelectorAll('.layout-mcu-marker');
            if (markers.length > 0) {{
                var block = markers[0].closest('[data-testid="stVerticalBlock"]');
                if (block) {{
                    var ta = block.querySelector('textarea');
                    if (ta) {{
                        ta.scrollTop = ta.scrollHeight;
                    }}
                }}
            }}
        }}
        // Poll aggressively for 1.5 seconds to ensure Streamlit's delayed DOM render is caught
        var scrollInterval = setInterval(scrollToBottom, 50);
        setTimeout(function() {{ clearInterval(scrollInterval); }}, 1500);
        </script>
        """,
        height=0,
        width=0
    )

