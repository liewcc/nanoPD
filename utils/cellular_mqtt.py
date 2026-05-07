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
    "cell_modbus_id_dec": "1",
    "cell_modbus_id_hex": "0x01",
    "cell_modbus_addr_dec": "0",
    "cell_modbus_addr_hex": "0x0000",
    "cell_modbus_qty": 1,
    "cell_modbus_func": "03 (Read Holding Registers)",
    "cell_task_cycle": 1,
    "cell_task_interval": 100,
    "cell_identifier_format": "<%d>",
    "cell_subs_ui": [{"topic": "", "qos": 0} for _ in range(4)], # State for 4 slots
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

def _log_raw(direction: str, data: bytes):
    t = time.time()
    st.session_state.cell_logs.append({
        "time": t,
        "dir": direction,
        "data": data
    })
    if len(st.session_state.cell_logs) > 200:
        st.session_state.cell_logs.pop(0)
    
    # Persistent Logging
    try:
        import os
        log_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Cellular_MQTT.log"))
        
        # Format: [HH:MM:SS.ms] DIR DATA (Hex)
        tm = time.localtime(t)
        ms = int((t % 1) * 1000)
        ts_str = f"[{tm.tm_hour:02d}:{tm.tm_min:02d}:{tm.tm_sec:02d}.{ms:03d}]"
        dir_sym = "RX<<" if direction == "RX" else "TX>>"
        
        # Clean hex for the log file
        hex_data = data.hex(' ').upper()
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{ts_str} {dir_sym} {hex_data}\n")
    except:
        pass

def _send_and_wait(ser, data: bytes, wait: float = 1.5, hide_tx: bool = False) -> bytes:
    ser.reset_input_buffer()
    if not hide_tx and data:
        _log_raw("TX", data)

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
        for line in buf.replace(b'\r', b'').split(b'\n'):
            if line:
                _log_raw("RX", line)
    return bytes(buf)

# ─── COM Actions ─────────────────────────────────────────────────────────────
def handle_com_connect(port, baudrate):
    if not port or port == "None":
        st.toast("No valid COM port selected.", icon="⚠️")
        return
    try:
        if st.session_state.cell_serial and st.session_state.cell_serial.is_open:
            st.session_state.cell_serial.close()
            
        databits = st.session_state.get("cell_databits_new", 8)
        parity_str = st.session_state.get("cell_parity_new", "None")
        stopbits = st.session_state.get("cell_stopbits_new", 1)
        
        parity_map = {
            "None": serial.PARITY_NONE,
            "Even": serial.PARITY_EVEN,
            "Odd": serial.PARITY_ODD,
            "Mark": serial.PARITY_MARK,
            "Space": serial.PARITY_SPACE
        }
        p_val = parity_map.get(parity_str, serial.PARITY_NONE)
        
        st.session_state.cell_serial = serial.Serial(
            port, 
            baudrate, 
            bytesize=databits, 
            parity=p_val, 
            stopbits=stopbits, 
            timeout=0.1
        )
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
        raw_data = text.encode('utf-8')
        ser.write(raw_data)
        ser.flush()
        _log_raw("TX", raw_data)

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
            for line in rx_buf.replace(b'\r', b'').split(b'\n'):
                if line:
                    _log_raw("RX", line)

        # Auto-enable refresh so user sees incoming messages
        st.session_state.cell_auto_refresh = True
    except Exception as e:
        st.toast(f"Send error: {e}", icon="❌")

def handle_read_serial():
    """Read any pending bytes from serial. Returns True if data was read."""
    ser = st.session_state.cell_serial
    if not ser or not ser.is_open:
        return False
    try:
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            if data:
                _log_raw("RX", data)
                return True
    except:
        pass
    return False

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
    """Enter AT command mode safely with strict guard time (1.1s silence)."""
    # 1. Pre-sequence Guard Time: Wait to ensure no data is in flight
    time.sleep(1.1)
    ser.reset_input_buffer()
    
    _log_raw("TX", b"+++")
    ser.write(b'+++')
    ser.flush()
    
    # 2. Post-sequence Guard Time: Wait for DTU to process escape
    time.sleep(1.1)
    
    rx = bytearray()
    # Read any buffered response (should contain 'atk')
    if ser.in_waiting > 0:
        rx.extend(ser.read(ser.in_waiting))
    
    if rx:
        _log_raw("RX", rx)

    if b'atk' in rx.lower():
        _log_raw("TX", b"ATK")
        ser.write(b'ATK')
        ser.flush()
        time.sleep(0.5)
        if ser.in_waiting > 0:
            rx2 = ser.read(ser.in_waiting)
            if rx2:
                _log_raw("RX", rx2)
                if b'ERROR' in rx2.upper():
                    return False
        return True
    else:
        resp = _send_and_wait(ser, b'AT\r\n', 1.0)
        return b'OK' in resp.upper()

