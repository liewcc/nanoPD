import machine
import neopixel
import time

# ─── Pin Definitions (from official MicroPython SEEED_XIAO_RP2350 pins.csv) ──
# LED          = GPIO25  (onboard yellow/green mono LED)
# NEOPIXEL     = GPIO22  (WS2812 RGB LED data pin)
# NEOPIXEL_POWER = GPIO23  (WS2812 RGB LED power enable)

# ─── Initialization ─────────────────────────────────────────────────────────
mono = machine.Pin(25, machine.Pin.OUT)

# Enable power to the RGB LED first, then init NeoPixel on the data pin
neo_power = machine.Pin(23, machine.Pin.OUT)
neo_power.value(1)
time.sleep_ms(50)  # Brief delay to let power stabilize

np = neopixel.NeoPixel(machine.Pin(22), 1)

# ─── Color Palette ──────────────────────────────────────────────────────────
COLORS = [
    (255,   0,   0),  # Red
    (  0, 255,   0),  # Green
    (  0,   0, 255),  # Blue
    (255, 255,   0),  # Yellow
    (  0, 255, 255),  # Cyan
    (255,   0, 255),  # Magenta
    (255, 128,   0),  # Orange
    (255, 255, 255),  # White
]

# ─── Main Loop: Blink mono LED + cycle RGB colors ───────────────────────────
print("NanoPD 2.0 — LED Blink Test")
print(f"  Mono LED : GPIO25")
print(f"  NeoPixel : GPIO22 (data), GPIO23 (power)")
print("Running...")

idx = 0
while True:
    # Toggle mono LED every cycle (heartbeat)
    mono.toggle()

    # Set RGB to current color
    np[0] = COLORS[idx]
    np.write()
    print(f"  RGB -> {COLORS[idx]}")

    time.sleep(0.5)

    # Turn off RGB briefly for blink effect
    np[0] = (0, 0, 0)
    np.write()

    time.sleep(0.2)

    # Advance to next color
    idx = (idx + 1) % len(COLORS)