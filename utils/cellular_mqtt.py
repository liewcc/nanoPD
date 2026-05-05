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
    "cell_enable_identifier": True,
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
    st.session_state.cell_logs.append({
        "time": time.time(),
        "dir": direction,
        "data": data
    })
    if len(st.session_state.cell_logs) > 200:
        st.session_state.cell_logs.pop(0)

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
    """Read any pending bytes from serial."""
    ser = st.session_state.cell_serial
    if not ser or not ser.is_open:
        return
    try:
        if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            if data:
                _log_raw("RX", data)
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

    try:
        st.session_state.cell_provisioning = True

        # Step 1: Escape to AT mode
        if not _enter_at_mode(ser):
            st.session_state.cell_provisioning = False
            st.toast("Failed to enter AT mode for provisioning", icon="❌")
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

        # Read back the actual hardware state BEFORE exiting AT mode.
        # This completely avoids the buggy GPRS-connection period.
        _read_hw_state_in_at_mode(ser)

        # Return to transparent mode (auto-saves on these modules)
        _send_and_wait(ser, b'ATO\r\n', 1.0)
            
        st.toast("Provisioning applied & synced successfully!", icon="✅")
            
    except Exception as e:
        st.toast(f"Provisioning error: {e}", icon="❌")
        _log_raw("RX", f"[System] Error: {e}".encode('utf-8'))
    finally:
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
    st.toast(f"HW synced: {count} sub(s){pub_info}, {len(polling_list)} task(s)", icon="✅")

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
        _send_and_wait(ser, b'ATO\r\n', 1.0)
        st.toast(f"Found {len(polling_list)} polling tasks.", icon="✅")
    else:
        st.toast("Failed to enter AT mode", icon="❌")


def handle_send_polling_list(polling_list):
    """Send configured polling tasks to DTU."""
    ser = st.session_state.cell_serial
    if not ser or not ser.is_open:
        st.toast("COM not connected.", icon="⚠️")
        return
        
    st.toast("Sending polling list...", icon="⏳")
    if _enter_at_mode(ser):
        count = 0
        for item in polling_list:
            cmd = str(item.get("Command", "")).strip()
            if cmd and cmd.lower() != "nan" and cmd.lower() != "none":
                count += 1
                # The hardware expects double quotes around the command string
                at_cmd = f'AT+TRANSCMD{count}="{cmd}"\r\n'.encode('utf-8')
                _send_and_wait(ser, at_cmd, 1.0)
                time.sleep(0.5)  # Crucial delay for DTU to complete flash write
                
        # Update the total active polling number
        num_cmd = f'AT+TRANSPOLLNUM="{count}"\r\n'.encode('utf-8')
        _send_and_wait(ser, num_cmd, 1.0)
        time.sleep(0.5)
        
        # Update TASKTIME
        cycle = st.session_state.get("cell_task_cycle", 1)
        interval = st.session_state.get("cell_task_interval", 100)
        tt_cmd = f'AT+TASKTIME="{cycle}","{interval}"\r\n'.encode('utf-8')
        _send_and_wait(ser, tt_cmd, 1.0)
        time.sleep(0.5)

        # Set TASKDIST (Identifier Toggle)
        enable_id = st.session_state.get("cell_enable_identifier", True)
        id_val = "1" if enable_id else "0"
        dist_cmd = f'AT+TASKDIST="{id_val}","<%d>"\r\n'.encode('utf-8')
        _send_and_wait(ser, dist_cmd, 1.0)
        time.sleep(0.5)
        
        # Restart the module to apply the changes
        _send_and_wait(ser, b'AT+PWR\r\n', 1.5)
        st.toast("Polling list saved! DTU is restarting...", icon="✅")
    else:
        st.toast("Failed to enter AT mode", icon="❌")