# ─── One-Click DTU Provisioning ──────────────────────────────────────────────
def handle_provision():
    """Sync all hardware state back to UI (Read-only)."""
    ser = st.session_state.cell_serial
    if not ser or not ser.is_open:
        st.toast("COM not connected.", icon="⚠️")
        return

    try:
        st.session_state.cell_provisioning = True
        st.toast("Syncing all HW state...", icon="⏳")

        if _enter_at_mode(ser):
            # Read back the actual hardware state
            _read_hw_state_in_at_mode(ser)
            # Return to transparent mode
            _send_and_wait(ser, b'ATO\r\n', 1.0)
            st.toast("All hardware states synced!", icon="✅")
        else:
            st.toast("Failed to enter AT mode", icon="❌")
            
    except Exception as e:
        st.toast(f"Sync error: {e}", icon="❌")
    finally:
        st.session_state.cell_provisioning = False

def handle_apply_mqtt_config():
    """Write basic MQTT connection settings (Broker, ID, Auth) to DTU."""
    ser = st.session_state.cell_serial
    if not ser or not ser.is_open:
        st.toast("COM not connected.", icon="⚠️")
        return

    host = st.session_state.get("prov_ip_new", "")
    port = st.session_state.get("prov_port_new", "")
    cid = st.session_state.get("prov_cid_new", "")
    user = st.session_state.get("prov_user_new", "")
    pwd = st.session_state.get("prov_pwd_new", "")

    st.toast("Applying MQTT Connection Config...", icon="⏳")
    if _enter_at_mode(ser):
        cmds = [
            f'AT+MQTTIP="{host}","{port}"',
            f'AT+MQTTCD="{cid}"',
            f'AT+MQTTUN="{user}"',
            f'AT+MQTTPW="{pwd}"',
        ]
        for cmd in cmds:
            _send_and_wait(ser, (cmd + "\r\n").encode('utf-8'), 1.5)
            time.sleep(0.2)
        
        # Read back to confirm
        _read_hw_state_in_at_mode(ser)
        _send_and_wait(ser, b'ATO\r\n', 1.0)
        st.toast("MQTT Connection Config applied!", icon="✅")
    else:
        st.toast("Failed to enter AT mode", icon="❌")

def handle_apply_work_mode():
    """Apply the selected Working Mode and MQTT configuration to DTU."""
    ser = st.session_state.cell_serial
    if not ser or not ser.is_open:
        st.toast("COM not connected.", icon="⚠️")
        return

    mode = st.session_state.get("cell_work_mode", "MQTT")
    broker_ip = st.session_state.get("prov_ip_new", "")
    broker_port = st.session_state.get("prov_port_new", "")
    client_id = st.session_state.get("prov_cid_new", "")
    username = st.session_state.get("prov_user_new", "")
    password = st.session_state.get("prov_pwd_new", "")

    st.toast(f"Applying {mode} mode...", icon="⏳")
    if _enter_at_mode(ser):
        # 1. Set Work Mode
        _send_and_wait(ser, f'AT+WORK="{mode}"\r\n'.encode('utf-8'), 1.0)
        time.sleep(0.5)

        # 2. If MQTT, apply MQTT settings
        if mode == "MQTT":
            if broker_ip and broker_port:
                _send_and_wait(ser, f'AT+MQTTIP="{broker_ip}","{broker_port}"\r\n'.encode('utf-8'), 1.0)
                time.sleep(0.2)
            if client_id:
                _send_and_wait(ser, f'AT+MQTTCD="{client_id}"\r\n'.encode('utf-8'), 1.0)
                time.sleep(0.2)
            if username:
                _send_and_wait(ser, f'AT+MQTTUN="{username}"\r\n'.encode('utf-8'), 1.0)
                time.sleep(0.2)
            if password:
                _send_and_wait(ser, f'AT+MQTTPW="{password}"\r\n'.encode('utf-8'), 1.0)
                time.sleep(0.2)
        
        # 3. Restart to apply
        _send_and_wait(ser, b'AT+PWR\r\n', 1.5)
        st.toast(f"Mode applied! DTU is restarting...", icon="✅")
    else:
        st.toast("Failed to enter AT mode", icon="❌")

