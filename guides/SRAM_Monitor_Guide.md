# SRAM Monitor Interpretation Guide

This guide explains how to read and interpret the real-time memory data provided by the **SRAM Monitor** in NanoPD 2.0.

## 1. Scanning Methodology: Smart Hybrid Scanning

The SRAM Monitor does not perform a full physical scan every second (which would be slow and might freeze the MCU). Instead, it uses a **Hybrid Approach**:

*   **Baseline Deep Probe**: Performed automatically once when you enter the page. It uses a hardware "probe" (`machine.mem32`) to detect every single non-zero byte in the SRAM. This captures the static footprint of the firmware and any "dirty" memory left over from previous operations.
*   **Live Heap Polling**: Runs every 1 second. It performs a nearly instant $O(1)$ query to the MicroPython Garbage Collector (`gc.mem_alloc()`) to find out exactly how many bytes are currently being used by active Python objects.
*   **DMA & Stack Sniffing**: The system looks at CPU registers to find the exact location of the Stack Pointer and any active DMA transfer buffers.

---

## 2. Understanding the Global SRAM Usage Bar

The horizontal bar at the top represents the total **520KB** of SRAM on the RP2350.

| Segment | Color | Meaning |
| :--- | :--- | :--- |
| **FW** | ⬛ Black | **Firmware Static Area**. Contains the fixed C-code variables (`.data` and `.bss`) and system overhead. |
| **HEAP** | 🟡 Yellow | **Active Python Objects**. This is the exact amount of memory being used by your running code *right now*. |
| **PHYS** | 🟣 Indigo | **Physical Residue**. These are bytes that are non-zero but are *not* active objects. This happens because MicroPython does not "zero out" memory when it releases an object. It is "dirty" but available for future heap use. |
| **DMA** | 🟢 Green | **DMA Buffers**. Memory currently being used for high-speed background data transfers. |
| **STACK** | 🟤 Brown | **CPU Stack**. Memory used for function call nesting and local variables in C/MicroPython. |
| **FREE** | ░ Gray | **Vacuum Empty**. Memory that contains only zeros and has never been written to since the last power-cycle. |

---

## 3. Reading the Bank Detail Cards

The RP2350 SRAM is divided into **10 Banks**. Each card shows a mini-version of the memory layout for that specific bank.

> [!NOTE]
> **Why is there no yellow HEAP in the Bank cards?**
> A physical hardware probe can only see if a byte is "1" or "0". It cannot tell if a "1" belongs to a live Python variable or a deleted one. Therefore, in the detailed Bank view, everything in the "Heap Territory" is lumped into **PHYS (Indigo)**.

### How to interpret Bank 0:
Bank 0 usually contains a mix of **FW (Black)** and **PHYS (Indigo)**. The point where the color shifts from Black to Indigo is the **Heap Start Address**.

### How to interpret Banks 1-4:
These usually appear as solid **PHYS (Indigo)** because the MicroPython Heap Pool is mapped to these banks. Even if your code only uses 4KB of "active" heap, these banks will show "occupied" if they were used once before and not cleared.

### How to interpret Banks 5-9:
These are typically **FREE (Gray)** unless you are using specific high-speed features or large data buffers that spill over into these regions.
