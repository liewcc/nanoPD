import streamlit as st
import time
import paho.mqtt.client as mqtt
from utils.style_utils import apply_global_css
from utils.config_utils import load_ui_config
from utils import cellular_mqtt
import os
import json
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
        "cellular_data_bits": get_val("cell_databits_new", "cellular_data_bits", 8),
        "cellular_parity": get_val("cell_parity_new", "cellular_parity", "None"),
        "cellular_stop_bits": get_val("cell_stopbits_new", "cellular_stop_bits", 1),
        "inet_log_format": get_val("inet_log_format", "inet_log_format", "Auto"),
        "cell_log_format": get_val("cell_log_format", "cell_log_format", "Auto"),
        "cell_modbus_id_hex": get_val("cell_modbus_id_hex", "cell_modbus_id_hex", "0x01"),
        "cell_modbus_id_dec": get_val("cell_modbus_id_dec", "cell_modbus_id_dec", "1"),
        "cell_modbus_func": get_val("cell_modbus_func", "cell_modbus_func", "03 (Read Holding Registers)"),
        "cell_modbus_addr_hex": get_val("cell_modbus_addr_hex", "cell_modbus_addr_hex", "0x0000"),
        "cell_modbus_addr_dec": get_val("cell_modbus_addr_dec", "cell_modbus_addr_dec", "0"),
        "cell_modbus_qty": get_val("cell_modbus_qty", "cell_modbus_qty", 1),
        "cell_enable_identifier": get_val("cell_enable_identifier", "cell_enable_identifier", True),
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
    state_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Internet_MQTT_state.jsonl"))
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            obj = json.loads(line.strip())
                            if "msg" in obj:
                                st.session_state.mqtt_logs.append({"msg": obj["msg"]})
                            else:
                                st.session_state.mqtt_logs.append({
                                    "time": obj["time"],
                                    "dir": obj["dir"],
                                    "data": bytes.fromhex(obj["data_hex"])
                                })
                        except:
                            pass
            st.session_state.mqtt_logs = st.session_state.mqtt_logs[-100:]
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
    st.session_state.inet_log_format = st.session_state.mqtt_cfg.get("inet_log_format", "Auto")
if 'cell_log_format' not in st.session_state:
    st.session_state.cell_log_format = st.session_state.mqtt_cfg.get("cell_log_format", "Auto")
if 'cell_enable_identifier' not in st.session_state:
    st.session_state.cell_enable_identifier = st.session_state.mqtt_cfg.get("cell_enable_identifier", True)