# ─── Dynamic Subscription Management ─────────────────────────────────────────
def handle_dtu_update_sub(slot, topic, qos):
    """Dynamically update DTU subscription by breaking out of transparent mode."""
    ser = st.session_state.cell_serial
    if not ser or not ser.is_open:
        st.toast("COM not connected.", icon="⚠️")
        return

    if not topic:
        st.toast("Topic cannot be empty", icon="⚠️")
        return

    time.sleep(1.0)
    if _enter_at_mode(ser):
        cmd = f'AT+MQTTSUB{slot}="1","{topic}","{qos}"'
        resp = _send_and_wait(ser, (cmd + "\r\n").encode('utf-8'), 1.5)
        
        _read_hw_state_in_at_mode(ser)
        _send_and_wait(ser, b'ATO\r\n', 1.0)
        st.toast(f"Slot {slot} updated", icon="✅")

def handle_dtu_unsubscribe(slot):
    """Dynamically remove DTU subscription."""
    ser = st.session_state.cell_serial
    if not ser or not ser.is_open:
        st.toast("COM not connected.", icon="⚠️")
        return

    time.sleep(1.0)
    if _enter_at_mode(ser):
        # Disable the slot with state=0
        cmd = f'AT+MQTTSUB{slot}="0","nanopd/dtu/rx","0"'
        resp = _send_and_wait(ser, (cmd + "\r\n").encode('utf-8'), 1.5)
        
        _read_hw_state_in_at_mode(ser)
        _send_and_wait(ser, b'ATO\r\n', 1.0)
        st.toast(f"Slot {slot} unsubscribed", icon="✅")


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
                retain = parts[3] if len(parts) >= 4 else 0
                try:
                    return (int(enable), topic, int(qos), int(retain))
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
            enable, topic, qos, retain = parsed
            active_subs.append({"slot": i, "topic": topic, "qos": qos, "en": (enable == 1)})
            
    active_pubs = []
    for i in range(1, 5):
        cmd = f"AT+MQTTPUB{i}{query_suffix}\r\n"
        resp = _send_and_wait(ser, cmd.encode('utf-8'), 1.5)
        parsed = _parse_mqtt_query_response(resp, f"+MQTTPUB{i}")
        if parsed:
            enable, topic, qos, retain = parsed
            active_pubs.append({"slot": i, "topic": topic, "qos": qos, "retain": retain, "en": (enable == 1)})

    st.session_state.cell_hw_subs = active_subs
    st.session_state.cell_hw_pubs = active_pubs

    # Update UI state for 4 slots (SUBS)
    new_subs_ui = [{"topic": "", "qos": 0} for _ in range(4)]
    for sub in active_subs:
        idx = sub["slot"] - 1
        if 0 <= idx < 4:
            new_subs_ui[idx] = {"topic": sub["topic"], "qos": sub["qos"], "en": sub["en"]}
            st.session_state[f"cell_sub_en_{idx}"] = sub["en"]
            st.session_state[f"cell_sub_t_{idx}"] = sub["topic"]
            st.session_state[f"cell_sub_q_{idx}"] = sub["qos"]
    
    # Update UI state for 4 slots (PUBS)
    new_pubs_ui = [{"topic": "", "qos": 0, "retain": False, "en": False} for _ in range(4)]
    for pub in active_pubs:
        idx = pub["slot"] - 1
        if 0 <= idx < 4:
            new_pubs_ui[idx] = {"topic": pub["topic"], "qos": pub["qos"], "retain": (pub["retain"] == 1), "en": pub["en"]}
            st.session_state[f"cell_pub_en_{idx}"] = pub["en"]
            st.session_state[f"cell_pub_t_{idx}"] = pub["topic"]
            st.session_state[f"cell_pub_q_{idx}"] = pub["qos"]
            st.session_state[f"cell_pub_r_{idx}"] = (pub["retain"] == 1)

    # Clear markers for missing slots (already handled by default initializations above)
    pass

    st.session_state.cell_subs_ui = new_subs_ui
    st.session_state.cell_pubs_ui = new_pubs_ui

    # Also update the primary active_sub for backward compatibility
    if active_subs:
        st.session_state.cell_active_sub = active_subs[0]["topic"]
        st.session_state.cell_active_qos = active_subs[0]["qos"]
    else:
        st.session_state.cell_active_sub = None
        st.session_state.cell_active_qos = 0

    count = len(active_subs)
    pub_info = f", PUBs: {len(active_pubs)}"

    # --- Also read Polling List ---
    # 0. Read TASKTIME
    resp_time = _send_and_wait(ser, b'AT+TASKTIME\r\n', 1.0)
    time_text = resp_time.decode('utf-8', errors='replace')
    for line in time_text.splitlines():
        line = line.strip()
        if line.upper().startswith('+TASKTIME:'):
            val = line.split(":", 1)[1].strip()
            parts = val.split(',')
            if len(parts) == 2:
                try:
                    st.session_state.cell_task_cycle = int(parts[0].replace('"', '').strip())
                    st.session_state.cell_task_interval = int(parts[1].replace('"', '').strip())
                except ValueError:
                    pass

    # 0.5. Read TASKDIST
    resp_dist = _send_and_wait(ser, b'AT+TASKDIST\r\n', 1.0)
    dist_text = resp_dist.decode('utf-8', errors='replace')
    for line in dist_text.splitlines():
        line = line.strip()
        if line.upper().startswith('+TASKDIST:'):
            val = line.split(":", 1)[1].strip()
            parts = val.split(',')
            if len(parts) >= 2:
                try:
                    st.session_state.cell_enable_identifier = (parts[0].replace('"', '').strip() == "1")
                    st.session_state.cell_identifier_format = parts[1].replace('"', '').strip()
                except:
                    pass

    # 1. Read how many polling scripts are active
    resp = _send_and_wait(ser, b'AT+TRANSPOLLNUM\r\n', 1.0)
    
    text = resp.decode('utf-8', errors='replace')
    num = 0
    for line in text.splitlines():
        line = line.strip()
        if line.upper().startswith('+TRANSPOLLNUM:'):
            val = line.split(":", 1)[1].strip().replace('"', '')
            try:
                num = int(val)
            except ValueError:
                pass

    polling_list = []
    # 2. Read each script up to the active count
    if num > 0:
        for i in range(1, num + 1):
            c_resp = _send_and_wait(ser, f'AT+TRANSCMD{i}\r\n'.encode('utf-8'), 0.5)
            c_text = c_resp.decode('utf-8', errors='replace')
            for line in c_text.splitlines():
                line = line.strip()
                if line.upper().startswith(f'+TRANSCMD{i}:'):
                    cmd_val = line.split(":", 1)[1].strip().replace('"', '')
                    polling_list.append({"Index": str(i), "Command": cmd_val})
                    break
    st.session_state.cell_polling_list = polling_list
    if "cell_polling_editor" in st.session_state:
        del st.session_state["cell_polling_editor"]
    
    # --- Sync Working Mode ---
    resp_work = _send_and_wait(ser, b'AT+WORK\r\n', 1.0)
    work_text = resp_work.decode('utf-8', errors='replace')
    for line in work_text.splitlines():
        line = line.strip()
        if line.upper().startswith('+WORK:'):
            val = line.split(":", 1)[1].strip().replace('"', '')
            st.session_state.cell_work_mode = val.upper()

    # --- Sync LTE & Network Info ---
    net_info = {
        "MODULE": "N/A", "SYSINFO": "N/A", "ICCID": "N/A",
        "IMSI": "N/A", "SN": "N/A", "CLK": "N/A",
        "IMEI": "N/A", "CSQ": "N/A"
    }
    net_cmds = [
        ("MODULE", b'AT+MODULE\r\n', "+MODULE:"),
        ("SYSINFO", b'AT+SYSINFO\r\n', "+SYSINFO:"),
        ("ICCID", b'AT+ICCID\r\n', "+ICCID:"),
        ("IMSI", b'AT+IMSI\r\n', "+IMSI:"),
        ("SN", b'AT+SN\r\n', "+SN:"),
        ("CLK", b'AT+CLK\r\n', "+CLK:"),
        ("IMEI", b'AT+IMEI\r\n', "+IMEI:"),
        ("CSQ", b'AT+CSQ\r\n', "+CSQ:")
    ]
    for key, cmd, prefix in net_cmds:
        resp = _send_and_wait(ser, cmd, 1.0)
        text = resp.decode('utf-8', errors='replace')
        for line in text.splitlines():
            line = line.strip()
            if line.upper().startswith(prefix):
                try:
                    val = line.split(":", 1)[1].strip().replace('"', '')
                    net_info[key] = val
                except: pass
                break
    st.session_state.cell_network_info = net_info

    st.toast(f"HW synced: {count} sub(s){pub_info}, {len(polling_list)} task(s)", icon="✅")


