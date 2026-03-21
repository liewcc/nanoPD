import streamlit as st
from utils.style_utils import apply_global_css
from utils.config_utils import load_ui_config, save_ui_config, DEFAULT_UI_CONFIG

# 1. Load Persisted UI Configuration
if "ui_cfg" not in st.session_state:
    st.session_state.ui_cfg = load_ui_config()

# 2. Calibration Dialog Definition
@st.dialog("UI Style Calibration")
def calibration_dialog():
    st.markdown("### 🎨 System Typography")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        st.session_state.ui_cfg["title_size"] = st.text_input("Title size", value=st.session_state.ui_cfg["title_size"])
        st.session_state.ui_cfg["label_size"] = st.text_input("Label size", value=st.session_state.ui_cfg["label_size"])
    with col_f2:
        st.session_state.ui_cfg["info_size"] = st.text_input("Info text size", value=st.session_state.ui_cfg["info_size"])
    
    st.markdown("---")
    st.markdown("### 💻 Code Block Styling")
    st.session_state.ui_cfg["code_font"] = st.text_input("Font Family", value=st.session_state.ui_cfg["code_font"])
    cf3, cf4 = st.columns(2)
    with cf3:
        st.session_state.ui_cfg["code_size"] = st.text_input("Font Size", value=st.session_state.ui_cfg["code_size"])
    with cf4:
        st.session_state.ui_cfg["code_lh"] = st.text_input("Line Height", value=st.session_state.ui_cfg["code_lh"])

    st.markdown("---")
    st.markdown("### 🏠 Home Page Scaling")
    st.session_state.ui_cfg["logo_scale"] = st.number_input("home page Logo Scale (%)", 
                                                         min_value=1, max_value=500, 
                                                         value=int(st.session_state.ui_cfg["logo_scale"]))

    if st.button("OK", width="stretch"):
        save_ui_config(st.session_state.ui_cfg)
        st.toast("Settings saved to UI_config.json")
        st.rerun()

# 3. Sidebar: Unified Calibration Access
with st.sidebar:
    st.markdown("### 🎨 UI Style Tuning")
    if st.button("🔧 calibrate", width="stretch"):
        calibration_dialog()
    
    if st.button("🔄 Reset to Defaults", width="stretch", help="Revert to factory settings"):
        st.session_state.ui_cfg = DEFAULT_UI_CONFIG.copy()
        save_ui_config(st.session_state.ui_cfg)
        st.rerun()

# 4. Apply Global CSS + fix stMarkdown implicit bottom margin
apply_global_css(
    title_size=st.session_state.ui_cfg["title_size"],
    label_size=st.session_state.ui_cfg["label_size"],
    info_size=st.session_state.ui_cfg["info_size"],
    code_font=st.session_state.ui_cfg["code_font"],
    code_size=st.session_state.ui_cfg["code_size"],
    code_lh=st.session_state.ui_cfg["code_lh"]
)

# KEY FIX: Streamlit adds a large implicit bottom margin to every stMarkdown block.
# Also reduces Streamlit's main block padding-bottom from ~200px to 20px.
st.markdown("""
    <style>
        /* Reduce Streamlit's large default bottom padding on the main content area */
        section[data-testid="stMain"] > div {
            padding-bottom: 20px !important;
        }
        .main > div.block-container {
            padding-bottom: 20px !important;
        }
        div[data-testid="block-container"] {
            padding-bottom: 20px !important;
        }
    </style>
""", unsafe_allow_html=True)

# 5. TOP ROW — Using native st.columns so gaps A = B = C automatically
m1, m2, m3, m4 = st.columns(4)

with m1:
    with st.container(height=110, border=True):
        st.markdown('<p class="metric-label" style="margin:0 0 4px 0">METRIC LABEL 1</p>', unsafe_allow_html=True)
        st.success("Info Box 1")

with m2:
    with st.container(height=110, border=True):
        st.markdown('<p class="metric-label" style="margin:0 0 4px 0">METRIC LABEL 2</p>', unsafe_allow_html=True)
        st.info("Info Box 2")

with m3:
    with st.container(height=90, border=True):
        st.markdown('<p class="metric-label" style="margin:0 0 4px 0">METRIC LABEL 3</p>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:14px">METRIC VALUE 3</div>', unsafe_allow_html=True)

with m4:
    with st.container(height=90, border=True):
        st.markdown('<p class="metric-label" style="margin:0 0 4px 0">METRIC LABEL 4</p>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:14px">METRIC VALUE 4</div>', unsafe_allow_html=True)

# 6. MAIN ROW — same column layout, so gap to top row equals A automatically
col_left, col_right = st.columns([1, 1])

with col_left:
    with st.container(height=720, border=True):
        st.markdown('<p class="metric-label" style="margin:0 0 12px 0">METRIC LABEL 5</p>', unsafe_allow_html=True)
        st.info("Info Box 3")
        st.line_chart([10, 12, 11, 15, 14, 13], height=400, width="stretch")

with col_right:
    with st.container(height=720, border=True):
        st.markdown('<p class="metric-label" style="margin:0 0 12px 0">METRIC LABEL 6</p>', unsafe_allow_html=True)
        st.button("Button 1", width="stretch")
        
        if "log_content" not in st.session_state:
            st.session_state.log_content = "[Text Area 1 Content]\n" * 50
        
        st.text_area(
            "Logs", 
            value=st.session_state.log_content, 
            height=600, 
            label_visibility="collapsed",
            key="log_content_input"
        )
        st.session_state.log_content = st.session_state.log_content_input

