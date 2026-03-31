import streamlit as st
import sys
import os
import time
from utils.style_utils import apply_global_css
from utils.config_utils import load_ui_config
from utils.mount_utils import is_mounted, is_rp2350_connected

# 1. Load SRAM Core Utilities
try:
    from utils.sram_scanner import (fetch_live_heap, fetch_baseline_deep_scan, apply_live_heap_to_baseline,
                                    get_base_bank_list, fetch_detailed_memory_map, compute_bank_segments)
except ImportError:
    st.error("Backend Error: 'utils/sram_scanner.py' not found.")
    st.stop()

# 2. Load UI Configuration
if "ui_cfg" not in st.session_state:
    st.session_state.ui_cfg = load_ui_config()

# 3. Session State Initialization
if "sram_baseline_banks" not in st.session_state:
    st.session_state["sram_baseline_banks"] = None
    st.session_state["sram_baseline_static_total"] = 0
    st.session_state["sram_detail_map"] = None
if "sram_live_heap" not in st.session_state:
    st.session_state["sram_live_heap"] = {"heap_used": 0, "heap_free": 0}

# Auto-retrace baseline on page entry
if st.session_state.get("current_active_page") != "SRAM":
    st.session_state["current_active_page"] = "SRAM"
    st.session_state["sram_baseline_banks"] = None 

# 4. Apply Global CSS
apply_global_css(
    title_size=st.session_state.ui_cfg.get("title_size", "1.5rem"),
    label_size=st.session_state.ui_cfg.get("label_size", "0.875rem"),
    info_size=st.session_state.ui_cfg.get("info_size", "1.0rem"),
    code_font=st.session_state.ui_cfg.get("code_font", "Consolas, Monaco, monospace"),
    code_size=st.session_state.ui_cfg.get("code_size", "14px"),
    code_lh=st.session_state.ui_cfg.get("code_lh", "1.3"),
    is_mcu_page=True
)

# 5. Page Specific CSS
st.markdown("""
<style>
    /* SRAM Progress Bar */
    .sram-progress-container {
        width: 100%;
        height: 24px;
        background-color: #f1f5f9;
        border-radius: 12px;
        overflow: hidden;
        display: flex;
        margin-top: 8px;
        margin-bottom: 24px;
        border: 1px solid #e2e8f0;
    }
    .sram-segment {
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 0.7rem;
        font-weight: 600;
        transition: width 0.3s ease;
    }
    .seg-fw    { background-color: #1e293b; } /* Slate 800 */
    .seg-heap  { background-color: #3b82f6; } /* Blue 500 */
    .seg-phys  { background-color: #6366f1; } /* Indigo 500 */
    .seg-dma   { background-color: #10b981; } /* Emerald 500 */
    .seg-stack { background-color: #f59e0b; } /* Amber 500 */
    
    /* Bank Mini Bar */
    .bank-mini-bar {
        width: 100%;
        height: 8px;
        background-color: #f1f5f9;
        border-radius: 4px;
        overflow: hidden;
        margin-top: 12px;
        display: flex;
        border: 1px solid #e2e8f0;
    }
    .mini-seg { height: 100%; transition: width 0.3s ease; }
    
    .metric-value-large {
        font-size: 1.5rem;
        font-weight: 700;
        color: #0f172a;
        display: block;
    }
    .metric-sub-value {
        font-family: var(--code-font, monospace);
        font-size: 0.85rem;
        color: #64748b;
        display: block;
        margin-top: 2px;
    }
    .legend-item {
        display: inline-flex;
        align-items: center;
        margin-right: 12px;
        font-size: 0.75rem;
        color: #64748b;
        font-weight: 500;
    }
    .legend-box {
        width: 10px;
        height: 10px;
        border-radius: 2px;
        margin-right: 6px;
    }
    
    /* ── SRAM Grid Scrollable Wrapper ── */
    [data-testid="stVerticalBlockBorderWrapper"]:has(.sram-grid-wrapper) {
        height: calc(100vh - 215px) !important;
        overflow-y: auto !important;
    }
</style>
""", unsafe_allow_html=True)

# 6. Baseline Initialization
mounted = is_mounted()
connected = is_rp2350_connected()

if st.session_state["sram_baseline_banks"] is None and not mounted and connected:
    with st.spinner("Initializing SRAM Baseline..."):
        banks, static_total = fetch_baseline_deep_scan()
        detail = fetch_detailed_memory_map()
        if banks:
            st.session_state["sram_baseline_banks"] = banks
            st.session_state["sram_baseline_static_total"] = static_total
            st.session_state["sram_detail_map"] = detail
        else:
            st.session_state["sram_baseline_banks"] = get_base_bank_list()