def _read_polling_config_in_at_mode(ser):
    """Internal helper to ONLY query polling-related settings while in AT mode."""
    # 0. Read TASKTIME
    resp_time = _send_and_wait(ser, b'AT+TASKTIME\r\n', 1.0)
    time_text = resp_time.decode('utf-8', errors='replace')
    for line in time_text.splitlines():
        line = line.strip()
        if line.upper().startswith('+TASKTIME:'):
            val = line.split(":", 1)[1].strip()
            parts = val.split(',')
            if len(parts) == 2:
                try:
                    st.session_state.cell_task_cycle = int(parts[0].replace('"', '').strip())
                    st.session_state.cell_task_interval = int(parts[1].replace('"', '').strip())
                except ValueError: pass

    # 0.5. Read TASKDIST
    resp_dist = _send_and_wait(ser, b'AT+TASKDIST\r\n', 1.0)
    dist_text = resp_dist.decode('utf-8', errors='replace')
    for line in dist_text.splitlines():
        line = line.strip()
        if line.upper().startswith('+TASKDIST:'):
            val = line.split(":", 1)[1].strip()
            parts = val.split(',')
            if len(parts) >= 2:
                try:
                    st.session_state.cell_enable_identifier = (parts[0].replace('"', '').strip() == "1")
                    st.session_state.cell_identifier_format = parts[1].replace('"', '').strip()
                except: pass

    # 1. Now call the scoped helper to handle the actual list and time reading
    _read_polling_list_only_in_at_mode(ser)


