"""
RP2350 Peripheral Register Map and Logical Grouping.
Based on the RP2350 Datasheet.
"""

# Base addresses for atomic aliases
# Base + 0x0000: Normal
# Base + 0x1000: XOR (Atomic XOR)
# Base + 0x2000: SET (Atomic SET)
# Base + 0x3000: CLR (Atomic CLR)

PERIPHERALS = {
    "System Control": {
        "SYSINFO": 0x40000000,
        "SYSCFG": 0x40008000,
        "CLOCKS": 0x40010000,
        "RESETS": 0x40018000,
        "PSM": 0x40020000,
        "WATCHDOG": 0x400d8000,
        "POWMAN": 0x40100000,
        "TICKS": 0x40108000,
        "TBMAN": 0x40160000,
    },
    "Communication": {
        "UART0": 0x40070000,
        "UART1": 0x40078000,
        "SPI0": 0x40080000,
        "SPI1": 0x40088000,
        "I2C0": 0x40090000,
        "I2C1": 0x40098000,
        "USB": 0x50110000,
    },
    "Actuators & Timing": {
        "PWM": 0x400a8000,
        "DMA": 0x50000000,
        "TIMER0": 0x400b0000,
        "TIMER1": 0x400b8000,
        "ADC": 0x400a0000,
        "PIO0": 0x50200000,
        "PIO1": 0x50300000,
        "PIO2": 0x50400000,
    },
    "Security & OTP": {
        "SHA256": 0x400f8000,
        "OTP": 0x40120000,
        "TRNG": 0x400f0000,
    },
    "High-Speed IO": {
        "SIO": 0xd0000000,
        "HSTX": 0x400c0000,
    },
    "ARM Core Peripherals": {
        "SysTick": 0xe000e010,
        "NVIC": 0xe000e100,
        "SCB": 0xe000ed00,
        "MPU": 0xe000ed90,
        "SAU": 0xe000ede0,
        "FPU": 0xe000ef30,
        "M33_EPPB": 0xe0080000,
    },
    "RISC-V Core Peripherals": {
        "Hazard3 CLIC": 0xe0000000,
        "Machine Timer (SIO)": 0xd00001b0,
    }
}

# Example register offsets for some blocks
# (We can expand this as needed)
REGISTER_DEFINITIONS = {
    "SYSINFO": {
        "CHIP_ID": 0x00,
        "PLATFORM": 0x04,
        "GIT_HASH": 0x08,
    },
    "CLOCKS": {
        "CLK_GPOUT0_CTRL": 0x00,
        "CLK_GPOUT0_DIV": 0x04,
        "CLK_GPOUT0_SELECTED": 0x08,
        "CLK_SYS_CTRL": 0x48,
        "CLK_SYS_DIV": 0x4C,
        "CLK_SYS_SELECTED": 0x50,
        "CLK_USB_CTRL": 0x54,
        "CLK_ADC_CTRL": 0x60,
    },
    "RESETS": {
        "RESET": 0x00,
        "WDSEL": 0x04,
        "RESET_DONE": 0x08,
    },
    "SIO": {
        "CPUID": 0x00,
        "GPIO_IN": 0x04,
        "GPIO_HI_IN": 0x08,
        "GPIO_OUT": 0x10,
        "GPIO_SET": 0x14,
        "GPIO_CLR": 0x18,
        "GPIO_XOR": 0x1c,
    }
}
