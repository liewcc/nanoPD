# RP2350 Peripherals & Register Analysis Guide

The **Peripherals** page in NanoPD 2.0 provides a real-time, bit-level view of the RP2350's internal hardware registers. This guide explains how the register definitions are sourced, how the host communicates with the microcontroller, and how the application is structured.

## 1. Extracting Register Data from SVD

The RP2350 microcontroller has hundreds of hardware registers, each with specific bitfields controlling various peripherals (e.g., UART, I2C, SPI, ADC). To make this human-readable, we extract definitions from the [official System View Description (SVD)](https://github.com/raspberrypi/pico-sdk/blob/master/src/rp2350/hardware_regs/RP2350.svd) file provided by Raspberry Pi.

- **SVD to JSON Conversion**: A pre-processing step parses the massive XML-based `.svd` file into a highly optimized, hierarchical JSON format (`utils/rp2350_regs.json`).
- **Metadata Structure**: The JSON is structured by `peripheral_base_hex` and `register_offset_hex`, containing bitfield ranges (`[start:end]`), names, and descriptions.
- **Lookup Mechanism**: The `utils/peripheral_metadata.py` module loads this JSON into memory. When a user clicks on a specific address in the UI, the script calculates the offset from the peripheral's base address and retrieves the exact bitfield descriptions for rendering the interactive bit-grid.

## 2. MCU Communication Mechanism

To read the live state of these registers without interrupting the main application, NanoPD 2.0 uses a dynamic code injection approach rather than traditional serial commands.

- **Dynamic Execution**: The application utilizes standard `mpremote exec` to inject a short, ephemeral Python script directly into the MicroPython REPL running on the target device.
- **Direct Memory Access**: The injected script uses the `machine.mem32` object to perform direct 32-bit width memory reads at the requested hardware addresses.
- **Stateless Read**: The script collects the values, formats them as hexadecimal strings, and prints them back to the host via standard output (stdout), which NanoPD 2.0 captures and decodes. This allows for instantaneous, crash-safe reads of the register tree.

## 3. Application Deployment & Architecture

The Peripherals scanning module adheres strictly to the NanoPD 2.0 `utils/` versus `mcu/` separation rule.

- **Host-Side Execution**: The actual scanning logic (`utils/peripheral_scanner.py`, metadata parsing, and data fetching in `pages/Peripherals.py`) resides entirely on the host PC. 
- **Zero MCU Dependencies**: Because we use `mpremote exec` to inject standard `machine.mem32` calls on demand, no custom firmware or background scripts need to be deployed to or stored on the MCU file system for this feature to work.
## 4. Addressing Missing Official Register Definitions

While the RP2350 SVD provides definitions for most peripherals, certain critical "Core-Private" registers are systematically missing. NanoPD 2.0 supplements these using a manual metadata overlay (`utils/core_regs.json`).

### Why are these missing from official SVDs?
Architectural registers (ARM/RISC-V) are typically managed by the processor vendor rather than the chip's peripheral designers. Consequently:
- **Architecture Standards**: Standard ARM (Cortex-M) or RISC-V (Privileged) registers are documented in architectural reference manuals, not in vendor-specific SVD files.
- **Platform Extensions**: Custom core logic (e.g., RP2350's EPPB or Hazard3 CLIC) is often described in the datasheet's text chapters but omitted from the machine-readable SVD, which generic tools rely on.

### Documented Omissions (Supplemented by NanoPD 2.0)

| Register Block | Base Address | Architecture | Key Registers | Implementation Reason |
| :--- | :--- | :--- | :--- | :--- |
| **Arm Private Peripherals** | `0xE000E000` | ARM M33 | SysTick, NVIC, SCB, MPU | Standard ARM Core components (v8-M). |
| **Arm EPPB** | `0xE0080000` | ARM M33 | NMI_MASK0/1 | Enhanced Private Peripheral Bus (RP2350 specific). |
| **Hazard3 CLIC** | `0xE0000000` | RISC-V | CLICCFG, CLICINFO | Core-Local Interrupt Controller for Hazard3. |
| **RISC-V Timer** | `0xD00001B0` | RISC-V | MTIME, MTIMECMP | RISC-V standard timer, embedded in RP2350 SIO. |

### How to use in NanoPD 2.0
When browsing the **Peripherals** page, use the **Architecture** selector to toggle between ARM and RISC-V definitions. The system will automatically switch the metadata mapping for the `0xE0000000` region to match the selected core's hardware logic.