def _read_polling_list_only_in_at_mode(ser):
    """Internal helper to query polling command list and time settings."""
    # 0. Read TASKTIME
    resp_time = _send_and_wait(ser, b'AT+TASKTIME\r\n', 1.0)
    time_text = resp_time.decode('utf-8', errors='replace')
    for line in time_text.splitlines():
        line = line.strip()
        if line.upper().startswith('+TASKTIME:'):
            val = line.split(":", 1)[1].strip()
            parts = val.split(',')
            if len(parts) == 2:
                try:
                    st.session_state.cell_task_cycle = int(parts[0].replace('"', '').strip())
                    st.session_state.cell_task_interval = int(parts[1].replace('"', '').strip())
                except ValueError: pass

    # 1. Read how many polling scripts are active
    resp = _send_and_wait(ser, b'AT+TRANSPOLLNUM\r\n', 1.0)
    text = resp.decode('utf-8', errors='replace')
    num = 0
    for line in text.splitlines():
        line = line.strip()
        if line.upper().startswith('+TRANSPOLLNUM:'):
            val = line.split(":", 1)[1].strip().replace('"', '')
            try: num = int(val)
            except ValueError: num = 0

    polling_list = []
    if num > 0:
        limit = min(num, 20)
        for i in range(1, limit + 1):
            c_resp = _send_and_wait(ser, f'AT+TRANSCMD{i}\r\n'.encode('utf-8'), 0.5)
            c_text = c_resp.decode('utf-8', errors='replace')
            for line in c_text.splitlines():
                line = line.strip()
                if line.upper().startswith(f'+TRANSCMD{i}:'):
                    cmd_val = line.split(":", 1)[1].strip().replace('"', '')
                    if cmd_val and cmd_val.lower() not in ["none", "nan", "error"]:
                        polling_list.append({"Index": str(i), "Command": cmd_val})
                    break
    
    st.session_state.cell_polling_list = polling_list
    if "cell_polling_editor" in st.session_state:
        del st.session_state["cell_polling_editor"]


def _read_subs_only_in_at_mode(ser):
    """Internal helper to ONLY query MQTT subscriptions."""
    subs = []
    for i in range(1, 5):
        resp = _send_and_wait(ser, f'AT+MQTTSUB{i}\r\n'.encode('utf-8'), 1.0)
        text = resp.decode('utf-8', errors='replace')
        for line in text.splitlines():
            line = line.strip()
            if line.upper().startswith(f'+MQTTSUB{i}:'):
                val = line.split(":", 1)[1].strip()
                parts = val.split(',')
                if len(parts) >= 2:
                    en = (parts[0].replace('"', '').strip() == "1")
                    top = parts[1].replace('"', '').strip()
                    qos = int(parts[2].replace('"', '').strip()) if len(parts) > 2 else 0
                    subs.append({"topic": top, "qos": qos, "en": en})
                break
    while len(subs) < 4:
        subs.append({"topic": "", "qos": 0, "en": False})
    st.session_state.cell_subs_ui = subs
    for i in range(4):
        st.session_state[f"cell_sub_en_{i}"] = subs[i]["en"]
        st.session_state[f"cell_sub_t_{i}"] = subs[i]["topic"]
        st.session_state[f"cell_sub_q_{i}"] = subs[i]["qos"]

