import serial
import time
import sys

PORT = "COM3"
BAUD = 115200 

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

def try_escape_with_reply(reply: bytes):
    print(f"\n--- Trying +++ then replying with {reply} ---")
    time.sleep(1.0)
    resp = send_and_wait(b'+++', 1.0)
    if b'atk' in resp.lower() or b'a' in resp.lower() or b'ok' in resp.lower():
        time.sleep(0.1)
        resp2 = send_and_wait(reply, 1.0)
        if b'ok' in resp2.lower():
            print("SUCCESS! Entered AT mode.")
            return True
        else:
            print(f"Failed. Received: {resp2}")
    return False

# Try sending 'a'
if not try_escape_with_reply(b'a'):
    time.sleep(2)
    # Try sending 'atk'
    if not try_escape_with_reply(b'atk'):
        time.sleep(2)
        # Try sending 'ATK'
        try_escape_with_reply(b'ATK')

ser.close()
