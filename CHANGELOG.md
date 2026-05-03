# 🆕 Changelog (Bug Fixes & New Features)

## Latest Updates

*   **COM Port Detection (Home Page)**: Updated to automatically refresh the COM port list using modern Streamlit API (`@st.fragment`), displaying full details (VID, PID, description) without full page reloads.
*   **REPL Execution Stability (`mpremote` Raw REPL Fix)**: Fixed the common `TransportError: could not enter raw repl` issue. The system now uses `pyserial` to explicitly send a direct `Ctrl+C` interrupt to the exact MCU port (detected via VID `0x2E8A` / `RP2`), bypassing busy loops. It then securely connects using `mpremote connect <port> exec` rather than relying on automatic port guessing.
*   **Over-The-Air (OTA) Updates & Versioning**: Added a "System Version" container on the Home page that automatically queries the GitHub remote (with a 60-second cache) to detect if a newer commit is available. Provides a 1-click `Update` button to execute a safe `git pull` without overriding local configurations.
*   **UI Polish & Aesthetics**: Perfected vertical alignment across metric blocks and action buttons. Enforced strict monospace typography on the COM Ports data table to match the register analysis aesthetics.