def _read_pubs_only_in_at_mode(ser):
    """Internal helper to ONLY query MQTT publishing slots."""
    pubs = []
    for i in range(1, 5):
        resp = _send_and_wait(ser, f'AT+MQTTPUB{i}\r\n'.encode('utf-8'), 1.0)
        text = resp.decode('utf-8', errors='replace')
        for line in text.splitlines():
            line = line.strip()
            if line.upper().startswith(f'+MQTTPUB{i}:'):
                val = line.split(":", 1)[1].strip()
                parts = val.split(',')
                if len(parts) >= 2:
                    en = (parts[0].replace('"', '').strip() == "1")
                    top = parts[1].replace('"', '').strip()
                    qos = int(parts[2].replace('"', '').strip()) if len(parts) > 2 else 0
                    ret = (parts[3].replace('"', '').strip() == "1") if len(parts) > 3 else False
                    pubs.append({"topic": top, "qos": qos, "retain": ret, "en": en})
                break
    while len(pubs) < 4:
        pubs.append({"topic": "", "qos": 0, "retain": False, "en": False})
    st.session_state.cell_pubs_ui = pubs
    for i in range(4):
        st.session_state[f"cell_pub_en_{i}"] = pubs[i]["en"]
        st.session_state[f"cell_pub_t_{i}"] = pubs[i]["topic"]
        st.session_state[f"cell_pub_q_{i}"] = pubs[i]["qos"]
        st.session_state[f"cell_pub_r_{i}"] = pubs[i]["retain"]

# ─── Hardware State Sync ──────────────────────────────────────────────────────
def handle_sync_hw_state():
    """Manual sync triggered from UI (Full Read)."""
    ser = st.session_state.cell_serial
    if not ser or not ser.is_open:
        st.toast("COM not connected.", icon="⚠️")
        return
        
    st.toast("Syncing all hardware state...", icon="⏳")
    if _enter_at_mode(ser):
        _read_hw_state_in_at_mode(ser)
        _send_and_wait(ser, b'ATO\r\n', 1.0)
        st.toast("Hardware state synced!", icon="✅")
    else:
        st.toast("Failed to enter AT mode", icon="❌")

def handle_sync_subs_only():
    """Query only MQTT subscriptions."""
    ser = st.session_state.cell_serial
    if not ser or not ser.is_open:
        st.toast("COM not connected.", icon="⚠️")
        return
    if _enter_at_mode(ser):
        _read_subs_only_in_at_mode(ser)
        _send_and_wait(ser, b'ATO\r\n', 1.0)
        st.toast("Subscriptions synced!", icon="✅")
    else:
        st.toast("Failed to enter AT mode", icon="❌")

def handle_sync_pubs_only():
    """Query only MQTT publishing slots."""
    ser = st.session_state.cell_serial
    if not ser or not ser.is_open:
        st.toast("COM not connected.", icon="⚠️")
        return
    if _enter_at_mode(ser):
        _read_pubs_only_in_at_mode(ser)
        _send_and_wait(ser, b'ATO\r\n', 1.0)
        st.toast("Publishing config synced!", icon="✅")
    else:
        st.toast("Failed to enter AT mode", icon="❌")

def calculate_crc16(data: bytes) -> bytes:
    """Standard Modbus RTU CRC16."""
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc.to_bytes(2, byteorder='little')


def handle_publish_modbus():
    """Generates a Modbus RTU frame and publishes it via the DTU's MQTT transparent mode."""
    ser = st.session_state.cell_serial
    if not ser or not ser.is_open:
        st.toast("COM not connected.", icon="⚠️")
        return

    try:
        # Get values from session state
        dev_id_str = st.session_state.get("cell_modbus_id_dec", "1")
        dev_id = int(dev_id_str) if dev_id_str else 1
        
        func_selection = st.session_state.get("cell_modbus_func", "03")
        func_code = int(func_selection.split(" ")[0], 16)
        
        addr_str = st.session_state.get("cell_modbus_addr_dec", "0")
        start_addr = int(addr_str) if addr_str else 0
        
        quantity = int(st.session_state.get("cell_modbus_qty", 1))

        # Build frame
        frame = bytearray()
        frame.append(dev_id)
        frame.append(func_code)
        frame.append((start_addr >> 8) & 0xFF)
        frame.append(start_addr & 0xFF)
        frame.append((quantity >> 8) & 0xFF)
        frame.append(quantity & 0xFF)
        frame.extend(calculate_crc16(frame))

        # Send to serial (DTU in MQTT mode will publish this payload)
        ser.reset_input_buffer()
        ser.write(frame)
        ser.flush()
        
        _log_raw("TX", frame)

        # Brief wait for any echo/response
        time.sleep(0.5)
        if ser.in_waiting > 0:
            rx_data = ser.read(ser.in_waiting)
            if rx_data:
                _log_raw("RX", rx_data)
        
        st.session_state.cell_auto_refresh = True
        st.toast("Modbus frame sent to DTU", icon="📤")
    except Exception as e:
        st.toast(f"Modbus Error: {e}", icon="❌")


