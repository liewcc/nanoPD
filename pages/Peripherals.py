import streamlit as st
import sys
import os
import html
import subprocess
from utils.style_utils import apply_global_css
from utils.config_utils import load_ui_config
from utils.mount_utils import is_mounted, is_rp2350_connected

# 1. Load Peripheral Core Utilities
try:
    from utils.peripheral_mapper import PERIPHERALS
    from utils.peripheral_scanner import read_register
    from utils.peripheral_metadata import get_bit_metadata, get_peripheral_name
except ImportError:
    st.error("Backend Error: Core peripheral utilities missing in utils/")
    st.stop()

# 2. Load UI Configuration
if "ui_cfg" not in st.session_state:
    st.session_state.ui_cfg = load_ui_config()

# 3. Session State Initialization
if "p_start_addr" not in st.session_state:
    st.session_state.p_start_addr = 0x40000000
if "p_scan_count" not in st.session_state:
    st.session_state.p_scan_count = 16 
if "p_arch" not in st.session_state:
    st.session_state.p_arch = "ARM"

# 4. Data Fetching
def fetch_peripheral_data(start_addr, count):
    script = f"""
import machine
base = {start_addr}
count = {count}
vals = []
for i in range(count):
    try:
        vals.append(hex(machine.mem32[base + i*4]))
    except:
        vals.append('Error')
print(vals)
"""
    if is_mounted() or not is_rp2350_connected():
        return ["LOCKED"] * count
    
    cmd = [sys.executable, "-m", "mpremote", "exec", script]
    try:
        # Hide console window on Windows
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        res = subprocess.run(cmd, capture_output=True, timeout=5.0, creationflags=creationflags)
        if res.returncode == 0:
            output = res.stdout.decode().strip()
            return eval(output)
    except Exception:
        return ["Error"] * count
    return ["0x00000000"] * count

# 5. Apply Global CSS
apply_global_css(
    title_size=st.session_state.ui_cfg.get("title_size", "1.5rem"),
    label_size=st.session_state.ui_cfg.get("label_size", "0.875rem"),
    info_size=st.session_state.ui_cfg.get("info_size", "1.0rem"),
    code_font=st.session_state.ui_cfg.get("code_font", "Consolas, Monaco, monospace"),
    code_size=st.session_state.ui_cfg.get("code_size", "14px"),
    code_lh=st.session_state.ui_cfg.get("code_lh", "1.3"),
    is_mcu_page=True
)

# 6. Page Specific CSS (Bitfield grid & Hex Terminal)
st.markdown("""
<style>
    /* Hex Terminal Styling */
    .hex-terminal {
        background: #ffffff;
        padding: 12px;
        border-radius: 8px;
        font-family: var(--code-font, monospace);
        font-size: """ + st.session_state.ui_cfg.get("code_size", "14px") + """;
        border: 1px solid #e2e8f0;
        color: #0f172a;
        overflow-x: auto;
        white-space: pre;
        height: 655px;
        overflow-y: auto;
    }
    
    /* Bitfield Grid */
    .bit-container {
        display: grid;
        grid-template-columns: repeat(16, minmax(0, 1fr));
        gap: 2px;
        margin-bottom: 6px;
        width: 100%;
        box-sizing: border-box;
    }
    .bit-box {
        background: #f1f5f9;
        border: 1px solid #e2e8f0;
        padding: 4px 0;
        text-align: center;
        font-family: inherit;
        font-size: 0.65rem;
        border-radius: 4px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 32px;
    }
    .bit-box b {
        font-size: 0.8rem;
        line-height: 1;
        font-weight: 600;
    }
    .bit-box.one {
        background: #3b82f6;
        color: white;
        border-color: #2563eb;
    }
    .bit-label {
        font-size: 0.7rem;
        color: #64748b;
        line-height: 1;
        margin-bottom: 2px;
    }
    .bit-box.one .bit-label {
        color: #bfdbfe;
    }
    
    /* Table Styling */
    .styled-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.85rem;
        color: #0f172a;
    }
    .styled-table th {
        text-align: left;
        padding: 8px;
        border-bottom: 2px solid #e2e8f0;
        color: #64748b;
        font-size: 0.75rem;
        text-transform: uppercase;
    }
    .styled-table td {
        padding: 8px;
        border-bottom: 1px solid #f1f5f9;
        font-size: 0.8rem;
    }
    .mono-cell {
        font-family: monospace;
        font-weight: 500;
    }
    
    .field-label-small {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #64748b;
        font-weight: 600;
        margin-bottom: 4px;
        display: block;
    }
    
    .table-scroll {
        max-height: 425px;
        overflow-y: auto;
        border-top: 1px solid #f1f5f9;
        margin-top: 12px;
    }

    /* Fix Streamlit padding */
    section[data-testid="stMain"] > div {
        padding-bottom: 20px !important;
    }
</style>
""", unsafe_allow_html=True)

