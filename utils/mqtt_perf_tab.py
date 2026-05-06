import streamlit as st
import pandas as pd
import altair as alt
import time
import re
from utils import cellular_mqtt

def find_modbus_packets(raw_data):
    """Robustly find valid Modbus RTU RESPONSES within a raw byte stream."""
    packets = []
    if not isinstance(raw_data, (bytes, bytearray)) or len(raw_data) < 4:
        return packets
    
    offset = 0
    data_len = len(raw_data)
    while offset + 4 <= data_len:
        fc = raw_data[offset + 1]
        
        # We only care about sensor RESPONSES. 
        # For FC 01, 02, 03, 04, the response format is: [ID, FC, BYTE_COUNT, DATA..., CRC_L, CRC_H]
        # Packet length must be exactly 3 (header) + BYTE_COUNT + 2 (CRC)
        if fc in (1, 2, 3, 4): 
            if offset + 2 < data_len:
                byte_count = raw_data[offset + 2]
                length = 3 + byte_count + 2
                
                # Validation: Modbus commands (Requests) for FC 01-04 are always 8 bytes.
                # If length is 8, it could be a command. 
                # A response with byte_count=3 would also be 8 bytes, but that's rare/invalid for these FCs.
                # Most importantly, if the byte_count doesn't align with the available data, it's not a response.
                if offset + length <= data_len:
                    pkt = raw_data[offset:offset+length]
                    try:
                        if cellular_mqtt.calculate_crc16(pkt[:-2]) == pkt[-2:]:
                            # It's a valid Modbus packet. 
                            # Is it a response? Responses for 01-04 MUST have this specific length.
                            # Commands are fixed 8 bytes. 
                            # If byte_count is e.g. 0, length is 5.
                            # The user's example 2F 03 00 00 00 0A C3 83 is 8 bytes. 
                            # Here byte_count is 0x00. 3+0+2 = 5 != 8. So it's NOT a response.
                            packets.append(pkt)
                            offset += length
                            continue
                    except:
                        pass
        
        # FC 05, 06, 15, 16 responses are usually echoes of the command (8 bytes).
        # These are less common for "sensor data" but we can include them if needed.
        # However, the user specifically wants to avoid "commands" being mistaken for "responses".
        # For now, we only strictly match the [ID, FC, BYTE_COUNT, ...] pattern for 01-04.
        
        offset += 1
    return packets

def parse_log_entry(log):
    """Normalize log entry (dict or string) into (data_bytes, timestamp, direction)."""
    if isinstance(log, dict):
        return log.get("data"), log.get("time"), log.get("dir")
    
    if isinstance(log, str):
        try:
            m = re.search(r'\[(\d+):(\d+):(\d+)\.(\d+)\]\s+(RX<<|TX>>|RX|TX|<<|>>)\s+(.*)', log)
            if m:
                h, m_min, s, ms = map(int, m.groups()[:4])
                direction_str = m.group(5)
                content = m.group(6).strip()
                direction = "RX" if "RX" in direction_str or "<<" in direction_str else "TX"
                now = time.localtime()
                t_struct = (now.tm_year, now.tm_mon, now.tm_mday, h, m_min, s, 0, 0, -1)
                ts = time.mktime(t_struct) + ms/1000.0
                clean_hex = content.replace(' ', '')
                if all(c in '0123456789ABCDEFabcdef' for c in clean_hex) and len(clean_hex) % 2 == 0:
                    return bytes.fromhex(clean_hex), ts, direction
                else:
                    return content.encode('utf-8', errors='replace'), ts, direction
        except:
            pass
    return None, None, None

def strip_identifier(data):
    """Strip <n> identifier prefix from bytes if present."""
    if not data:
        return data
    m = re.match(br'^(<\d+>)(.*)', data)
    if m:
        return m.group(2)
    return data

