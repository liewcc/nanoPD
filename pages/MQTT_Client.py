import streamlit as st
import time
import paho.mqtt.client as mqtt
from utils.style_utils import apply_global_css
from utils.config_utils import load_ui_config
from utils import cellular_mqtt

# ─── Session State Initialization ───────────────────────────────────────────
if "ui_cfg" not in st.session_state:
    st.session_state.ui_cfg = load_ui_config()

if 'mqtt_logs' not in st.session_state:
    st.session_state.mqtt_logs = []
if 'mqtt_client' not in st.session_state:
    st.session_state.mqtt_client = None
if 'mqtt_subscriptions' not in st.session_state:
    st.session_state.mqtt_subscriptions = {}
if 'mqtt_auto_refresh' not in st.session_state:
    st.session_state.mqtt_auto_refresh = False
if 'mqtt_shared_state' not in st.session_state:
    st.session_state.mqtt_shared_state = {"status": "disconnected"}


# Initialize Cellular MQTT state
cellular_mqtt.init_state()

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
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
            padding-bottom: 0 !important; margin-bottom: 0 !important;
        }}
        div[data-testid="stVerticalBlock"]:has(.layout-coding-marker),
        div[data-testid="stVerticalBlock"]:has(.layout-mcu-marker) {{
            overflow-y: hidden !important; scrollbar-width: none !important;
        }}
        div[data-testid="stVerticalBlock"]:has(.layout-coding-marker)::-webkit-scrollbar,
        div[data-testid="stVerticalBlock"]:has(.layout-mcu-marker)::-webkit-scrollbar {{
            display: none !important; width: 0 !important;
        }}
        div[data-testid="stVerticalBlock"]:has(.layout-mcu-marker) div[data-testid="stTextArea"] textarea {{
            height: var(--dynamic-ta-height, 350px) !important; resize: none !important;
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
            "state_obj": st.session_state.mqtt_shared_state
        }
        client.user_data_set(shared_state)
        if user:
            client.username_pw_set(user, pwd)

        def on_connect_cb(c, userdata, flags, rc, props):
            if rc == 0:
                userdata["state_obj"]["status"] = "connected"
                userdata["logs"].append("[System] Connected successfully!")
                for t, q in userdata["subscriptions"].items():
                    c.subscribe(t, q)
            else:
                userdata["state_obj"]["status"] = f"refused:{rc}"
                userdata["logs"].append(f"[System] Connection refused! Reason code: {rc}")

        def on_disconnect_cb(c, userdata, flags, rc, props):
            userdata["state_obj"]["status"] = "disconnected"
            userdata["logs"].append(f"[System] Disconnected. Reason code: {rc}")

        def on_message_cb(c, userdata, msg):
            try:
                payload = msg.payload.decode('utf-8', errors='replace')
            except:
                payload = msg.payload.hex()
            t = time.localtime()
            ms = int((time.time() % 1) * 1000)
            t_str = f"[{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}.{ms:03d}]"
            userdata["logs"].append(f"{t_str} [📥 {msg.topic}]: {payload}")
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
        st.toast(f"Unsubscribed from {topic}", icon="✅")

def handle_publish(topic, qos, payload):
    if not topic:
        st.toast("Topic is required.", icon="⚠️")
        return
    is_conn = st.session_state.mqtt_shared_state.get("status") == "connected"
    if st.session_state.mqtt_client and is_conn:
        st.session_state.mqtt_client.publish(topic, payload, qos)
        t = time.localtime()
        ms = int((time.time() % 1) * 1000)
        t_str = f"[{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}.{ms:03d}]"
        st.session_state.mqtt_logs.append(f"{t_str} [📤 {topic}]: {payload}")
        if len(st.session_state.mqtt_logs) > 100:
            st.session_state.mqtt_logs.pop(0)
    else:
        st.toast("Cannot publish: Not connected.", icon="❌")

def handle_clear_logs():
    st.session_state.mqtt_logs.clear()


# ═══════════════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════════════
tab_internet, tab_cellular = st.tabs(["🌐 Internet MQTT", "📶 Cellular MQTT"])
is_connected = st.session_state.mqtt_shared_state.get("status") == "connected"

# ─── TAB 1: INTERNET MQTT ───────────────────────────────────────────────────
with tab_internet:
    col_left, col_right = st.columns([1, 1])

    with col_left:
        with st.container(border=True):
            st.markdown('<p class="metric-label" style="margin:0 0 12px 0">BROKER CONFIGURATION</p>', unsafe_allow_html=True)
            c_host, c_port, c_cid = st.columns([0.4, 0.2, 0.4])
            with c_host:
                st.markdown('<p class="metric-label" style="margin:4px 0 0 0">HOST ADDRESS</p>', unsafe_allow_html=True)
                broker = st.text_input("Host", value="202.59.9.164", key="cfg_broker", label_visibility="collapsed")
            with c_port:
                st.markdown('<p class="metric-label" style="margin:4px 0 0 0">PORT</p>', unsafe_allow_html=True)
                port = st.number_input("Port", value=1883, min_value=1, max_value=65535, key="cfg_port", label_visibility="collapsed")
            with c_cid:
                st.markdown('<p class="metric-label" style="margin:4px 0 0 0">CLIENT ID</p>', unsafe_allow_html=True)
                client_id = st.text_input("Client ID", value="nanopd_mqtt_client", key="cfg_cid", label_visibility="collapsed")
            u_col, pw_col = st.columns(2)
            with u_col:
                st.markdown('<p class="metric-label" style="margin:12px 0 0 0">USERNAME</p>', unsafe_allow_html=True)
                username = st.text_input("Username", value="", key="cfg_user", label_visibility="collapsed", placeholder="Optional")
            with pw_col:
                st.markdown('<p class="metric-label" style="margin:12px 0 0 0">PASSWORD</p>', unsafe_allow_html=True)
                password = st.text_input("Password", value="", type="password", key="cfg_pwd", label_visibility="collapsed", placeholder="Optional")
            c1, c2, c3 = st.columns([0.4, 0.3, 0.3])
            with c1:
                if not is_connected:
                    st.button("🔌 Connect", width="stretch", type="primary", on_click=handle_connect, args=(broker, port, client_id, username, password), key="inet_connect")
                else:
                    st.button("🛑 Disconnect", width="stretch", type="secondary", on_click=handle_disconnect, key="inet_disconnect")
            with c2:
                if st.button("🔁 Auto", width="stretch", type="primary" if st.session_state.mqtt_auto_refresh else "secondary", key="inet_auto", help="Auto-refresh UI"):
                    st.session_state.mqtt_auto_refresh = not st.session_state.mqtt_auto_refresh
                    st.rerun()
            with c3:
                if is_connected:
                    st.markdown('<p style="color:#00C853; font-weight:bold; padding-top:8px;">🟢 CONNECTED</p>', unsafe_allow_html=True)
                else:
                    st.markdown('<p style="color:#FF5252; font-weight:bold; padding-top:8px;">🔴 DISCONNECTED</p>', unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown('<p class="metric-label" style="margin:0 0 12px 0">SUBSCRIPTION MANAGEMENT</p>', unsafe_allow_html=True)
            s1, s2, s3 = st.columns([0.6, 0.15, 0.25])
            with s1:
                st.markdown('<p class="metric-label" style="margin:4px 0 0 0">TOPIC</p>', unsafe_allow_html=True)
                sub_topic = st.text_input("Sub Topic", value="nanopd/test/#", key="cfg_sub_topic", label_visibility="collapsed")
            with s2:
                st.markdown('<p class="metric-label" style="margin:4px 0 0 0">QOS</p>', unsafe_allow_html=True)
                sub_qos = st.selectbox("Sub QoS", [0, 1, 2], key="cfg_sub_qos", label_visibility="collapsed")
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

    with col_right:
        with st.container(border=True):
            st.markdown('<div class="layout-mcu-marker" style="display:none;"></div>', unsafe_allow_html=True)
            tc, bc = st.columns([0.8, 0.2])
            with tc:
                st.markdown('<p class="metric-label" style="margin:0">MESSAGE LOGS</p>', unsafe_allow_html=True)
            with bc:
                st.button("🗑️ Clear", width='stretch', key="clear_mqtt_log", on_click=handle_clear_logs)
            inet_log_placeholder = st.empty()
            lines = st.session_state.mqtt_logs if st.session_state.mqtt_logs else ["(No messages received)"]
            inet_log_placeholder.text_area("Logs", value="\n".join(lines), height=350, label_visibility="collapsed", disabled=False)

        with st.container(border=True):
            st.markdown('<div class="layout-coding-marker" style="display:none;"></div><p class="metric-label" style="margin:0 0 12px 0">PUBLISH MESSAGE</p>', unsafe_allow_html=True)
            pt, pq = st.columns([0.8, 0.2])
            with pt:
                st.markdown('<p class="metric-label" style="margin:4px 0 0 0">TOPIC</p>', unsafe_allow_html=True)
                pub_topic = st.text_input("Pub Topic", value="nanopd/test/pub", key="cfg_pub_topic", label_visibility="collapsed")
            with pq:
                st.markdown('<p class="metric-label" style="margin:4px 0 0 0">QOS</p>', unsafe_allow_html=True)
                pub_qos = st.selectbox("Pub QoS", [0, 1, 2], key="cfg_pub_qos", label_visibility="collapsed")
            st.markdown('<p class="metric-label" style="margin:12px 0 0 0">PAYLOAD</p>', unsafe_allow_html=True)
            pub_payload = st.text_input("Payload", value='{"msg": "Hello NanoPD"}', key="cfg_pub_payload", label_visibility="collapsed")
            st.button("📤 Publish", width="stretch", type="primary", disabled=not is_connected, on_click=handle_publish, args=(pub_topic, pub_qos, pub_payload), key="inet_pub")

# ─── TAB 2: CELLULAR MQTT ───────────────────────────────────────────────────
with tab_cellular:
    cell_ser = st.session_state.cell_serial
    cell_connected = cell_ser is not None and cell_ser.is_open
    cl, cr = st.columns([1, 1])

    with cl:
        # COM Port Configuration
        with st.container(border=True):
            st.markdown('<p class="metric-label" style="margin:0 0 12px 0">COM PORT CONFIGURATION</p>', unsafe_allow_html=True)
            ports = cellular_mqtt.get_com_ports()
            if not ports:
                ports = ["None"]
            cp, cb, cbtn = st.columns([0.45, 0.3, 0.25])
            with cp:
                st.markdown('<p class="metric-label" style="margin:4px 0 0 0">PORT</p>', unsafe_allow_html=True)
                cell_port = st.selectbox("COM", ports, key="cell_com_port", label_visibility="collapsed", disabled=cell_connected)
            with cb:
                st.markdown('<p class="metric-label" style="margin:4px 0 0 0">BAUDRATE</p>', unsafe_allow_html=True)
                cell_baud = st.selectbox("Baud", [9600, 19200, 38400, 57600, 115200], index=4, key="cell_baud", label_visibility="collapsed", disabled=cell_connected)
            with cbtn:
                st.markdown('<p class="metric-label" style="margin:4px 0 0 0">&nbsp;</p>', unsafe_allow_html=True)
                if not cell_connected:
                    st.button("🔌 Connect", width="stretch", type="primary", on_click=cellular_mqtt.handle_com_connect, args=(cell_port, cell_baud), key="cell_connect")
                else:
                    st.button("🛑 Disconnect", width="stretch", type="secondary", on_click=cellular_mqtt.handle_com_disconnect, key="cell_disconnect")

        # DTU MQTT Provisioning
        with st.container(border=True):
            st.markdown('<p class="metric-label" style="margin:0 0 12px 0">🚀 DTU MQTT PROVISIONING</p>', unsafe_allow_html=True)
            pi_ip, pi_port, pi_cid = st.columns([0.4, 0.2, 0.4])
            with pi_ip:
                st.markdown('<p class="metric-label" style="margin:4px 0 0 0">BROKER IP</p>', unsafe_allow_html=True)
                prov_ip = st.text_input("Broker IP", value="202.59.9.164", key="prov_ip", label_visibility="collapsed")
            with pi_port:
                st.markdown('<p class="metric-label" style="margin:4px 0 0 0">PORT</p>', unsafe_allow_html=True)
                prov_port = st.text_input("Broker Port", value="1883", key="prov_port", label_visibility="collapsed")
            with pi_cid:
                st.markdown('<p class="metric-label" style="margin:4px 0 0 0">CLIENT ID</p>', unsafe_allow_html=True)
                prov_cid = st.text_input("DTU Client ID", value="nano_dtu_001", key="prov_cid", label_visibility="collapsed")
            pu, pp = st.columns(2)
            with pu:
                st.markdown('<p class="metric-label" style="margin:12px 0 0 0">USERNAME</p>', unsafe_allow_html=True)
                prov_user = st.text_input("DTU User", value="", key="prov_user", label_visibility="collapsed", placeholder="Optional")
            with pp:
                st.markdown('<p class="metric-label" style="margin:12px 0 0 0">PASSWORD</p>', unsafe_allow_html=True)
                prov_pwd = st.text_input("DTU Pwd", value="", type="password", key="prov_pwd", label_visibility="collapsed", placeholder="Optional")
            st.button(
                "🚀 One-Click Provision",
                width="stretch", type="primary",
                disabled=not cell_connected or st.session_state.cell_provisioning,
                on_click=cellular_mqtt.handle_provision,
                key="cell_provision"
            )

        # SUBSCRIPTION MANAGEMENT
        with st.container(border=True):
            st.markdown('<p class="metric-label" style="margin:0 0 12px 0">SUBSCRIPTION MANAGEMENT</p>', unsafe_allow_html=True)
            cs1, cs2, cs3 = st.columns([0.6, 0.15, 0.25])
            with cs1:
                st.markdown('<p class="metric-label" style="margin:4px 0 0 0">TOPIC</p>', unsafe_allow_html=True)
                prov_sub = st.text_input("DTU Sub", value="nanopd/dtu/rx", key="prov_sub", label_visibility="collapsed")
            with cs2:
                st.markdown('<p class="metric-label" style="margin:4px 0 0 0">QOS</p>', unsafe_allow_html=True)
                prov_sub_qos = st.selectbox("Sub QoS", [0, 1, 2], key="prov_sub_qos", label_visibility="collapsed")
            with cs3:
                st.markdown('<p class="metric-label" style="margin:4px 0 0 0">&nbsp;</p>', unsafe_allow_html=True)
                st.button("➕ Subscribe", width="stretch", disabled=not cell_connected, key="cell_sub_btn", on_click=cellular_mqtt.handle_dtu_update_sub, args=(prov_sub, prov_sub_qos))
            
            if 'cell_active_sub' not in st.session_state:
                st.session_state.cell_active_sub = "nanopd/dtu/rx"
            if 'cell_active_qos' not in st.session_state:
                st.session_state.cell_active_qos = 0
            
            active_dtu_sub = st.session_state.get("cell_active_sub")
            active_dtu_qos = st.session_state.get("cell_active_qos")
            
            if active_dtu_sub:
                st.markdown(f'<p class="metric-label" style="margin:12px 0 4px 0">ACTIVE (1): <span style="font-weight:normal;color:#888;">{active_dtu_sub} (Q{active_dtu_qos})</span></p>', unsafe_allow_html=True)
                cus1, cus2 = st.columns([0.75, 0.25])
                with cus1:
                    st.selectbox("Remove", [active_dtu_sub], key="cell_unsub_select", label_visibility="collapsed")
                with cus2:
                    st.button("➖ Unsub", width="stretch", key="cell_unsub_btn", disabled=not cell_connected, on_click=cellular_mqtt.handle_dtu_unsubscribe)
            else:
                st.markdown('<p class="metric-label" style="margin:12px 0 4px 0">ACTIVE (0): <span style="font-weight:normal;color:#888;">None</span></p>', unsafe_allow_html=True)
                cus1, cus2 = st.columns([0.75, 0.25])
                with cus1:
                    st.selectbox("Remove", ["None"], key="cell_unsub_select", label_visibility="collapsed", disabled=True)
                with cus2:
                    st.button("➖ Unsub", width="stretch", key="cell_unsub_btn", disabled=True)

    with cr:
        # Cellular Logs
        # Cellular Logs
        with st.container(border=True):
            st.markdown('<div class="layout-mcu-marker" style="display:none;"></div>', unsafe_allow_html=True)
            tc2, bc2 = st.columns([0.8, 0.2])
            with tc2:
                st.markdown('<p class="metric-label" style="margin:0">MESSAGE LOGS</p>', unsafe_allow_html=True)
            with bc2:
                st.button("🗑️ Clear", width='stretch', key="clear_cell_log", on_click=cellular_mqtt.handle_clear_logs)
            cell_log_placeholder = st.empty()
            cell_lines = st.session_state.cell_logs if st.session_state.cell_logs else ["(No messages received)"]
            cell_log_placeholder.text_area("DTU Logs", value="\n".join(cell_lines), height=350, label_visibility="collapsed", disabled=False)

        # Send data through DTU (transparent mode)
        with st.container(border=True):
            st.markdown('<div class="layout-coding-marker" style="display:none;"></div><p class="metric-label" style="margin:0 0 12px 0">PUBLISH MESSAGE</p>', unsafe_allow_html=True)
            pt, pq = st.columns([0.8, 0.2])
            with pt:
                st.markdown('<p class="metric-label" style="margin:4px 0 0 0">TOPIC (Provisioned)</p>', unsafe_allow_html=True)
                prov_pub = st.text_input("DTU Pub", value="nanopd/dtu/tx", key="prov_pub", label_visibility="collapsed")
            with pq:
                st.markdown('<p class="metric-label" style="margin:4px 0 0 0">QOS</p>', unsafe_allow_html=True)
                st.selectbox("Pub QoS", [0, 1, 2], key="prov_pub_qos", label_visibility="collapsed")
            st.markdown('<p class="metric-label" style="margin:12px 0 0 0">PAYLOAD</p>', unsafe_allow_html=True)
            cell_payload = st.text_input("Payload", value="Hello from DTU!", key="cell_payload", label_visibility="collapsed")
            ca1, ca2 = st.columns([0.7, 0.3])
            with ca1:
                st.button("📤 Publish", width="stretch", type="primary", disabled=not cell_connected, key="cell_send", on_click=cellular_mqtt.handle_send_data)
            with ca2:
                if st.button("🔁 Auto RX", width="stretch", type="primary" if st.session_state.cell_auto_refresh else "secondary", key="cell_auto", help="Auto-refresh to read serial"):
                    st.session_state.cell_auto_refresh = not st.session_state.cell_auto_refresh
                    st.rerun()

# ─── Auto-Read Loops ─────────────────────────────────────────────────────────
needs_rerun = False
if st.session_state.mqtt_auto_refresh:
    needs_rerun = True
if st.session_state.cell_auto_refresh and cell_connected:
    cellular_mqtt.handle_read_serial()
    needs_rerun = True
if needs_rerun:
    time.sleep(0.2)
    st.rerun()

# ─── DYNAMIC LAYOUT SCRIPT ──────────────────────────────────────────────────
scroll_flag = "true" if (st.session_state.mqtt_logs or st.session_state.cell_logs) else "false"
st.html(f"""
    <!-- Render Time: {time.time()} -->
    <script>
    function updateLayoutAndScroll() {{
        var parentDoc = window.parent && window.parent.document ? window.parent.document : document;
        var mcuMarker = parentDoc.querySelector('.layout-mcu-marker');
        var codingMarker = parentDoc.querySelector('.layout-coding-marker');
        if (mcuMarker && codingMarker) {{
            var ta = mcuMarker.closest('[data-testid="stVerticalBlock"]')?.querySelector('textarea');
            var inputBlock = codingMarker.closest('[data-testid="stVerticalBlockBorderWrapper"]');
            if (ta && inputBlock) {{
                var taRect = ta.getBoundingClientRect();
                var inputBlockHeight = inputBlock.offsetHeight;
                var newHeight = window.innerHeight - taRect.top - inputBlockHeight - 45;
                if (newHeight > 150) {{
                    parentDoc.documentElement.style.setProperty('--dynamic-ta-height', newHeight + 'px');
                }}
            }}
        }}
        if ({scroll_flag} === true) {{
            var allTas = parentDoc.querySelectorAll('.layout-mcu-marker');
            allTas.forEach(function(marker) {{
                var block = marker.closest('[data-testid="stVerticalBlock"]');
                if (block) {{
                    var ta = block.querySelector('textarea');
                    if (ta) ta.scrollTop = ta.scrollHeight;
                }}
            }});
        }}
    }}
    var layoutInterval = setInterval(updateLayoutAndScroll, 50);
    setTimeout(function() {{ clearInterval(layoutInterval); }}, 1500);
    var parentWin = window.parent || window;
    parentWin.addEventListener('resize', updateLayoutAndScroll);
    </script>
""")
