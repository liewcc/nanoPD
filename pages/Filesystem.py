import streamlit as st
import os
import json
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
import subprocess
import sys
import shutil
import time
import plotly.graph_objects as go
from utils.style_utils import apply_global_css
from utils.config_utils import load_ui_config
from utils.mount_utils import is_mounted, start_mount, stop_mount, CREATIONFLAGS, is_rp2350_connected


CONFIG_PATH = os.path.abspath("config.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_config(config):
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=4)
    except:
        pass

def get_local_path():
    config = load_config()
    path_str = config.get("xip_local_path")
    if path_str and os.path.exists(path_str):
        return path_str
    mcu_path = os.path.abspath("mcu")
    if not os.path.exists(mcu_path):
        os.makedirs(mcu_path, exist_ok=True)
    return mcu_path

def format_bytes(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0: return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

TREE_OUTER_STYLE = (
    "padding: 10px 12px; border-radius: 8px; overflow-y: auto;"
)

def build_local_tree(base_path: str):
    """Build a recursive node list from local filesystem."""
    nodes = []
    try:
        entries = sorted(Path(base_path).iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
    except PermissionError:
        return nodes
    for entry in entries:
        if entry.name.startswith('.'): continue
        if entry.is_dir():
            nodes.append({"name": entry.name, "type": "dir", "size": 0, "children": build_local_tree(str(entry))})
        else:
            nodes.append({"name": entry.name, "type": "file", "size": entry.stat().st_size, "children": []})
    return nodes

def flatten_nodes(nodes, prefix=""):
    result = {}
    for node in nodes:
        path = f"{prefix}/{node['name']}".strip("/")
        if node['type'] == 'file':
            result[path] = node['size']
        elif node['type'] == 'dir':
            result.update(flatten_nodes(node.get('children', []), path))
    return result

def render_ascii_tree(nodes, target="local", is_delete_mode=False, path_prefix="", visual_prefix=""):
    """Recursively render a flat list imitating a DOS ASCII tree.
    Always renders checkboxes to ensure pixel-perfect alignment in both modes."""
    if not nodes:
        if not path_prefix:
            st.markdown(f"<div style='color:#94a3b8; font-size:0.87em; padding:4px 0;'>(empty)</div>", unsafe_allow_html=True)
        return
        
    for i, node in enumerate(sorted(nodes, key=lambda x: (x['type'] != 'dir', x['name'].lower()))):
        is_last = (i == len(nodes) - 1)
        connector = "└── " if is_last else "├── "
        icon = "📁" if node['type'] == 'dir' else "📄"
        
        spacer_text = f"{visual_prefix}{connector}"
        size_str = f" ({format_bytes(node['size'])})" if node['type'] != 'dir' else ""
        display_text = f"{spacer_text}{icon} {node['name']}{size_str}"
        full_path = f"{path_prefix}/{node['name']}".strip("/")
        
        if is_delete_mode:
            cb_key = f"del_{target}_{full_path}"
            st.checkbox(display_text, key=cb_key)
        else:
            cb_key = f"view_{target}_{full_path}"
            st.checkbox(display_text, key=cb_key, value=False)
            
        if node['type'] == 'dir':
            new_visual_prefix = visual_prefix + ("    " if is_last else "│   ")
            render_ascii_tree(node.get('children', []), target, is_delete_mode, f"{path_prefix}/{node['name']}".strip("/"), new_visual_prefix)

def build_mcu_tree():
    """Fetches MCU filesystem and returns node list in same format as build_local_tree."""
    rc, out, err = run_mpremote(["exec", MCU_WALK_SCRIPT])
    if rc != 0 or not out.strip():
        return None
    try:
        raw = json.loads(out.strip())
        def _convert(node_list):
            result = []
            for n in sorted(node_list, key=lambda x: (x['t'] != 'dir', x['n'].lower())):
                result.append({
                    "name": n['n'],
                    "type": n['t'],
                    "size": n.get('s', 0),
                    "children": _convert(n.get('c', []))
                })
            return result
        return _convert(raw)
    except:
        return None

def fetch_capacity():
    """Reads MCU flash capacity and usage."""
    rc, out, _ = run_mpremote(["exec", "import os; s=os.statvfs('/'); print(f'{s[0]},{s[2]},{s[3]}')"], timeout=5.0)
    if rc == 0 and out and out.strip():
        try:
            parts = out.strip().split(',')
            if len(parts) == 3:
                bsize, tb, fb = int(parts[0]), int(parts[1]), int(parts[2])
                total = bsize * tb
                free  = bsize * fb
                return {"total": total, "used": total - free, "free": free}
        except:
            pass
    return None

def render_storage_gauge(capacity):
    """Renders a Plotly donut chart for storage usage."""
    if capacity:
        used_pct = int(capacity['used'] / capacity['total'] * 100) if capacity['total'] > 0 else 0
        fig = go.Figure(data=[go.Pie(
            labels=['Used', 'Free'], values=[capacity['used'], capacity['free']],
            hole=0.72, 
            marker_colors=['#3b82f6', '#bbf7d0'], # Blue for used, Light Green for total/free
            showlegend=False, 
            textinfo='none',
            hoverinfo='label+percent'
        )])
        fig.update_layout(
            margin=dict(t=10, b=10, l=10, r=10), height=180, paper_bgcolor='rgba(0,0,0,0)',
            annotations=[{'text': f'<b>{used_pct}%</b>', 'x': 0.5, 'y': 0.5, 'showarrow': False, 'font': {'size': 24, 'color': '#0f172a'}}],
        )
        st.plotly_chart(fig, width='stretch', config={'displayModeBar': False})
        st.markdown(
            f"<div style='text-align:center; font-size:0.9rem; color:#64748b; margin-top:-15px; font-family:var(--code-font);'>"
            f"{format_bytes(capacity['used'])} / {format_bytes(capacity['total'])}</div>",
            unsafe_allow_html=True
        )
    else:
        # Disconnected or Busy state
        fig = go.Figure(data=[go.Pie(
            labels=['N/A'], values=[100],
            hole=0.72, 
            marker_colors=['#f1f5f9'], # Grey
            showlegend=False, 
            textinfo='none',
            hoverinfo='none'
        )])
        fig.update_layout(
            margin=dict(t=10, b=10, l=10, r=10), height=180, paper_bgcolor='rgba(0,0,0,0)',
            annotations=[{'text': '<b>--</b>', 'x': 0.5, 'y': 0.5, 'showarrow': False, 'font': {'size': 24, 'color': '#cbd5e1'}}],
        )
        st.plotly_chart(fig, width='stretch', config={'displayModeBar': False})
        st.markdown(
            f"<div style='text-align:center; font-size:0.9rem; color:#cbd5e1; margin-top:-15px; font-family:var(--code-font);'>"
            f"Device Offline</div>",
            unsafe_allow_html=True
        )
def run_mpremote(args, timeout=20.0, soft_reset=False):
    """
    Executes mpremote with a retry loop for Raw REPL entry.
    soft_reset: optional boolean to run 'soft-reset' before the main command.
    """
    if soft_reset:
        subprocess.run([sys.executable, "-m", "mpremote", "soft-reset"], capture_output=True, creationflags=CREATIONFLAGS)
        time.sleep(0.5)

    cmd = [sys.executable, "-m", "mpremote"] + args
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            res = subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=CREATIONFLAGS)
            stdout = res.stdout.decode('utf-8', errors='replace')
            stderr = res.stderr.decode('utf-8', errors='replace')
            
            # Check for REPL entry failure to justify a retry
            if "could not enter raw repl" in stderr.lower() or "failed to access" in stderr.lower():
                time.sleep(1.0)
                continue
                
            return res.returncode, stdout, stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Timeout: MCU did not respond."
        except Exception as e:
            return -2, "", str(e)
            
    return -3, "", "Failed to enter Raw REPL after retries."

MCU_WALK_SCRIPT = """
import os, json
def walk(p):
    out = []
    try:
        for f in os.ilistdir(p):
            n, t = f[0], f[1]
            s = f[3] if len(f) > 3 else 0
            cp = (p + '/' + n) if p != '/' else ('/' + n)
            out.append({'n': n, 't': 'dir' if t == 0x4000 else 'file', 's': 0 if t == 0x4000 else s, 'c': walk(cp) if t == 0x4000 else []})
    except: pass
    return out
print(json.dumps(walk('/')))
"""


@st.dialog("File Viewer", width="large")
def file_viewer_dialog(file_path: str, is_mcu: bool = False):
    st.markdown(f"**Path:** `{file_path}`")
    
    try:
        if is_mcu:
            # 1. Fetch file from MCU to a temporary local file
            temp_path = Path("mcu_temp_preview.tmp")
            rc, out, err = run_mpremote(["fs", "cp", ":" + file_path, str(temp_path)])
            if rc != 0:
                st.error(f"Failed to fetch file from MCU: {err}")
                return
            target_file_path = str(temp_path)
        else:
            target_file_path = file_path
            
        # 2. Try to decode as text
        with open(target_file_path, "rb") as f:
            content = f.read()
            
        is_text = False
        try:
            text_content = content.decode('utf-8')
            is_text = True
        except UnicodeDecodeError:
            pass
            
        if is_text:
            ext = os.path.splitext(file_path)[1].lower()
            lang = "python" if ext == ".py" else ("json" if ext == ".json" else "text")
            st.code(text_content, language=lang)
        else:
            ext = os.path.splitext(file_path)[1].lower()
            if ext in [".png", ".jpg", ".jpeg"]:
                st.image(content)
            else:
                st.warning("This is a binary file and cannot be previewed.")
                st.download_button("Download File", data=content, file_name=os.path.basename(file_path))
                
        # Clean up temp mcu file
        if is_mcu and Path(target_file_path).exists():
            Path(target_file_path).unlink()
            
    except Exception as e:
        st.error(f"Error accessing file: {e}")

def trigger_virtual_disk_reset():
    """Reboot MCU into BOOTSEL (USB Mass Storage) mode via mpremote exec.
    Equivalent to pressing RST+BOOT buttons. MCU disconnects immediately on success.
    """
    st.session_state.pop("xip_capacity", None)
    st.session_state["mcu_needs_refresh"] = True
    run_mpremote(["exec", "import machine; machine.bootloader()"], timeout=2.0)
    st.rerun()


def trigger_mcu_reset():
    """Perform a soft reset of the MCU via mpremote exec.
    Equivalent to pressing the RST button only. MicroPython restarts normally.
    """
    st.session_state.pop("xip_capacity", None)
    st.session_state["mcu_needs_refresh"] = True
    run_mpremote(["exec", "import machine; machine.reset()"], timeout=2.0)
    st.rerun()

if "xip_local_path" not in st.session_state:
    st.session_state["xip_local_path"] = get_local_path()

if "delete_mode" not in st.session_state:
    st.session_state["delete_mode"] = False

# 1. Load Persisted UI Configuration (needed for style parameters)
if "ui_cfg" not in st.session_state:
    st.session_state.ui_cfg = load_ui_config()

# 2. Page Configuration
# Page title and icons are handled by st.navigation in main.py

# Auto-refresh monitor for background mount state and USB connection state
@st.fragment()
def storage_usage_gauge():
    """Fragment to display storage gauge with auto-refresh logic."""
    mounted = is_mounted()
    connected = is_rp2350_connected()
    
    # Store previous connection state to trigger refresh on re-connect
    if "prev_connected" not in st.session_state:
        st.session_state.prev_connected = connected
        
    # Trigger fetch if connected and (wasn't connected or capacity is empty)
    should_fetch = connected and (not st.session_state.prev_connected or "xip_capacity" not in st.session_state)
    st.session_state.prev_connected = connected

    if should_fetch and not mounted:
        st.session_state["xip_capacity"] = fetch_capacity()
        
    capacity = st.session_state.get("xip_capacity") if (connected and not mounted) else None
    render_storage_gauge(capacity)

@st.fragment(run_every="2s")
def mount_status_monitor():
    current_mount   = is_mounted()
    current_usb     = is_rp2350_connected()
    last_mount      = st.session_state.get("last_mount_state", current_mount)
    last_usb        = st.session_state.get("last_usb_state", current_usb)
    # Force a rerun if we were told to refresh (e.g. after a Reset button)
    needs_refresh = st.session_state.get("mcu_needs_refresh", False)
    
    if current_mount != last_mount or current_usb != last_usb or needs_refresh:
        st.session_state["last_mount_state"] = current_mount
        st.session_state["last_usb_state"]   = current_usb
        st.session_state["mcu_needs_refresh"] = False
        st.rerun()  
    
    # Sync states even if no rerun (precautionary)
    st.session_state["last_mount_state"] = current_mount
    st.session_state["last_usb_state"]   = current_usb

# 3. Apply Global CSS
apply_global_css(
    title_size=st.session_state.ui_cfg.get("title_size", "1.5rem"),
    label_size=st.session_state.ui_cfg.get("label_size", "0.875rem"),
    info_size=st.session_state.ui_cfg.get("info_size", "1.0rem"),
    code_font=st.session_state.ui_cfg.get("code_font", "Consolas, Monaco, monospace"),
    code_size=st.session_state.ui_cfg.get("code_size", "14px"),
    code_lh=st.session_state.ui_cfg.get("code_lh", "1.3"),
    is_mcu_page=True
)

# Fix stMarkdown implicit bottom margin and main block padding
code_font = st.session_state.ui_cfg.get("code_font", "Consolas, Monaco, monospace")
code_size = st.session_state.ui_cfg.get("code_size", "14px")
code_lh = st.session_state.ui_cfg.get("code_lh", "1.3")

st.markdown(f"""
    <style>
        section[data-testid="stMain"] > div {{
            padding-bottom: 20px !important;
        }}
        .main > div.block-container {{
            padding-bottom: 20px !important;
        }}
        div[data-testid="block-container"] {{
            padding-bottom: 20px !important;
        }}
        
        /* Tree-specific styling using :has() to restrict to tree containers */
        [data-testid="stVerticalBlock"]:has(> div.element-container .custom-tree-wrapper) {{
            gap: 0 !important;
        }}
        [data-testid="stVerticalBlock"]:has(> div.element-container .custom-tree-wrapper) .stCheckbox {{
            min-height: 24px !important;
            margin-bottom: 0 !important;
        }}
        [data-testid="stVerticalBlock"]:has(> div.element-container .custom-tree-wrapper) .stCheckbox label {{
            min-height: 24px !important;
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            align-items: center !important;
        }}
        [data-testid="stVerticalBlock"]:has(> div.element-container .custom-tree-wrapper) .stCheckbox label > div:first-child {{
            padding-top: 0 !important;
            margin-top: 0 !important;
            align-self: flex-start !important;
            transform: translateY(2px);
        }}
        [data-testid="stVerticalBlock"]:has(> div.element-container .custom-tree-wrapper) .stCheckbox label p,
        [data-testid="stVerticalBlock"]:has(> div.element-container .custom-tree-wrapper) .stCheckbox label span,
        [data-testid="stVerticalBlock"]:has(> div.element-container .custom-tree-wrapper) .ascii-tree-node {{
            font-family: {code_font} !important;
            font-size: {code_size} !important;
            line-height: {code_lh} !important;
            white-space: pre !important;
            margin: 0 !important;
            padding: 0 !important;
        }}
        [data-testid="stVerticalBlock"]:has(> div.element-container .custom-tree-wrapper) .ascii-tree-node {{
            padding: 2px 0 !important;
            line-height: 24px !important;
            color: inherit;
        }}
        
        /* Readonly Mode Overrides */
        [data-testid="stVerticalBlock"]:has(> div.element-container .readonly-tree-wrapper) .stCheckbox {{
            pointer-events: none !important;
        }}
        [data-testid="stVerticalBlock"]:has(> div.element-container .readonly-tree-wrapper) .stCheckbox label {{
            visibility: hidden !important; /* Hides the checkbox square and everything else */
        }}
        [data-testid="stVerticalBlock"]:has(> div.element-container .readonly-tree-wrapper) .stCheckbox [data-testid="stMarkdownContainer"] {{
            visibility: visible !important; /* Forces the text to remain visible */
            color: var(--text-color) !important;
            opacity: 1 !important;
        }}
    </style>
""", unsafe_allow_html=True)

# 4. Layout Implementation
# Start background polling
mount_status_monitor()

# Left column for control, Right column for two filesystem views
# Using columns to create the layout
col_left, col_right1, col_right2 = st.columns([1, 1.2, 1.2])

# Left: Control Container
with col_left:
    with st.container(height=850, border=True):
        st.markdown('<p class="metric-label" style="margin:0 0 12px 0">CONTROL</p>', unsafe_allow_html=True)
        
        # Add Storage Gauge at the top
        storage_usage_gauge()
        st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        
        st.markdown("<p style='font-size: 0.85em; font-weight: bold; margin-bottom: 5px; text-transform: uppercase;'>LOCAL PATH</p>", unsafe_allow_html=True)
        
        path_col1, path_col2 = st.columns([5, 1])
        with path_col1:
            new_path = st.text_input("Local Source Path", value=st.session_state["xip_local_path"], label_visibility="collapsed")
            if new_path != st.session_state["xip_local_path"]:
                st.session_state["xip_local_path"] = new_path
                config = load_config()
                config["xip_local_path"] = new_path
                save_config(config)
                st.rerun()
                
        with path_col2:
            if st.button("📁", help="Select Folder", width="stretch"):
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                selected_folder = filedialog.askdirectory(initialdir=st.session_state["xip_local_path"])
                root.destroy()
                
                if selected_folder:
                    st.session_state["xip_local_path"] = selected_folder
                    config = load_config()
                    config["xip_local_path"] = selected_folder
                    save_config(config)
                    st.rerun()

        btn_col1, btn_col2 = st.columns([1, 1])
        with btn_col1:
            if st.button("📂 View Local Folder", width="stretch"):
                try:
                    os.startfile(st.session_state["xip_local_path"])
                except Exception as e:
                    st.error(f"Failed to open folder: {e}")
        with btn_col2:
            if st.button("🔄 Refresh Drives", width="stretch"):
                st.session_state.pop("xip_capacity", None)
                st.rerun()
        
        
        mounted = is_mounted()
        
        if mounted:
            if st.button("🔌 Unmount Virtual Drive", width="stretch", type="primary"):
                stop_mount()
                st.rerun()
        else:
            if st.button("🔌 Mount Virtual Drive", width="stretch"):
                start_mount(st.session_state["xip_local_path"])
                st.rerun()

        push_slot = st.empty()
        if push_slot.button("Push to MCU", width="stretch", disabled=mounted):
            push_slot.button("⌛ Pushing...", width="stretch", disabled=True)
            local_nodes = build_local_tree(st.session_state["xip_local_path"])
            mcu_nodes = build_mcu_tree() if (not mounted and is_rp2350_connected()) else []
            if mcu_nodes is not None:
                local_map = flatten_nodes(local_nodes)
                mcu_map = flatten_nodes(mcu_nodes)
                
                # 1. Mirror - Delete extras on MCU
                to_delete = [p for p in mcu_map if p not in local_map]
                if to_delete:
                    delete_script = f"import os; r=lambda d: ([r(d+'/'+f[0]) for f in os.ilistdir(d) if f[1]==0x4000], [os.remove(d+'/'+f[0]) for f in os.ilistdir(d) if f[1]!=0x4000], os.rmdir(d)); [r('/'+p) if (os.stat('/'+p)[0]&0x4000) else os.remove('/'+p) for p in {json.dumps(to_delete)}]"
                    run_mpremote(["exec", delete_script], soft_reset=True)
                    
                # 2. Transfer - Single-process recursive copy
                # Use /. pattern to copy contents into root
                local_pattern = str(Path(st.session_state["xip_local_path"])).replace("\\", "/") + "/."
                rc, out, err = run_mpremote(["fs", "cp", "-r", local_pattern, ":/"], timeout=180.0, soft_reset=True)
                
                if rc == 0:
                    st.toast("Successfully pushed/mirrored files to MCU.", icon="✅")
                    st.session_state.pop("xip_capacity", None) # Force refresh
                    st.rerun()
                else:
                    st.error(f"Push Failed: {err}")
                    st.rerun()

        pull_slot = st.empty()
        if pull_slot.button("Pull from MCU", width="stretch", disabled=mounted):
            pull_slot.button("⌛ Pulling...", width="stretch", disabled=True)
            local_base = Path(st.session_state["xip_local_path"])
            # Transfer - Single-process recursive copy from MCU
            # mpremote fs cp -r :. <dest>
            rc, out, err = run_mpremote(["fs", "cp", "-r", ":.", str(local_base).replace("\\", "/")], timeout=300.0, soft_reset=True)
            
            if rc == 0:
                st.toast("Successfully pulled files from MCU.", icon="✅")
                st.rerun()
            else:
                st.error(f"Pull Failed: {err}")
                st.rerun()

        format_slot = st.empty()
        if format_slot.button("Format MCU Flash", width="stretch", disabled=mounted):
            format_slot.button("⌛ Formatting...", width="stretch", disabled=True)
            format_script = "import os\ndef r(d):\n try:\n  if os.stat(d)[0]&0x4000:\n   for f in os.ilistdir(d): r(d+'/'+f[0])\n   if d!='/': os.rmdir(d)\n  else: os.remove(d)\n except: pass\nr('/')"
            rc, out, err = run_mpremote(["exec", format_script], timeout=60.0, soft_reset=True)
            if rc == 0:
                st.toast("MCU Flash formatted thoroughly!", icon="✅")
                st.session_state.pop("xip_capacity", None) # Force refresh
                st.rerun()
            else:
                st.error(f"Format Failed: {err}")
                st.rerun()

        
        del_col1, del_col2 = st.columns([1, 1])
        with del_col1:
            if not st.session_state["delete_mode"]:
                if st.button("Select files to delete", width="stretch", disabled=mounted):
                    st.session_state["delete_mode"] = True
                    st.rerun()
            else:
                del_slot = st.empty()
                if del_slot.button("Delete files", type="primary", width="stretch"):
                    del_slot.button("⌛ Deleting...", type="primary", width="stretch", disabled=True)
                    local_base = Path(st.session_state["xip_local_path"])
                    
                    # Delete local files
                    for key in list(st.session_state.keys()):
                        if key.startswith("del_local_") and st.session_state[key]:
                            rel_path = key[len("del_local_"):]
                            target_path = local_base / rel_path
                            if target_path.exists():
                                if target_path.is_dir():
                                    shutil.rmtree(target_path, ignore_errors=True)
                                else:
                                    target_path.unlink(missing_ok=True)
                            del st.session_state[key]
                    
                    # Delete MCU files (batched using a fast recursion script)
                    mcu_keys = [k for k in st.session_state.keys() if k.startswith("del_mcu_") and st.session_state[k]]
                    if mcu_keys:
                        paths_to_delete = [k[len("del_mcu_"):] for k in mcu_keys]
                        paths_json = json.dumps(paths_to_delete)
                        delete_script = f"""
import os, json
def rm_rf(d):
    try:
        if (os.stat(d)[0] & 0x4000):
            for f in os.ilistdir(d): rm_rf(d + '/' + f[0])
            os.rmdir(d)
        else: os.remove(d)
    except: pass
for p in {paths_json}: rm_rf('/' + p)
"""
                        run_mpremote(["exec", delete_script])
                        for key in mcu_keys:
                            del st.session_state[key]
                            
                    st.session_state["delete_mode"] = False
                    st.session_state.pop("xip_capacity", None) # Force refresh
                    st.rerun()

        with del_col2:
            if st.button("Cancel", width="stretch", disabled=not st.session_state["delete_mode"]):
                for key in list(st.session_state.keys()):
                    if key.startswith("del_local_") or key.startswith("del_mcu_"):
                        del st.session_state[key]
                st.session_state["delete_mode"] = False
                st.rerun()


        st.markdown("<p style='font-size: 0.85em; font-weight: bold; margin-bottom: 5px; text-transform: uppercase;'>BOOTSEL</p>", unsafe_allow_html=True)

        if st.button("💾 Virtual Disk Reset", width="stretch", disabled=mounted,
                     help="Reboot MCU into BOOTSEL mode (USB Mass Storage). Equivalent to RST+BOOT."):
            trigger_virtual_disk_reset()

        if st.button("🔄 MCU Reset", width="stretch", disabled=mounted,
                     help="Soft reset the MCU. Equivalent to pressing the RST button."):
            trigger_mcu_reset()

# Right 1: Local Filesystem Container
with col_right1:
    with st.container(height=850, border=True):
        wrapper_class = "custom-tree-wrapper" if st.session_state["delete_mode"] else "custom-tree-wrapper readonly-tree-wrapper"
        st.markdown(f'<div class="{wrapper_class}" style="display:none;"></div>', unsafe_allow_html=True)
        st.markdown('<p class="metric-label" style="margin:0 0 12px 0">LOCAL</p>', unsafe_allow_html=True)
        local_nodes = build_local_tree(st.session_state["xip_local_path"])
        st.markdown(f"<div style='{TREE_OUTER_STYLE}'>", unsafe_allow_html=True)
        render_ascii_tree(local_nodes, target="local", is_delete_mode=st.session_state["delete_mode"])
        st.markdown("</div>", unsafe_allow_html=True)

# Right 2: MCU Filesystem Container
with col_right2:
    with st.container(height=850, border=True):
        wrapper_class = "custom-tree-wrapper" if st.session_state["delete_mode"] else "custom-tree-wrapper readonly-tree-wrapper"
        st.markdown(f'<div class="{wrapper_class}" style="display:none;"></div>', unsafe_allow_html=True)
        st.markdown('<p class="metric-label" style="margin:0 0 12px 0">MCU FLASH</p>', unsafe_allow_html=True)
        mcu_nodes = None
        if not mounted and is_rp2350_connected():
            mcu_nodes = build_mcu_tree()
            
        if mcu_nodes is None:
            st.caption("Not connected or device busy.")
        else:
            st.markdown(f"<div style='{TREE_OUTER_STYLE}'>", unsafe_allow_html=True)
            render_ascii_tree(mcu_nodes, target="mcu", is_delete_mode=st.session_state["delete_mode"])
            st.markdown("</div>", unsafe_allow_html=True)



