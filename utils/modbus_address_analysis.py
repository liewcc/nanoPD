"""
Modbus Address Analysis Tab
───────────────────────────
Standalone module rendered inside the RS485_Decoder page as a tab.
Keeps all logic & state isolated from the main decoder code.
"""

import streamlit as st
import csv
import os
import tkinter as tk
from tkinter import filedialog

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RS485_CONFIG_DIR = os.path.join(_BASE_DIR, "RS485_config_file")

# ─── Session State Defaults ─────────────────────────────────────────────────
def _init_state():
    if "modbus_csv_path" not in st.session_state:
        st.session_state.modbus_csv_path = ""
    if "modbus_csv_data" not in st.session_state:
        st.session_state.modbus_csv_data = []       # list[dict]
    if "modbus_csv_headers" not in st.session_state:
        st.session_state.modbus_csv_headers = []     # list[str]
    if "modbus_render_list" not in st.session_state:
        st.session_state.modbus_render_list = st.session_state.get("persist_modbus_render_list", False)
    if "modbus_start_hex" not in st.session_state:
        st.session_state.modbus_start_hex = st.session_state.get("persist_modbus_start_hex", "")
    if "modbus_end_hex" not in st.session_state:
        st.session_state.modbus_end_hex = st.session_state.get("persist_modbus_end_hex", "")
    if "modbus_addr_format" not in st.session_state:
        st.session_state.modbus_addr_format = st.session_state.get("persist_modbus_addr_format", "HEX")
    if "modbus_type_selector" not in st.session_state:
        st.session_state.modbus_type_selector = st.session_state.get("persist_modbus_type_selector", "All")
    if "modbus_applied_start" not in st.session_state:
        st.session_state.modbus_applied_start = st.session_state.get("persist_modbus_applied_start", "")
    if "modbus_applied_end" not in st.session_state:
        st.session_state.modbus_applied_end = st.session_state.get("persist_modbus_applied_end", "")
    if "modbus_applied_format" not in st.session_state:
        st.session_state.modbus_applied_format = st.session_state.get("persist_modbus_applied_format", "HEX")

# ─── File Actions ────────────────────────────────────────────────────────────
def _open_csv():
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', True)
    path = filedialog.askopenfilename(
        title="Open Modbus Address CSV",
        initialdir=_RS485_CONFIG_DIR,
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )
    root.destroy()
    if path:
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                st.session_state.modbus_csv_headers = reader.fieldnames or []
                st.session_state.modbus_csv_data = list(reader)
            st.session_state.modbus_csv_path = path
            st.session_state.modbus_render_list = False
            st.toast(f"Loaded: {os.path.basename(path)}  ({len(st.session_state.modbus_csv_data)} rows)", icon="✅")
        except Exception as e:
            st.toast(f"Open failed: {e}", icon="❌")


def _save_csv():
    if not st.session_state.modbus_csv_data:
        st.toast("No data to save.", icon="⚠️")
        return
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', True)
    path = filedialog.asksaveasfilename(
        title="Save Modbus Address CSV",
        initialdir=_RS485_CONFIG_DIR,
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )
    root.destroy()
    if path:
        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=st.session_state.modbus_csv_headers)
                writer.writeheader()
                writer.writerows(st.session_state.modbus_csv_data)
            st.session_state.modbus_csv_path = path
            st.toast(f"Saved: {os.path.basename(path)}", icon="✅")
        except Exception as e:
            st.toast(f"Save failed: {e}", icon="❌")


# ─── Styled Table Renderer ──────────────────────────────────────────────────
_TYPE_COLORS = {
    "Holding Register": ("#dbeafe", "#1e40af"),   # blue
    "Input Register":   ("#dcfce7", "#166534"),   # green
    "Coil":             ("#fef9c3", "#854d0e"),   # yellow
    "Discrete Input":   ("#fce7f3", "#9d174d"),   # pink
}

