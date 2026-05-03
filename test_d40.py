import serial
import time
import sys

PORT = "COM3"
BAUD = 115200 # common DTU baudrate, we can try 9600 if this fails

print(f"Opening {PORT} at {BAUD} baud...")
try:
    ser = serial.Serial(PORT, BAUD, timeout=0.1)
except Exception as e:
    print(f"Failed to open port: {e}")
    sys.exit(1)

def send_and_wait(data: bytes, wait_time: float = 1.0) -> bytes:
    ser.reset_input_buffer()
    ser.write(data)
    ser.flush()
    print(f">> TX: {data}")
    
    deadline = time.time() + wait_time
    rx_buf = bytearray()
    last_t = None
    while time.time() < deadline:
        w = ser.in_waiting
        if w > 0:
            rx_buf.extend(ser.read(w))
            last_t = time.time()
        elif last_t and (time.time() - last_t) > 0.2:
            break
        time.sleep(0.01)
    
    print(f"<< RX: {bytes(rx_buf)}")
    return bytes(rx_buf)

print("\n--- Step 1: Escape Transparent Mode ---")
print("Waiting 1s silence...")
time.sleep(1.0)
resp = send_and_wait(b'+++', 2.0)
if b'atk' not in resp.lower() and b'ok' not in resp.lower():
    print("WARNING: Did not receive expected escape response.")
time.sleep(0.5)

print("\n--- Step 2: Testing AT Command Combinations ---")
commands_to_test = [
    (b'AT\r\n', "Standard CRLF"),
    (b'AT\r', "Only CR"),
    (b'AT\n', "Only LF"),
    (b'at\r\n', "Lowercase CRLF"),
    (b'AT+CSQ\r\n', "Standard CSQ"),
    (b'ALIENTEK@AT\r\n', "Password prefix"),
    (b'ATK+VER\r\n', "ATK proprietary prefix"),
    (b'ATK+RST\r\n', "ATK proprietary restart"),
]

for cmd, desc in commands_to_test:
    print(f"\nTesting: {desc}")
    resp = send_and_wait(cmd, 1.5)
    if b'OK' in resp.upper() or b'ATK' in resp.upper() and b'ERROR' not in resp.upper():
        print(f"SUCCESS! '{desc}' worked.")
        if b'Restart' not in resp:
            break # Found the working format!
    else:
        print(f"Failed.")
    time.sleep(1.0) # wait before next test

ser.close()
print("\nDone testing.")
