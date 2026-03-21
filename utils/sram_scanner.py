import subprocess
import sys
import json

CREATIONFLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

def run_mpremote(args, timeout=2.0, supress=True):
    """Utility to run an mpremote command safely."""
    cmd = [sys.executable, "-m", "mpremote"] + args
    
    if not supress:
        print(f"Backend>> {' '.join(cmd)}")
    
    try:
        res = subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=CREATIONFLAGS)
        stdout = res.stdout.decode('utf-8', errors='replace') if res.stdout else ""
        stderr = res.stderr.decode('utf-8', errors='replace') if res.stderr else ""
        
        if not supress and stderr:
            print(f"Backend>> ERROR: {stderr.strip()}")
            
        return res.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        if not supress: print("Backend>> ERROR: TimeoutExpired")
        return -1, "", "TimeoutExpired"
    except Exception as e:
        if not supress: print(f"Backend>> ERROR: {str(e)}")
        return -2, "", str(e)

# ── 1. Global View (Live Heap Telemetry) ─────────────────────────────────────
def fetch_live_heap(supress=True):
    """
    O(1) footprint lookup via `gc.mem_alloc()` and `gc.mem_free()`.
    Only returns dynamic heap numbers.
    """
    script = "import gc; print(f'{gc.mem_alloc()},{gc.mem_free()}')"
    rc, out, err = run_mpremote(["exec", script], timeout=2.0, supress=supress)
    
    res = {
        "heap_used": 0,
        "heap_free": 0,
        "gc_static": 0,
        "success": False
    }

    if rc == 0 and out.strip():
        try:
            alloc_b, free_b = map(int, out.strip().split(','))
            res["heap_used"] = alloc_b
            res["heap_free"] = free_b
            # total gc-visible memory
            gc_heap_cap = alloc_b + free_b
            total = 520 * 1024
            res["gc_static"] = max(0, total - gc_heap_cap)
            res["success"] = True
        except:
            pass
    return res

# Host-side session latch for UI stability
_session_state = {"cause": None, "label": None, "last_uptime": -1}
_last_telemetry = None

def fetch_core_telemetry(supress=True):
    """
    Fetches hardware metrics from XIAO RP2350.
    Reset cause: machine.reset_cause() only (POWMAN is cleared before Python runs).
    Labels: PWRON/HW_RST=1, SOFT_RST=5, WDT=3.
    Session-latched so the UI is stable across continuous polling.
    """
    global _session_state, _last_telemetry

    telemetry_script = """
import machine, json, time, os

def get_metrics():
    rc_std = machine.reset_cause()
    ut_ms  = time.ticks_ms()
    arch = "Unknown"
    try:
        mach = os.uname().machine.upper()
        if "RISC-V" in mach or "RV32" in mach:
            arch = "RISC-V"
        else:
            arch = "ARM (Cortex-M33)"
    except: pass

    # Sequential Stable ADC Sampling (CRITICAL: DO NOT CHANGE ORDER)
    raws = {}
    for i in range(10):
        try:
            adc = machine.ADC(i)
            n = 16 if i != 4 else 128
            acc = 0
            for _ in range(n): acc += adc.read_u16()
            raws[i] = acc / n
        except: pass

    # Temperature (Proven 33C calibration)
    vref  = 3.3
    vt    = raws.get(4, 0) * vref / 65535
    temp  = 27 - (vt - 0.706) / 0.001721
    if temp > 45 or temp < 10: temp = 27 - (vt - 0.655) / 0.001721

    # Power Mode (P19 → ADC3)
    vsys = 5.0; mode = "USB"
    try:
        p19 = machine.Pin(19, machine.Pin.OUT)
        p19.value(1); time.sleep_ms(20)
        v_raw = machine.ADC(3).read_u16()
        p19.value(0)
        p19 = machine.Pin(19, machine.Pin.IN)
        v = (v_raw * vref / 65535) * 2
        if v > 2.0: vsys = v; mode = "Battery"
    except: pass

    # Reset cause label
    if   rc_std == 5: label = "Soft Reset";  rc_val = 5
    elif rc_std == 3: label = "WDT Reset";   rc_val = 3
    else:             label = "Power On";    rc_val = 1

    return {
        "freq": machine.freq() // 1000000,
        "temp": round(temp, 1),
        "volt": round(vsys, 2),
        "rc_str": f"{label} (RC:{rc_std})",
        "rc_val": rc_val,
        "mode": mode,
        "uptime": ut_ms // 1000,
        "arch": arch
    }

print(json.dumps(get_metrics()))
"""
    rc, out, err = run_mpremote(["exec", telemetry_script.strip()], timeout=8.0, supress=supress)

    if rc != 0 or not out.strip():
        if _last_telemetry: return _last_telemetry
        return {"success": False, "temp_c": 0, "reset_cause": 1, "reset_cause_str": "Syncing..."}

    try:
        raw = json.loads(out.strip().split('\n')[-1])
        data = {
            "freq_mhz":       raw["freq"],
            "temp_c":         raw["temp"],
            "vsys_v":         raw["volt"],
            "reset_cause_str": raw["rc_str"],
            "reset_cause":    raw["rc_val"],
            "power_mode":     raw["mode"],
            "uptime_s":       raw["uptime"],
            "arch":           raw.get("arch", "Unknown"),
            "success":        True
        }

        # Simple session latch: lock cause on first boot, reset if uptime drops
        up = data["uptime_s"]
        if _session_state["last_uptime"] == -1 or up < (_session_state["last_uptime"] - 5):
            _session_state.update({"cause": data["reset_cause"],
                                   "label": data["reset_cause_str"]})
        _session_state["last_uptime"] = up

        data["reset_cause"]     = _session_state["cause"]
        data["reset_cause_str"] = _session_state["label"]

        _last_telemetry = data
        return data
    except:
        if _last_telemetry: return _last_telemetry
        return {"success": False, "temp_c": 0, "reset_cause": 1, "reset_cause_str": "Parsing..."}


