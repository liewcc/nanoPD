import streamlit as st
import base64
from PIL import Image
from utils.style_utils import apply_global_css
from utils.config_utils import load_ui_config
import serial.tools.list_ports
import serial
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
    code_lh=st.session_state.ui_cfg["code_lh"],
    is_mcu_page=True
)

sidebar_msg_placeholder = st.sidebar.empty()

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
        if st.button("Update", type="primary", disabled=not has_update, width="stretch"):
            try:
                creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                subprocess.run(["git", "pull"], check=True, capture_output=True, timeout=15, creationflags=creationflags)
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Update failed: {e}")
    with col3:
        st.link_button("GitHub", "https://github.com/liewcc/nanoPD", width="stretch")

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
            import html
            
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

            lines = []
            for p in ports:
                desc = (p.description or "").strip()
                mfr = (getattr(p, "manufacturer", "") or "").strip()
                ser = (getattr(p, "serial_number", "") or "").strip()
                
                vid_str = f"VID:{p.vid:#06x}" if p.vid else "VID:------"
                pid_str = f"PID:{p.pid:#06x}" if p.pid else "PID:------"
                mfr_str = f"MFR:{mfr}" if mfr else "MFR:------"
                ser_str = f"SER:{ser}" if ser else "SER:------"
                
                # Highlight if it's the RP2350 target
                is_rp = "RP2" in desc.upper() or "RP2" in mfr.upper() or p.vid == 0x2E8A
                badge = " 🎯 TARGET" if is_rp else ""
                
                if p.device in occupied_ports:
                    badge += " 🔒 OCCUPIED"
                
                # Truncate strings if they are too long to maintain alignment
                desc_trunc = desc[:28] + ".." if len(desc) > 30 else desc
                mfr_trunc = mfr_str[:26] + ".." if len(mfr_str) > 28 else mfr_str
                ser_trunc = ser_str[:22] + ".." if len(ser_str) > 24 else ser_str
                
                # Format into perfectly aligned columns
                badge_color = "#92400e" if "OCCUPIED" in badge else "#2ba14b"
                line = f"<b>{p.device:<6}</b> {desc_trunc:<30} <span style='color:#64748b;'>{mfr_trunc:<28} {vid_str:<12} {pid_str:<12} {ser_trunc:<24}</span><b style='color:{badge_color};'>{badge}</b>"
                lines.append(line)
            
            term_text = "\n".join(lines)
            st.markdown(
                f"""
                <div style="background: #f8fafc; padding: 10px 14px; border-radius: 6px; border: 1px solid #e2e8f0; font-family: var(--code-font, monospace); font-size: var(--code-size, 14px); color: #0f172a; white-space: pre-wrap; overflow-x: auto; line-height: 1.5;">{term_text}</div>
                """, unsafe_allow_html=True
            )
            
            if occupied_ports:
                ports_str = ", ".join(occupied_ports)
                sidebar_msg_placeholder.markdown(f"""
                    <div style='background:#fffbeb; border:1px solid #fde68a; color:#92400e; padding:12px; border-radius:8px; margin-bottom:1rem; font-size:0.85em;'>
                        <div style='font-weight:700; display:flex; align-items:center; gap:6px;'>
                            🔒 COM PORT IN USE
                        </div>
                        <div style='margin-top:4px; color:#b45309; line-height:1.3;'>
                            The following ports are currently occupied: <b>{ports_str}</b>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            else:
                sidebar_msg_placeholder.empty()
        else:
            sidebar_msg_placeholder.empty()
            st.markdown("<div style='font-size: 14px; color: #64748b;'>No COM ports detected.</div>", unsafe_allow_html=True)

com_ports_panel()
