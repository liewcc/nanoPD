import streamlit as st
import time
import paho.mqtt.client as mqtt
from utils.style_utils import apply_global_css
from utils.config_utils import load_ui_config
from utils import cellular_mqtt
import os
from utils.config_utils import load_ui_config, save_ui_config, load_mqtt_config, save_mqtt_config

def save_current_mqtt_config():
    def get_val(state_key, cfg_key, default_val):
        if state_key in st.session_state:
            return st.session_state[state_key]
        return st.session_state.mqtt_cfg.get(cfg_key, default_val)

    cfg = {
        "internet_host": get_val("cfg_broker", "internet_host", ""),
        "internet_port": get_val("cfg_port", "internet_port", 1883),
        "internet_cid": get_val("cfg_cid", "internet_cid", ""),
        "internet_user": get_val("cfg_user", "internet_user", ""),
        "internet_pwd": get_val("cfg_pwd", "internet_pwd", ""),
        "internet_sub_topic": get_val("cfg_sub_topic", "internet_sub_topic", ""),
        "internet_sub_qos": get_val("cfg_sub_qos", "internet_sub_qos", 0),
        "internet_pub_topic": get_val("cfg_pub_topic", "internet_pub_topic", ""),
        "internet_pub_qos": get_val("cfg_pub_qos", "internet_pub_qos", 0),
        "internet_pub_payload": get_val("cfg_pub_payload", "internet_pub_payload", ""),
        "cellular_ip": get_val("prov_ip_new", "cellular_ip", ""),
        "cellular_port": get_val("prov_port_new", "cellular_port", ""),
        "cellular_cid": get_val("prov_cid_new", "cellular_cid", ""),
        "cellular_user": get_val("prov_user_new", "cellular_user", ""),
        "cellular_pwd": get_val("prov_pwd_new", "cellular_pwd", ""),
        "cellular_sub_topic": get_val("prov_sub_new", "cellular_sub_topic", ""),
        "cellular_sub_qos": get_val("prov_sub_qos_new", "cellular_sub_qos", 0),
        "cellular_pub_topic": get_val("prov_pub_new", "cellular_pub_topic", ""),
        "cellular_pub_qos": get_val("prov_pub_qos_new", "cellular_pub_qos", 0),
        "cellular_payload": get_val("cell_payload_new", "cellular_payload", ""),
        "cellular_port_name": get_val("cell_com_port_new", "cellular_port_name", ""),
        "cellular_baud_rate": get_val("cell_baud_new", "cellular_baud_rate", 115200),
        "inet_log_format": get_val("inet_log_format", "inet_log_format", "ASCII"),
        "cell_log_format": get_val("cell_log_format", "cell_log_format", "ASCII"),
        "cell_modbus_id_hex": get_val("cell_modbus_id_hex", "cell_modbus_id_hex", "0x01"),
        "cell_modbus_id_dec": get_val("cell_modbus_id_dec", "cell_modbus_id_dec", "1"),
        "cell_modbus_func": get_val("cell_modbus_func", "cell_modbus_func", "03 (Read Holding Registers)"),
        "cell_modbus_addr_hex": get_val("cell_modbus_addr_hex", "cell_modbus_addr_hex", "0x0000"),
        "cell_modbus_addr_dec": get_val("cell_modbus_addr_dec", "cell_modbus_addr_dec", "0"),
        "cell_modbus_qty": get_val("cell_modbus_qty", "cell_modbus_qty", 1),
        "mqtt_subscriptions": dict(st.session_state.get("mqtt_subscriptions", st.session_state.mqtt_cfg.get("mqtt_subscriptions", {})))
    }
    st.session_state.mqtt_cfg = cfg
    save_mqtt_config(cfg)

# ─── Session State Initialization ───────────────────────────────────────────
if "ui_cfg" not in st.session_state:
    st.session_state.ui_cfg = load_ui_config()

# Load MQTT configuration from config.json
if "mqtt_cfg" not in st.session_state:
    st.session_state.mqtt_cfg = load_mqtt_config()

if 'mqtt_logs' not in st.session_state:
    st.session_state.mqtt_logs = []
    log_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Internet_MQTT.log"))
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
                st.session_state.mqtt_logs = lines[-100:]
        except:
            pass
if 'mqtt_client' not in st.session_state:
    st.session_state.mqtt_client = None
if 'mqtt_subscriptions' not in st.session_state:
    st.session_state.mqtt_subscriptions = dict(st.session_state.mqtt_cfg.get("mqtt_subscriptions", {}))
if 'mqtt_auto_refresh' not in st.session_state:
    st.session_state.mqtt_auto_refresh = False
if 'mqtt_shared_state' not in st.session_state:
    st.session_state.mqtt_shared_state = {"status": "disconnected"}

# Initialize Cellular Modbus state for persistent configs
if 'cell_modbus_id_hex' not in st.session_state:
    st.session_state.cell_modbus_id_hex = st.session_state.mqtt_cfg.get("cell_modbus_id_hex", "0x01")
if 'cell_modbus_id_dec' not in st.session_state:
    st.session_state.cell_modbus_id_dec = st.session_state.mqtt_cfg.get("cell_modbus_id_dec", "1")
if 'cell_modbus_addr_hex' not in st.session_state:
    st.session_state.cell_modbus_addr_hex = st.session_state.mqtt_cfg.get("cell_modbus_addr_hex", "0x0000")