# 7. Main Layout
data = fetch_peripheral_data(st.session_state.p_start_addr, st.session_state.p_scan_count)
addr_list = [hex(st.session_state.p_start_addr + (i*4)) for i in range(st.session_state.p_scan_count)]

# Control Bar
with st.container(border=True):
    mounted = is_mounted()
    c0, c1, c2, c3, c4, c5 = st.columns([1.0, 1.1, 1.1, 0.8, 0.7, 1.3])
    
    with c0:
        arch_map = {"ARM": "ARM M33", "RISCV": "RISC-V (Hazard3)"}
        selected_arch_label = st.selectbox("Architecture", list(arch_map.values()), 
                                          index=0 if st.session_state.p_arch == "ARM" else 1, 
                                          disabled=mounted)
        new_arch = "ARM" if selected_arch_label == "ARM M33" else "RISCV"
        if st.session_state.p_arch != new_arch:
            st.session_state.p_arch = new_arch
            st.rerun()

    with c1:
        other_arch_group = "RISC-V Core Peripherals" if st.session_state.p_arch == "ARM" else "ARM Core Peripherals"
        group_list = [g for g in PERIPHERALS.keys() if g != other_arch_group]
        curr_g_idx = 0
        for i, g in enumerate(group_list):
            if any(addr == st.session_state.p_start_addr for addr in PERIPHERALS[g].values()):
                curr_g_idx = i
                break
        selected_group = st.selectbox("Quick-Jump", group_list, index=curr_g_idx, disabled=mounted)

    with c2:
        modules = PERIPHERALS[selected_group]
        module_list = list(modules.keys())
        curr_m_idx = 0
        for i, m in enumerate(module_list):
            if modules[m] == st.session_state.p_start_addr:
                curr_m_idx = i
                break
        module_name = st.selectbox("Module", module_list, index=curr_m_idx, disabled=mounted)
        target_addr = modules[module_name]
        if st.session_state.p_start_addr != target_addr:
            st.session_state.p_start_addr = target_addr
            st.rerun()

    with c3:
        addr_input = st.text_input("Address", value=hex(st.session_state.p_start_addr), disabled=mounted)
        try:
            curr_val = int(addr_input, 16)
            if st.session_state.p_start_addr != curr_val:
                st.session_state.p_start_addr = curr_val
                st.rerun()
        except: pass

    with c4:
        count_input = st.number_input("Count", min_value=1, max_value=256, 
                                     value=st.session_state.p_scan_count, disabled=mounted)
        if st.session_state.p_scan_count != int(count_input):
            st.session_state.p_scan_count = int(count_input)
            st.rerun()

    with c5:
        selected_addr_hex = st.selectbox("Analyze Register", addr_list, disabled=mounted)

# Register View Grid
col_list, col_analysis = st.columns([1.2, 1.5])

