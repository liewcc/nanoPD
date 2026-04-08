import streamlit as st
import base64
from PIL import Image
from utils.style_utils import apply_global_css
from utils.config_utils import load_ui_config

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

# 3. Empty Space
st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)
