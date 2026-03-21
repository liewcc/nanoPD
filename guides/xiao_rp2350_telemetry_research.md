# Research Article: RP2350 Core Monitoring & Seeed XIAO Nuances

## Overview
This document summarizes technical findings discovered during the development of the **NanoPD 2.0** Core Monitoring dashboard for the Seeed Studio XIAO RP2350.

## 1. The "ADC Ghosting" Phenomenon
During development, we observed temperature readings jumping to 60°C while the chip was physically cool. 
### Findings:
- The RP2350's ADC is significantly faster than the RP2040. When switching from the VSYS channel (high voltage) to the Internal Temperature channel (lower voltage), leftover charge in the sample-and-hold circuit creates a "ghost reading."
- **Solution**: Implementing a "Safe Read" protocol that discards the first sample and averages subsequent high-speed samples (N=32+).

## 2. Seeed Studio XIAO RP2350 Power Design
The XIAO RP2350 implements a specific Battery Management System (BMS) that differs from the Raspberry Pi Pico 2.

### Pin Map:
- **Enable (GPIO19)**: Must be active (High) to close the sensing loop. 
- **Sample (GPIO29/ADC3)**: Reads the divided voltage.

### The "0V USB" Mystery:
On the standard Pico, the VSYS pin monitors the main system rail, which is powered by either USB or battery. On the XIAO RP2350, the sensing circuit is behind a diode that isolates it to the **battery terminal only**.
- **Result**: On USB power without a battery, the sensor reports 0V.
- **Handling**: Our software now detects this "Low Voltage + High Raw Noise" state and identifies it as **"USB Power (No Battery)"**.

## 3. Thermal Calibration Constants
The RP2350 datasheet provides a nominal formula:
`T = 27 - (Vadc - 0.706) / 0.001721`

However, real-world variations on the XIAO RP2350 showed:
- **VREF Stability**: While nominally 3.3V, USB ripple can affect accuracy.
- **Sensor Offset**: Some silicon revisions match a 0.650V offset better than the standard 0.706V. We implemented an adaptive heuristic to choose the correct offset based on uptime and reported temperature.

---
*Created for the NanoPD 2.0 Project Documentation & Guides.*
