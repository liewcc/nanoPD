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
            if k == "cell_logs":
                import os
                log_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Cellular_MQTT.log"))
                if os.path.exists(log_file):
                    try:
                        with open(log_file, "r", encoding="utf-8") as f:
                            lines = [line.strip() for line in f.readlines() if line.strip()]
                            st.session_state.cell_logs = lines[-200:]
                    except:
                        pass

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
        text = st.session_state.get("cell_payload_new") or st.session_state.get("cell_payload", "")
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
    import os
    log_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Cellular_MQTT.log"))
    try:
        if os.path.exists(log_file):
            open(log_file, "w", encoding="utf-8").close()
    except:
        pass


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

    broker_ip = st.session_state.get("prov_ip_new", "")
    broker_port = st.session_state.get("prov_port_new", "")
    client_id = st.session_state.get("prov_cid_new", "")
    username = st.session_state.get("prov_user_new", "")
    password = st.session_state.get("prov_pwd_new", "")
    sub_topic = st.session_state.get("prov_sub_new", "")
    pub_topic = st.session_state.get("prov_pub_new", "")

    # AT+WORK="MQTT" resets all SUB enable flags to 0.
    # If the user left prov_sub blank, preserve the existing HW subscription
    # from the last scan so it is re-applied during the provision sequence.
    if not sub_topic:
        existing_hw = st.session_state.get("cell_hw_subs", [])
        if existing_hw:
            sub_topic = existing_hw[0]["topic"]

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
        f'AT+MQTTPUB1="1","{pub_topic}","0","0"' if pub_topic else None,
        f'AT+MQTTSUB1="1","{sub_topic}","0"' if sub_topic else None,
    ]

    for cmd in commands:
        if cmd:  # Skip None entries
            _send_and_wait(ser, (cmd + "\r\n").encode('utf-8'), 1.5)

    # Return to transparent mode (auto-saves on these modules)
    _send_and_wait(ser, b'ATO\r\n', 1.0)
    st.session_state.cell_provisioning = False

    # Re-enter AT mode after a short settle delay to read back the real
    # hardware state. This is done AFTER ATO so AT+WORK="MQTT" has fully
    # applied before we query.
    time.sleep(1.5)
    if _enter_at_mode(ser):
        _read_hw_state_in_at_mode(ser)
        _send_and_wait(ser, b'ATO\r\n', 1.0)

# ─── Dynamic Subscription Management ─────────────────────────────────────────
def handle_dtu_update_sub(topic, qos):
    """Dynamically update DTU subscription by breaking out of transparent mode."""
    ser = st.session_state.cell_serial
    if not ser or not ser.is_open:
        st.toast("COM not connected.", icon="⚠️")
        return

    time.sleep(1.0)
    if _enter_at_mode(ser):
        # Find a free slot, default to 1 if we can't find one
        free_slot = 1
        hw_subs = st.session_state.get("cell_hw_subs", [])
        used_slots = {s["slot"] for s in hw_subs}
        for i in range(1, 5):
            if i not in used_slots:
                free_slot = i
                break

        cmd = f'AT+MQTTSUB{free_slot}="1","{topic}","{qos}"'
        resp = _send_and_wait(ser, (cmd + "\r\n").encode('utf-8'), 1.5)
        
        _read_hw_state_in_at_mode(ser)
        _send_and_wait(ser, b'ATO\r\n', 1.0)

def handle_dtu_unsubscribe():
    """Dynamically remove DTU subscription."""
    ser = st.session_state.cell_serial
    if not ser or not ser.is_open:
        st.toast("COM not connected.", icon="⚠️")
        return

    # Find which slot to unsub — try all possible widget keys
    selected = (
        st.session_state.get("cell_unsub_select_new_1")
        or st.session_state.get("cell_unsub_select_new_3")
    )
    slot = "1"
    if selected and selected.startswith("SUB"):
        # e.g., "SUB2: atk/sub2" -> "2"
        slot = selected[3:selected.find(":")]

    time.sleep(1.0)
    if _enter_at_mode(ser):
        # Disable the slot with state=0
        cmd = f'AT+MQTTSUB{slot}="0","nanopd/dtu/rx","0"'
        resp = _send_and_wait(ser, (cmd + "\r\n").encode('utf-8'), 1.5)
        
        _read_hw_state_in_at_mode(ser)
        _send_and_wait(ser, b'ATO\r\n', 1.0)


