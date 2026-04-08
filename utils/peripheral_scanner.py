import subprocess
import sys
import os
import json

def read_register(address):
    """Reads a 32-bit register value from the given address via mpremote."""
    cmd = [
        sys.executable, "-m", "mpremote", "exec",
        f"import machine; print(hex(machine.mem32[{hex(address)}]))"
    ]
    try:
        # Hide console window on Windows
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        res = subprocess.run(cmd, capture_output=True, timeout=2.0, creationflags=creationflags)
        if res.returncode == 0:
            return res.stdout.decode().strip()
    except Exception:
        pass
    return "0x00000000"

def read_multiple_registers(address_map):
    """
    Reads multiple registers in a single mpremote call for efficiency.
    address_map: dict of {name: address}
    """
    keys = list(address_map.keys())
    addrs = [hex(address_map[k]) for k in keys]
    
    script = f"import machine; print([hex(machine.mem32[a]) for a in {addrs}])"
    cmd = [
        sys.executable, "-m", "mpremote", "exec",
        script
    ]
    try:
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        res = subprocess.run(cmd, capture_output=True, timeout=2.0, creationflags=creationflags)
        if res.returncode == 0:
            values = eval(res.stdout.decode().strip())
            return dict(zip(keys, values))
    except Exception:
        pass
    return {k: "0x00000000" for k in keys}

if __name__ == "__main__":
    # Quick test
    print(f"SYSINFO: {read_register(0x40000000)}")