def _render_table(data, headers):
    """Build a custom HTML table matching the project's aesthetic."""
    # Header row
    header_cells = "".join(
        f'<th style="padding:8px 12px;text-align:left;font-size:0.78rem;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:0.05em;color:#64748b;'
        f'border-bottom:2px solid #e2e8f0;white-space:nowrap;">{h}</th>'
        for h in headers
    )

    # Data rows
    body_rows = []
    for i, row in enumerate(data):
        bg = "#ffffff" if i % 2 == 0 else "#f8fafc"
        cells = []
        for h in headers:
            val = row.get(h, "")
            cell_style = (
                f"padding:6px 12px;font-size:0.82rem;border-bottom:1px solid #f1f5f9;"
                f"color:#334155;white-space:nowrap;"
            )
            # Color-code the Type column
            if h == "Type" and val in _TYPE_COLORS:
                bg_c, fg_c = _TYPE_COLORS[val]
                val = (
                    f'<span style="background:{bg_c};color:{fg_c};padding:2px 8px;'
                    f'border-radius:4px;font-size:0.75rem;font-weight:600;">{val}</span>'
                )
            # Color-code Access column
            elif h == "Access":
                if val == "RW":
                    val = f'<span style="color:#7c3aed;font-weight:600;">{val}</span>'
                elif val == "R":
                    val = f'<span style="color:#0891b2;font-weight:600;">{val}</span>'
            cells.append(f'<td style="{cell_style}">{val}</td>')
        body_rows.append(f'<tr style="background:{bg};">{"".join(cells)}</tr>')

    html = f"""
    <div style="max-height:calc(100vh - 380px);overflow:auto;border:1px solid #e2e8f0;border-radius:8px;">
        <table style="width:100%;border-collapse:collapse;font-family:Inter,sans-serif;">
            <thead style="position:sticky;top:0;background:#f8fafc;z-index:1;">
                <tr>{header_cells}</tr>
            </thead>
            <tbody>
                {"".join(body_rows)}
            </tbody>
        </table>
    </div>
    """
    return html


# ─── Data Update from RX ────────────────────────────────────────────────────
def update_from_rx(rx_data: bytes, start_addr: int, quantity: int, func_code: int):
    """Parses a Modbus RX payload and updates the loaded address map."""
    if "modbus_csv_data" not in st.session_state or not st.session_state.modbus_csv_data:
        return
        
    # Minimum valid modbus response length: ID(1) + Func(1) + ByteCount(1) + Data(N) + CRC(2)
    if len(rx_data) < 5:
        return
        
    # Check if func code matches what was requested
    if rx_data[1] != func_code:
        return
        
    byte_count = rx_data[2]
    if len(rx_data) < 3 + byte_count + 2:
        return
        
    data_payload = rx_data[3:3+byte_count]
    num_registers = byte_count // 2
    
    # We only process read register functions (03 or 04) for now
    if func_code not in (3, 4):
        return
        
    # Parse each register
    for i in range(num_registers):
        addr = start_addr + i
        raw_val = data_payload[i*2 : i*2+2]
        int_val = int.from_bytes(raw_val, byteorder='big', signed=False)
        
        for row in st.session_state.modbus_csv_data:
            if str(row.get("Addr", "")) == str(addr):
                row["Raw Data"] = f"0x{raw_val.hex().upper()}"
                
                datatype = row.get("DataType", "UINT16").upper()
                scale_str = row.get("Scale", "1.0")
                try:
                    scale = float(scale_str)
                except ValueError:
                    scale = 1.0
                    
                val = int_val
                if "INT16" in datatype and "UINT" not in datatype:
                    val = int.from_bytes(raw_val, byteorder='big', signed=True)
                    
                # Calculate final formatted float, remove trailing zeros if integer
                final_val = val * scale
                row["Data"] = f"{final_val:g}"
                break

def _on_type_change():
    """Callback to update Start and End address when Addr Type changes."""
    sel_type = st.session_state.get("modbus_type_selector")
    if not sel_type or sel_type == "All":
        return
        
    min_addr = float('inf')
    max_addr = -1
    for row in st.session_state.modbus_csv_data:
        if row.get("Addr Type") == sel_type:
            try:
                addr = int(row.get("Addr", -1))
                if addr >= 0:
                    min_addr = min(min_addr, addr)
                    max_addr = max(max_addr, addr)
            except ValueError:
                pass
                
    if max_addr >= 0:
        fmt = st.session_state.get("modbus_addr_format", "HEX")
        if fmt == "HEX":
            st.session_state.modbus_start_hex = f"0x{min_addr:04X}"
            st.session_state.modbus_end_hex = f"0x{max_addr:04X}"
        else:
            st.session_state.modbus_start_hex = str(min_addr)
            st.session_state.modbus_end_hex = str(max_addr)


