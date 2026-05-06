# ATK-D40/D43 Data Collection & Modbus Knowledge Base

This document summarizes the configuration methods for the ATK-D40/D43 series DTU's data collection features, covering Mode switching, Custom Polling, and Modbus Packaging.

## 1. Core Mode Switch (`AT+TASKMD`)

The `AT+TASKMD` command determines how the DTU handles data collection.

| Value | Mode | Description |
| :--- | :--- | :--- |
| `"OFF"` | **Disable** | No automated polling. Standard MQTT/Transparent mode. |
| `"TRANS"` | **Custom Polling** | DTU sends raw HEX commands and reports responses as-is. |
| `"MODBUS"` | **Modbus Packaging** | DTU parses Modbus RTU responses into logical data points. |
| `"ALINK"` | **Aliyun Alink** | Modbus data is packaged into Aliyun IoT JSON format. |
| `"ONENET"` | **OneNET** | Modbus data is packaged for China Mobile OneNET. |

---

## 2. Custom Polling Mode (`TRANS`)

Used for reading raw data blocks or non-standard protocols.

### Key AT Commands:
- **Set Mode**: `AT+TASKMD="TRANS"`
- **Task Count**: `AT+TRANSPOLLNUM=<num>` (e.g., `AT+TRANSPOLLNUM="1"`)
- **Set Command**: `AT+TRANSCMD<n>="<hex_string>"`
  - *Example*: `AT+TRANSCMD1="2F0300000028439A"` (Reads 40 registers from Slave 2F).
- **Polling Interval**: `AT+TASKTIME="<n>","<ms>"`
  - *Example*: `AT+TASKTIME="1","5000"` (5 second interval for Task 1).
- **Reporting Format**: `AT+TASKDIST="<switch>","<format_string>"`
  - **`<switch>`**:
    - `"0"`: **Disable Identifier**. Only reports the content of `<format_string>`.
    - `"1"`: **Enable Identifier**. Prepend the **Key Name (键名)** to the reported data.
  - *Example (No ID)*: `AT+TASKDIST="0","<%d>"`
  - *Example (With ID)*: `AT+TASKDIST="1","<%d>"`

---

## 3. Modbus Packaging Mode (`MODBUS`)

Used when you want the DTU to parse registers into specific data types (int, float, etc.).

### UI Logic (Config Software):
- **Main Data (主数据)**: The actual register values requested (maps to `<%d>`).
- **Sub Data (副数据)**: Metadata like Slave ID, Function Code, etc. (maps to `<%a>`, `<%f>`).

### Data Length & Types:
The DTU automatically calculates the number of registers to read based on the **Format (格式)** column:
- `uint16`: 1 Register (2 bytes)
- `uint32` / `float`: 2 Registers (4 bytes)
- `int64` / `double`: 4 Registers (8 bytes)

### Key AT Commands:
- **Set Mode**: `AT+TASKMD="MODBUS"`
- **Define Task**: `AT+TASKDEV` (Usually configured via PC software due to complexity of mapping multiple fields).

---

## 4. Reporting Formats & Placeholders

When using `AT+TASKDIST` or `AT+MQTTDIST`, use placeholders to build your packet:

| Placeholder | Meaning |
| :--- | :--- |
| `<%d>` | **Main Data**: The content of the registers. |
| `<%a>` | **Slave Address**: The Modbus device ID. |
| `<%f>` | **Function Code**: E.g., 03 (Read), 01 (Coil). |
| `<%i>` | **Task ID**: The index of the command (Cmd 1, Cmd 2...). |
| `<%t>` | **Timestamp**: Current time from the network (if available). |

*Example MQTT Format*: `{"id":<%a>, "val":<%d>, "cmd":<%i>}`

---

## 5. Important Operations

- **Save & Apply**: Most changes require `AT+Z` (Restart) to take effect.
- **Task Limit**: Supports multiple tasks (usually up to 5-20 depending on firmware).
- **Guard Time**: Ensure 1.1s silence before/after `+++` to enter AT mode reliably.

---
## 6. Project Development Rules

- **File Exclusion**: `all parameter.txt` is for local reference only and **MUST NOT** be pushed to the repository.
- **Aesthetics**: Maintain the "GemiPersona Pro" style with consistent spacing and premium CSS tokens.
- **Hardware Safety**: Always use `AT+PWR` for full restarts and respect the 1.1s guard time for mode switching.

---
*Last Updated: 2026-05-07 | Based on Manual V1.1 and Parameter Logs.*
