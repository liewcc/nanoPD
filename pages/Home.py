import streamlit as st
import base64
from PIL import Image
from utils.style_utils import apply_global_css
from utils.config_utils import load_ui_config
import serial.tools.list_ports
import subprocess

# 1. Load configuration and apply styles
if "ui_cfg" not in st.session_state:
    st.session_state.ui_cfg = load_ui_config()

apply_global_css(
    title_size=st.session_state.ui_cfg["title_size"],
    label_size=st.session_state.ui_cfg["label_size"],
    info_size=st.session_state.ui_cfg["info_size"],
    code_font=st.session_state.ui_cfg["code_font"],
    code_size=st.session_state.ui_cfg["code_size"],
    code_lh=st.session_state.ui_cfg["code_lh"]
)

# 2. Foolproof Centered Logo (Base64 + HTML)
import os
logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "img", "logo.png"))

def get_base64_image(path):
    with open(path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

try:
    with Image.open(logo_path) as img:
        original_width = img.width
    
    # Use logo_scale from the global UI config
    calc_width = int(original_width * (st.session_state.ui_cfg["logo_scale"] / 100))
    b64_str = get_base64_image(logo_path)
    
    st.markdown(
        f"""
        <div style="display: flex; justify-content: center; width: 100%; margin-top: 2rem;">
            <img src="data:image/png;base64,{b64_str}" style="width: {calc_width}px;">
        </div>
        """,
        unsafe_allow_html=True
    )
except Exception as e:
    st.error(f"Error loading logo: {e}")

# Version Check
@st.cache_data(ttl=60, show_spinner=False)
def check_git_updates():
    try:
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        subprocess.run(["git", "fetch"], check=True, capture_output=True, timeout=10, creationflags=creationflags)
        local = subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True, creationflags=creationflags).stdout.strip()
        remote = subprocess.run(["git", "rev-parse", "@{u}"], check=True, capture_output=True, text=True, creationflags=creationflags).stdout.strip()
        return local != remote, local[:7], remote[:7]
    except Exception:
        return False, "unknown", "unknown"

has_update, loc_hash, rem_hash = check_git_updates()

with st.container(border=True):
    st.markdown(
        """
        <div class="layout-control-marker" style="display:none;"></div>
        <p class="metric-label" style="margin:0 0 12px 0">SYSTEM VERSION</p>
        """,
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns([6, 1, 1], vertical_alignment="bottom")
    with col1:
        if has_update:
            st.markdown(
                f"""
                <div style="background-color: rgba(255, 189, 69, 0.15); color: #ffbd45; padding: 0 1rem; border-radius: 0.5rem; height: 38px; display: flex; align-items: center; border: 1px solid rgba(255, 189, 69, 0.4); font-size: 14px;">
                    🚀 <b style="margin-right: 8px;">Update Available!</b> (Local: <code>{loc_hash}</code> &nbsp;→&nbsp; Remote: <code>{rem_hash}</code>)
                </div>
                """, unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div style="background-color: rgba(43, 161, 75, 0.15); color: #2ba14b; padding: 0 1rem; border-radius: 0.5rem; height: 38px; display: flex; align-items: center; border: 1px solid rgba(43, 161, 75, 0.4); font-size: 14px;">
                    ✅ <b style="margin-right: 8px;">Up to date</b> (Commit: <code>{loc_hash}</code>)
                </div>
                """, unsafe_allow_html=True
            )
    with col2:
        if st.button("Update", type="primary", disabled=not has_update, use_container_width=True):
            try:
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                subprocess.run(["git", "pull"], check=True, capture_output=True, timeout=15, creationflags=creationflags)
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Update failed: {e}")
    with col3:
        st.link_button("GitHub", "https://github.com/liewcc/nanoPD", use_container_width=True)

# COM ports section — auto-refresh every 3 seconds using @st.fragment
@st.fragment(run_every=3)
def com_ports_panel():
    with st.container(border=True):
        st.markdown(
            """
            <div class="layout-control-marker" style="display:none;"></div>
            <p class="metric-label" style="margin:0 0 12px 0">COM PORTS</p>
            <style>
                [data-testid="stTable"] {
                    font-family: var(--code-font, monospace) !important;
                }
                [data-testid="stTable"] th, [data-testid="stTable"] td {
                    font-family: var(--code-font, monospace) !important;
                    font-size: 13px !important;
                }
                [data-testid="stTable"] th {
                    font-weight: 600 !important;
                }
            </style>
            """,
            unsafe_allow_html=True,
        )
        ports = serial.tools.list_ports.comports()
        if ports:
            rows = []
            for p in ports:
                rows.append({
                    "Device": p.device,
                    "Description": p.description,
                    "Manufacturer": getattr(p, "manufacturer", ""),
                    "VID": f"{p.vid:#04x}" if p.vid else "",
                    "PID": f"{p.pid:#04x}" if p.pid else "",
                    "Serial": getattr(p, "serial_number", "")
                })
            st.table(rows)
        else:
            st.write("No COM ports detected.")

com_ports_panel()
