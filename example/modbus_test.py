import machine
import time

# ─── Modbus RTU Master — RP2350 / UART1 ─────────────────────────────────────
#
# Hardware: SEEED XIAO RP2350
#   UART1 TX  → GPIO4
#   UART1 RX  → GPIO5
#
# Settings : 9600 baud, 8 data bits, No parity, 1 stop bit (8N1)
#
# Query frame  : 01 03 23 2B 00 0A BE 41
#   Byte[0]  = 0x01  → Slave address (1 decimal)
#   Byte[1]  = 0x03  → Function code: Read Holding Registers
#   Byte[2-3]= 0x232B → Start register address
#   Byte[4-5]= 0x000A → Number of registers to read (10)
#   Byte[6-7]= 0xBE41 → CRC-16 (pre-calculated)
# ─────────────────────────────────────────────────────────────────────────────

# ─── Configuration ───────────────────────────────────────────────────────────
BAUD_RATE    = 9600
TX_PIN       = 4          # GPIO4
RX_PIN       = 5          # GPIO5

# Modbus RTU inter-frame silence = 3.5 character times
# At 115200 baud, 1 char ≈ 86 µs → 3.5 chars ≈ 302 µs → use 5 ms for safety
INTER_FRAME_MS  = 5
RESPONSE_TIMEOUT_MS = 500   # Max time to wait for response

# Fixed query frame (hex): 01 03 23 2B 00 0A BE 41
QUERY_FRAME = bytes([0x01, 0x03, 0x23, 0x2B, 0x00, 0x0A, 0xBE, 0x41])


# ─── CRC-16/Modbus (reference, for verification) ─────────────────────────────
def crc16_modbus(data: bytes) -> int:
    """Calculate Modbus RTU CRC-16 for the given byte sequence."""
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
    """Return True if the last two bytes of frame match its CRC-16."""
    if len(frame) < 3:
        return False
    calculated = crc16_modbus(frame[:-2])
    received   = frame[-2] | (frame[-1] << 8)   # little-endian in Modbus
    return calculated == received


# ─── Helper ──────────────────────────────────────────────────────────────────
def to_hex(data):
    """Return space-separated uppercase hex string (MicroPython-safe)."""
    parts = []
    for b in data:
        parts.append("{:02X}".format(b))
    return ' '.join(parts)



# ─── UART Init ───────────────────────────────────────────────────────────────
uart = machine.UART(
    1,
    baudrate = BAUD_RATE,
    bits     = 8,
    parity   = None,
    stop     = 1,
    tx       = machine.Pin(TX_PIN),
    rx       = machine.Pin(RX_PIN),
)

print("=" * 56)
print("  NanoPD 2.0 — Modbus RTU Master Test")
print("=" * 56)
print(f"  UART  : UART1  TX=GPIO{TX_PIN}  RX=GPIO{RX_PIN}")
print(f"  Baud  : {BAUD_RATE} 8N1")
print("  Query : " + to_hex(QUERY_FRAME))
print("=" * 56)
print("  Sending every 2 s — Press CTRL-C to stop")
print()


# ─── Main Loop ───────────────────────────────────────────────────────────────
try:
    cycle = 0
    while True:
        cycle += 1
        print("[{:04d}] TX -> ".format(cycle) + to_hex(QUERY_FRAME))

        # Flush any stale RX data before sending
        uart.read()

        # Send query
        uart.write(QUERY_FRAME)

        # Wait for inter-frame silence, then collect response
        time.sleep_ms(INTER_FRAME_MS)

        deadline = time.ticks_add(time.ticks_ms(), RESPONSE_TIMEOUT_MS)
        response = bytearray()

        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            chunk = uart.read()
            if chunk:
                response.extend(chunk)
                # Reset deadline on fresh data (streaming guard)
                deadline = time.ticks_add(time.ticks_ms(), INTER_FRAME_MS * 2)
            else:
                time.sleep_ms(1)

        # ── Parse & display response ─────────────────────────────────────────
        if not response:
            print("       RX ← (no response — timeout)")
        else:
            hex_str = to_hex(response)
            print(f"       RX ← {hex_str}  ({len(response)} bytes)")

            # Basic Modbus RTU validation
            if len(response) >= 3:
                slave_addr  = response[0]
                func_code   = response[1]
                crc_ok      = verify_crc(bytes(response))

                print(f"            Slave addr  : 0x{slave_addr:02X} ({slave_addr})")
                print(f"            Func code   : 0x{func_code:02X}", end="")

                if func_code == 0x03:
                    print(" (Read Holding Registers)")
                    if len(response) >= 3:
                        byte_count = response[2]
                        print(f"            Byte count  : {byte_count}")
                        reg_data = response[3:3 + byte_count]
                        registers = []
                        for i in range(0, len(reg_data) - 1, 2):
                            val = (reg_data[i] << 8) | reg_data[i + 1]
                            registers.append(val)
                        for idx, val in enumerate(registers):
                            print(f"            Reg[{idx:02d}]     : {val:5d}  (0x{val:04X})")
                elif func_code & 0x80:
                    exc_code = response[2] if len(response) > 2 else "?"
                    print(f" (Exception!  Code={exc_code})")
                else:
                    print()

                print(f"            CRC check   : {'✓ OK' if crc_ok else '✗ FAIL'}")
            else:
                print("            (frame too short to parse)")

        print()
        time.sleep(2)

except KeyboardInterrupt:
    print("\n[INFO] Interrupted by user. UART released. Ready.")
    uart.deinit()