if 'cell_modbus_addr_dec' not in st.session_state:
    st.session_state.cell_modbus_addr_dec = st.session_state.mqtt_cfg.get("cell_modbus_addr_dec", "0")
if 'cell_modbus_func' not in st.session_state:
    st.session_state.cell_modbus_func = st.session_state.mqtt_cfg.get("cell_modbus_func", "03 (Read Holding Registers)")
if 'cell_modbus_qty' not in st.session_state:
    st.session_state.cell_modbus_qty = st.session_state.mqtt_cfg.get("cell_modbus_qty", 1)
if 'cell_task_cycle' not in st.session_state:
    st.session_state.cell_task_cycle = None
if 'cell_task_interval' not in st.session_state:
    st.session_state.cell_task_interval = None
if 'cell_polling_list' not in st.session_state:
    st.session_state.cell_polling_list = []
if 'inet_log_format' not in st.session_state:
    st.session_state.inet_log_format = st.session_state.mqtt_cfg.get("inet_log_format", "ASCII")
if 'cell_log_format' not in st.session_state:
    st.session_state.cell_log_format = st.session_state.mqtt_cfg.get("cell_log_format", "ASCII")
if 'prov_sub_new' not in st.session_state:
    st.session_state.prov_sub_new = st.session_state.mqtt_cfg.get("cellular_sub_topic", "")
if 'prov_sub_qos_new' not in st.session_state:
    st.session_state.prov_sub_qos_new = st.session_state.mqtt_cfg.get("cellular_sub_qos", 0)

# Initialize Cellular MQTT state
cellular_mqtt.init_state()

if 'cell_active_sub' not in st.session_state:
    st.session_state.cell_active_sub = ""
if 'cell_active_qos' not in st.session_state:
    st.session_state.cell_active_qos = 0

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
        section[data-testid="stMain"] > div {{ padding-bottom: 20px !important; }}
        div[data-testid="block-container"] {{ padding-bottom: 20px !important; }}
        .main-left-column::-webkit-scrollbar {{
            width: 6px !important;
            display: block !important;
            background: transparent !important;
        }}
        .main-left-column::-webkit-scrollbar-thumb {{
            background: #cbd5e1 !important;
            border-radius: 10px !important;
        }}
        div[data-testid="stVerticalBlock"]:has(.layout-mcu-marker) {{
            overflow-y: hidden !important; scrollbar-width: none !important;
        }}
        div[data-testid="stVerticalBlock"]:has(.layout-mcu-marker)::-webkit-scrollbar {{
            display: none !important; width: 0 !important;
        }}
        /* Un-clip parent elements so left column can independently scroll */
        div[data-testid="stHorizontalBlock"]:has(.layout-mcu-marker) {{
            overflow: visible !important;
        }}
        div[data-testid="stVerticalBlock"]:has(div[data-testid="stHorizontalBlock"]:has(.layout-mcu-marker)) {{
            overflow: visible !important;
        }}
        div[data-testid="stTabPanel"]:has(.layout-mcu-marker) {{
            overflow: visible !important;
        }}
        /* Reset full-height on bordered containers in MQTT multi-panel layout */
        div[data-testid="stHorizontalBlock"]:has(.layout-mcu-marker) [data-testid="stVerticalBlockBorderWrapper"] {{
            height: auto !important;
            min-height: unset !important;
            overflow-y: visible !important;
        }}
        /* Fix height for the log block to push PAYLOAD container to the bottom */
        div[data-testid="stVerticalBlock"]:has(.layout-mcu-marker) pre {{
            height: 458px !important; overflow-y: auto !important; margin: 0 !important;
        }}
        /* Zero out Streamlit default bottom padding so no empty space appears below containers */
        section[data-testid="stMain"] > div {{ padding-bottom: 0 !important; }}
        div[data-testid="block-container"] {{ padding-bottom: 0 !important; }}
        div[data-testid="stTabPanel"] {{ padding-bottom: 0 !important; }}
    </style>
