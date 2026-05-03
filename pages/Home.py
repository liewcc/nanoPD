import streamlit as st
import base64
from PIL import Image
from utils.style_utils import apply_global_css
from utils.config_utils import load_ui_config
import serial.tools.list_ports

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

# COM ports section — auto-refresh every 3 seconds using @st.fragment
@st.fragment(run_every=3)
def com_ports_panel():
    with st.container(border=True):
        st.markdown(
            """
            <div class="layout-control-marker" style="display:none;"></div>
            <p class="metric-label" style="margin:0 0 12px 0">COM PORTS</p>
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
