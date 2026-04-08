# 💡 Hardware LED Control Guide

This guide explains the pinout logic and hardware-level operations for the onboard LEDs on the **Seeed Studio XIAO RP2350**.

## 1. LED Pin Definitions & Logic

The XIAO RP2350 features three distinct LED systems. While many online resources provide conflicting information, the following definitions are sourced from the **official MicroPython board configuration**.

| LED Type | Label | GPIO (RP2350) | Logic / Requirement |
| :--- | :--- | :--- | :--- |
| **Power LED** | `PWR` | N/A | Hardware-managed (Red). Lights up when USB/Battery power is active. |
| **User LED** | `L` | **GPIO 25** | Programmable Mono LED (Yellow). |
| **RGB NeoPixel** | `RGB` | **GPIO 22** (Data) | WS2812 Addressable LED. |
| **RGB Power** | `V_RGB` | **GPIO 23** (Power) | **CRITICAL**: Use `Pin(23).value(1)` to enable power to the RGB LED. |

### 🛠️ Official Definition Source
The ground truth for these mappings can be found in the [MicroPython GitHub Repository](https://github.com/micropython/micropython/blob/master/ports/rp2/boards/SEEED_XIAO_RP2350/pins.csv):
> **Reference**: `ports/rp2/boards/SEEED_XIAO_RP2350/pins.csv`
> - `NEO_POWER,GPIO23`
> - `NEOPIXEL,GPIO22`
> - `LED,GPIO25`

---

## 2. Example Code Snippet
The following MicroPython code demonstrates how to initialize the RGB power rail and cycle through the colors while toggling the user LED.

```python
import machine, neopixel, time

# 1. Enable RGB Power (GPIO 23)
machine.Pin(23, machine.Pin.OUT).value(1)
time.sleep_ms(50) # Power stabilization delay

# 2. Initialize NeoPixel (GPIO 22)
np = neopixel.NeoPixel(machine.Pin(22), 1)

# 3. Toggle Mono LED (GPIO 25)
mono = machine.Pin(25, machine.Pin.OUT)
mono.toggle()

# 4. Set RGB color
np[0] = (255, 0, 0) # Red
np.write()
```

---

*Note: For instructions on how to load and run this code on your device, please refer to the [MCU Deployment Guide](MCU_Deployment_Guide.md).*
