import streamlit as st
import os
import json
import pandas as pd
import tkinter as tk
from tkinter import filedialog
from utils.style_utils import apply_global_css
from utils.config_utils import load_ui_config

# 1. Load UI Configuration
if "ui_cfg" not in st.session_state:
    st.session_state.ui_cfg = load_ui_config()

# 2. Apply Global CSS
apply_global_css(
    title_size=st.session_state.ui_cfg.get("title_size", "1.5rem"),
    label_size=st.session_state.ui_cfg.get("label_size", "0.875rem"),
    info_size=st.session_state.ui_cfg.get("info_size", "1.0rem"),
    code_font=st.session_state.ui_cfg.get("code_font", "Consolas, Monaco, monospace"),
    code_size=st.session_state.ui_cfg.get("code_size", "14px"),
    code_lh=st.session_state.ui_cfg.get("code_lh", "1.3"),
    is_mcu_page=True
)

# Session state initialization
if "json_current_file" not in st.session_state:
    st.session_state["json_current_file"] = None

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GLOBAL_CONFIG_PATH = os.path.join(_BASE_DIR, "config.json")

def _read_global_config():
    try:
        with open(_GLOBAL_CONFIG_PATH, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def _write_global_config(data):
    try:
        with open(_GLOBAL_CONFIG_PATH, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass

def get_last_json_dir():
    cfg = _read_global_config()
    last_dir = cfg.get("json_editor_last_dir", _BASE_DIR)
    return last_dir if os.path.exists(last_dir) else _BASE_DIR

def set_last_json_dir(path):
    if path:
        d = os.path.dirname(path)
        if os.path.exists(d):
            cfg = _read_global_config()
            cfg["json_editor_last_dir"] = d
            _write_global_config(cfg)

def open_json_file():
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', True)
    path = filedialog.askopenfilename(
        title="Open JSON File",
        initialdir=get_last_json_dir(),
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    root.destroy()
    if path:
        set_last_json_dir(path)
        st.session_state["json_current_file"] = path

def new_json_file():
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', True)
    path = filedialog.asksaveasfilename(
        title="Create New JSON File",
        initialdir=get_last_json_dir(),
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    root.destroy()
    if path:
        if not os.path.exists(path):
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump([], f)
            except Exception:
                pass
        set_last_json_dir(path)
        st.session_state["json_current_file"] = path

tab1, tab2 = st.tabs(["Table Editing", "Raw Data Editing"])

def load_json(filepath):
    if not os.path.exists(filepath):
        return [], False
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                return [data], True
            elif isinstance(data, list):
                return data, False
            else:
                return [{"value": data}], False
    except Exception as e:
        st.error(f"Error loading {filepath}: {e}")
        return [], False

def save_json(filepath, data, was_dict=False):
    try:
        # If it was originally a dict and now it has exactly 1 row, save as dict
        if was_dict and len(data) == 1:
            save_data = data[0]
        elif was_dict and len(data) == 0:
            save_data = {}
        else:
            save_data = data
            
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=4, ensure_ascii=False)
        st.success(f"Saved to {filepath}")
    except Exception as e:
        st.error(f"Error saving {filepath}: {e}")

@st.dialog("Add Column")
def add_column_dialog(current_file, data, df_cols, was_dict):
    col_name = st.text_input("New Column Name")
    if df_cols:
        target_col = st.selectbox("Relative to Column", options=df_cols)
        position = st.radio("Position", ["Add Before", "Add After"], horizontal=True)
    else:
        target_col = None
        position = "Add After"
    
    _, btn_col, _ = st.columns([1, 2, 1])
    with btn_col:
        confirm = st.button("Confirm", type="primary", use_container_width=True)
    
    if confirm:
        if col_name and col_name not in df_cols:
            if not data:
                data = [{col_name: ""}]
            else:
                for row in data:
                    if isinstance(row, dict):
                        if target_col:
                            new_row = {}
                            for k, v in row.items():
                                if position == "Add Before" and k == target_col:
                                    new_row[col_name] = ""
                                new_row[k] = v
                                if position == "Add After" and k == target_col:
                                    new_row[col_name] = ""
                            row.clear()
                            row.update(new_row)
                        else:
                            row[col_name] = ""
            save_json(current_file, data, was_dict)
            st.rerun()

@st.dialog("Edit Column")
def edit_column_dialog(current_file, data, df_cols, was_dict):
    if not df_cols:
        st.warning("No columns to edit.")
        return
    edit_col_name = st.selectbox("Select Column to Edit", options=df_cols)
    new_edit_name = st.text_input("New Name")
    _, btn_col, _ = st.columns([1, 2, 1])
    with btn_col:
        confirm = st.button("Confirm", type="primary", use_container_width=True)
        
    if confirm:
        if edit_col_name and new_edit_name and new_edit_name not in df_cols:
            for row in data:
                if isinstance(row, dict) and edit_col_name in row:
                    new_row = {}
                    for k, v in row.items():
                        if k == edit_col_name:
                            new_row[new_edit_name] = v
                        else:
                            new_row[k] = v
                    row.clear()
                    row.update(new_row)
            save_json(current_file, data, was_dict)
            st.rerun()

@st.dialog("Delete Column")
def delete_column_dialog(current_file, data, df_cols, was_dict):
    if not df_cols:
        st.warning("No columns to delete.")
        return
    del_col_name = st.selectbox("Select Column to Delete", options=df_cols)
    _, btn_col, _ = st.columns([1, 2, 1])
    with btn_col:
        confirm = st.button("Confirm", type="primary", use_container_width=True)
        
    if confirm:
        if del_col_name:
            for row in data:
                if isinstance(row, dict) and del_col_name in row:
                    del row[del_col_name]
            save_json(current_file, data, was_dict)
            st.rerun()

with tab1:
    with st.container(border=True):
        st.markdown(
            '<div class="layout-control-marker" style="display:none;"></div>'
            '<p class="metric-label" style="margin:0 0 12px 0">FILE SELECTION</p>',
            unsafe_allow_html=True
        )
        
        col1, col2 = st.columns(2)
        with col1:
            st.button("📂 Open", use_container_width=True, on_click=open_json_file)
        with col2:
            st.button("📄 New", use_container_width=True, on_click=new_json_file)

    if st.session_state.get("json_current_file"):
        current_file = st.session_state["json_current_file"]
        st.markdown(f"**Editing:** `{current_file}`")
        
        data, was_dict = load_json(current_file)
        
        if not data:
            df = pd.DataFrame([{"New Column": ""}])
        else:
            df = pd.DataFrame(data)
        
        # Tools to add/remove columns
        with st.container(border=True):
            st.markdown(
                '<div class="layout-control-marker" style="display:none;"></div>'
                '<p class="metric-label" style="margin:0 0 12px 0">COLUMN MANAGEMENT</p>',
                unsafe_allow_html=True
            )
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                if st.button("➕ Add", use_container_width=True):
                    add_column_dialog(current_file, data, list(df.columns) if not df.empty else [], was_dict)
            with col_m2:
                if st.button("✏️ Edit", use_container_width=True):
                    edit_column_dialog(current_file, data, list(df.columns) if not df.empty else [], was_dict)
            with col_m3:
                if st.button("🗑️ Delete", use_container_width=True):
                    delete_column_dialog(current_file, data, list(df.columns) if not df.empty else [], was_dict)

        with st.container(border=True):
            top_col1, top_col2 = st.columns([0.7, 0.3])
            with top_col1:
                st.markdown('<p class="metric-label" style="margin:8px 0 12px 0">DATA EDITOR</p>', unsafe_allow_html=True)
            
            save_btn_placeholder = top_col2.empty()
            
            # Fixed height limits scrolling to the container instead of the page
            edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, height=380, key=f"data_editor_{current_file}")
            
            if save_btn_placeholder.button("💾 Save Changes", type="primary", use_container_width=True):
                new_data = edited_df.to_dict('records')
                save_json(current_file, new_data, was_dict)
                st.rerun()
    else:
        st.info("Please select or create a JSON file to begin table editing.")

with tab2:
    if st.session_state.get("json_current_file"):
        current_file = st.session_state["json_current_file"]
        st.markdown(f"**Raw Editing:** `{current_file}`")
        
        try:
            with open(current_file, 'r', encoding='utf-8') as f:
                raw_text = f.read()
        except Exception as e:
            raw_text = ""
            
        new_raw_text = st.text_area("JSON Content", value=raw_text, height=400, key=f"raw_text_area_{current_file}")
        
        if st.button("Save Raw Data", type="primary"):
            try:
                # Validate JSON before saving
                parsed = json.loads(new_raw_text)
                with open(current_file, 'w', encoding='utf-8') as f:
                    f.write(new_raw_text)
                st.success("Saved successfully!")
                st.rerun()
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON format: {e}")
            except Exception as e:
                st.error(f"Error saving file: {e}")
    else:
        st.info("Please select a file in the Table Editing tab first.")