# ── 2. Bank Details ──────────────────────────────────────────────────────────

def get_base_bank_list():
    """Returns the blueprint for the 10 PR2350 banks."""
    return [
        {"name": "Bank 0 (Core 0/Static)", "total": 65536, "used": 0, "start": "0x20000000"},
        {"name": "Bank 1 (Heap Start)", "total": 65536, "used": 0, "start": "0x20010000"},
        {"name": "Bank 2 (Heap Mid)", "total": 65536, "used": 0, "start": "0x20020000"},
        {"name": "Bank 3 (Heap End)", "total": 65536, "used": 0, "start": "0x20030000"},
        {"name": "Bank 4 (Free)", "total": 65536, "used": 0, "start": "0x20040000"},
        {"name": "Bank 5 (Free)", "total": 65536, "used": 0, "start": "0x20050000"},
        {"name": "Bank 6 (Free)", "total": 65536, "used": 0, "start": "0x20060000"},
        {"name": "Bank 7 (Free)", "total": 65536, "used": 0, "start": "0x20070000"},
        {"name": "Bank 8 (Fast 4KB)", "total": 4096, "used": 0, "start": "0x20080000"},
        {"name": "Bank 9 (Fast 4KB)", "total": 4096, "used": 0, "start": "0x20081000"},
    ]


def fetch_baseline_deep_scan(supress=True):
    """
    Runs once to map the true physical layout of the C firmware, stack, and frozen objects.
    Provides the ground-truth foundation for the hybrid model.
    """
    # Sample 16 points for 64K, 4 points for 4K.
    probe_script = """
import machine, json
res = []
# 8x64KB Banks
for b in range(8):
    base = 0x20000000 + (b * 0x10000)
    hits = 0
    pts = 16
    stride = 0x10000 // pts
    for p in range(pts):
        try:
            if machine.mem32[base + (p * stride)] != 0: hits += 1
        except: pass
    res.append(int((hits/pts) * 65536))
# 2x4KB Banks
for b in range(2):
    base = 0x20080000 + (b * 0x1000)
    hits = 0
    pts = 4
    stride = 0x1000 // pts
    for p in range(pts):
        try:
            if machine.mem32[base + (p * stride)] != 0: hits += 1
        except: pass
    res.append(int((hits/pts) * 4096))
print(json.dumps(res))
"""
    rc, out, err = run_mpremote(["exec", probe_script.strip()], timeout=5.0, supress=supress)
    
    banks = get_base_bank_list()
    total_static_found = 0
    
    if rc == 0 and out.strip():
        try:
            usages = json.loads(out.strip())
            for i in range(min(10, len(usages))):
                parsed = usages[i]
                banks[i]["used"] = max(0, min(banks[i]["total"], parsed))
                total_static_found += banks[i]["used"]
        except:
            pass
            
    return banks, total_static_found

def apply_live_heap_to_baseline(baseline_banks, live_heap_data):
    """
    Overlays dynamic heap usage on top of the cached deep-scan baseline.
    Avoids re-probing MCU memory constantly.
    """
    import copy
    banks = copy.deepcopy(baseline_banks)
    
    if not live_heap_data or not live_heap_data.get("success"):
        return banks
        
    heap_to_distribute = live_heap_data["heap_used"]
    
    # Heap in MicroPython typically lives in Banks 1, 2, 3, 4 where space permits.
    # We find free contiguous blocks in the Baseline and fill them mathematically.
    for i in range(1, 8):
        if heap_to_distribute <= 0:
            break
            
        free_space = banks[i]["total"] - banks[i]["used"]
        if free_space > 0:
            fill = min(heap_to_distribute, free_space)
            banks[i]["used"] += fill
            heap_to_distribute -= fill
            
    return banks

