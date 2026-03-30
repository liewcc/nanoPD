# 🚀 MCU Deployment Guide

This guide explains the primary methods for loading code (e.g., `example/LED.py`) to your NanoPD hardware using the application interface.

## 1. Method A: Filesystem Integration (Persistent)
Use the **Filesystem** page to manage files stored on the MCU's internal flash memory. This method is used for code that needs to persist across reboots.

1.  **Stage to Project**: Copy your target script (e.g., `example/LED.py` from the root) and paste it into the **`mcu/`** folder of the repository.
2.  **Preparation**: Rename the file inside the **`mcu/`** folder to **`main.py`** if you want it to run automatically whenever the board is powered on.
3.  **Upload & Execute**:
    *   **Push to MCU**: In the **Filesystem** page, select the newly renamed `main.py` from the local source column and click **Push to MCU**.
    *   **Virtual Drive**: Alternatively, if the **Virtual Drive** is mounted (using the "Mount Virtual Drive" button), drag and drop the `main.py` directly into the mapped drive letter in Windows Explorer.
4.  **Reset**: Perform a **Soft Reset** or hardware power cycle to trigger the new `main.py`.

---

## 2. Method B: REPL Console (Immediate/Testing)
The **REPL Console** is ideal for rapid prototyping, debugging, and one-off script execution without writing to the permanent flash storage.

1.  **Option 1: Load Local File**: Click the **📂 Load Local File** button in the REPL Console and select your script from the filesystem. The code will populate the editor immediately.
2.  **Option 2: Copy & Paste**: Simply copy the code from your external editor and paste it into the **CODING** text area.
3.  **Execution**: Click **🚀 Run Code**. The script is sent over the serial connection to the MCU's RAM and executed.
4.  **Monitoring**: View the real-time results, print statements, and error logs in the **MCU OUTPUT** panel on the right.

---

*Note: For official pinout details and hardware-specific logic, please refer to the [Hardware LED Control Guide](Hardware_LED_Guide.md).*
