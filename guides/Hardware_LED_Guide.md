# 💡 Hardware LED Control Guide

This guide explains the pinout logic and deployment methods for the onboard LEDs on the **Seeed Studio XIAO RP2350**.

## 1. LED Pin Definitions & Logic

The XIAO RP2350 features three distinct LED systems. While many online resources provide conflicting information, the following definitions are sourced from the **official MicroPython board configuration**.

| LED Type | Label | GPIO (RP2350) | Logic / Requirement |
| :--- | :--- | :--- | :--- |
| **Power LED** | `PWR` | N/A | Hardware-managed (Green). Lights up when USB/Battery power is active. |
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

## 2. Methodology: Loading Code to MCU

There are two primary ways to deploy the `example/LED.py` (or any script) to your NanoPD hardware using this application.

### Method A: Filesystem Integration (Persistent)
Use the **Filesystem** page to manage files stored on the MCU's internal flash memory.

1.  **Stage to Project**: Copy `example/LED.py` (from the root) and paste it into the **`mcu/`** folder.
2.  **Preparation**: Rename the file inside the `mcu/` folder to **`main.py`** so it runs automatically on boot.
3.  **Upload & Execute**:
    *   **Push to MCU**: In the Filesystem interface, select the newly renamed `main.py` from the local source and click **Push to MCU**.
    *   **Virtual Drive**: Alternatively, if the Virtual Drive is mounted, drag and drop the `main.py` directly into the mapped drive.
4.  **Reset**: Perform a Soft Reset or hardware power cycle to trigger the new `main.py`.

### Method B: REPL Console (Immediate/Testing)
The **REPL Console** is ideal for rapid prototyping without writing to the permanent flash.

1.  **Option 1: Load Local File**: Click the **📂 Load Local File** button and select `example/LED.py`. The code will appear in the editor.
2.  **Option 2: Copy & Paste**: Simply copy the code from your editor and paste it into the **CODING** text area.
3.  **Execution**: Click **🚀 Run Code**. The script is sent to the MCU's RAM and executed immediately. Output will appear in the **MCU OUTPUT** panel.

---

## 3. Example Code Snippet
```python
import machine, neopixel, time

# Enable RGB Power (GPIO 23)
machine.Pin(23, machine.Pin.OUT).value(1)
time.sleep_ms(50)

# Initialize NeoPixel (GPIO 22)
np = neopixel.NeoPixel(machine.Pin(22), 1)
np[0] = (255, 0, 0) # Red
np.write()
```
