import streamlit as st
from utils.mount_utils import is_mounted, is_rp2350_connected
import serial.tools.list_ports
import serial

@st.fragment(run_every=3)
def _sidebar_occupied_ports_panel():
    ports = serial.tools.list_ports.comports()
    if ports:
        occupied_ports = []
        for p in ports:
            try:
                s = serial.Serial(p.device)
                s.close()
            except serial.SerialException as e:
                if "Access is denied" in str(e) or "PermissionError" in str(e):
                    occupied_ports.append(p.device)
            except Exception:
                pass
        
        if occupied_ports:
            ports_str = ", ".join(occupied_ports)
            st.markdown(f"""
                <div style='background:#fffbeb; border:1px solid #fde68a; color:#92400e; padding:12px; border-radius:8px; margin-bottom:0; margin-top:0; font-size:0.85em;'>
                    <div style='font-weight:700; display:flex; align-items:center; gap:6px;'>
                        🔒 COM PORT IN USE
                    </div>
                    <div style='margin-top:4px; color:#b45309; line-height:1.3;'>
                        The following ports are currently occupied: <b>{ports_str}</b>
                    </div>
                </div>
            """, unsafe_allow_html=True)

@st.fragment(run_every=3)
def render_mqtt_status_panel():
    state_obj = st.session_state.get("mqtt_shared_state", {})
    if state_obj.get("status") == "connected":
        host = st.session_state.get("mqtt_cfg", {}).get("internet_host", "Unknown Broker")
        st.markdown(f"""
            <div style='background:#eff6ff; border:1px solid #bfdbfe; color:#1e3a8a; padding:12px; border-radius:8px; margin-bottom:0; margin-top:0; font-size:0.85em;'>
                <div style='font-weight:700; display:flex; align-items:center; gap:6px;'>
                    🌐 INTERNET MQTT ACTIVE
                </div>
                <div style='margin-top:4px; color:#1d4ed8; line-height:1.3;'>
                    Background connection running.<br>Broker: <b>{host}</b>
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.empty()

def get_global_styles(
    title_size="1.5rem",
    label_size="0.875rem",
    info_size="1.0rem",
    code_font="Consolas, Monaco, monospace", 
    code_size="14px", 
    code_lh="1.3"
):
    """Returns the raw CSS contents with dynamic styling (Main Panel Only)."""
    return f"""
    /* 1. Viewport Locking */
    html, body, .stApp, [data-testid="stAppViewContainer"] {{
        box-sizing: border-box !important;
        height: 100vh !important;
        width: 100vw !important;
        overflow: hidden !important;
        position: fixed !important;
        margin: 0 !important;
        padding: 0 !important;
    }}

    /* 2. Absolute Header */
    header[data-testid="stHeader"] {{
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        right: 0 !important;
        height: 48px !important;
        background: transparent !important;
        z-index: 999999 !important;
    }}

    /* 3. Main Content Container (Stable v716 Logic) */
    [data-testid="stAppViewBlockContainer"], 
    .block-container {{
        max-width: calc(100vw - 360px) !important; 
        margin-left: 0 !important;
        margin-top: 0 !important; 
        padding-top: 1.5rem !important; 
        padding-bottom: 20px !important;
        padding-left: 1rem !important;
        padding-right: 3rem !important;
        box-sizing: border-box !important;
        height: 100vh !important;
        overflow: hidden !important;
    }}

    /* 4. Title (Subheader) Scaling - Targets st.subheader (Title 1/2) */
    [data-testid="stAppViewBlockContainer"] h3,
    [data-testid="stAppViewBlockContainer"] .stSubheader h3,
    h3 {{
        font-size: {title_size} !important;
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }}

    /* 5. Metric Label Styling */
    .metric-label,
    .metric-label * {{
        color: #64748b !important;
        font-size: {label_size} !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }}
    
    /* 6. Info Box (Alert) Scaling */
    .stAlert,
    .stAlert * {{
        font-size: {info_size} !important;
    }}

    /* 7. Code & Text Area Styling (Monospace) */
    [data-testid="stCode"] code, 
    [data-testid="stCode"] pre,
    [data-testid="stTextArea"] textarea,
    [data-testid="stTextArea"] textarea *,
    pre code {{
        font-family: {code_font} !important;
        font-size: {code_size} !important;
        line-height: {code_lh} !important;
    }}

    footer {{ display: none !important; }}

    /* Custom Scrollbar */
    ::-webkit-scrollbar {{
        width: 8px;
        height: 8px;
    }}
    ::-webkit-scrollbar-track {{
        background: transparent;
    }}
    ::-webkit-scrollbar-thumb {{
        background: #e2e8f0;
        border-radius: 10px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: #cbd5e1;
    }}

    /* GLOBAL FIX: Reduce Streamlit's large default bottom padding on the main content area (C = 20px) */
    section[data-testid="stMain"] > div {{
        padding-bottom: 20px !important;
    }}
    div[data-testid="block-container"] {{
        padding-bottom: 20px !important;
    }}

    /* GLOBAL FIX: Remove extra margin below st.markdown elements to ensure uniform inner padding (B = A) */
    [data-testid="stMarkdownContainer"] {{
        margin-bottom: 0 !important;
    }}
    [data-testid="stMarkdownContainer"] > p:last-child {{
        margin-bottom: 0 !important;
    }}

    /* SIDEBAR FIX: Compact the gaps between consecutive status panels */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] {{
        margin-top: -8px !important;
    }}
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"]:first-child {{
        margin-top: 0 !important;
    }}
    """

def apply_global_css(
    title_size="1.5rem",
    label_size="0.875rem",
    info_size="1.0rem",
    code_font="Consolas, Monaco, monospace", 
    code_size="14px", 
    code_lh="1.3",
    is_mcu_page=False
):
    """Injects the global CSS with Google Font support and dynamic parameters."""
    
    # Render Global Mounting Status in Sidebar (Only for MCU-related pages)
    if is_mcu_page:
        with st.sidebar:
            if is_mounted():
                st.markdown("""
                    <div style='background:#fef2f2; border:1px solid #fee2e2; color:#991b1b; padding:12px; border-radius:8px; margin-bottom:0; margin-top:-14px; font-size:0.85em;'>
                        <div style='font-weight:700; display:flex; align-items:center; gap:6px;'>
                            🔒 SERIAL PORT BUSY
                        </div>
                        <div style='margin-top:4px; color:#b91c1c; line-height:1.3;'>
                            Device is currently mounted. Hardware operations are locked.
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            elif not is_rp2350_connected():
                st.markdown("""
                    <div style='background:#f8fafc; border:1px solid #e2e8f0; color:#475569; padding:12px; border-radius:8px; margin-bottom:0; margin-top:-14px; font-size:0.85em;'>
                        <div style='font-weight:700; display:flex; align-items:center; gap:6px;'>
                            🔌 USB DISCONNECTED
                        </div>
                        <div style='margin-top:4px; color:#64748b; line-height:1.3;'>
                            No RP2xxx device detected. Please connect the device.
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                    <div style='background:#f0fdf4; border:1px solid #dcfce7; color:#166534; padding:12px; border-radius:8px; margin-bottom:0; margin-top:-14px; font-size:0.85em;'>
                        <div style='font-weight:700; display:flex; align-items:center; gap:6px;'>
                            ✅ SERIAL PORT READY
                        </div>
                        <div style='margin-top:4px; color:#15803d; line-height:1.3;'>
                            Device is unmounted. Hardware operations are available.
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        with st.sidebar:
            _sidebar_occupied_ports_panel()

    raw_styles = get_global_styles(
        title_size=title_size, 
        label_size=label_size, 
        info_size=info_size, 
        code_font=code_font, 
        code_size=code_size, 
        code_lh=code_lh
    )
    
    # Minify to prevent markdown code-block detection
    minified_css = "".join([line.strip() for line in raw_styles.splitlines() if line.strip()])
    
    # Combined injection with Google Font
    combined_html = (
        f'<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap" rel="stylesheet">'
        f'<style>{minified_css}</style>'
    )
    
    # Using st.markdown
    st.markdown(combined_html, unsafe_allow_html=True)