if 'known_at_patterns' not in st.session_state:
    known_patterns = {"+++", "atk", "ATK", "OK", "ERROR", "AT"}
    param_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "all parameter.txt"))
    if os.path.exists(param_file):
        try:
            with open(param_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        if line.startswith("AT+") or line.startswith("+"):
                            cmd_part = line.split(':')[0].split('=')[0]
                            known_patterns.add(cmd_part)
        except:
            pass
    st.session_state.known_at_patterns = known_patterns

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
            display: flex !important; flex-direction: column-reverse !important;
        }}
        /* Zero out Streamlit default bottom padding so no empty space appears below containers */
        section[data-testid="stMain"] > div {{ padding-bottom: 0 !important; }}
        div[data-testid="block-container"] {{ padding-bottom: 0 !important; }}
        div[data-testid="stTabPanel"] {{ padding-bottom: 0 !important; }}
        
        /* Compact code block styling for one-line display with copy button */
        div[data-testid="stElementContainer"]:has(.compact-code-marker) + div[data-testid="stElementContainer"] div[data-testid="stCode"] {{
            width: fit-content !important;
        }}
        div[data-testid="stElementContainer"]:has(.compact-code-marker) + div[data-testid="stElementContainer"] div[data-testid="stCode"] pre {{
            width: fit-content !important;
            height: auto !important;
            min-height: unset !important;
            padding: 6px 12px !important;
            margin: 0 !important;
            display: block !important;
            border: 1px solid rgba(255,255,255,0.1);
            background-color: rgba(255,255,255,0.05);
        }}
        div[data-testid="stElementContainer"]:has(.compact-code-marker) + div[data-testid="stElementContainer"] div[data-testid="stCode"] [data-testid="stElementToolbar"] {{
            top: 2px !important;
            right: 2px !important;
        }}
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
            "log_file": os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Internet_MQTT.log")),
            "state_file": os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Internet_MQTT_state.jsonl"))
        }
        client.user_data_set(shared_state)
        if user:
            client.username_pw_set(user, pwd)

        def on_connect_cb(c, userdata, flags, rc, props):
            if rc == 0:
                userdata["state_obj"]["status"] = "connected"
                _now = time.time()
                _t = time.localtime(_now)
                _ms = int((_now % 1) * 1000)
                _ts = f"[{_t.tm_hour:02d}:{_t.tm_min:02d}:{_t.tm_sec:02d}.{_ms:03d}]"
                msg_dict = {"msg": f"{_ts} SY>> Connected"}
                userdata["logs"].append(msg_dict)
                try:
                    with open(userdata.get("state_file", "Internet_MQTT_state.jsonl"), "a", encoding="utf-8") as f:
                        f.write(json.dumps(msg_dict) + "\n")
                except:
                    pass
                for t, q in userdata["subscriptions"].items():
                    c.subscribe(t, q)
            else:
                userdata["state_obj"]["status"] = f"refused:{rc}"
                _now = time.time()
                _t = time.localtime(_now)
                _ms = int((_now % 1) * 1000)
                _ts = f"[{_t.tm_hour:02d}:{_t.tm_min:02d}:{_t.tm_sec:02d}.{_ms:03d}]"
                msg_dict = {"msg": f"{_ts} SY>> Connection refused! Reason code: {rc}"}
                userdata["logs"].append(msg_dict)
                try:
                    with open(userdata.get("state_file", "Internet_MQTT_state.jsonl"), "a", encoding="utf-8") as f:
                        f.write(json.dumps(msg_dict) + "\n")
                except:
                    pass

        def on_disconnect_cb(c, userdata, flags, rc, props):
            userdata["state_obj"]["status"] = "disconnected"
            _now = time.time()
            _t = time.localtime(_now)
            _ms = int((_now % 1) * 1000)
            _ts = f"[{_t.tm_hour:02d}:{_t.tm_min:02d}:{_t.tm_sec:02d}.{_ms:03d}]"
            msg_dict = {"msg": f"{_ts} SY>> Disconnected. Reason code: {rc}"}
            userdata["logs"].append(msg_dict)
            try:
                with open(userdata.get("state_file", "Internet_MQTT_state.jsonl"), "a", encoding="utf-8") as f:
                        f.write(json.dumps(msg_dict) + "\n")
            except:
                pass

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
                state_entry = json.dumps({
                    "time": log_dict["time"],
                    "dir": log_dict["dir"],
                    "data_hex": log_dict["data"].hex()
                })
                with open(userdata.get("state_file", "Internet_MQTT_state.jsonl"), "a", encoding="utf-8") as f:
                    f.write(state_entry + "\n")
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
            state_entry = json.dumps({
                "time": log_dict["time"],
                "dir": log_dict["dir"],
                "data_hex": log_dict["data"].hex()
            })
            state_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Internet_MQTT_state.jsonl"))
            with open(state_path, "a", encoding="utf-8") as f:
                f.write(state_entry + "\n")
        except:
            pass
        save_current_mqtt_config()
    else:
        st.toast("Cannot publish: Not connected.", icon="❌")