# 7. Global Overview Fragment
@st.fragment(run_every="1s")
def render_global_overview():
    mounted = is_mounted()
    connected = is_rp2350_connected()
    
    if not mounted and connected:
        heap_data = fetch_live_heap()
        if heap_data.get("success"):
            st.session_state["sram_live_heap"] = heap_data
    
    total = 520 * 1024
    heap_total = st.session_state.get("sram_live_heap", {}).get("heap_used", 0)
    baseline_total = st.session_state.get("sram_baseline_static_total", 0)
    gc_static = st.session_state.get("sram_live_heap", {}).get("gc_static", 0)
    
    # Segment Calculation
    fw_bytes    = int(gc_static * 0.75)
    dma_bytes   = int(gc_static * 0.20)
    stack_bytes = int(gc_static * 0.05)
    phys_bytes  = max(0, baseline_total - gc_static - heap_total)
    free_bytes  = max(0, total - (gc_static + phys_bytes + heap_total))
    
    fw_pct   = (fw_bytes    / total) * 100
    hp_pct   = (heap_total  / total) * 100
    py_pct   = (phys_bytes  / total) * 100
    dm_pct   = (dma_bytes   / total) * 100
    st_pct   = (stack_bytes / total) * 100
    
    with st.container(border=True):
        st.markdown("<p class='metric-label' style='margin-bottom:8px;'>GLOBAL SRAM USAGE (520KB)</p>", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="sram-progress-container">
            <div class="sram-segment seg-fw"    style="width: {fw_pct}%">FW</div>
            <div class="sram-segment seg-heap"  style="width: {hp_pct}%">HEAP</div>
            <div class="sram-segment seg-phys"  style="width: {py_pct}%">PHYS</div>
            <div class="sram-segment seg-dma"   style="width: {dm_pct}%">DMA</div>
            <div class="sram-segment seg-stack" style="width: {st_pct}%"></div>
        </div>
        """, unsafe_allow_html=True)
        
        # Legend
        l_html = f"""
        <div style="display:flex; flex-wrap:wrap;">
            <div class="legend-item"><div class="legend-box seg-fw"></div>FW: {fw_bytes//1024}KB</div>
            <div class="legend-item"><div class="legend-box seg-heap"></div>HEAP: {heap_total//1024}KB</div>
            <div class="legend-item"><div class="legend-box seg-phys"></div>PHYS: {phys_bytes//1024}KB</div>
            <div class="legend-item"><div class="legend-box seg-dma"></div>DMA: {dma_bytes//1024}KB</div>
            <div class="legend-item"><div class="legend-box seg-stack"></div>STACK: {stack_bytes//1024}KB</div>
            <div class="legend-item"><div class="legend-box" style="background:#f1f5f9; border:1px solid #e2e8f0;"></div>FREE: {free_bytes//1024}KB</div>
        </div>
        """
        st.markdown(l_html, unsafe_allow_html=True)
        st.markdown(f"<div style='text-align:right; font-size:0.7rem; color:#94a3b8;'>Last scan: {time.strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)

# 8. Bank Details Fragment
@st.fragment(run_every="3s")
def render_bank_details():
    mounted = is_mounted()
    baseline = st.session_state.get("sram_baseline_banks")
    
    if mounted or baseline is None:
        st.info("SRAM details offline during mount or disconnect.")
        return

    heap_data = st.session_state.get("sram_live_heap", {})
    detail    = st.session_state.get("sram_detail_map")
    banks     = apply_live_heap_to_baseline(baseline, heap_data)
    if banks:
        banks = compute_bank_segments(banks, detail)
    
    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
    st.markdown("<p class='metric-label' style='margin-bottom:12px;'>SRAM BANK DISTRIBUTION</p>", unsafe_allow_html=True)
    
    def render_bank(bank):
        used = bank["used"]
        total = bank["total"]
        fw_pct = (bank.get("seg_fw", 0) / total) * 100
        hp_pct = (bank.get("seg_heap", 0) / total) * 100
        dm_pct = (bank.get("seg_dma", 0) / total) * 100
        st_pct = (bank.get("seg_stack", 0) / total) * 100
        # Phys residue is everything between fw/dma/stack and physical used boundary
        phys_pct = max(0, (used / total * 100) - (fw_pct + hp_pct + dm_pct + st_pct)) 
        
        with st.container(border=True):
            st.markdown(f"<p class='metric-label' style='font-size:0.7rem;'>{bank['name']}</p>", unsafe_allow_html=True)
            st.markdown(f"<span class='metric-value-large'>{used//1024} <small style='color:#64748b; font-size:0.9rem;'>/ {total//1024} KB</small></span>", unsafe_allow_html=True)
            st.markdown(f"<span class='metric-sub-value'>{bank['start']}</span>", unsafe_allow_html=True)
            st.markdown(f"""
            <div class="bank-mini-bar">
                <div class="mini-seg seg-fw"    style="width:{fw_pct}%"></div>
                <div class="mini-seg seg-heap"  style="width:{hp_pct}%"></div>
                <div class="mini-seg seg-phys"  style="width:{phys_pct}%"></div>
                <div class="mini-seg seg-dma"   style="width:{dm_pct}%"></div>
                <div class="mini-seg seg-stack" style="width:{st_pct}%"></div>
            </div>
            """, unsafe_allow_html=True)

    # Grid Layout: 4 cols for Top, 3 cols for Mid/Bottom
    row0_cols = st.columns(4)
    for i in range(4):
        with row0_cols[i]: render_bank(banks[i])
        
    row1_cols = st.columns(3)
    for i in range(3):
        with row1_cols[i]: render_bank(banks[4+i])
        
    row2_cols = st.columns(3)
    for i in range(3):
        with row2_cols[i]: render_bank(banks[7+i])

# 9. Main Render
render_global_overview()

with st.container(border=True):
    st.markdown('<div class="sram-grid-wrapper"></div>', unsafe_allow_html=True)
    render_bank_details()