with col_list:
    with st.container(height=720, border=True):
        st.markdown('<p class="metric-label" style="margin:0 0 12px 0">REGISTER LIST (32-BIT)</p>', unsafe_allow_html=True)
        lines = []
        divider = "-" * 58
        lines.append(divider)
        lines.append("ADDRESS   VALUE        BINARY (31...0)")
        lines.append(divider)
        
        for i, val in enumerate(data):
            curr_addr = st.session_state.p_start_addr + (i * 4)
            if val == 'Error':
                val_str = "ERR        "
                bin_pretty = "..."
            elif val == 'LOCKED':
                val_str = "LOCKED     "
                bin_pretty = "..."
            else:
                try:
                    v_int = int(val, 16)
                    h_str = f"{v_int:08X}"
                    val_str = f"{h_str[0:2]} {h_str[2:4]} {h_str[4:6]} {h_str[6:8]}"
                    bin_str = bin(v_int)[2:].zfill(32)
                    bin_pretty = f"{bin_str[0:8]} {bin_str[8:16]} {bin_str[16:24]} {bin_str[24:32]}"
                except:
                    val_str = "INV        "
                    bin_pretty = "..."
            lines.append(f"{curr_addr:08X}  {val_str}  {bin_pretty}")

        term_text = html.escape("\n".join(lines))
        st.markdown(f"<div class='hex-terminal'>{term_text}</div>", unsafe_allow_html=True)

with col_analysis:
    with st.container(height=720, border=True):
        st.markdown('<p class="metric-label" style="margin:0 0 12px 0">REGISTER ANALYSIS</p>', unsafe_allow_html=True)
        if selected_addr_hex:
            sel_addr = int(selected_addr_hex, 16)
            sel_val = read_register(sel_addr)
            p_name = get_peripheral_name(sel_addr, arch=st.session_state.p_arch)
            
            # Calculate offset from peripheral base (or just from start addr if base not found)
            offset = sel_addr - st.session_state.p_start_addr
            metadata_list = get_bit_metadata(st.session_state.p_start_addr, offset, arch=st.session_state.p_arch)

            try:
                v_int = int(sel_val, 16)
                binary = bin(v_int)[2:].zfill(32)
                
                # Header
                st.markdown(f"<span class='field-label-small'>Module</span><div style='margin-bottom:12px; font-weight:600;'>{p_name}</div>", unsafe_allow_html=True)
                
                # Bit rows
                def get_row_html(bits_range):
                    row_html = "<div class='bit-container'>"
                    for bit_idx in bits_range:
                        bit_val = binary[31 - bit_idx]
                        cls = "bit-box one" if bit_val == '1' else "bit-box"
                        row_html += f"<div class='{cls}'><span class='bit-label'>{bit_idx}</span><b>{bit_val}</b></div>"
                    row_html += "</div>"
                    return row_html

                st.markdown(get_row_html(range(31, 15, -1)), unsafe_allow_html=True)
                st.markdown(get_row_html(range(15, -1, -1)), unsafe_allow_html=True)
                
                # Metadata Table
                if metadata_list:
                    st.markdown("<span class='field-label-small' style='margin-top:20px;'>Bitfield Metadata</span>", unsafe_allow_html=True)
                    table_html = "<table class='styled-table'><thead><tr><th style='width:20%'>Bits</th><th style='width:30%'>Name</th><th style='width:50%'>Description</th></tr></thead><tbody>"
                    seen = set()
                    for m in metadata_list:
                        tag = f"{m['name']}_{m['bits']}"
                        if tag not in seen:
                            bits_str = f"[{m['bits'][1]}:{m['bits'][0]}]"
                            desc_clean = " ".join(m.get('desc', 'N/A').replace("\n", " ").split())
                            table_html += f"<tr><td class='mono-cell'>{bits_str}</td><td>{m['name']}</td><td>{desc_clean}</td></tr>"
                            seen.add(tag)
                    table_html += "</tbody></table>"
                    st.markdown(f"<div class='table-scroll'>{table_html}</div>", unsafe_allow_html=True)
                else:
                    st.info("No bitfield definitions found for this address.")
                
            except Exception as e:
                st.error(f"Analysis Error: {str(e)}")
        else:
            st.info("Select a register to analyze in the control bar.")

st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