# ─── Public Entry Point ─────────────────────────────────────────────────────
def render():
    """Call this inside the Streamlit tab context to render the full UI."""
    _init_state()

    # ── Toolbar: path display + Open / Save buttons ─────────────────────────
    with st.container(border=True):
        st.markdown(
            '<p class="metric-label" style="margin:0 0 12px 0">MODBUS ADDRESS MAP</p>',
            unsafe_allow_html=True
        )
        path_col, btn_col = st.columns([0.7, 0.3])
        with path_col:
            display_path = st.session_state.modbus_csv_path or "(No file loaded)"
            st.code(display_path, language="text")
        with btn_col:
            ob_col, sb_col = st.columns(2)
            with ob_col:
                st.button("📂 Open", key="modbus_open_btn", width='stretch', on_click=_open_csv)
            with sb_col:
                st.button("💾 Save", key="modbus_save_btn", width='stretch', on_click=_save_csv)

    # ── Data Table ──────────────────────────────────────────────────────────
    data = st.session_state.modbus_csv_data
    headers = st.session_state.modbus_csv_headers

    if data and headers:
        # ── Filter / Load Controls ──
        fc_col1, fc_type, fc_fmt, fc_col2, fc_col3 = st.columns([0.15, 0.25, 0.15, 0.225, 0.225], vertical_alignment="bottom")
        with fc_col1:
            if st.button("🚀 Load Data", type="primary", width='stretch'):
                st.session_state.modbus_render_list = True
                st.session_state.modbus_applied_start = st.session_state.get("modbus_start_hex", "")
                st.session_state.modbus_applied_end = st.session_state.get("modbus_end_hex", "")
                st.session_state.modbus_applied_format = st.session_state.get("modbus_addr_format", "HEX")
                
        with fc_type:
            unique_types = []
            for row in data:
                t = row.get("Addr Type")
                if t and t not in unique_types:
                    unique_types.append(t)
            options = ["All"] + unique_types
            
            if st.session_state.get("modbus_type_selector") not in options:
                st.session_state.modbus_type_selector = "All"
                
            st.selectbox("Addr Type", options, key="modbus_type_selector", on_change=_on_type_change)

        with fc_fmt:
            addr_format = st.selectbox("Format", ["HEX", "DEC"], key="modbus_addr_format")
        with fc_col2:
            st.text_input(f"Start Addr ({addr_format})", key="modbus_start_hex", placeholder="e.g. 0x0000" if addr_format=="HEX" else "e.g. 0")
        with fc_col3:
            st.text_input(f"End Addr ({addr_format})", key="modbus_end_hex", placeholder="e.g. 0x05DC" if addr_format=="HEX" else "e.g. 1500")

        if st.session_state.modbus_render_list:
            filtered_data = data
            s_str = st.session_state.modbus_applied_start.strip()
            e_str = st.session_state.modbus_applied_end.strip()
            
            base = 16 if st.session_state.modbus_applied_format == "HEX" else 10
            
            s_val = None
            e_val = None
            try:
                if s_str: s_val = int(s_str, base)
            except ValueError: pass
            
            try:
                if e_str: e_val = int(e_str, base)
            except ValueError: pass
            
            if s_val is not None or e_val is not None:
                new_data = []
                for row in data:
                    addr_val = None
                    try:
                        addr_val = int(row.get("Addr", -1))
                    except ValueError:
                        pass
                        
                    if addr_val is not None:
                        if s_val is not None and addr_val < s_val:
                            continue
                        if e_val is not None and addr_val > e_val:
                            continue
                    new_data.append(row)
                filtered_data = new_data



            if filtered_data:
                st.markdown(_render_table(filtered_data, headers), unsafe_allow_html=True)
            else:
                st.info("No registers match the specified address range.")
    else:
        st.markdown(
            '<div style="text-align:center;padding:60px 20px;color:#94a3b8;font-size:0.95rem;">'
            '📄 Click <b>Open</b> to load a Modbus address CSV file'
            '</div>',
            unsafe_allow_html=True
        )

    # ─── Persist Widget State ───────────────────────────────────────────────────
    persist_keys = [
        "modbus_render_list", "modbus_start_hex", "modbus_end_hex", 
        "modbus_addr_format", "modbus_type_selector",
        "modbus_applied_start", "modbus_applied_end", "modbus_applied_format"
    ]
    for key in persist_keys:
        if key in st.session_state:
            st.session_state[f"persist_{key}"] = st.session_state[key]