""", unsafe_allow_html=True)

# ─── Internet MQTT Helper Functions ─────────────────────────────────────────
def handle_connect(host, port, cid, user, pwd):
    if not host or not cid:
        st.toast("Host and Client ID are required.", icon="⚠️")
        return
    try:
        if st.session_state.mqtt_client:
            st.session_state.mqtt_client.loop_stop()
            st.session_state.mqtt_client.disconnect()
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cid)
        shared_state = {
            "logs": st.session_state.mqtt_logs,
            "subscriptions": st.session_state.mqtt_subscriptions,
            "state_obj": st.session_state.mqtt_shared_state,
            "log_file": os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Internet_MQTT.log"))
        }
        client.user_data_set(shared_state)
        if user:
            client.username_pw_set(user, pwd)

        def on_connect_cb(c, userdata, flags, rc, props):
            if rc == 0:
                userdata["state_obj"]["status"] = "connected"
                userdata["logs"].append({"msg": "[System] Connected successfully!"})
                for t, q in userdata["subscriptions"].items():
                    c.subscribe(t, q)
            else:
                userdata["state_obj"]["status"] = f"refused:{rc}"
                userdata["logs"].append({"msg": f"[System] Connection refused! Reason code: {rc}"})

        def on_disconnect_cb(c, userdata, flags, rc, props):
            userdata["state_obj"]["status"] = "disconnected"
            userdata["logs"].append({"msg": f"[System] Disconnected. Reason code: {rc}"})

        def on_message_cb(c, userdata, msg):
            log_dict = {
                "time": time.time(),
                "dir": "RX",
                "data": msg.payload
            }
            userdata["logs"].append(log_dict)
            # Append to log file
            try:
                t = time.localtime(log_dict["time"])
                ms = int((log_dict["time"] % 1) * 1000)
                t_str = f"[{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}.{ms:03d}]"
                try:
                    payload_str = msg.payload.decode('utf-8', errors='replace')
                except:
                    payload_str = msg.payload.hex()
                log_entry = f"{t_str} RX<< {payload_str}"
                with open(userdata.get("log_file", "Internet_MQTT.log"), "a", encoding="utf-8") as f:
                    f.write(log_entry + "\n")
            except Exception:
                pass
            if len(userdata["logs"]) > 100:
                userdata["logs"].pop(0)

        client.on_connect = on_connect_cb
        client.on_disconnect = on_disconnect_cb
        client.on_message = on_message_cb
        client.connect(host, port, 60)
        client.loop_start()
        st.session_state.mqtt_client = client
        st.session_state.mqtt_auto_refresh = True
        st.toast(f"Connecting to {host}:{port}...", icon="⏳")
        save_current_mqtt_config()
    except Exception as e:
        st.toast(f"Connection failed: {e}", icon="❌")

def handle_disconnect():
    if st.session_state.mqtt_client:
        st.session_state.mqtt_client.loop_stop()
        st.session_state.mqtt_client.disconnect()
        st.session_state.mqtt_client = None
    st.session_state.mqtt_shared_state["status"] = "disconnected"
    st.session_state.mqtt_auto_refresh = False
    st.toast("Disconnected.", icon="🛑")

def handle_subscribe(topic, qos):
    if not topic:
        return
    is_conn = st.session_state.mqtt_shared_state.get("status") == "connected"
    if st.session_state.mqtt_client and is_conn:
        st.session_state.mqtt_client.subscribe(topic, qos)
        st.session_state.mqtt_subscriptions[topic] = qos
        st.toast(f"Subscribed to {topic}", icon="✅")
        save_current_mqtt_config()
    else:
        st.session_state.mqtt_subscriptions[topic] = qos
        st.toast(f"Topic saved. Will subscribe when connected.", icon="ℹ️")

def handle_unsubscribe(topic):
    if not topic:
        return
    is_conn = st.session_state.mqtt_shared_state.get("status") == "connected"
    if st.session_state.mqtt_client and is_conn:
        st.session_state.mqtt_client.unsubscribe(topic)
    if topic in st.session_state.mqtt_subscriptions:
        del st.session_state.mqtt_subscriptions[topic]
        # Immediately sync mqtt_cfg to prevent stale data on next save
        st.session_state.mqtt_cfg["mqtt_subscriptions"] = dict(st.session_state.mqtt_subscriptions)
        st.toast(f"Unsubscribed from {topic}", icon="✅")
        save_current_mqtt_config()

def handle_publish(topic, qos, payload):
    if not topic:
        st.toast("Topic is required.", icon="⚠️")
        return
    is_conn = st.session_state.mqtt_shared_state.get("status") == "connected"
    if st.session_state.mqtt_client and is_conn:
        st.session_state.mqtt_client.publish(topic, payload, qos)
        
        log_dict = {
            "time": time.time(),
            "dir": "TX",
            "data": payload.encode('utf-8')
        }
        st.session_state.mqtt_logs.append(log_dict)
        if len(st.session_state.mqtt_logs) > 100:
            st.session_state.mqtt_logs.pop(0)
        
        try:
            t = time.localtime(log_dict["time"])
            ms = int((log_dict["time"] % 1) * 1000)
            t_str = f"[{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}.{ms:03d}]"
            log_entry = f"{t_str} TX>> {payload}"
            log_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Internet_MQTT.log"))
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
        except:
            pass
        save_current_mqtt_config()
    else:
        st.toast("Cannot publish: Not connected.", icon="❌")

def handle_clear_logs():
    st.session_state.mqtt_logs.clear()
    save_current_mqtt_config()


# ═══════════════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════════════
tab_internet, tab_cellular = st.tabs(["🌐 Internet MQTT", "📶 Cellular MQTT"])
is_connected = st.session_state.mqtt_shared_state.get("status") == "connected"

# ─── TAB 1: INTERNET MQTT ───────────────────────────────────────────────────
with tab_internet:
    col_left, col_right = st.columns([1, 1])

    with col_left:
        with st.container(height=760, border=False):
            # BROKER CONFIGURATION
            with st.container(border=True):
                st.markdown('<p class="metric-label" style="margin:0 0 12px 0">BROKER CONFIGURATION</p>', unsafe_allow_html=True)
                c_host, c_port, c_cid = st.columns([0.4, 0.2, 0.4])
                with c_host:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">HOST ADDRESS</p>', unsafe_allow_html=True)
                    broker = st.text_input("Host", value=st.session_state.mqtt_cfg.get("internet_host", "202.59.9.164"), key="cfg_broker", label_visibility="collapsed")
                with c_port:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">PORT</p>', unsafe_allow_html=True)
                    port = st.number_input("Port", value=st.session_state.mqtt_cfg.get("internet_port", 1883), min_value=1, max_value=65535, key="cfg_port", label_visibility="collapsed")
                with c_cid:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">CLIENT ID</p>', unsafe_allow_html=True)
                    client_id = st.text_input("Client ID", value=st.session_state.mqtt_cfg.get("internet_cid", "nanopd_mqtt_client"), key="cfg_cid", label_visibility="collapsed")
                u_col, pw_col = st.columns(2)
                with u_col:
                    st.markdown('<p class="metric-label" style="margin:12px 0 0 0">USERNAME</p>', unsafe_allow_html=True)
                    username = st.text_input("Username", value=st.session_state.mqtt_cfg.get("internet_user", ""), key="cfg_user", label_visibility="collapsed", placeholder="Optional")
                with pw_col:
                    st.markdown('<p class="metric-label" style="margin:12px 0 0 0">PASSWORD</p>', unsafe_allow_html=True)
                    password = st.text_input("Password", value=st.session_state.mqtt_cfg.get("internet_pwd", ""), type="password", key="cfg_pwd", label_visibility="collapsed", placeholder="Optional")
                c1, c2 = st.columns([0.6, 0.4])
                with c1:
                    if not is_connected:
                        st.button("🔌 Connect", width="stretch", type="primary", on_click=handle_connect, args=(broker, port, client_id, username, password), key="inet_connect")
                    else:
                        st.button("🛑 Disconnect", width="stretch", type="secondary", on_click=handle_disconnect, key="inet_disconnect")
                with c2:
                    if is_connected:
                        st.markdown('<p style="color:#00C853; font-weight:bold; padding-top:8px;">🟢 CONNECTED</p>', unsafe_allow_html=True)
                    else:
                        st.markdown('<p style="color:#FF5252; font-weight:bold; padding-top:8px;">🔴 DISCONNECTED</p>', unsafe_allow_html=True)

            # SUBSCRIPTION MANAGEMENT
            with st.container(border=True):
                st.markdown('<p class="metric-label" style="margin:0 0 12px 0">SUBSCRIPTION MANAGEMENT</p>', unsafe_allow_html=True)
                s1, s2, s3 = st.columns([0.6, 0.15, 0.25])
                with s1:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">TOPIC</p>', unsafe_allow_html=True)
                    sub_topic = st.text_input("Sub Topic", value=st.session_state.mqtt_cfg.get("internet_sub_topic", "nanopd/test/#"), key="cfg_sub_topic", label_visibility="collapsed")
                with s2:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">QOS</p>', unsafe_allow_html=True)
                    sub_qos = st.selectbox("Sub QoS", [0, 1, 2], key="cfg_sub_qos", label_visibility="collapsed", index=st.session_state.mqtt_cfg.get("internet_sub_qos", 0))
                with s3:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">&nbsp;</p>', unsafe_allow_html=True)
                    if st.button("➕ Subscribe", width="stretch", key="inet_sub"):
                        handle_subscribe(sub_topic, sub_qos)
                        st.rerun()
                if st.session_state.mqtt_subscriptions:
                    active_topics = list(st.session_state.mqtt_subscriptions.keys())
                    summary = " | ".join([f"{t} (Q{st.session_state.mqtt_subscriptions[t]})" for t in active_topics])
                    st.markdown(f'<p class="metric-label" style="margin:12px 0 4px 0">ACTIVE ({len(active_topics)}): <span style="font-weight:normal;color:#888;">{summary}</span></p>', unsafe_allow_html=True)
                    us1, us2 = st.columns([0.75, 0.25])
                    with us1:
                        st.selectbox("Remove", active_topics, key="unsub_select", label_visibility="collapsed")
                    with us2:
                        def _do_unsub_selected():
                            t = st.session_state.get("unsub_select")
                            if t:
                                handle_unsubscribe(t)
                        st.button("➖ Unsub", width="stretch", key="inet_unsub", on_click=_do_unsub_selected)

            # PUBLISH MESSAGE (Topic & QoS)
            with st.container(border=True):
                st.markdown('<p class="metric-label" style="margin:0 0 12px 0">PUBLISH MESSAGE</p>', unsafe_allow_html=True)
                pt, pq = st.columns([0.8, 0.2])
                with pt:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">TOPIC</p>', unsafe_allow_html=True)
                    pub_topic = st.text_input("Pub Topic", value=st.session_state.mqtt_cfg.get("internet_pub_topic", "nanopd/test/pub"), key="cfg_pub_topic", label_visibility="collapsed")
                with pq:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">QOS</p>', unsafe_allow_html=True)
                    pub_qos = st.selectbox("Pub QoS", [0, 1, 2], key="cfg_pub_qos", label_visibility="collapsed", index=st.session_state.mqtt_cfg.get("internet_pub_qos", 0))

    with col_right:
        with st.container(height=760, border=False):
            # MESSAGE LOGS
            with st.container(border=True):
                st.markdown('<div class="layout-mcu-marker" style="display:none;"></div>', unsafe_allow_html=True)
                tc, mc, bc = st.columns([0.4, 0.4, 0.2])
                with tc:
                    st.markdown('<p class="metric-label" style="margin:0">MESSAGE LOGS</p>', unsafe_allow_html=True)
                with mc:
                    st.radio("Log Format", ["ASCII", "HEX"], horizontal=True, label_visibility="collapsed", key="inet_log_format")
                with bc:
                    st.button("🗑️ Clear", width='stretch', key="clear_mqtt_log", on_click=handle_clear_logs)
                
                inet_log_placeholder = st.empty()
                display_lines = []
                log_format = st.session_state.get("inet_log_format", "ASCII")
                for log in st.session_state.mqtt_logs:
                    if isinstance(log, dict):
                        if "msg" in log and log["msg"] is not None:
                            display_lines.append(log["msg"])
                        else:
                            direction = log.get("dir", "??")
                            raw_data = log.get("data", b"")
                            t = log.get("time", 0.0)
                            
                            t_str = ""
                            if t > 0:
                                dt = time.localtime(t)
                                ms = int((t % 1) * 1000)
                                t_str = f"[{dt.tm_hour:02d}:{dt.tm_min:02d}:{dt.tm_sec:02d}.{ms:03d}] "
                            
                            if log_format == "HEX":
                                formatted = raw_data.hex(' ').upper()
                            else:
                                formatted = raw_data.decode('utf-8', errors='replace').replace('\r', '\\r').replace('\n', '\\n')
                                
                            prefix = ">>" if direction == "TX" else "<<" if direction == "RX" else ""
                            display_lines.append(f"{t_str}{direction}{prefix} {formatted}")
                    else:
                        display_lines.append(log)
                
                if not display_lines:
                    display_lines = [""]
                inet_log_placeholder.code("\n".join(display_lines), language="text")

                # Auto-scroll logs to bottom
                if st.session_state.mqtt_logs:
                    st.html("""
                        <script>
                        (function() {
                            var parentDoc = window.parent && window.parent.document ? window.parent.document : document;
                            function scrollLogsToBottom() {
                                var markers = parentDoc.querySelectorAll('.layout-mcu-marker');
                                markers.forEach(function(marker) {
                                    var block = marker.closest('[data-testid="stVerticalBlock"]');
                                    if (block) {
                                        var pre = block.querySelector('pre');
                                        if (pre) pre.scrollTop = pre.scrollHeight;
                                    }
                                });
                            }
                            scrollLogsToBottom();
                            setTimeout(scrollLogsToBottom, 100);
                            setTimeout(scrollLogsToBottom, 300);
                            setTimeout(scrollLogsToBottom, 600);
                        })();
                        </script>
                    """)

            # PAYLOAD & ACTIONS
            with st.container(border=True):
                st.markdown('<p class="metric-label" style="margin:0 0 12px 0">PAYLOAD</p>', unsafe_allow_html=True)
                pub_payload = st.text_input("Payload", value=st.session_state.mqtt_cfg.get("internet_pub_payload", '{"msg": "Hello NanoPD"}'), key="cfg_pub_payload", label_visibility="collapsed")
                ca1, ca2 = st.columns([0.7, 0.3])
                with ca1:
                    st.button("📤 Publish", width="stretch", type="primary", disabled=not is_connected, on_click=handle_publish, args=(pub_topic, pub_qos, pub_payload), key="inet_pub")
                with ca2:
                    if st.button("🔁 Auto", width="stretch", type="primary" if st.session_state.mqtt_auto_refresh else "secondary", key="inet_auto_rx", help="Auto-refresh to read incoming messages"):
                        st.session_state.mqtt_auto_refresh = not st.session_state.mqtt_auto_refresh
                        st.rerun()



# ─── Cellular Modbus Helpers ────────────────────────────────────────────────
def update_cell_modbus_id_from_hex():
    val = st.session_state.get("cell_modbus_id_hex", "").strip()
    try:
        if val:
            clean_val = val[2:] if val.lower().startswith('0x') else val
            dec_val = int(clean_val, 16)
            st.session_state.cell_modbus_id_dec = str(dec_val)
            st.session_state.cell_modbus_id_hex = f"0x{dec_val:02X}"
    except ValueError: pass

def update_cell_modbus_id_from_dec():
    val = st.session_state.get("cell_modbus_id_dec", "").strip()
    try:
        if val:
            st.session_state.cell_modbus_id_hex = f"0x{int(val):02X}"
    except ValueError: pass

def update_cell_modbus_addr_from_hex():
    val = st.session_state.get("cell_modbus_addr_hex", "").strip()
    try:
        if val:
            clean_val = val[2:] if val.lower().startswith('0x') else val
            dec_val = int(clean_val, 16)
            st.session_state.cell_modbus_addr_dec = str(dec_val)
            st.session_state.cell_modbus_addr_hex = f"0x{dec_val:04X}"
    except ValueError: pass

def update_cell_modbus_addr_from_dec():
    val = st.session_state.get("cell_modbus_addr_dec", "").strip()
    try:
        if val:
            st.session_state.cell_modbus_addr_hex = f"0x{int(val):04X}"
    except ValueError: pass


# ─── TAB 2: CELLULAR MQTT ───────────────────────────────────────────────────
with tab_cellular:
    cell_ser = st.session_state.cell_serial
    cell_connected = cell_ser is not None and cell_ser.is_open
    cl, cr = st.columns([1, 1])

    with cl:
        with st.container(height=760, border=False):
            # COM Port Configuration
            with st.container(border=True):
                st.markdown('<p class="metric-label" style="margin:0 0 12px 0">COM PORT CONFIGURATION</p>', unsafe_allow_html=True)
                ports = cellular_mqtt.get_com_ports()
                if not ports:
                    ports = ["None"]
                saved_port = st.session_state.mqtt_cfg.get("cellular_port_name", "")
                port_index = ports.index(saved_port) if saved_port in ports else 0
                baud_options = [9600, 19200, 38400, 57600, 115200]
                saved_baud = st.session_state.mqtt_cfg.get("cellular_baud_rate", 115200)
                baud_index = baud_options.index(saved_baud) if saved_baud in baud_options else 4
                cp, cb, cbtn = st.columns([0.45, 0.3, 0.25])
                with cp:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">PORT</p>', unsafe_allow_html=True)
                    cell_port = st.selectbox("COM", ports, index=port_index, key="cell_com_port_new", label_visibility="collapsed", disabled=cell_connected)
                with cb:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">BAUDRATE</p>', unsafe_allow_html=True)
                    cell_baud = st.selectbox("Baud", baud_options, index=baud_index, key="cell_baud_new", label_visibility="collapsed", disabled=cell_connected)
                with cbtn:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">&nbsp;</p>', unsafe_allow_html=True)
                    if not cell_connected:
                        st.button("🔌 Connect", width="stretch", type="primary", on_click=cellular_mqtt.handle_com_connect, args=(cell_port, cell_baud), key="cell_connect_new")
                    else:
                        st.button("🛑 Disconnect", width="stretch", type="secondary", on_click=cellular_mqtt.handle_com_disconnect, key="cell_disconnect_new")

            # DTU MQTT Provisioning
            with st.container(border=True):
                st.markdown('<p class="metric-label" style="margin:0 0 12px 0">🚀 DTU MQTT PROVISIONING</p>', unsafe_allow_html=True)
                pi_ip, pi_port, pi_cid = st.columns([0.4, 0.2, 0.4])
                with pi_ip:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">BROKER IP</p>', unsafe_allow_html=True)
                    prov_ip = st.text_input("Broker IP", value=st.session_state.mqtt_cfg.get("cellular_ip", "202.59.9.164"), key="prov_ip_new", label_visibility="collapsed")
                with pi_port:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">PORT</p>', unsafe_allow_html=True)
                    prov_port = st.text_input("Broker Port", value=st.session_state.mqtt_cfg.get("cellular_port", "1883"), key="prov_port_new", label_visibility="collapsed")
                with pi_cid:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">CLIENT ID</p>', unsafe_allow_html=True)
                    prov_cid = st.text_input("DTU Client ID", value=st.session_state.mqtt_cfg.get("cellular_cid", "nano_dtu_001"), key="prov_cid_new", label_visibility="collapsed")
                pu, pp = st.columns(2)
                with pu:
                    st.markdown('<p class="metric-label" style="margin:12px 0 0 0">USERNAME</p>', unsafe_allow_html=True)
                    prov_user = st.text_input("DTU User", value=st.session_state.mqtt_cfg.get("cellular_user", ""), key="prov_user_new", label_visibility="collapsed", placeholder="Optional")
                with pp:
                    st.markdown('<p class="metric-label" style="margin:12px 0 0 0">PASSWORD</p>', unsafe_allow_html=True)
                    prov_pwd = st.text_input("DTU Pwd", value=st.session_state.mqtt_cfg.get("cellular_pwd", ""), type="password", key="prov_pwd_new", label_visibility="collapsed", placeholder="Optional")
                st.button(
                    "🚀 One-Click Provision",
                    width="stretch", type="primary",
                    disabled=not cell_connected or st.session_state.cell_provisioning,
                    on_click=lambda: [save_current_mqtt_config(), cellular_mqtt.handle_provision()],
                    key="cell_provision_new",
                    help="Apply config to DTU"
                )

            # SUBSCRIPTION MANAGEMENT
            with st.container(border=True):
                st.markdown('<p class="metric-label" style="margin:0 0 12px 0">SUBSCRIPTION MANAGEMENT</p>', unsafe_allow_html=True)
                cs1, cs2, cs3 = st.columns([0.6, 0.15, 0.25])
                with cs1:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">TOPIC</p>', unsafe_allow_html=True)
                    prov_sub = st.text_input("DTU Sub", key="prov_sub_new", label_visibility="collapsed")
                with cs2:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">QOS</p>', unsafe_allow_html=True)
                    prov_sub_qos = st.selectbox("Sub QoS", [0, 1, 2], key="prov_sub_qos_new", label_visibility="collapsed")
                with cs3:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">&nbsp;</p>', unsafe_allow_html=True)
                    st.button("➕ Subscribe", width="stretch", disabled=not cell_connected, key="cell_sub_btn_new", on_click=cellular_mqtt.handle_dtu_update_sub, args=(prov_sub, prov_sub_qos))
                
                hw_subs = st.session_state.get("cell_hw_subs")
                hw_pub = st.session_state.get("cell_hw_pub")
                if hw_subs is not None:
                    if hw_subs:
                        sub_items = " | ".join([f"SUB{s['slot']}: {s['topic']} (Q{s['qos']})" for s in hw_subs])
                        st.markdown(f'<p class="metric-label" style="margin:12px 0 4px 0">ACTIVE ({len(hw_subs)}): <span style="font-weight:normal;color:#888;">{sub_items}</span></p>', unsafe_allow_html=True)
                        active_topics = [f"SUB{s['slot']}: {s['topic']}" for s in hw_subs]
                        cus1, cus2 = st.columns([0.75, 0.25])
                        with cus1:
                            st.selectbox("Remove", active_topics, key="cell_unsub_select_new_1", label_visibility="collapsed")
                        with cus2:
                            st.button("➖ Unsub", width="stretch", key="cell_unsub_btn_new_1", disabled=not cell_connected, on_click=cellular_mqtt.handle_dtu_unsubscribe)
                    else:
                        st.markdown('<p class="metric-label" style="margin:12px 0 4px 0">ACTIVE (0): <span style="font-weight:normal;color:#888;">None (verified from HW)</span></p>', unsafe_allow_html=True)
                        cus1, cus2 = st.columns([0.75, 0.25])
                        with cus1:
                            st.selectbox("Remove", ["None"], key="cell_unsub_select_new_2", label_visibility="collapsed", disabled=True)
                        with cus2:
                            st.button("➖ Unsub", width="stretch", key="cell_unsub_btn_new_2", disabled=True)
                    if hw_pub:
                        st.markdown(f'<p class="metric-label" style="margin:8px 0 0 0">📤 HW PUB: <span style="font-weight:normal;color:#888;">{hw_pub["topic"]} (Q{hw_pub["qos"]})</span></p>', unsafe_allow_html=True)
                else:
                    active_dtu_sub = st.session_state.get("cell_active_sub")
                    active_dtu_qos = st.session_state.get("cell_active_qos")
                    if active_dtu_sub:
                        st.markdown(f'<p class="metric-label" style="margin:12px 0 4px 0">ACTIVE (1): <span style="font-weight:normal;color:#888;">{active_dtu_sub} (Q{active_dtu_qos})</span></p>', unsafe_allow_html=True)
                        cus1, cus2 = st.columns([0.75, 0.25])
                        with cus1:
                            st.selectbox("Remove", [active_dtu_sub], key="cell_unsub_select_new_3", label_visibility="collapsed")
                        with cus2:
                            st.button("➖ Unsub", width="stretch", key="cell_unsub_btn_new_3", disabled=not cell_connected, on_click=cellular_mqtt.handle_dtu_unsubscribe)
                    else:
                        st.markdown('<p class="metric-label" style="margin:12px 0 4px 0">ACTIVE (0): <span style="font-weight:normal;color:#888;">None</span></p>', unsafe_allow_html=True)
                        cus1, cus2 = st.columns([0.75, 0.25])
                        with cus1:
                            st.selectbox("Remove", ["None"], key="cell_unsub_select_new_4", label_visibility="collapsed", disabled=True)
                        with cus2:
                            st.button("➖ Unsub", width="stretch", key="cell_unsub_btn_new_4", disabled=True)

            # PUBLISH MESSAGE
            with st.container(border=True):
                st.markdown('<p class="metric-label" style="margin:0 0 12px 0">PUBLISH MESSAGE</p>', unsafe_allow_html=True)
                pt, pq = st.columns([0.8, 0.2])
                with pt:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">TOPIC (Provisioned)</p>', unsafe_allow_html=True)
                    prov_pub = st.text_input("DTU Pub", value=st.session_state.mqtt_cfg.get("cellular_pub_topic", "nanopd/dtu/tx"), key="prov_pub_new", label_visibility="collapsed")
                with pq:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">QOS</p>', unsafe_allow_html=True)
                    st.selectbox("Pub QoS", [0, 1, 2], key="prov_pub_qos_new", label_visibility="collapsed", index=st.session_state.mqtt_cfg.get("cellular_pub_qos", 0))

            # MODBUS RTU PANEL (New Container)
            with st.container(border=True):
                st.markdown('<p class="metric-label" style="margin:0 0 12px 0">📋 MODBUS RTU CONFIGURATION</p>', unsafe_allow_html=True)
                
                m1, m2 = st.columns(2)
                with m1:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">DEVICE ID (HEX | DEC)</p>', unsafe_allow_html=True)
                    mh_col, md_col = st.columns(2)
                    with mh_col:
                        st.text_input("ID HEX", key="cell_modbus_id_hex", on_change=update_cell_modbus_id_from_hex, label_visibility="collapsed")
                    with md_col:
                        st.text_input("ID DEC", key="cell_modbus_id_dec", on_change=update_cell_modbus_id_from_dec, label_visibility="collapsed")
                with m2:
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
                    st.selectbox("Func", modbus_funcs, key="cell_modbus_func", label_visibility="collapsed")

                m3, m4, m5 = st.columns(3)
                with m3:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">START ADDR (HEX | DEC)</p>', unsafe_allow_html=True)
                    sah_col, sad_col = st.columns(2)
                    with sah_col:
                        st.text_input("Addr HEX", key="cell_modbus_addr_hex", on_change=update_cell_modbus_addr_from_hex, label_visibility="collapsed")
                    with sad_col:
                        st.text_input("Addr DEC", key="cell_modbus_addr_dec", on_change=update_cell_modbus_addr_from_dec, label_visibility="collapsed")
                with m4:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">QUANTITY (DEC)</p>', unsafe_allow_html=True)
                    st.number_input("Qty", min_value=1, max_value=125, key="cell_modbus_qty", label_visibility="collapsed")
                with m5:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">&nbsp;</p>', unsafe_allow_html=True)
                    st.button("⚙️ Set DTU Modbus", width="stretch", type="secondary", on_click=cellular_mqtt.handle_setup_dtu_modbus, help="Configure DTU for Modbus via AT commands")

            # POLLING CONTAINER
            with st.container(border=True):
                st.markdown('<p class="metric-label" style="margin:0 0 12px 0">🔄 POLLING CONFIGURATION</p>', unsafe_allow_html=True)
                
                tt_c1, tt_c2 = st.columns(2)
                with tt_c1:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">CYCLE TIME (s)</p>', unsafe_allow_html=True)
                    st.number_input("Cycle", min_value=1, max_value=3600, value=None, key="cell_task_cycle", label_visibility="collapsed", help="Polling cycle time")
                with tt_c2:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">INTERVAL (ms)</p>', unsafe_allow_html=True)
                    st.number_input("Interval", min_value=10, max_value=5000, value=None, key="cell_task_interval", label_visibility="collapsed", help="Delay between each command")

                st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)

                import pandas as pd
                polling_list = st.session_state.get("cell_polling_list")
                if polling_list is None:
                    polling_list = []
                df = pd.DataFrame(polling_list)
                if df.empty:
                    df = pd.DataFrame(columns=["Index", "Command"])
                edited_df = st.data_editor(
                    df,
                    num_rows="dynamic",
                    key="cell_polling_editor",
                    width='stretch',
                    hide_index=True
                )
                st.session_state.cell_polling_list = edited_df.to_dict('records')
                
                pc1, pc2 = st.columns(2)
                with pc1:
                    st.button("📥 Check Polling List", width="stretch", disabled=not cell_connected, on_click=cellular_mqtt.handle_check_polling_list)
                with pc2:
                    if st.button("📤 Send Polling List", width="stretch", disabled=not cell_connected):
                        cellular_mqtt.handle_send_polling_list(st.session_state.get("cell_polling_list", []))
                        st.rerun()


    with cr:
        with st.container(height=760, border=False):
            # Cellular Logs
            with st.container(border=True):
                st.markdown('<div class="layout-mcu-marker" style="display:none;"></div>', unsafe_allow_html=True)
                tc2, mc2, bc2 = st.columns([0.4, 0.4, 0.2])
                with tc2:
                    st.markdown('<p class="metric-label" style="margin:0">MESSAGE LOGS</p>', unsafe_allow_html=True)
                with mc2:
                    st.radio("Log Format", ["ASCII", "HEX"], horizontal=True, label_visibility="collapsed", key="cell_log_format")
                with bc2:
                    st.button("🗑️ Clear", width='stretch', key="clear_cell_log_new", on_click=cellular_mqtt.handle_clear_logs)
                
                # Format logs dynamically based on selected format
                cell_log_placeholder = st.empty()
                display_lines = []
                log_format = st.session_state.get("cell_log_format", "ASCII")
                for log in st.session_state.cell_logs:
                    if isinstance(log, dict):
                        direction = log.get("dir", "??")
                        raw_data = log.get("data", b"")
                        t = log.get("time", 0.0)
                        
                        t_str = ""
                        if t > 0:
                            dt = time.localtime(t)
                            ms = int((t % 1) * 1000)
                            t_str = f"[{dt.tm_hour:02d}:{dt.tm_min:02d}:{dt.tm_sec:02d}.{ms:03d}] "
                        
                        if log_format == "HEX":
                            formatted = raw_data.hex(' ').upper()
                        else:
                            formatted = raw_data.decode('utf-8', errors='replace').replace('\r', '\\r').replace('\n', '\\n')
                            
                        prefix = ">>" if direction == "TX" else "<<" if direction == "RX" else ""
                        display_lines.append(f"{t_str}{direction}{prefix} {formatted}")
                    else:
                        # Fallback for old logs stored as strings
                        display_lines.append(log)
                        
                if not display_lines:
                    display_lines = [""]
                    
                cell_log_placeholder.code("\n".join(display_lines), language="text")

                # Auto-scroll logs to bottom (DOS-style)
                if st.session_state.cell_logs:
                    st.html("""
                        <script>
                        (function() {
                            var parentDoc = window.parent && window.parent.document ? window.parent.document : document;
                            function scrollLogsToBottom() {
                                var markers = parentDoc.querySelectorAll('.layout-mcu-marker');
                                markers.forEach(function(marker) {
                                    var block = marker.closest('[data-testid="stVerticalBlock"]');
                                    if (block) {
                                        var pre = block.querySelector('pre');
                                        if (pre) pre.scrollTop = pre.scrollHeight;
                                    }
                                });
                            }
                            scrollLogsToBottom();
                            setTimeout(scrollLogsToBottom, 100);
                            setTimeout(scrollLogsToBottom, 300);
                            setTimeout(scrollLogsToBottom, 600);
                        })();
                        </script>
                    """)

            # PAYLOAD & ACTIONS
            with st.container(border=True):
                st.markdown('<p class="metric-label" style="margin:0 0 12px 0">PAYLOAD</p>', unsafe_allow_html=True)
                cell_payload = st.text_input("Payload", value=st.session_state.mqtt_cfg.get("cellular_payload", "Hello from DTU!"), key="cell_payload_new", label_visibility="collapsed")
                ca1, ca2 = st.columns([0.5, 0.5])
                with ca1:
                    st.button("📤 Publish", width="stretch", type="primary", disabled=not cell_connected, key="cell_send_new", on_click=cellular_mqtt.handle_send_data)
                with ca2:
                    st.button("📡 Publish Modbus", width="stretch", type="primary", disabled=not cell_connected, key="cell_modbus_pub_new", on_click=cellular_mqtt.handle_publish_modbus, help="Build Modbus RTU frame and publish via MQTT")

# Automatically save the current configuration to config.json at the end of each rerun
save_current_mqtt_config()

# ─── Auto-Read Loops ─────────────────────────────────────────────────────────
needs_rerun = False
if st.session_state.mqtt_auto_refresh:
    needs_rerun = True
if cell_connected:
    cellular_mqtt.handle_read_serial()
    needs_rerun = True
if needs_rerun:
    time.sleep(0.2)
    st.rerun()

