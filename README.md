<p align="center">
  <img src="img/logo.png" alt="nanoPD Logo" width="200">
</p>

## 📍 Table of Contents

- [🆕 Changelog (Bug Fixes & New Features)](CHANGELOG.md)
- [🚀 Quick Start](#-quick-start-windows)
- [✨ Features](#-features)
- [📂 Project Structure](#-project-structure)
- [📖 Documentation & Guides](#-documentation--guides)
  - [RP2350 Peripherals & Register Analysis Guide](guides/Peripherals_Guide.md)
  - [MCU Deployment Guide](guides/MCU_Deployment_Guide.md)
  - [SRAM Monitor Interpretation Guide](guides/SRAM_Monitor_Guide.md)
  - [XIAO RP2350 Telemetry Research](guides/xiao_rp2350_telemetry_research.md)
  - [XIAO RP2350 Reset Behavior](guides/xiao_rp2350_reset_behavior.md)
- [💡 Examples](#-examples)
  - [Hardware LED Control Guide](guides/Hardware_LED_Guide.md)

# NanoPD 2.0

**NanoPD 2.0** is an advanced debugging dashboard and control system designed specifically for the **Seeed Studio XIAO RP2350**. It provides a premium, pixel-perfect Streamlit interface for microcontroller file management, real-time memory monitoring, peripheral bit-level analysis, and low-level hardware interaction.

---

## 🚀 Quick Start (Windows)

This project is optimized for stability and ease of use. All Python dependencies are automatically managed within a self-contained `.venv`, ensuring no interference with your system.

### 1. Download and Extract
- **Download**: Get the latest source code by selecting **Download ZIP** from the Code menu.
- **Extract**: Unzip the archive into any local folder.

### 2. One-Click Setup
- **Double-click `setup.bat`** in the project folder.
- This will automatically create the virtual environment and install all required packages.

### 3. Launch the Application
- Once setup is complete, **Double-click `run.bat`** to start the dashboard.

---

## ✨ Features

- **Interactive REPL Console**: Real-time Python code execution, local file loading, and synchronized terminal output.
- **Modern Multi-page UI**: Built with Streamlit 1.36+, native navigation, and standardized 20px bottom-anchored layout.
- **MicroPython Filesystem Manager**: Push and Pull files directly from the MCU with interactive sync status.
- **SRAM Hybrid Monitor**: Real-time 520KB memory visualization with 10-bank detail tracking.
- **Peripheral Register Analyst**: Bit-level interactive grid for all RP2350 hardware registers using official SVD definitions.
- **Hardware Telemetry**: Accurate sensing for temperature, VSYS voltage (Battery/USB), and architecture (ARM/RISC-V) detection.

---

## 📂 Project Structure

- `main.py`: Entry point and navigation router.
- `pages/`: Individual dashboard pages (Filesystem, SRAM, Peripherals, etc.).
- `utils/`: Core backend logic and hardware scanning utilities.
- `guides/`: Technical documentation and hardware research.
- `img/`: Static assets and visual documentation.
- `setup.bat`: Environment setup script.
- `run.bat`: Application launch script.

---

## 📖 Documentation & Guides

Detailed research and interpretation manuals for NanoPD 2.0 components:

*   **[RP2350 Peripherals & Register Analysis Guide](guides/Peripherals_Guide.md)**: Learn how we extract official SVD definitions for live bit-level hardware reads.
*   **[MCU Deployment Guide](guides/MCU_Deployment_Guide.md)**: Detailed step-by-step instructions for loading code to the MCU using Filesystem or REPL Console.
*   **[SRAM Monitor Interpretation Guide](guides/SRAM_Monitor_Guide.md)**: Learn how the hybrid scanner works and how to read the physical memory layout.
*   **[XIAO RP2350 Telemetry Research](guides/xiao_rp2350_telemetry_research.md)**: Deep dive into the hardware nuances, ADC ghosting, and voltage sensing logic.
*   **[XIAO RP2350 Reset Behavior](guides/xiao_rp2350_reset_behavior.md)**: Official documentation detailing why the RST button and USB power cycles are identical on hardware level.

---

## 💡 Examples

Practical code examples and hardware-specific control logic for the NanoPD 2.0 platform:

*   **[Hardware LED Control Guide](guides/Hardware_LED_Guide.md)**: Detailed pinout and logic for User LED and RGB NeoPixel on the XIAO RP2350.

---