def handle_clear_logs():
    st.session_state.mqtt_logs.clear()
    
    # Clear both the readable log file and the JSONL state file
    log_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Internet_MQTT.log"))
    state_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Internet_MQTT_state.jsonl"))
    
    try:
        if os.path.exists(log_file):
            open(log_file, "w", encoding="utf-8").close()
    except:
        pass
        
    try:
        if os.path.exists(state_file):
            open(state_file, "w", encoding="utf-8").close()
    except:
        pass
        
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
                if not is_connected:
                    st.button("🔌 Connect", width="stretch", type="primary", on_click=handle_connect, args=(broker, port, client_id, username, password), key="inet_connect")
                else:
                    st.button("🛑 Disconnect", width="stretch", type="secondary", on_click=handle_disconnect, key="inet_disconnect")

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
                    st.radio("Log Format", ["ASCII", "HEX", "Auto"], horizontal=True, label_visibility="collapsed", key="inet_log_format")
                with bc:
                    st.button("🗑️ Clear", width='stretch', key="clear_mqtt_log", on_click=handle_clear_logs)
                
                inet_log_placeholder = st.empty()
                display_lines = []
                log_format = st.session_state.get("inet_log_format", "Auto")
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
                            
                            fmt = log_format
                            custom_formatted = None
                            modbus_packets = []
                            if fmt == "Auto":
                                import re
                                m = re.match(br'^(<\d+>)(.*)', raw_data)
                                if m:
                                    prefix_str = m.group(1).decode('ascii')
                                    hex_str = m.group(2).hex(' ').upper()
                                    custom_formatted = f"{prefix_str} {hex_str}"
                                elif b'\nTopic:' in raw_data or b'Please check GPRS' in raw_data:
                                    fmt = "ASCII"
                                else:
                                    is_at = False
                                    try:
                                        text = raw_data.decode('utf-8')
                                        for line in text.replace('\r', '\n').split('\n'):
                                            line = line.strip()
                                            if not line:
                                                continue
                                            cmd_part = line.split(':')[0].split('=')[0]
                                            if cmd_part in st.session_state.get('known_at_patterns', set()) or line in st.session_state.get('known_at_patterns', set()) or line.upper().startswith('AT') or line.startswith('+'):
                                                is_at = True
                                                break
                                    except:
                                        pass
                                        
                                    if is_at:
                                        fmt = "ASCII"
                                    else:
                                        if len(raw_data) >= 4:
                                            if cellular_mqtt.calculate_crc16(raw_data[:-2]) == raw_data[-2:]:
                                                modbus_packets = [raw_data]
                                            else:
                                                offset = 0
                                                while offset + 4 <= len(raw_data):
                                                    fc = raw_data[offset + 1]
                                                    candidates = [8]
                                                    if fc in (1, 2, 3, 4) and offset + 2 < len(raw_data):
                                                        candidates.append(3 + raw_data[offset + 2] + 2)
                                                    elif fc in (15, 16) and offset + 6 < len(raw_data):
                                                        candidates.append(7 + raw_data[offset + 6] + 2)
                                                    found = False
                                                    for l in set(candidates):
                                                        if offset + l <= len(raw_data):
                                                            pkt = raw_data[offset:offset+l]
                                                            if cellular_mqtt.calculate_crc16(pkt[:-2]) == pkt[-2:]:
                                                                modbus_packets.append(pkt)
                                                                offset += l
                                                                found = True
                                                                break
                                                    if not found: break
                                        
                                        if modbus_packets:
                                            fmt = "MODBUS"
                                        else:
                                            try:
                                                decoded_text = raw_data.decode('utf-8')
                                                # Allow all printable ASCII (32-126) plus common whitespace
                                                if decoded_text and all(32 <= ord(c) <= 126 or c in '\r\n\t' for c in decoded_text):
                                                    fmt = "ASCII"
                                                else:
                                                    fmt = "HEX"
                                            except:
                                                fmt = "HEX"

                            prefix = ">>" if direction == "TX" else "<<" if direction == "RX" else ""
                            if custom_formatted is not None:
                                display_lines.append(f"{t_str}{direction}{prefix} {custom_formatted}")
                            elif fmt == "MODBUS":
                                for pkt in modbus_packets:
                                    display_lines.append(f"{t_str}{direction}{prefix} {pkt.hex(' ').upper()}")
                            elif fmt == "HEX":
                                display_lines.append(f"{t_str}{direction}{prefix} {raw_data.hex(' ').upper()}")
                            else:
                                text = raw_data.decode('utf-8', errors='replace')
                                for l in text.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
                                    if l.strip():
                                        display_lines.append(f"{t_str}{direction}{prefix} {l}")
                    else:
                        display_lines.append(log)
                
                if not display_lines:
                    display_lines = [""]
                inet_log_placeholder.code("\n".join(display_lines), language="text")



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
                db_opts = [5, 6, 7, 8]
                saved_db = st.session_state.mqtt_cfg.get("cellular_data_bits", 8)
                db_idx = db_opts.index(saved_db) if saved_db in db_opts else 3
                
                pa_opts = ["None", "Even", "Odd", "Mark", "Space"]
                saved_pa = st.session_state.mqtt_cfg.get("cellular_parity", "None")
                pa_idx = pa_opts.index(saved_pa) if saved_pa in pa_opts else 0
                
                sb_opts = [1, 1.5, 2]
                saved_sb = st.session_state.mqtt_cfg.get("cellular_stop_bits", 1)
                sb_idx = sb_opts.index(saved_sb) if saved_sb in sb_opts else 0

                c_bd, c_db, c_pa, c_sb = st.columns([0.25, 0.25, 0.25, 0.25])
                with c_bd:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">BAUDRATE</p>', unsafe_allow_html=True)
                    cell_baud = st.selectbox("Baud", baud_options, index=baud_index, key="cell_baud_new", label_visibility="collapsed", disabled=cell_connected)
                with c_db:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">DATA BITS</p>', unsafe_allow_html=True)
                    st.selectbox("Data Bits", db_opts, index=db_idx, key="cell_databits_new", label_visibility="collapsed", disabled=cell_connected)
                with c_pa:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">PARITY</p>', unsafe_allow_html=True)
                    st.selectbox("Parity", pa_opts, index=pa_idx, key="cell_parity_new", label_visibility="collapsed", disabled=cell_connected)
                with c_sb:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">STOP BITS</p>', unsafe_allow_html=True)
                    st.selectbox("Stop Bits", sb_opts, index=sb_idx, key="cell_stopbits_new", label_visibility="collapsed", disabled=cell_connected)

                cp, cbtn = st.columns([0.6, 0.4])
                with cp:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">PORT</p>', unsafe_allow_html=True)
                    cell_port = st.selectbox("COM", ports, index=port_index, key="cell_com_port_new", label_visibility="collapsed", disabled=cell_connected)
                with cbtn:
                    st.markdown('<p class="metric-label" style="margin:4px 0 0 0">&nbsp;</p>', unsafe_allow_html=True)
                    if not cell_connected:
                        st.button("🔌 Connect", width="stretch", type="primary", on_click=cellular_mqtt.handle_com_connect, args=(cell_port, cell_baud), key="cell_connect_new")
                    else:
                        st.button("🛑 Disconnect", width="stretch", type="secondary", on_click=cellular_mqtt.handle_com_disconnect, key="cell_disconnect_new")

            # LTE & Network Check
            with st.container(border=True):
                st.markdown('<p class="metric-label" style="margin:0 0 12px 0">📡 LTE & NETWORK INFO</p>', unsafe_allow_html=True)
                n1, n2 = st.columns([0.7, 0.3])
                with n1:
                    st.markdown('<div style="font-size:0.85rem;color:#888;margin-top:8px;">Query device info, signal strength, and network status.</div>', unsafe_allow_html=True)
                with n2:
                    st.button("🔍 Check Network", width="stretch", type="secondary", disabled=not cell_connected, on_click=cellular_mqtt.handle_check_network, key="cell_check_net_btn")
                
                net_info = st.session_state.get("cell_network_info")
                if net_info:
                    st.divider()
                    nc1, nc2 = st.columns(2)
                    with nc1:
                        st.markdown(f'<p class="metric-label" style="margin:0">MODULE</p><div style="font-size:0.9rem;font-weight:500;margin-bottom:8px;font-family:Consolas,monospace;">{net_info.get("MODULE", "N/A")}</div>', unsafe_allow_html=True)
                        st.markdown(f'<p class="metric-label" style="margin:0">SYSINFO</p><div style="font-size:0.9rem;font-weight:500;margin-bottom:8px;font-family:Consolas,monospace;">{net_info.get("SYSINFO", "N/A")}</div>', unsafe_allow_html=True)
                        st.markdown(f'<p class="metric-label" style="margin:0">ICCID</p><div style="font-size:0.9rem;font-weight:500;margin-bottom:8px;font-family:Consolas,monospace;">{net_info.get("ICCID", "N/A")}</div>', unsafe_allow_html=True)
                        st.markdown(f'<p class="metric-label" style="margin:0">CSQ (SIGNAL)</p><div style="font-size:0.9rem;font-weight:500;margin-bottom:8px;font-family:Consolas,monospace;">{net_info.get("CSQ", "N/A")}</div>', unsafe_allow_html=True)
                    with nc2:
                        st.markdown(f'<p class="metric-label" style="margin:0">SN</p><div style="font-size:0.9rem;font-weight:500;margin-bottom:8px;font-family:Consolas,monospace;">{net_info.get("SN", "N/A")}</div>', unsafe_allow_html=True)
                        st.markdown(f'<p class="metric-label" style="margin:0">IMEI</p><div style="font-size:0.9rem;font-weight:500;margin-bottom:8px;font-family:Consolas,monospace;">{net_info.get("IMEI", "N/A")}</div>', unsafe_allow_html=True)
                        st.markdown(f'<p class="metric-label" style="margin:0">IMSI</p><div style="font-size:0.9rem;font-weight:500;margin-bottom:8px;font-family:Consolas,monospace;">{net_info.get("IMSI", "N/A")}</div>', unsafe_allow_html=True)
                        st.markdown(f'<p class="metric-label" style="margin:0">CLK</p><div style="font-size:0.9rem;font-weight:500;margin-bottom:8px;font-family:Consolas,monospace;">{net_info.get("CLK", "N/A")}</div>', unsafe_allow_html=True)


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
                st.markdown('<p class="metric-label" style="margin:0 0 12px 0">SUBSCRIPTION MANAGEMENT (MAX 4 SLOTS)</p>', unsafe_allow_html=True)
                
                subs_ui = st.session_state.get("cell_subs_ui", [{"topic": "", "qos": 0} for _ in range(4)])
                
                # Header
                h1, h2, h3, h4 = st.columns([0.45, 0.15, 0.2, 0.2])
                with h1: st.markdown('<p class="metric-label" style="margin:0">TOPIC</p>', unsafe_allow_html=True)
                with h2: st.markdown('<p class="metric-label" style="margin:0">QOS</p>', unsafe_allow_html=True)
                with h3: st.markdown('<p class="metric-label" style="margin:0">&nbsp;</p>', unsafe_allow_html=True)
                with h4: st.markdown('<p class="metric-label" style="margin:0">&nbsp;</p>', unsafe_allow_html=True)

                for i in range(4):
                    sub = subs_ui[i]
                    r1, r2, r3, r4 = st.columns([0.45, 0.15, 0.2, 0.2])
                    with r1:
                        # Use a unique key and value from state
                        topic_val = st.text_input(f"T{i}", value=sub["topic"], key=f"cell_sub_t_{i}", label_visibility="collapsed")
                    with r2:
                        qos_val = st.selectbox(f"Q{i}", [0, 1, 2], index=int(sub["qos"]), key=f"cell_sub_q_{i}", label_visibility="collapsed")
                    with r3:
                        st.button("➕ Sub", key=f"btn_sub_{i}", width="stretch", disabled=not cell_connected, 
                                  on_click=cellular_mqtt.handle_dtu_update_sub, args=(i+1, topic_val, qos_val))
                    with r4:
                        st.button("➖ Unsub", key=f"btn_unsub_{i}", width="stretch", disabled=not cell_connected,
                                  on_click=cellular_mqtt.handle_dtu_unsubscribe, args=(i+1,))
                
                st.markdown('<div style="margin-top:12px;"></div>', unsafe_allow_html=True)
                st.button("🔄 Reload Subscriptions", width="stretch", type="secondary", 
                          disabled=not cell_connected, on_click=cellular_mqtt.handle_sync_hw_state,
                          help="Re-read all subscription slots from DTU hardware")

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

                m3, m4 = st.columns(2)
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

                # Dynamically generate Modbus RTU frame
                dev_id_str = st.session_state.get("cell_modbus_id_dec", "").strip()
                addr_str = st.session_state.get("cell_modbus_addr_dec", "").strip()
                qty_val = st.session_state.get("cell_modbus_qty")
                func_str = st.session_state.get("cell_modbus_func", "03")

                if dev_id_str and addr_str and qty_val is not None:
                    try:
                        dev_id = int(dev_id_str)
                        func_code = int(func_str.split(" ")[0], 16)
                        start_addr = int(addr_str)
                        quantity = int(qty_val)
                        
                        frame = bytearray()
                        frame.append(dev_id)
                        frame.append(func_code)
                        frame.append((start_addr >> 8) & 0xFF)
                        frame.append(start_addr & 0xFF)
                        frame.append((quantity >> 8) & 0xFF)
                        frame.append(quantity & 0xFF)
                        frame.extend(cellular_mqtt.calculate_crc16(frame))
                        
                        cmd_hex = frame.hex(' ').upper()
                        st.markdown('<p class="metric-label" style="margin:12px 0 4px 0">GENERATED COMMAND (HEX)</p>', unsafe_allow_html=True)
                        st.markdown('<div class="compact-code-marker" style="display:none;"></div>', unsafe_allow_html=True)
                        st.code(cmd_hex, language="text")
                    except ValueError:
                        pass

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

                st.checkbox("Enable Identifier (Append Key Name to data)", key="cell_enable_identifier", help="Enables AT+TASKDIST=\"1\" to prepend the Key Name to reported data")

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
                    st.radio("Log Format", ["ASCII", "HEX", "Auto"], horizontal=True, label_visibility="collapsed", key="cell_log_format")
                with bc2:
                    st.button("🗑️ Clear", width='stretch', key="clear_cell_log_new", on_click=cellular_mqtt.handle_clear_logs)
                
                # Format logs dynamically based on selected format
                cell_log_placeholder = st.empty()
                display_lines = []
                log_format = st.session_state.get("cell_log_format", "Auto")
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
                        
                        fmt = log_format
                        custom_formatted = None
                        modbus_packets = []
                        if fmt == "Auto":
                            import re
                            m = re.match(br'^(<\d+>)(.*)', raw_data)
                            if m:
                                prefix_str = m.group(1).decode('ascii')
                                hex_str = m.group(2).hex(' ').upper()
                                custom_formatted = f"{prefix_str} {hex_str}"
                            elif b'\nTopic:' in raw_data or b'Please check GPRS' in raw_data:
                                fmt = "ASCII"
                            else:
                                is_at = False
                                try:
                                    text = raw_data.decode('utf-8')
                                    for line in text.replace('\r', '\n').split('\n'):
                                        line = line.strip()
                                        if not line:
                                            continue
                                        cmd_part = line.split(':')[0].split('=')[0]
                                        if cmd_part in st.session_state.get('known_at_patterns', set()) or line in st.session_state.get('known_at_patterns', set()) or line.upper().startswith('AT') or line.startswith('+'):
                                            is_at = True
                                            break
                                except:
                                    pass
                                    
                                if is_at:
                                    fmt = "ASCII"
                                else:
                                    if len(raw_data) >= 4:
                                        if cellular_mqtt.calculate_crc16(raw_data[:-2]) == raw_data[-2:]:
                                            modbus_packets = [raw_data]
                                        else:
                                            offset = 0
                                            while offset + 4 <= len(raw_data):
                                                fc = raw_data[offset + 1]
                                                candidates = [8]
                                                if fc in (1, 2, 3, 4) and offset + 2 < len(raw_data):
                                                    candidates.append(3 + raw_data[offset + 2] + 2)
                                                elif fc in (15, 16) and offset + 6 < len(raw_data):
                                                    candidates.append(7 + raw_data[offset + 6] + 2)
                                                found = False
                                                for l in set(candidates):
                                                    if offset + l <= len(raw_data):
                                                        pkt = raw_data[offset:offset+l]
                                                        if cellular_mqtt.calculate_crc16(pkt[:-2]) == pkt[-2:]:
                                                            modbus_packets.append(pkt)
                                                            offset += l
                                                            found = True
                                                            break
                                                if not found: break
                                    
                                    if modbus_packets:
                                        fmt = "MODBUS"
                                    else:
                                        try:
                                            decoded_text = raw_data.decode('utf-8')
                                            # Allow all printable ASCII (32-126) plus common whitespace
                                            if decoded_text and all(32 <= ord(c) <= 126 or c in '\r\n\t' for c in decoded_text):
                                                fmt = "ASCII"
                                            else:
                                                fmt = "HEX"
                                        except:
                                            fmt = "HEX"

                        prefix = ">>" if direction == "TX" else "<<" if direction == "RX" else ""
                        if custom_formatted is not None:
                            display_lines.append(f"{t_str}{direction}{prefix} {custom_formatted}")
                        elif fmt == "MODBUS":
                            for pkt in modbus_packets:
                                display_lines.append(f"{t_str}{direction}{prefix} {pkt.hex(' ').upper()}")
                        elif fmt == "HEX":
                            display_lines.append(f"{t_str}{direction}{prefix} {raw_data.hex(' ').upper()}")
                        else:
                            text = raw_data.decode('utf-8', errors='replace')
                            for l in text.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
                                if l.strip():
                                    display_lines.append(f"{t_str}{direction}{prefix} {l}")
                    else:
                        # Fallback for old logs stored as strings
                        display_lines.append(log)
                        
                if not display_lines:
                    display_lines = [""]
                    
                cell_log_placeholder.code("\n".join(display_lines), language="text")



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

