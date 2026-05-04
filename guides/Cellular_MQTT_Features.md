# Cellular MQTT (ATK-D40-B) Feature Updates

## 1. Systematized UI Layout
The layout of the Cellular MQTT tab has been fully aligned with the Internet MQTT tab to provide a consistent and premium user experience:
- **Compact Layout**: The COM Port configuration, Topic inputs, and QoS selections have been optimized into tight multi-column rows. Redundant vertical spacing and text labels have been removed to completely resolve page overflow issues.
- **Race Condition Prevention**: All interactive controls (`Subscribe`, `Unsub`, `Publish`, and `Clear`) have been heavily refactored to utilize Streamlit's `on_click` callback mechanism. This ensures that button clicks are executed immediately and reliably, bypassing the background `Auto RX` execution loop that previously swallowed input states.

## 2. Dynamic Subscription Management
While preserving the high-performance Transparent Mode (Data Mode) of the DTU, the application now supports dynamic hardware subscription configuration:
- **Subscribe Button**: Dynamically breaks the DTU out of transparent mode using the `+++` and `ATK` escape sequence. It updates the target topic via the `AT+MQTTSUB1` command and automatically resumes transparent mode using `ATO`.
- **Unsub Button**: Uses the same automated AT command sequence to send `AT+MQTTSUB1="0","<topic>","0"`, removing the designated subscription directly from the hardware.
- **State Synchronization**: The `ACTIVE` subscription UI is strictly synchronized with the hardware response (`OK` or `ERROR`). The UI will only reflect a subscription change if the DTU confirms the execution of the AT command.

## 3. Pure Hardware Communication Logs
All irrelevant diagnostic labels, system alerts, and emojis have been stripped from the `MESSAGE LOGS` area to transform it into a professional, low-level serial analyzer:
- **Raw Byte Interception**: The logging utility now hooks directly into the core read/write serial buffer.
- **TX>> and RX<< Formatting**: Every byte sent to the DTU (whether an AT command or raw transparent payload) is printed in its pure form as `[Timestamp] TX>> <data>`. Responses from the DTU are cleanly logged as `[Timestamp] RX<< <data>`.
- **Hardware Debugging**: This unadulterated view allows users to accurately debug hardware-level handshake processes and interpret transient module warnings (e.g., `Please check GPRS !!!`).

## 4. Transparent Publish Mechanism
- The `Publish` button operates instantly via **Transparent Mode**. Once the DTU is provisioned, the payload is flushed directly into the serial buffer without any AT command wrappers, publishing automatically to the `PUB1` topic stored in the DTU's memory.
- This approach guarantees real-time data transmission with millisecond latency, entirely avoiding the 3-4 second blocking delay that would otherwise occur if AT commands were issued before every message.
