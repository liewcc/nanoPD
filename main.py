import streamlit as st
import os
from utils.mount_utils import startup_cleanup, register_exit_handlers

# 0. Global Support (Once per server lifecycle)
# Startup cleanup to ensure no orphaned mount processes exist
if "mount_initialized" not in st.session_state:
    startup_cleanup()
    register_exit_handlers()
    st.session_state["mount_initialized"] = True

# 1. Set Page Config (Must be FIRST and only ONCE in main for global wide layout)
st.set_page_config(
    page_title="NanoPD 2.0",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Page Navigation Configuration
from utils.style_utils import apply_global_css
apply_global_css() # Apply style for the navigation container itself




# Configure the native navigation panel (Home at root, others grouped)
pages = {
    "": [
        st.Page("pages/Home.py", title="Home", icon="🏠", default=True),
    ],
    "MCU": [
        st.Page("pages/Filesystem.py", title="Filesystem", icon="📁"),
        st.Page("pages/REPL_Console.py", title="REPL Console", icon="🖥️"),
        st.Page("pages/Peripherals.py", title="Peripherals", icon="🧩"),
        st.Page("pages/SRAM.py", title="SRAM", icon="💾"),
        st.Page("pages/BootROM.py", title="BootROM", icon="🔒"),
        st.Page("pages/OTP.py", title="OTP", icon="🔑"),
    ],
    "Utilities": [
        st.Page("pages/UI_calibration_sandbox.py", title="UI calibration sandbox", icon="🧪"),
        st.Page("pages/RS485_Decoder.py", title="RS485 Decoder", icon="🔌"),
    ]
}

# Initialize and run the multi-page navigation router
pg = st.navigation(pages)

if st.session_state.get("current_nav_page") != pg.title:
    st.session_state["current_nav_page"] = pg.title
    st.session_state["rs485_config_loaded"] = False

pg.run()

