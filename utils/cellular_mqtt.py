"""
Cellular MQTT helper — manages serial COM connection to ATK-D40-B 4G DTU
and provides one-click MQTT provisioning via AT commands.
"""
import streamlit as st
import serial
import serial.tools.list_ports
import time

# ─── Session State Keys (prefixed with 'cell_') ─────────────────────────────
_DEFAULTS = {
    "cell_serial": None,
    "cell_logs": [],
    "cell_auto_refresh": False,
    "cell_provisioning": False,
}

def init_state():
    for k, v in _DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v

def get_com_ports():
    return [p.device for p in serial.tools.list_ports.comports()]

def _log(msg):
    t = time.localtime()
    ms = int((time.time() % 1) * 1000)
    ts = f"[{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}.{ms:03d}]"
    st.session_state.cell_logs.append(f"{ts} {msg}")
    if len(st.session_state.cell_logs) > 200:
        st.session_state.cell_logs.pop(0)

def _send_and_wait(ser, data: bytes, wait: float = 1.5, hide_tx: bool = False) -> bytes:
    ser.reset_input_buffer()
    if not hide_tx and data:
        try:
            tx_text = data.decode('utf-8', errors='replace').strip()
        except:
            tx_text = data.hex()
        if tx_text:
            _log(f"TX>> {tx_text}")

    ser.write(data)
    ser.flush()
    deadline = time.time() + wait
    buf = bytearray()
    last_t = None
    while time.time() < deadline:
        w = ser.in_waiting
        if w > 0:
            buf.extend(ser.read(w))
            last_t = time.time()
        elif last_t and (time.time() - last_t) > 0.3:
            break
        time.sleep(0.01)
    
    if not hide_tx and buf:
        try:
            rx_text = buf.decode('utf-8', errors='replace').strip()
        except:
            rx_text = buf.hex()
        if rx_text:
            for line in rx_text.splitlines():
                line = line.strip()
                if line:
                    _log(f"RX<< {line}")
    return bytes(buf)

# ─── COM Actions ─────────────────────────────────────────────────────────────
def handle_com_connect(port, baudrate):
    if not port or port == "None":
        st.toast("No valid COM port selected.", icon="⚠️")
        return
    try:
        if st.session_state.cell_serial and st.session_state.cell_serial.is_open:
            st.session_state.cell_serial.close()
        st.session_state.cell_serial = serial.Serial(port, baudrate, timeout=0.1)
        st.toast(f"Connected to {port}", icon="✅")
    except Exception as e:
        st.toast(f"COM error: {e}", icon="❌")

def handle_com_disconnect():
    if st.session_state.cell_serial and st.session_state.cell_serial.is_open:
        st.session_state.cell_serial.close()
    st.session_state.cell_serial = None
    st.session_state.cell_auto_refresh = False
    st.toast("Disconnected.", icon="🛑")

def handle_send_data(text=None):
    """Send raw text through DTU serial (transparent mode).
    After sending, waits briefly to capture any echo or response."""
    ser = st.session_state.cell_serial
    if not ser or not ser.is_open:
        st.toast("COM not connected.", icon="⚠️")
        return
    
    if text is None:
        text = st.session_state.get("cell_payload", "")
    if not text:
        return
    try:
        ser.reset_input_buffer()
        ser.write(text.encode('utf-8'))
        ser.flush()
        _log(f"TX>> {text}")

        # Wait briefly and read any echo / response from DTU
        time.sleep(0.5)
        rx_buf = bytearray()
        deadline = time.time() + 1.0
        last_t = None
        while time.time() < deadline:
            w = ser.in_waiting
            if w > 0:
                rx_buf.extend(ser.read(w))
                last_t = time.time()
            elif last_t and (time.time() - last_t) > 0.2:
                break
            time.sleep(0.01)

        if rx_buf:
            try:
                rx_text = rx_buf.decode('utf-8', errors='replace').strip()
            except:
                rx_text = rx_buf.hex()
            if rx_text:
                for line in rx_text.splitlines():
                    if line.strip():
                        _log(f"RX<< {line.strip()}")

        # Auto-enable refresh so user sees incoming messages
        st.session_state.cell_auto_refresh = True
    except Exception as e:
        st.toast(f"Send error: {e}", icon="❌")

def handle_read_serial():
    """Read any pending bytes from serial."""
    ser = st.session_state.cell_serial
    if not ser or not ser.is_open:
        return
    try:
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            try:
                text = data.decode('utf-8', errors='replace').strip()
            except:
                text = data.hex()
            if text:
                for line in text.splitlines():
                    if line.strip():
                        _log(f"RX<< {line.strip()}")
    except:
        pass