def _parse_mqtt_query_response(resp_bytes, prefix):
    """Parse a DTU query response like +MQTTSUB1:1,"topic",0 into (enable, topic, qos).
    Returns None if parsing fails or the slot is disabled."""
    try:
        text = resp_bytes.decode('utf-8', errors='replace')
    except:
        return None

    for line in text.splitlines():
        line = line.strip()
        if line.upper().startswith(prefix.upper()):
            # Extract the part after the colon, e.g. '1,"nanopd/dtu/rx",0'
            payload = line.split(":", 1)[1].strip()
            # Remove surrounding quotes and split by comma
            parts = []
            current = ""
            in_quotes = False
            for ch in payload:
                if ch == '"':
                    in_quotes = not in_quotes
                elif ch == ',' and not in_quotes:
                    parts.append(current.strip().strip('"'))
                    current = ""
                    continue
                current += ch
            parts.append(current.strip().strip('"'))

            if len(parts) >= 3:
                enable = parts[0]
                topic = parts[1]
                qos = parts[2]
                try:
                    return (int(enable), topic, int(qos))
                except ValueError:
                    return None
    return None


def _read_hw_state_in_at_mode(ser):
    """Internal helper to query DTU subscriptions and update session state.
    Assumes DTU is ALREADY in AT mode."""
    active_subs = []
    test_resp = _send_and_wait(ser, b"AT+MQTTSUB1\r\n", 1.5)
    query_suffix = ""
    if b"ERROR" in test_resp.upper():
        test_resp = _send_and_wait(ser, b"AT+MQTTSUB1?\r\n", 1.5)
        if b"ERROR" not in test_resp.upper():
            query_suffix = "?"
    
    for i in range(1, 5):
        if i == 1 and query_suffix == "" and b"ERROR" not in test_resp.upper():
            resp = test_resp
        else:
            cmd = f"AT+MQTTSUB{i}{query_suffix}\r\n"
            resp = _send_and_wait(ser, cmd.encode('utf-8'), 1.5)
            
        parsed = _parse_mqtt_query_response(resp, f"+MQTTSUB{i}")
        if parsed:
            enable, topic, qos = parsed
            if enable == 1 and topic:
                active_subs.append({"slot": i, "topic": topic, "qos": qos})

    resp_pub = _send_and_wait(ser, f"AT+MQTTPUB1{query_suffix}\r\n".encode('utf-8'), 1.5)
    if b"ERROR" in resp_pub.upper() and query_suffix == "":
        resp_pub = _send_and_wait(ser, b"AT+MQTTPUB1?\r\n", 1.5)
        
    parsed_pub = _parse_mqtt_query_response(resp_pub, "+MQTTPUB1")
    hw_pub = None
    if parsed_pub:
        enable, topic, qos = parsed_pub
        if enable == 1 and topic:
            hw_pub = {"topic": topic, "qos": qos}

    st.session_state.cell_hw_subs = active_subs
    st.session_state.cell_hw_pub = hw_pub

    # Also update the primary active_sub for backward compatibility
    if active_subs:
        st.session_state.cell_active_sub = active_subs[0]["topic"]
        st.session_state.cell_active_qos = active_subs[0]["qos"]
    else:
        st.session_state.cell_active_sub = None
        st.session_state.cell_active_qos = 0

    count = len(active_subs)
    pub_info = f", PUB: {hw_pub['topic']}" if hw_pub else ""
    st.toast(f"HW synced: {count} active subscription(s){pub_info}", icon="✅")

# ─── Hardware State Sync ──────────────────────────────────────────────────────
def handle_sync_hw_state():
    """Manual sync triggered from UI."""
    ser = st.session_state.cell_serial
    if not ser or not ser.is_open:
        st.toast("COM not connected.", icon="⚠️")
        return

    time.sleep(1.0)
    if not _enter_at_mode(ser):
        st.toast("Failed to enter AT mode.", icon="❌")
        return

    _read_hw_state_in_at_mode(ser)
    _send_and_wait(ser, b'ATO\r\n', 1.0)
