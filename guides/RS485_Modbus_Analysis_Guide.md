# RS485 Decoder & Modbus Address Analysis Guide

## 1. Overview
The **RS485 Decoder** is an advanced serial monitoring and diagnostic interface built into the nanoPD dashboard. It is designed to interpret hex streams from industrial sensors (such as the NY-series Modbus devices) in real-time, while providing a specialized **Modbus Address Analysis** tab for deep register inspection.

## 2. RS485 Hex Stream Decoding
The primary tab focuses on capturing and formatting raw RS485 traffic:
- **Global Port Monitoring**: Implements a cross-page state mechanism that actively monitors COM port occupancy. If a port is already locked by another module (like the Cellular MQTT DTU), the interface displays an active warning in the sidebar and disables the port to prevent access denial errors.
- **Dynamic Viewport Constraints**: The message log utilizes a DOM-aware layout script that dynamically calculates the remaining screen height. This ensures the output `textarea` stretches perfectly to the bottom of the screen without causing browser scrolling or clipping.
- **Protocol Formatting**: Automatically formats raw byte streams into readable Hex structures (e.g., `01 03 04 01 02 03 04 CR LF`) and provides quick filtering capabilities to separate `TX` and `RX` channels.

## 3. Modbus Address Analysis
The secondary tab functions as a highly customizable Modbus register mapping tool:
- **CSV-Driven Configuration**: The analysis grid is driven by underlying CSV template files (e.g., `NY-401D.csv`, `NY-608D.csv`). These files map physical Modbus registers (like `9001`, `9002`) to human-readable names, data types, and scaling factors.
- **Interactive Data Grid**: Utilizes Streamlit's `st.data_editor` to provide a robust, Excel-like interface. Users can actively toggle switches, inspect values, or modify configuration scaling directly on the dashboard.
- **State Preservation Mechanism**: Implements strict session state persistence to ensure that dynamic modifications to the data grid are not wiped out by the app's auto-refresh loop or cross-tab navigation.

## 4. Architecture & Modularity
- The serial execution logic runs asynchronously, decoupled from the UI thread, ensuring the dashboard remains responsive even under heavy data loads at high baud rates.
- The separation of the raw hex viewer and the structured Modbus analyzer allows engineers to first verify physical layer connectivity, and then seamlessly switch tabs to interpret the application-layer payload.