def render_perf_tab():
    # --- GemiPersona Style CSS ---
    st.markdown("""
        <style>
        .dashboard-card {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            margin-bottom: 20px;
        }
        .metric-label {
            color: #a0a0ff;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            font-weight: 600;
            margin-bottom: 4px;
        }
        .metric-value {
            font-size: 28px;
            font-weight: bold;
            color: #ffffff;
            font-family: 'Inter', sans-serif;
        }
        .metric-unit {
            font-size: 14px;
            color: #8888aa;
            margin-left: 4px;
        }
        .section-header {
            color: #a0a0ff;
            font-size: 0.85em;
            font-weight: bold;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">📊 ACCOUNT HEALTH ANALYSIS</div>', unsafe_allow_html=True)
    
    cell_logs = st.session_state.get("cell_logs", [])
    mqtt_logs = st.session_state.get("mqtt_logs", [])
    current_time = time.time()
    
    if not cell_logs:
        st.info("No cellular logs available. Ensure the DTU is receiving data from sensors.")
        return

    # Process logs
    inet_data = []
    for log in mqtt_logs:
        data, ts, direction = parse_log_entry(log)
        if data and direction == "RX":
            inet_data.append({"data": data, "time": ts})
    
    used_inet_indices = set()
    data_points = []
    
    for log in reversed(cell_logs):
        raw_data, cell_time, direction = parse_log_entry(log)
        if not raw_data or direction != "RX":
            continue
        packets = find_modbus_packets(raw_data)
        if not packets:
            continue
            
        for pkt in packets:
            matched_rx = None
            for i, i_log in enumerate(inet_data):
                if i in used_inet_indices: continue
                rx_data = i_log["data"]
                # Use 'in' to match even if the identifier header is missing or corrupted
                if pkt in rx_data:
                    if i_log["time"] > (cell_time - 1.5):
                        matched_rx = i_log
                        used_inet_indices.add(i)
                        break
            
            t = time.localtime(cell_time)
            ms = int((cell_time % 1) * 1000)
            ts_str = f"{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}.{ms:03d}"
            
            if matched_rx:
                latency = matched_rx["time"] - cell_time
                data_points.append({
                    "Timestamp": ts_str,
                    "Delay": max(0.001, latency),
                    "Status": "Success",
                    "FullTime": cell_time,
                    "legend": "Success"
                })
            else:
                data_points.append({
                    "Timestamp": ts_str,
                    "Delay": current_time - cell_time,
                    "Status": "Pending",
                    "FullTime": cell_time,
                    "legend": "Fail"
                })
        
        if len(data_points) >= 50:
            break

    if not data_points:
        st.warning("No Modbus sensor responses found in cellular logs.")
        return

    # --- Render Metrics (GemiPersona Style) ---
    df = pd.DataFrame(data_points).sort_values("FullTime")
    rec_count = len(df[df["Status"] == "Success"])
    pen_count = len(df[df["Status"] != "Success"])
    avg_lat = df[df["Status"] == "Success"]["Delay"].mean() if rec_count > 0 else 0

    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f"""
            <div class="dashboard-card">
                <div class="metric-label">✅ Sync Success</div>
                <div class="metric-value">{rec_count}<span class="metric-unit">pkts</span></div>
            </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
            <div class="dashboard-card">
                <div class="metric-label">⏳ Pending / Lost</div>
                <div class="metric-value" style="color: #ff9999;">{pen_count}<span class="metric-unit">pkts</span></div>
            </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
            <div class="dashboard-card">
                <div class="metric-label">⏱ Avg Latency</div>
                <div class="metric-value">{avg_lat:.3f}<span class="metric-unit">s</span></div>
            </div>
        """, unsafe_allow_html=True)

    # --- Chart (Altair - GemiPersona Style) ---
    st.markdown('<p style="color: #a0a0ff; font-size: 0.9em; margin-bottom: 4px;">Performance Graph: <b>Sync Delay Trends</b></p>', unsafe_allow_html=True)
    
    # Altair Chart construction matching GemiPersona
    df["Sequence"] = range(1, len(df) + 1)
    df["Minutes"] = df["Delay"] / 60.0 # Match the 'Minutes' y-axis in GemiPersona
    
    # Colors matching GemiPersona's lr list
    ll = ['Success', 'Fail']
    lr = ['#2ecc71', '#ff9999']
    
    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('Sequence:Q', title="Sequence", scale=alt.Scale(nice=False), axis=alt.Axis(format='d', tickMinStep=1)),
        y=alt.Y('Delay:Q', title="Delay (seconds)", scale=alt.Scale(type='symlog')),
        color=alt.Color('legend:N', scale=alt.Scale(domain=ll, range=lr),
                        legend=alt.Legend(title=None, orient='bottom', columns=2)),
        tooltip=['Timestamp', 'Delay', 'Status']
    ).properties(height=400).interactive(bind_y=False)

    st.altair_chart(chart, width="stretch")
    
    st.markdown('</div>', unsafe_allow_html=True)