def handle_clear_logs():
    st.session_state.cell_logs.clear()

# ─── One-Click DTU Provisioning ──────────────────────────────────────────────
def handle_provision():
    """Run the full ATK-D40-B MQTT provisioning sequence."""
    ser = st.session_state.cell_serial
def _enter_at_mode(ser):
    """Enter AT command mode safely."""
    ser.reset_input_buffer()
    _log("TX>> +++")
    ser.write(b'+++')
    ser.flush()
    time.sleep(0.5)
    rx = bytearray()
    deadline = time.time() + 2.0
    while time.time() < deadline:
        if ser.in_waiting > 0:
            rx.extend(ser.read(ser.in_waiting))
        time.sleep(0.05)
    
    if rx:
        _log(f"RX<< {rx.decode('utf-8', errors='replace').strip()}")

    if b'atk' in rx.lower():
        _log("TX>> ATK")
        ser.write(b'ATK')
        ser.flush()
        time.sleep(0.5)
        if ser.in_waiting > 0:
            rx2 = ser.read(ser.in_waiting)
            if rx2:
                _log(f"RX<< {rx2.decode('utf-8', errors='replace').strip()}")
        return True
    else:
        resp = _send_and_wait(ser, b'AT\r\n', 1.0)
        return b'OK' in resp.upper()

# ─── One-Click DTU Provisioning ──────────────────────────────────────────────
def handle_provision():
    """Run the full ATK-D40-B MQTT provisioning sequence."""
    ser = st.session_state.cell_serial
    if not ser or not ser.is_open:
        st.toast("COM not connected.", icon="⚠️")
        return

    broker_ip = st.session_state.get("prov_ip", "")
    broker_port = st.session_state.get("prov_port", "")
    client_id = st.session_state.get("prov_cid", "")
    username = st.session_state.get("prov_user", "")
    password = st.session_state.get("prov_pwd", "")
    sub_topic = st.session_state.get("prov_sub", "")
    pub_topic = st.session_state.get("prov_pub", "")

    st.session_state.cell_provisioning = True

    # Step 1: Escape to AT mode
    if not _enter_at_mode(ser):
        st.session_state.cell_provisioning = False
        return

    # Step 2-7: Send configuration commands
    commands = [
        f'AT+WORK="MQTT"',
        f'AT+MQTTIP="{broker_ip}","{broker_port}"',
        f'AT+MQTTCD="{client_id}"',
        f'AT+MQTTUN="{username}"',
        f'AT+MQTTPW="{password}"',
        f'AT+MQTTSUB1="1","{sub_topic}","0"',
        f'AT+MQTTPUB1="1","{pub_topic}","0","0"'
    ]

    for cmd in commands:
        _send_and_wait(ser, (cmd + "\r\n").encode('utf-8'), 1.5)

    # Save & restart
    _send_and_wait(ser, b'AT+S\r\n', 1.0)
    _send_and_wait(ser, b'ATO\r\n', 1.0)
    st.session_state.cell_provisioning = False

# ─── Dynamic Subscription Management ─────────────────────────────────────────
def handle_dtu_update_sub(topic, qos):
    """Dynamically update DTU subscription by breaking out of transparent mode."""
    ser = st.session_state.cell_serial
    if not ser or not ser.is_open:
        st.toast("COM not connected.", icon="⚠️")
        return

    time.sleep(1.0)
    if _enter_at_mode(ser):
        cmd = f'AT+MQTTSUB1="1","{topic}","{qos}"'
        resp = _send_and_wait(ser, (cmd + "\r\n").encode('utf-8'), 1.5)
        if b'OK' in resp.upper():
            st.session_state.cell_active_sub = topic
            st.session_state.cell_active_qos = qos
        
        _send_and_wait(ser, b'ATO\r\n', 1.0)

def handle_dtu_unsubscribe():
    """Dynamically remove DTU subscription."""
    ser = st.session_state.cell_serial
    if not ser or not ser.is_open:
        st.toast("COM not connected.", icon="⚠️")
        return

    time.sleep(1.0)
    if _enter_at_mode(ser):
        # We try to disable it with state=0. The topic might still be required.
        cmd = f'AT+MQTTSUB1="0","nanopd/dtu/rx","0"'
        resp = _send_and_wait(ser, (cmd + "\r\n").encode('utf-8'), 1.5)
        if b'OK' in resp.upper():
            st.session_state.cell_active_sub = None
        
        _send_and_wait(ser, b'ATO\r\n', 1.0)
