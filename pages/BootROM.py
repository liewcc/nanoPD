import streamlit as st
import sys
import os
import subprocess
import html
from utils.style_utils import apply_global_css
from utils.config_utils import load_ui_config
from utils.mount_utils import is_mounted, is_rp2350_connected

# 1. Load UI Configuration
if "ui_cfg" not in st.session_state:
    st.session_state.ui_cfg = load_ui_config()

# 2. Session State Initialization
if "boot_start_input" not in st.session_state:
    st.session_state["boot_start_input"] = "0x00000000"
if "boot_end_input" not in st.session_state:
    st.session_state["boot_end_input"] = "0x00003FFF"

# 3. Apply Global CSS
apply_global_css(
    title_size=st.session_state.ui_cfg.get("title_size", "1.5rem"),
    label_size=st.session_state.ui_cfg.get("label_size", "0.875rem"),
    info_size=st.session_state.ui_cfg.get("info_size", "1.0rem"),
    code_font=st.session_state.ui_cfg.get("code_font", "Consolas, Monaco, monospace"),
    code_size=st.session_state.ui_cfg.get("code_size", "14px"),
    code_lh=st.session_state.ui_cfg.get("code_lh", "1.3"),
    is_mcu_page=True
)

# 4. Page Specific CSS
st.markdown(f"""
<style>
    .hex-terminal-large {{
        background: #ffffff;
        padding: 16px;
        border-radius: 8px;
        font-family: var(--code-font, monospace);
        font-size: {st.session_state.ui_cfg.get("code_size", "14px")};
        border: 1px solid #e2e8f0;
        color: #1e293b;
        overflow-x: auto;
        white-space: pre;
        height: calc(100vh - 220px);
        overflow-y: auto;
    }}
    .end-of-scan {{
        border-top: 1px solid #f1f5f9;
        padding: 10px;
        margin-top: 20px;
        text-align: center;
        color: #94a3b8;
        font-size: 11px;
        font-family: sans-serif;
    }}
</style>
""", unsafe_allow_html=True)

# 5. Pre-fetch State
is_scanning = st.session_state.get("bootrom_scanning", False)
mounted = is_mounted()
connected = is_rp2350_connected()

# 6. Main Layout
col1, col2 = st.columns([1, 4])

with col1:
    with st.container(border=True):
        st.markdown('<p class="metric-label" style="margin:0 0 12px 0">SCAN CONTROL</p>', unsafe_allow_html=True)
        
        start_addr_str = st.text_input("Start Address (Hex)", key="boot_start_input", disabled=mounted or is_scanning)
        end_addr_str   = st.text_input("End Address (Hex)",   key="boot_end_input",   disabled=mounted or is_scanning)
        
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        
        button_label = "⏳ SCANNING..." if is_scanning else "SCAN BOOTROM"
        if st.button(button_label, type="primary", width="stretch", disabled=is_scanning or mounted or not connected):
            st.session_state["bootrom_scanning"] = True
            st.rerun()

with col2:
    with st.container(border=True):
        st.markdown('<p class="metric-label" style="margin:0 0 12px 0">BOOT ROM HEX VIEW</p>', unsafe_allow_html=True)
        
        bootrom_raw = st.session_state.get("bootrom_data", "No data. Click 'SCAN BOOTROM' to begin.")
        data_html   = html.escape(bootrom_raw)
        
        st.markdown(f"""
        <div class="hex-terminal-large">{data_html}<div class="end-of-scan">--- END OF SCAN DATA ---</div></div>
        """, unsafe_allow_html=True)

# 7. Data Processing
if is_scanning and not mounted:
    try:
        s_addr = int(st.session_state.get("boot_start_input", "0x00000000"), 16)
        e_addr = int(st.session_state.get("boot_end_input",   "0x00003FFF"), 16)
        s_size = max(0, e_addr - s_addr + 1)
        
        if s_size > 65536: # Safety cap
            st.session_state["bootrom_data"] = "Error: Block too large (>64KB)"
        else:
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            cmd = [sys.executable, "-m", "mpremote", "exec",
                   f"import ubinascii, uctypes; print(ubinascii.hexlify(uctypes.bytearray_at({s_addr}, {s_size})).decode())"]
            res = subprocess.run(cmd, capture_output=True, timeout=15.0, creationflags=creationflags)

            if res.returncode == 0:
                hex_data = res.stdout.decode().strip()
                lines    = [f"ADDRESS   00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F  ASCII", "-"*74]
                for i in range(0, len(hex_data), 32):
                    chunk = hex_data[i:i+32]
                    addr  = f"{(s_addr + i//2):08X}"
                    h_sp  = " ".join([chunk[j:j+2] for j in range(0, len(chunk), 2)]).upper()
                    asc   = "".join([chr(int(chunk[j:j+2], 16)) if 32 <= int(chunk[j:j+2], 16) <= 126 else "." for j in range(0, len(chunk), 2)])
                    lines.append(f"{addr}  {h_sp:<47} {asc}")
                st.session_state["bootrom_data"] = "\n".join(lines)
            else:
                st.session_state["bootrom_data"] = "Scan Error: " + res.stderr.decode()
    except Exception as e:
        st.session_state["bootrom_data"] = f"Error: {str(e)}"
    st.session_state["bootrom_scanning"] = False
    st.rerun()