def handle_setup_dtu_modbus():
    """Configure DTU for Modbus over MQTT mode using AT commands."""
    ser = st.session_state.cell_serial
    if not ser or not ser.is_open:
        st.toast("COM not connected.", icon="⚠️")
        return
    
    st.toast("Setting up DTU for Modbus...", icon="⏳")
    if _enter_at_mode(ser):
        # 1. Ensure MQTT work mode
        _send_and_wait(ser, b'AT+WORK="MQTT"\r\n', 1.5)
        # 2. Enable Modbus RTU gateway mode (using quotes for parameter)
        _send_and_wait(ser, b'AT+MODBUSRTU="1"\r\n', 1.5)
        
        # Sync hardware state to UI (polling tasks, etc.)
        _read_hw_state_in_at_mode(ser)
        
        # 3. Exit back to transparent/working mode
        _send_and_wait(ser, b'ATO\r\n', 1.0)
        st.toast("DTU Setup Complete: MQTT + Modbus Mode", icon="✅")
    else:
        st.toast("Failed to enter AT mode", icon="❌")


def handle_check_polling_list():
    """Query DTU for all configured polling tasks via AT+COLLECT"""
    ser = st.session_state.cell_serial
    if not ser or not ser.is_open:
        st.toast("COM not connected.", icon="⚠️")
        return
        
    st.toast("Reading polling list (Debug Mode)...", icon="⏳")
    if "cell_polling_editor" in st.session_state:
        del st.session_state["cell_polling_editor"]
        
    if _enter_at_mode(ser):
        _read_polling_list_only_in_at_mode(ser)
        _send_and_wait(ser, b'ATO\r\n', 1.0)
        st.toast(f"Found {len(st.session_state.get('cell_polling_list', []))} polling tasks.", icon="✅")
    else:
        st.toast("Failed to enter AT mode", icon="❌")


def _push_polling_config_in_at_mode(ser):
    """Internal helper to push polling configuration while ALREADY in AT mode."""
    polling_list = st.session_state.get("cell_polling_list", [])
    count = 0
    for item in polling_list:
        cmd = str(item.get("Command", "")).strip()
        if cmd and cmd.lower() not in ["nan", "none"]:
            count += 1
            # The hardware expects double quotes around the command string
            at_cmd = f'AT+TRANSCMD{count}="{cmd}"\r\n'.encode('utf-8')
            _send_and_wait(ser, at_cmd, 1.0)
            time.sleep(0.4)  # Crucial delay for DTU flash write
            
    # Update the total active polling number
    num_cmd = f'AT+TRANSPOLLNUM="{count}"\r\n'.encode('utf-8')
    _send_and_wait(ser, num_cmd, 1.0)
    time.sleep(0.4)
    
    # Update TASKTIME
    cycle = st.session_state.get("cell_task_cycle")
    if cycle is None: cycle = 30
    interval = st.session_state.get("cell_task_interval")
    if interval is None: interval = 100
    
    tt_cmd = f'AT+TASKTIME="{cycle}","{interval}"\r\n'.encode('utf-8')
    _send_and_wait(ser, tt_cmd, 1.0)
    time.sleep(0.4)

    # Set TASKDIST (Identifier Toggle)
    enable_id = st.session_state.get("cell_enable_identifier", True)
    id_format = st.session_state.get("cell_identifier_format", "<%d>")
    id_val = "1" if enable_id else "0"
    dist_cmd = f'AT+TASKDIST="{id_val}","{id_format}"\r\n'.encode('utf-8')
    _send_and_wait(ser, dist_cmd, 1.0)
    time.sleep(0.4)