# ── 3. Detailed Memory Map (Once on Baseline Load) ────────────────────────────

def fetch_detailed_memory_map(supress=True):
    """
    Queries the MCU once to get heap reference address and active DMA write addresses.
    Uses id() instead of uctypes for compatibility with all MicroPython builds.
    """
    detail_script = """
import gc, json
gc.collect()

# id() returns the physical memory address in MicroPython
heap_ref = -1
try:
    b = bytearray(4)
    heap_ref = id(b)
    del b
except: pass

heap_used = -1
heap_free = -1
try:
    heap_used = gc.mem_alloc()
    heap_free = gc.mem_free()
except: pass

# Scan DMA channels for active write addresses
dma_addrs = []
try:
    import machine
    for ch in range(12):
        base = 0x50000000 + ch * 0x40
        ctrl = machine.mem32[base + 0x0C]
        if ctrl & 0x2:  # BUSY bit (bit 1)
            wa = machine.mem32[base + 0x04]
            if 0x20000000 <= wa <= 0x20082000:
                dma_addrs.append(wa)
except: pass

print(json.dumps({'heap_ref': heap_ref, 'heap_used': heap_used, 'heap_free': heap_free, 'dma': dma_addrs, 'sp': -1}))
"""
    rc, out, err = run_mpremote(["exec", detail_script.strip()], timeout=4.0, supress=supress)

    result = {
        "heap_ref": -1,
        "heap_used": 0,
        "heap_free": 0,
        "dma": [],
        "sp": -1,
        "success": False
    }

    if rc == 0 and out.strip():
        try:
            d = json.loads(out.strip())
            result.update(d)
            result["success"] = True
        except:
            pass

    return result


def compute_bank_segments(banks, detail):
    """
    Given baseline banks and detailed memory map, annotate each bank with
    {fw, heap, dma, stack} byte counts for rendering a mini 4-color stacked bar.
    """
    import copy
    banks = copy.deepcopy(banks)

    if not detail or not detail.get("success"):
        # Fallback: everything is classified as firmware
        for bank in banks:
            bank["seg_fw"] = bank["used"]
            bank["seg_heap"] = 0
            bank["seg_dma"] = 0
            bank["seg_stack"] = 0
        return banks

    heap_ref   = detail.get("heap_ref", -1)
    heap_used  = detail.get("heap_used", 0)
    heap_free  = detail.get("heap_free", 0)
    heap_total = heap_used + heap_free
    dma_addrs  = detail.get("dma", [])
    sp         = detail.get("sp", -1)

    for bank in banks:
        bank_start = int(bank["start"], 16)
        bank_end   = bank_start + bank["total"]
        used       = bank["used"]

        fw = 0; hp = 0; dm = 0; st = 0

        # ── Heap region: if heap_ref is valid ─────────────────────────────────
        if heap_ref > 0 and heap_total > 0:
            # After gc.collect(), the first allocation is near heap_start.
            # Subtract only the small GC block header overhead (16 bytes on 32-bit MicroPython).
            heap_start_est = heap_ref - 16
            heap_end_est   = heap_start_est + heap_total

            overlap_start = max(bank_start, heap_start_est)
            overlap_end   = min(bank_end,   heap_end_est)
            overlap       = max(0, overlap_end - overlap_start)

            # Clamp heap overlap to the bank's used bytes
            hp = min(int(overlap), used)
            fw = max(0, used - hp)
        else:
            fw = used

        # ── DMA buffers: any active write address that falls in this bank ─────
        dma_bytes = 0
        for dma_addr in dma_addrs:
            if bank_start <= dma_addr < bank_end:
                # Estimate 4KB per active DMA channel in this bank
                dma_bytes += min(4096, bank["total"] // 16)

        dma_bytes = min(dma_bytes, used)
        # Reclassify dma_bytes from fw or hp
        if fw >= dma_bytes:
            fw -= dma_bytes
        elif hp >= dma_bytes:
            hp -= dma_bytes
        else:
            dma_bytes = 0
        dm = dma_bytes

        # ── Stack: if stack pointer is inside this bank ───────────────────────
        stack_bytes = 0
        if sp > 0 and bank_start <= sp < bank_end:
            # Stack grows downward from the top of the bank
            stack_bytes = min(8 * 1024, used)
            if hp >= stack_bytes:
                hp -= stack_bytes
            elif fw >= stack_bytes:
                fw -= stack_bytes
            else:
                stack_bytes = 0
        st = stack_bytes

        bank["seg_fw"]    = max(0, fw)
        bank["seg_heap"]  = max(0, hp)
        bank["seg_dma"]   = max(0, dm)
        bank["seg_stack"] = max(0, st)

    return banks

# ── End Backend ──────────────────────────────────────────────────────────────
