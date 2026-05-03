import streamlit as st
import serial
import serial.tools.list_ports
import time
import json
import os
import tkinter as tk
from tkinter import filedialog
from utils.style_utils import apply_global_css
from utils.config_utils import load_ui_config

# ─── Paths ──────────────────────────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GLOBAL_CONFIG_PATH = os.path.join(_BASE_DIR, "config.json")
_RS485_CONFIG_DIR = os.path.join(_BASE_DIR, "RS485_config_file")
_DEFAULT_CONFIG_PATH = os.path.join(_RS485_CONFIG_DIR, "default.json")

# ─── Session State Initialization ───────────────────────────────────────────
if "ui_cfg" not in st.session_state:
    st.session_state.ui_cfg = load_ui_config()

if 'rs485_serial' not in st.session_state:
    st.session_state.rs485_serial = None
if 'rs485_output' not in st.session_state or isinstance(st.session_state.rs485_output, str):
    st.session_state.rs485_output = []
if 'rs485_auto_read' not in st.session_state:
    st.session_state.rs485_auto_read = False
if 'rs485_last_send_time' not in st.session_state:
    st.session_state.rs485_last_send_time = 0.0  # epoch: never sent

# ─── Config File State ──────────────────────────────────────────────────────
def _read_global_config():
    try:
        with open(_GLOBAL_CONFIG_PATH, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def _write_global_config(data: dict):
    try:
        with open(_GLOBAL_CONFIG_PATH, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass

def _load_last_config_path():
    cfg = _read_global_config()
    last = cfg.get("rs485_last_config", _DEFAULT_CONFIG_PATH)
    return last if os.path.exists(last) else _DEFAULT_CONFIG_PATH

if 'current_rs485_config_file' not in st.session_state:
    st.session_state.current_rs485_config_file = _load_last_config_path()

# ─── Config Load/Save functions ─────────────────────────────────────────────
CFG_KEYS = {
    "com_port": "cfg_com_port",
    "protocol_mode": "cfg_protocol_mode",
    "baudrate": "cfg_baudrate",
    "data_bits": "cfg_data_bits",
    "parity": "cfg_parity",
    "stop_bits": "cfg_stop_bits",
    "func_code": "cfg_func_code",
    "device_id_hex": "device_id_hex_input",
    "device_id_dec": "device_id_dec_input",
    "start_addr_hex": "start_addr_hex_input",
    "start_addr_dec": "start_addr_dec_input",
    "quantity": "cfg_quantity",
    "timeout": "cfg_timeout",
    "input_format": "cfg_input_format",
    "line_ending": "cfg_line_ending",
    "payload": "cfg_payload",
    "log_format": "cfg_log_format",
}

def _apply_config(data: dict):
    """Write config values into session_state keys."""
    for cfg_key, ss_key in CFG_KEYS.items():
        if cfg_key in data:
            st.session_state[ss_key] = data[cfg_key]
            st.session_state[f"persist_{ss_key}"] = data[cfg_key]

def load_rs485_config():
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', True)
    path = filedialog.askopenfilename(
        title="Load RS485 Configuration",
        initialdir=_RS485_CONFIG_DIR,
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    root.destroy()
    if path:
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            _apply_config(data)
            st.session_state.current_rs485_config_file = path
            gcfg = _read_global_config()
            gcfg["rs485_last_config"] = path
            _write_global_config(gcfg)
            st.toast(f"Loaded: {os.path.basename(path)}", icon="✅")
        except Exception as e:
            st.toast(f"Load failed: {e}", icon="❌")

def save_rs485_config():
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', True)
    path = filedialog.asksaveasfilename(
        title="Save RS485 Configuration",
        initialdir=_RS485_CONFIG_DIR,
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    root.destroy()
    if path:
        try:
            data = {}
            for cfg_key, ss_key in CFG_KEYS.items():
                val = st.session_state.get(ss_key)
                if val is None:
                    val = st.session_state.get(f"persist_{ss_key}")
                data[cfg_key] = val
            with open(path, 'w') as f:
                json.dump(data, f, indent=4)
            st.session_state.current_rs485_config_file = path
            gcfg = _read_global_config()
            gcfg["rs485_last_config"] = path
            _write_global_config(gcfg)
            st.toast(f"Saved: {os.path.basename(path)}", icon="✅")
        except Exception as e:
            st.toast(f"Save failed: {e}", icon="❌")

# ─── Apply saved config on first load ───────────────────────────────────────
if 'rs485_config_loaded' not in st.session_state:
    try:
        with open(st.session_state.current_rs485_config_file, 'r') as f:
            _apply_config(json.load(f))
    except Exception:
        pass
    st.session_state.rs485_config_loaded = True

if 'device_id_hex_input' not in st.session_state:
    st.session_state.device_id_hex_input = st.session_state.get("persist_device_id_hex_input", "0x01")
if 'device_id_dec_input' not in st.session_state:
    st.session_state.device_id_dec_input = st.session_state.get("persist_device_id_dec_input", "1")
if 'start_addr_hex_input' not in st.session_state:
    st.session_state.start_addr_hex_input = st.session_state.get("persist_start_addr_hex_input", "0x0000")
if 'start_addr_dec_input' not in st.session_state:
    st.session_state.start_addr_dec_input = st.session_state.get("persist_start_addr_dec_input", "0")

# Default values for cfg_ keys (only set if not already loaded from config)
if 'cfg_com_port' not in st.session_state:
    st.session_state.cfg_com_port = st.session_state.get("persist_cfg_com_port", "")
if 'cfg_protocol_mode' not in st.session_state:
    st.session_state.cfg_protocol_mode = st.session_state.get("persist_cfg_protocol_mode", "Modbus RTU")
if 'cfg_baudrate' not in st.session_state:
    st.session_state.cfg_baudrate = st.session_state.get("persist_cfg_baudrate", 115200)
if 'cfg_data_bits' not in st.session_state:
    st.session_state.cfg_data_bits = st.session_state.get("persist_cfg_data_bits", 8)
if 'cfg_parity' not in st.session_state:
    st.session_state.cfg_parity = st.session_state.get("persist_cfg_parity", "None")
if 'cfg_stop_bits' not in st.session_state:
    st.session_state.cfg_stop_bits = st.session_state.get("persist_cfg_stop_bits", 1)
if 'cfg_func_code' not in st.session_state:
    st.session_state.cfg_func_code = st.session_state.get("persist_cfg_func_code", "03 (Read Holding Registers)")
if 'cfg_quantity' not in st.session_state:
    st.session_state.cfg_quantity = st.session_state.get("persist_cfg_quantity", 1)
if 'cfg_timeout' not in st.session_state:
    st.session_state.cfg_timeout = st.session_state.get("persist_cfg_timeout", 100)
if 'cfg_input_format' not in st.session_state:
    st.session_state.cfg_input_format = st.session_state.get("persist_cfg_input_format", "HEX")
if 'cfg_line_ending' not in st.session_state:
    st.session_state.cfg_line_ending = st.session_state.get("persist_cfg_line_ending", "\\r\\n (CRLF)")
if 'cfg_payload' not in st.session_state:
    st.session_state.cfg_payload = st.session_state.get("persist_cfg_payload", "")
if 'cfg_log_format' not in st.session_state:
    st.session_state.cfg_log_format = st.session_state.get("persist_cfg_log_format", "HEX")

def update_device_id_from_hex():
    val = st.session_state.device_id_hex_input.strip()
    try:
        if val:
            # Handle both "0x01" and "01" formats
            clean_val = val[2:] if val.lower().startswith('0x') else val
            dec_val = int(clean_val, 16)
            st.session_state.device_id_dec_input = str(dec_val)
            # Reformat to ensure uniform 0x01 styling
            st.session_state.device_id_hex_input = f"0x{dec_val:02X}"
    except ValueError:
        pass

def update_device_id_from_dec():
    val = st.session_state.device_id_dec_input.strip()
    try:
        if val:
            st.session_state.device_id_hex_input = f"0x{int(val):02X}"
    except ValueError:
        pass

def update_start_addr_from_hex():
    val = st.session_state.start_addr_hex_input.strip()
    try:
        if val:
            clean_val = val[2:] if val.lower().startswith('0x') else val
            dec_val = int(clean_val, 16)
            st.session_state.start_addr_dec_input = str(dec_val)
            st.session_state.start_addr_hex_input = f"0x{dec_val:04X}"
    except ValueError:
        pass

def update_start_addr_from_dec():
    val = st.session_state.start_addr_dec_input.strip()
    try:
        if val:
            st.session_state.start_addr_hex_input = f"0x{int(val):04X}"
    except ValueError:
        pass

# ─── Helper Functions ───────────────────────────────────────────────────────
def get_com_ports():
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

def handle_connect(port, baudrate, data_bits, parity, stop_bits):
    if port == "None" or not port:
        st.toast("No valid COM port selected.", icon="⚠️")
        return
    try:
        if st.session_state.rs485_serial is not None and st.session_state.rs485_serial.is_open:
            st.session_state.rs485_serial.close()
            
        bytesize_map = {5: serial.FIVEBITS, 6: serial.SIXBITS, 7: serial.SEVENBITS, 8: serial.EIGHTBITS}
        parity_map = {"None": serial.PARITY_NONE, "Even": serial.PARITY_EVEN, "Odd": serial.PARITY_ODD, "Mark": serial.PARITY_MARK, "Space": serial.PARITY_SPACE}
        stopbits_map = {1: serial.STOPBITS_ONE, 1.5: serial.STOPBITS_ONE_POINT_FIVE, 2: serial.STOPBITS_TWO}
        
        st.session_state.rs485_serial = serial.Serial(
            port=port, 
            baudrate=baudrate, 
            bytesize=bytesize_map[data_bits], 
            parity=parity_map[parity], 
            stopbits=stopbits_map[stop_bits], 
            timeout=0.1
        )
        st.toast(f"Connected to {port} ({baudrate}, {data_bits}{parity[0]}, {stop_bits})", icon="✅")
    except Exception as e:
        st.toast(f"Error connecting: {e}", icon="❌")

def handle_disconnect():
    if st.session_state.rs485_serial is not None and st.session_state.rs485_serial.is_open:
        st.session_state.rs485_serial.close()
    st.session_state.rs485_serial = None
    st.session_state.rs485_auto_read = False
    st.toast("Disconnected.", icon="🛑")

def handle_send(data, format_type):
    if st.session_state.rs485_serial is not None and st.session_state.rs485_serial.is_open:
        try:
            if format_type == "HEX":
                data_bytes = bytes.fromhex(data.replace(" ", "").replace("\n", ""))
            else:
                data_bytes = data.encode('utf-8')

            # Clear stale RX data, then send
            st.session_state.rs485_serial.reset_input_buffer()
            st.session_state.rs485_serial.write(data_bytes)
            st.session_state.rs485_serial.flush()            # ensure all TX bytes are physically sent
            st.session_state.rs485_output.append({"time": time.time(), "dir": "TX", "data": data_bytes})

            # --- Drain-until-quiet RX strategy ---
            # Silence threshold differs by protocol:
            #   AT Command: 200ms — devices like ATK-D40-B may take 100-200ms to respond after echo
            #   Modbus RTU:  50ms — response follows echo almost immediately
            is_at_mode = (st.session_state.get("cfg_protocol_mode") == "AT Command")
            silence_threshold = 0.2 if is_at_mode else 0.05
            timeout_s = max(int(st.session_state.cfg_timeout) / 1000.0, 1.5 if is_at_mode else 0.5)

            deadline = time.time() + timeout_s
            rx_buffer = bytearray()
            last_byte_time = None

            while time.time() < deadline:
                waiting = st.session_state.rs485_serial.in_waiting
                if waiting > 0:
                    chunk = st.session_state.rs485_serial.read(waiting)
                    rx_buffer.extend(chunk)
                    last_byte_time = time.time()
                elif last_byte_time is not None and (time.time() - last_byte_time) > silence_threshold:
                    break  # silence_threshold ms of quiet after last byte = frame complete
                time.sleep(0.005)

            if rx_buffer:
                st.session_state.rs485_output.append({"time": time.time(), "dir": "RX", "data": bytes(rx_buffer)})

            # Record successful send time for cooldown enforcement
            st.session_state.rs485_last_send_time = time.time()

        except ValueError:
            st.toast("Invalid HEX format.", icon="❌")
        except Exception as e:
            st.toast(f"Error sending/receiving data: {e}", icon="❌")
    else:
        st.toast("Serial port is not connected.", icon="⚠️")

def calculate_crc16(data: bytes) -> bytes:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc.to_bytes(2, byteorder='little')

def read_data():
    if st.session_state.rs485_serial is not None and st.session_state.rs485_serial.is_open:
        try:
            st.session_state.rs485_serial.reset_input_buffer()
            
            # Active Polling
            if st.session_state.cfg_protocol_mode == "Modbus RTU":
                dev_id = int(st.session_state.device_id_dec_input)
                func_code = int(st.session_state.cfg_func_code.split(" ")[0], 16)
                start_addr = int(st.session_state.start_addr_dec_input)
                quantity = int(st.session_state.cfg_quantity)
                
                frame = bytearray()
                frame.append(dev_id)
                frame.append(func_code)
                frame.append((start_addr >> 8) & 0xFF)
                frame.append(start_addr & 0xFF)
                frame.append((quantity >> 8) & 0xFF)
                frame.append(quantity & 0xFF)
                
                frame.extend(calculate_crc16(frame))
                st.session_state.rs485_serial.write(frame)
                st.session_state.rs485_output.append({"time": time.time(), "dir": "TX", "data": bytes(frame)})
                
            elif st.session_state.cfg_protocol_mode == "AT Command":
                input_text = st.session_state.cfg_payload
                line_ending = st.session_state.cfg_line_ending
                le_map = {"\\r\\n (CRLF)": "\r\n", "\\r (CR)": "\r", "\\n (LF)": "\n", "None": ""}
                
                if input_text:
                    final_payload = input_text + le_map.get(line_ending, "")
                    data_bytes = final_payload.encode('utf-8')
                    st.session_state.rs485_serial.write(data_bytes)
                    st.session_state.rs485_output.append({"time": time.time(), "dir": "TX", "data": data_bytes})

            # --- Drain-until-quiet RX strategy ---
            timeout_s = int(st.session_state.cfg_timeout) / 1000.0
            deadline = time.time() + timeout_s
            rx_buffer = bytearray()
            last_byte_time = None
            sent_bytes = locals().get('data_bytes', b'') if st.session_state.cfg_protocol_mode == "AT Command" else b''

            while time.time() < deadline:
                waiting = st.session_state.rs485_serial.in_waiting
                if waiting > 0:
                    chunk = st.session_state.rs485_serial.read(waiting)
                    rx_buffer.extend(chunk)
                    last_byte_time = time.time()
                elif last_byte_time is not None and (time.time() - last_byte_time) > 0.02:
                    break  # 20ms silence after last byte = frame complete
                time.sleep(0.005)

            if rx_buffer:
                payload = rx_buffer
                # Strip TX echo for AT mode
                if st.session_state.cfg_protocol_mode == "AT Command" and sent_bytes and rx_buffer[:len(sent_bytes)] == sent_bytes:
                    payload = rx_buffer[len(sent_bytes):]
                if payload:
                    st.session_state.rs485_output.append({"time": time.time(), "dir": "RX", "data": bytes(payload)})
                    return True
        except Exception as e:
            st.toast(f"Error reading data: {e}", icon="❌")
            st.session_state.rs485_auto_read = False
    return False

def handle_escape_mode():
    """ATK-D40-B escape sequence: 1s silence → +++ (no CRLF) → wait for 'a' → reply 'a'."""
    ser = st.session_state.rs485_serial
    if ser is None or not ser.is_open:
        st.toast("Serial port is not connected.", icon="⚠️")
        return
    try:
        # Step 1: enforce 1s silence before +++
        st.session_state.rs485_output.append({"time": time.time(), "dir": "TX", "data": b"[Escape: waiting 1s silence...]"})
        time.sleep(1.0)

        # Step 2: send +++ with NO line ending
        ser.reset_input_buffer()
        escape_bytes = b'+++'
        ser.write(escape_bytes)
        ser.flush()
        st.session_state.rs485_output.append({"time": time.time(), "dir": "TX", "data": escape_bytes})

        # Step 3: wait up to 2s for device to reply
        deadline = time.time() + 2.0
        rx_buf = bytearray()
        last_t = None
        while time.time() < deadline:
            w = ser.in_waiting
            if w > 0:
                rx_buf.extend(ser.read(w))
                last_t = time.time()
            elif last_t and (time.time() - last_t) > 0.3:
                break
            time.sleep(0.01)

        if rx_buf:
            st.session_state.rs485_output.append({"time": time.time(), "dir": "RX", "data": bytes(rx_buf)})

        # Step 4: ATK proprietary handshake confirmation
        if b'atk' in rx_buf.lower():
            time.sleep(0.1)
            ser.write(b'ATK')  # Must be uppercase, no newline
            ser.flush()
            st.session_state.rs485_output.append({"time": time.time(), "dir": "TX", "data": b"ATK"})
            
            # Read confirmation (+OK)
            time.sleep(0.3)
            if ser.in_waiting > 0:
                ok_buf = ser.read(ser.in_waiting)
                st.session_state.rs485_output.append({"time": time.time(), "dir": "RX", "data": ok_buf})
                
            st.session_state.rs485_output.append({"time": time.time(), "dir": "RX", "data": b"[Escape OK - AT Command Mode entered]"})
            st.toast("ATK-D40-B entered AT Command Mode!", icon="✅")
        else:
            st.session_state.rs485_output.append({"time": time.time(), "dir": "RX", "data": b"[Escape sequence sent, but no 'atk' handshake found]"})
            st.toast("Escape sequence sent!", icon="✅")

        st.session_state.rs485_last_send_time = time.time()

    except Exception as e:
        st.toast(f"Escape error: {e}", icon="❌")

def handle_clear():
    st.session_state.rs485_output = []

# ─── Apply Global CSS ───────────────────────────────────────────────────────
apply_global_css(
    title_size=st.session_state.ui_cfg.get("title_size", "1.5rem"),
    label_size=st.session_state.ui_cfg.get("label_size", "0.875rem"),
    info_size=st.session_state.ui_cfg.get("info_size", "1.0rem"),
    code_font=st.session_state.ui_cfg.get("code_font", "Consolas, Monaco, monospace"),
    code_size=st.session_state.ui_cfg.get("code_size", "14px"),
    code_lh=st.session_state.ui_cfg.get("code_lh", "1.3"),
    is_mcu_page=True
)

code_font = st.session_state.ui_cfg.get("code_font", "Consolas, Monaco, monospace")
code_size = st.session_state.ui_cfg.get("code_size", "14px")
code_lh = st.session_state.ui_cfg.get("code_lh", "1.3")

st.markdown(f"""
    <style>
        .repl-output-block pre code,
        div[data-testid="stTextArea"] textarea {{
            font-family: {code_font} !important;
            font-size: {code_size} !important;
            line-height: {code_lh} !important;
        }}

        /* ─── VIEWPORT BOTTOM PADDING ─── */
        section[data-testid="stMain"] > div {{
            padding-bottom: 20px !important;
        }}
        div[data-testid="block-container"] {{
            padding-bottom: 20px !important;
        }}

        /* Strip column wrapper spacing */
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
            padding-bottom: 0 !important;
            margin-bottom: 0 !important;
        }}

        /* Hide unwanted vertical scrollbars on the main fixed-height containers */
        div[data-testid="stVerticalBlock"]:has(.layout-coding-marker),
        div[data-testid="stVerticalBlock"]:has(.layout-mcu-marker) {{
            overflow-y: hidden !important;
            scrollbar-width: none !important;
        }}
        div[data-testid="stVerticalBlock"]:has(.layout-coding-marker)::-webkit-scrollbar,
        div[data-testid="stVerticalBlock"]:has(.layout-mcu-marker)::-webkit-scrollbar {{
            display: none !important;
            width: 0 !important;
        }}

        /* OUTPUT LOGS textarea - constrained but not full-screen */
        div[data-testid="stVerticalBlock"]:has(.layout-mcu-marker) div[data-testid="stTextArea"] textarea {{
            height: 430px !important;
            resize: none !important;
        }}
    </style>
""", unsafe_allow_html=True)


is_connected = st.session_state.rs485_serial is not None and st.session_state.rs485_serial.is_open

# ─── MAIN LAYOUT ────────────────────────────────────────────────────────────
col_left, col_right = st.columns([1, 1])

with col_left:
    with st.container(border=True):
        st.markdown('<p class="metric-label" style="margin:0 0 12px 0">COM PORT CONFIGURATION</p>', unsafe_allow_html=True)
        available_ports = get_com_ports()
        if not available_ports:
            available_ports = ["None"]
            
        if is_connected and hasattr(st.session_state.rs485_serial, 'port'):
            active_port = st.session_state.rs485_serial.port
            if active_port and active_port not in available_ports:
                available_ports.append(active_port)
            st.session_state.cfg_com_port = active_port

        saved_port = st.session_state.get("cfg_com_port", "")
        if saved_port and saved_port not in available_ports:
            available_ports.append(saved_port)
            
        selected_port = st.selectbox("COM Port", available_ports, key="cfg_com_port", disabled=is_connected, label_visibility="collapsed")

    # Configuration File Manager
    with st.container(border=True):
        st.markdown('<p class="metric-label" style="margin:0 0 12px 0">CONFIGURATION FILE</p>', unsafe_allow_html=True)
        fc_left, fc_right = st.columns([0.7, 0.3])
        with fc_left:
            st.code(st.session_state.current_rs485_config_file, language="text")
        with fc_right:
            lb_col, sb_col = st.columns(2)
            with lb_col:
                st.button("📂 Load", use_container_width=True, on_click=load_rs485_config)
            with sb_col:
                st.button("💾 Save", use_container_width=True, on_click=save_rs485_config)

    # RS485 Parameters & Connection Controls
    with st.container(border=True):
        mode_col, title_col = st.columns([0.6, 0.4])
        with mode_col:
            protocol_mode = st.radio("Protocol Mode", ["Modbus RTU", "AT Command"], key="cfg_protocol_mode", horizontal=True, label_visibility="collapsed")
        with title_col:
            st.markdown('<p class="metric-label" style="margin:4px 0 12px 0; text-align:right;">PROTOCOL CONFIGURATION</p>', unsafe_allow_html=True)
            
        baud_col, db_col, par_col, sb_col = st.columns(4)
        with baud_col:
            st.markdown('<p class="metric-label" style="margin:4px 0 0 0">BAUD RATE</p>', unsafe_allow_html=True)
            baudrate = st.selectbox("Baud Rate", [9600, 14400, 19200, 38400, 57600, 115200, 128000, 256000, 921600], key="cfg_baudrate", disabled=is_connected, label_visibility="collapsed")
        with db_col:
            st.markdown('<p class="metric-label" style="margin:4px 0 0 0">DATA BITS</p>', unsafe_allow_html=True)
            data_bits = st.selectbox("Data Bits", [5, 6, 7, 8], key="cfg_data_bits", disabled=is_connected, label_visibility="collapsed")
        with par_col:
            st.markdown('<p class="metric-label" style="margin:4px 0 0 0">PARITY</p>', unsafe_allow_html=True)
            parity = st.selectbox("Parity", ["None", "Even", "Odd", "Mark", "Space"], key="cfg_parity", disabled=is_connected, label_visibility="collapsed")
        with sb_col:
            st.markdown('<p class="metric-label" style="margin:4px 0 0 0">STOP BITS</p>', unsafe_allow_html=True)
            stop_bits = st.selectbox("Stop Bits", [1, 1.5, 2], key="cfg_stop_bits", disabled=is_connected, label_visibility="collapsed")

        if protocol_mode == "Modbus RTU":
            rs_col1, rs_col2 = st.columns(2)
            with rs_col1:
                st.markdown('<p class="metric-label" style="margin:4px 0 0 0">DEVICE ID (HEX | DEC)</p>', unsafe_allow_html=True)
                id_hex_col, id_dec_col = st.columns(2)
                with id_hex_col:
                    device_id_hex = st.text_input("Device ID HEX", key="device_id_hex_input", on_change=update_device_id_from_hex, label_visibility="collapsed")
                with id_dec_col:
                    device_id_dec = st.text_input("Device ID DEC", key="device_id_dec_input", on_change=update_device_id_from_dec, label_visibility="collapsed")
            with rs_col2:
                st.markdown('<p class="metric-label" style="margin:4px 0 0 0">FUNCTION (HEX)</p>', unsafe_allow_html=True)
                modbus_funcs = [
                    "01 (Read Coils)",
                    "02 (Read Discrete Inputs)",
                    "03 (Read Holding Registers)",
                    "04 (Read Input Registers)",
                    "05 (Write Single Coil)",
                    "06 (Write Single Register)",
                    "0F (Write Multiple Coils)",
                    "10 (Write Multiple Registers)"
                ]
                func_code_selection = st.selectbox("Function Code", modbus_funcs, key="cfg_func_code", label_visibility="collapsed")
                func_code = (func_code_selection or "03 (Read Holding Registers)").split(" ")[0]

            r3_col1, r3_col2, r3_col3 = st.columns(3)
            with r3_col1:
                st.markdown('<p class="metric-label" style="margin:4px 0 0 0">START ADDR (HEX | DEC)</p>', unsafe_allow_html=True)
                sa_hex_col, sa_dec_col = st.columns(2)
                with sa_hex_col:
                    start_addr_hex = st.text_input("Start Addr HEX", key="start_addr_hex_input", on_change=update_start_addr_from_hex, label_visibility="collapsed")
                with sa_dec_col:
                    start_addr_dec = st.text_input("Start Addr DEC", key="start_addr_dec_input", on_change=update_start_addr_from_dec, label_visibility="collapsed")
            with r3_col2:
                st.markdown('<p class="metric-label" style="margin:4px 0 0 0">QUANTITY (DEC)</p>', unsafe_allow_html=True)
                quantity = st.number_input("Quantity", min_value=1, max_value=125, step=1, key="cfg_quantity", label_visibility="collapsed")
            with r3_col3:
                st.markdown('<p class="metric-label" style="margin:4px 0 0 0">TIMEOUT (MS)</p>', unsafe_allow_html=True)
                rs_timeout = st.number_input("Timeout", min_value=10, max_value=5000, step=10, key="cfg_timeout", label_visibility="collapsed")
        else:
            at_col1, at_col2, at_col3 = st.columns(3)
            with at_col1:
                st.markdown('<p class="metric-label" style="margin:4px 0 0 0">TIMEOUT (MS)</p>', unsafe_allow_html=True)
                rs_timeout = st.number_input("Timeout", min_value=10, max_value=5000, step=10, key="cfg_timeout", label_visibility="collapsed")

        ab1, ab2, ab3 = st.columns(3)
        with ab1:
            if not is_connected:
                st.button("🔌 Connect", width="stretch", type="primary", on_click=handle_connect, args=(selected_port, baudrate, data_bits, parity, stop_bits))
            else:
                st.button("🛑 Disconnect", width="stretch", type="secondary", on_click=handle_disconnect)
        with ab2:
            st.button("📥 Read", width="stretch", disabled=not is_connected, on_click=read_data)
        with ab3:
            if st.button("🔁 Auto", width="stretch", disabled=not is_connected, type="primary" if st.session_state.rs485_auto_read else "secondary"):
                st.session_state.rs485_auto_read = not st.session_state.rs485_auto_read
                st.rerun()


with col_right:
    # Output container
    with st.container(border=True):
        st.markdown('<div class="layout-mcu-marker" style="display:none;"></div>', unsafe_allow_html=True)
        title_col, radio_col, btn_col = st.columns([0.45, 0.35, 0.2])
        with title_col:
            st.markdown('<p class="metric-label" style="margin:12px 0 12px 0">OUTPUT LOGS</p>', unsafe_allow_html=True)
        with radio_col:
            st.markdown('<div style="margin-top:4px;"></div>', unsafe_allow_html=True)
            log_format = st.radio("Log Format", ["HEX", "ASCII"], horizontal=True, label_visibility="collapsed", key="cfg_log_format")
        with btn_col:
            st.button("🗑️ Clear", on_click=handle_clear, use_container_width=True)
        
        # Display logs
        output_placeholder = st.empty()
        display_lines = []
        for log in st.session_state.rs485_output[-42:]:
            direction = log.get("dir", "??")
            raw_data = log.get("data", b"")
            t = log.get("time", 0.0)
            
            # Format time as HH:MM:SS.mmm
            t_str = ""
            if t > 0:
                dt = time.localtime(t)
                ms = int((t - int(t)) * 1000)
                t_str = f"[{dt.tm_hour:02d}:{dt.tm_min:02d}:{dt.tm_sec:02d}.{ms:03d}] "

            if log_format == "HEX":
                formatted = raw_data.hex(' ').upper()
            else:
                formatted = raw_data.decode('utf-8', errors='replace').replace('\r', '\\r').replace('\n', '\\n')
                
            prefix = ">>" if direction == "TX" else "<<"
            display_lines.append(f"{t_str}{prefix} {direction}: {formatted}")
            
        if not display_lines:
            display_lines = ["(No data received)"]
        output_placeholder.text_area(
            "RS485 Logs",
            value="\n".join(display_lines),
            height=430,
            label_visibility="collapsed",
            disabled=False
        )

    # DATA INPUT container (right-bottom)
    with st.container(border=True):
        st.markdown(
            '<div class="layout-coding-marker" style="display:none;"></div>'
            '<p class="metric-label" style="margin:0 0 12px 0">DATA INPUT</p>',
            unsafe_allow_html=True
        )
        if protocol_mode == "Modbus RTU":
            input_format = st.radio("Format", ["HEX", "ASCII"], key="cfg_input_format", horizontal=True, label_visibility="collapsed")
            input_text = st.text_input(
                "Payload",
                key="cfg_payload",
                label_visibility="collapsed",
                placeholder="Enter payload here...\ne.g. 01 03 00 00 00 02 C4 0B" if input_format == "HEX" else "Hello RS485"
            )
            if st.button("📤 Send Data", width="stretch", type="primary", disabled=not is_connected):
                if input_text:
                    handle_send(input_text, input_format)
                    st.rerun()
        else:
            fmt_col, le_col = st.columns(2)
            with fmt_col:
                st.markdown('<p class="metric-label" style="margin:4px 0 0 0">FORMAT</p>', unsafe_allow_html=True)
                input_format = st.selectbox("Format", ["ASCII"], index=0, disabled=True, label_visibility="collapsed")
            with le_col:
                st.markdown('<p class="metric-label" style="margin:4px 0 0 0">LINE ENDING</p>', unsafe_allow_html=True)
                line_ending = st.selectbox("Line Ending", ["\\r\\n (CRLF)", "\\r (CR)", "\\n (LF)", "None"], key="cfg_line_ending", label_visibility="collapsed")
            input_text = st.text_input(
                "Payload",
                key="cfg_payload",
                label_visibility="collapsed",
                placeholder="AT+RST"
            )
            send_col, esc_col = st.columns([0.6, 0.4])
            with send_col:
                if st.button("📤 Send AT Command", width="stretch", type="primary", disabled=not is_connected):
                    _AT_COOLDOWN = 0.5  # ATK-D40-B requires >500ms between commands
                    elapsed = time.time() - st.session_state.rs485_last_send_time
                    if elapsed < _AT_COOLDOWN:
                        remaining_ms = int((_AT_COOLDOWN - elapsed) * 1000)
                        st.toast(f"⏳ Please wait {remaining_ms}ms before sending next command (ATK-D40-B requirement)", icon="⚠️")
                    else:
                        le_map = {"\\r\\n (CRLF)": "\r\n", "\\r (CR)": "\r", "\\n (LF)": "\n", "None": ""}
                        final_payload = input_text + le_map.get(line_ending, "")
                        if final_payload:
                            handle_send(final_payload, "ASCII")
                            st.rerun()
            with esc_col:
                if st.button("⎋ Escape Mode", width="stretch", type="secondary", disabled=not is_connected,
                             help="ATK-D40-B: 1s silence → +++ → wait 'a' → reply 'a' to enter AT Command Mode"):
                    handle_escape_mode()
                    st.rerun()
        output_placeholder.text_area(
            "RS485 Logs",
            value="\n".join(display_lines),
            height=650,
            label_visibility="collapsed",
            disabled=False
        )


# ─── Auto-Read Loop ─────────────────────────────────────────────────────────
if st.session_state.rs485_auto_read and is_connected:
    # Modest delay to not overload the UI loop, but responsive enough
    time.sleep(0.2)
    if read_data():
        st.rerun()
    else:
        # Rerun to keep polling
        st.rerun()

# ─── PERSIST WIDGET STATE ───────────────────────────────────────────────────
for ss_key in CFG_KEYS.values():
    if ss_key in st.session_state:
        st.session_state[f"persist_{ss_key}"] = st.session_state[ss_key]

# ─── AUTO-SCROLL SCRIPT ─────────────────────────────────────────────────────
if st.session_state.rs485_output:
    st.html(
        f"""
        <!-- Scroll: {{time.time()}} -->
        <script>
        function scrollToBottom() {{
            var parentDoc = window.parent && window.parent.document ? window.parent.document : document;
            var markers = parentDoc.querySelectorAll('.layout-mcu-marker');
            if (markers.length > 0) {{
                var block = markers[0].closest('[data-testid="stVerticalBlock"]');
                if (block) {{
                    var ta = block.querySelector('textarea');
                    if (ta) {{
                        ta.scrollTop = ta.scrollHeight;
                    }}
                }}
            }}
        }}
        var scrollInterval = setInterval(scrollToBottom, 50);
        setTimeout(function() {{ clearInterval(scrollInterval); }}, 1500);
        </script>
        """,
        unsafe_allow_javascript=True
    )
