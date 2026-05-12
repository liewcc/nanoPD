import machine
import time

# ─── Modbus RTU Proxy/Gateway — RP2350 ──────────────────────────────────────
#
# Host Side   (UART0): 115200 baud, 8N1
#   UART0 TX  → GPIO0
#   UART0 RX  → GPIO1
#
# Device Side (UART1): 9600 baud, 8N1
#   UART1 TX  → GPIO4
#   UART1 RX  → GPIO5
#
# Behavior: 
#   1. Listen on UART0.
#   2. When a complete Modbus frame is received, check if Device ID == 1.
#   3. If valid, forward the frame exactly as is out to UART1.
#   4. Wait for the device's response on UART1.
#   5. Forward the received response back to UART0.
# ─────────────────────────────────────────────────────────────────────────────

# ─── Configuration ───────────────────────────────────────────────────────────
UART0_BAUD = 115200
UART0_TX   = 0
UART0_RX   = 1

UART1_BAUD = 9600
UART1_TX   = 4
UART1_RX   = 5

TARGET_DEVICE_ID = 1
RESPONSE_TIMEOUT_MS = 500

# ─── Helpers ─────────────────────────────────────────────────────────────────
def to_hex(data):
    """Return space-separated uppercase hex string (MicroPython-safe)."""
    parts = []
    for b in data:
        parts.append("{:02X}".format(b))
    return ' '.join(parts)

def crc16_modbus(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc

def verify_crc(frame: bytes) -> bool:
    if len(frame) < 3:
        return False
    calculated = crc16_modbus(frame[:-2])
    received   = frame[-2] | (frame[-1] << 8)
    return calculated == received

# ─── Init ────────────────────────────────────────────────────────────────────
uart0 = machine.UART(0, baudrate=UART0_BAUD, tx=machine.Pin(UART0_TX), rx=machine.Pin(UART0_RX))
uart1 = machine.UART(1, baudrate=UART1_BAUD, tx=machine.Pin(UART1_TX), rx=machine.Pin(UART1_RX))

print("=" * 60)
print("  NanoPD 2.0 — Modbus RTU Proxy")
print("=" * 60)
print("  [ HOST ] UART0 : 115200 8N1 (TX=GPIO0, RX=GPIO1)")
print("  [ DEV  ] UART1 : 9600   8N1 (TX=GPIO4, RX=GPIO5)")
print(f"  Target ID      : {TARGET_DEVICE_ID} (0x{TARGET_DEVICE_ID:02X})")
print("=" * 60)
print("  Listening on UART0... Press CTRL-C to stop")
print()

try:
    while True:
        # 1. Listen for incoming query on UART0
        if uart0.any():
            query = bytearray()
            # For 115200, 3.5 char times is < 1ms. Use 5ms as safe silence gap.
            deadline = time.ticks_add(time.ticks_ms(), 5)
            
            while time.ticks_diff(deadline, time.ticks_ms()) > 0:
                chunk = uart0.read()
                if chunk:
                    query.extend(chunk)
                    deadline = time.ticks_add(time.ticks_ms(), 5)
                else:
                    time.sleep_ms(1)
            
            if len(query) > 0:
                print(f"HOST  → PROXY : {to_hex(query)}")
                
                # Validation: Minimum length for Modbus RTU is 4 bytes (ID, Func, CRC_L, CRC_H)
                if len(query) >= 4 and query[0] == TARGET_DEVICE_ID:
                    if verify_crc(bytes(query)):
                        print("PROXY → DEV   : (Forwarding to UART1)")
                        # Flush any stale data on UART1 RX before sending
                        uart1.read() 
                        uart1.write(query)
                        
                        # 2. Collect response from UART1
                        response = bytearray()
                        # Wait up to 500ms for the device to start responding
                        resp_deadline = time.ticks_add(time.ticks_ms(), RESPONSE_TIMEOUT_MS)
                        first_byte_received = False
                        
                        while time.ticks_diff(resp_deadline, time.ticks_ms()) > 0:
                            chunk = uart1.read()
                            if chunk:
                                response.extend(chunk)
                                first_byte_received = True
                                # For 9600 baud, 3.5 chars is ~4ms. Use 15ms as safe gap.
                                resp_deadline = time.ticks_add(time.ticks_ms(), 15)
                            else:
                                time.sleep_ms(1)
                                
                        if response:
                            print(f"DEV   → PROXY : {to_hex(response)}")
                            print("PROXY → HOST  : (Forwarding to UART0)")
                            uart0.write(response)
                        else:
                            print("DEV   ✗ PROXY : (Timeout! No response from device)")
                    else:
                        print("PROXY ✗ DEV   : (Ignored! Invalid CRC from Host)")
                else:
                    print("PROXY ✗ DEV   : (Ignored! Wrong Device ID or Too Short)")
                
                print("-" * 60)
        
        # Small delay to prevent 100% CPU lockup
        time.sleep_ms(5)

except KeyboardInterrupt:
    print("\n[INFO] Interrupted by user. Releasing UARTs.")
    uart0.deinit()
    uart1.deinit()
    print("Ready.")