def handle_send_polling_list(polling_list):
    """Send configured polling tasks to DTU."""
    ser = st.session_state.cell_serial
    if not ser or not ser.is_open:
        st.toast("COM not connected.", icon="⚠️")
        return
        
    st.toast("Sending polling list...", icon="⏳")
    if _enter_at_mode(ser):
        # 1. Push the list and core tasks
        _push_polling_config_in_at_mode(ser)
        
        # 2. Ensure TASKMD is ON (Data Packaging Mode)
        task_mode = st.session_state.get("cell_task_mode", "TRANS")
        _send_and_wait(ser, f'AT+TASKMD="{task_mode}"\r\n'.encode('utf-8'), 1.0)
        time.sleep(0.4)
        
        # 3. Read back to confirm POLLING ONLY
        _read_polling_config_in_at_mode(ser)
        
        # 4. Return to transparent mode
        _send_and_wait(ser, b'ATO\r\n', 1.0)
        st.toast("Polling configuration applied & synced!", icon="✅")
    else:
        st.toast("Failed to enter AT mode", icon="❌")

def handle_check_network():
    """Check LTE and network status via AT commands."""
    ser = st.session_state.cell_serial
    if not ser or not ser.is_open:
        st.toast("COM not connected.", icon="⚠️")
        return
        
    st.toast("Checking LTE and Network Info...", icon="⏳")
    
    info = {
        "MODULE": "N/A", "SYSINFO": "N/A", "ICCID": "N/A",
        "IMSI": "N/A", "SN": "N/A", "CLK": "N/A",
        "IMEI": "N/A", "CSQ": "N/A"
    }
    
    if _enter_at_mode(ser):
        cmds = [
            ("MODULE", b'AT+MODULE\r\n', "+MODULE:"),
            ("SYSINFO", b'AT+SYSINFO\r\n', "+SYSINFO:"),
            ("ICCID", b'AT+ICCID\r\n', "+ICCID:"),
            ("IMSI", b'AT+IMSI\r\n', "+IMSI:"),
            ("SN", b'AT+SN\r\n', "+SN:"),
            ("CLK", b'AT+CLK\r\n', "+CLK:"),
            ("IMEI", b'AT+IMEI\r\n', "+IMEI:"),
            ("CSQ", b'AT+CSQ\r\n', "+CSQ:")
        ]
        
        for key, cmd, prefix in cmds:
            resp = _send_and_wait(ser, cmd, 1.0)
            text = resp.decode('utf-8', errors='replace')
            for line in text.splitlines():
                line = line.strip()
                if line.upper().startswith(prefix):
                    try:
                        val = line.split(":", 1)[1].strip()
                        val = val.replace('"', '')
                        info[key] = val
                    except:
                        pass
                    break
                    
        _send_and_wait(ser, b'ATO\r\n', 1.0)
        st.session_state.cell_network_info = info
        st.toast("Network info updated.", icon="✅")
    else:
        st.toast("Failed to enter AT mode", icon="❌")

def handle_apply_subscriptions(subs_list):
    """Send all subscriptions from the list to DTU."""
    ser = st.session_state.cell_serial
    if not ser or not ser.is_open:
        st.toast("COM not connected.", icon="⚠️")
        return
        
    st.toast("Applying subscriptions...", icon="⏳")
    if _enter_at_mode(ser):
        for i, item in enumerate(subs_list):
            slot = i + 1
            en = "1" if item.get("Active", False) else "0"
            topic = str(item.get("Topic", "")).strip()
            qos = item.get("QoS", 0)
            
            # Always send the topic even if disabled, as requested
            cmd = f'AT+MQTTSUB{slot}="{en}","{topic}","{qos}"\r\n'
            _send_and_wait(ser, cmd.encode('utf-8'), 1.5)
            time.sleep(0.2)
            
        _send_and_wait(ser, b'ATO\r\n', 1.0)
        st.toast("Subscriptions updated!", icon="✅")
    else:
        st.toast("Failed to enter AT mode", icon="❌")

def handle_apply_publishing(pubs_list):
    """Send all publishing presets to DTU."""
    ser = st.session_state.cell_serial
    if not ser or not ser.is_open:
        st.toast("COM not connected.", icon="⚠️")
        return
        
    st.toast("Applying publishing config...", icon="⏳")
    if _enter_at_mode(ser):
        for i, item in enumerate(pubs_list):
            slot = i + 1
            en = "1" if item.get("Active", False) else "0"
            topic = str(item.get("Topic", "")).strip()
            qos = item.get("QoS", 0)
            retain = "1" if item.get("Retain", False) else "0"
            
            # Always send the topic even if disabled
            cmd = f'AT+MQTTPUB{slot}="{en}","{topic}","{qos}","{retain}"\r\n'
            _send_and_wait(ser, cmd.encode('utf-8'), 1.5)
            time.sleep(0.2)
            
        _send_and_wait(ser, b'ATO\r\n', 1.0)
        st.toast("Publishing config updated!", icon="✅")
    else:
        st.toast("Failed to enter AT mode", icon="❌")

