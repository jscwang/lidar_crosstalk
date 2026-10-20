"""Line transports: the real USB-UART port, or anything with the same shape.

Author: Jessica
"""
from __future__ import annotations

import time
from typing import Optional, Protocol


class Transport(Protocol):
    def write_line(self, line: str) -> None: ...
    def read_line(self, timeout: float) -> Optional[str]: ...
    def close(self) -> None: ...


class SerialTransport:
    """pyserial port to the ESP32-S3-DevKitC-1 (port marked UART).

    DTR and RTS are held released before the port opens: on the DevKitC's
    auto-reset circuit, toggling them can reset the ESP32 or put it into the
    bootloader. The device client still copes with a BOOT line at any time.
    """

    def __init__(self, port: str, baud: int = 921600):
        import serial   # imported here so the simulator works without pyserial

        self._ser = serial.Serial()
        self._ser.port = port
        self._ser.baudrate = baud
        self._ser.timeout = 0.05
        self._ser.dtr = False
        self._ser.rts = False
        self._ser.open()
        self._buf = bytearray()

    def write_line(self, line: str) -> None:
        self._ser.write(line.encode("ascii") + b"\n")
        self._ser.flush()

    def read_line(self, timeout: float) -> Optional[str]:
        deadline = time.monotonic() + timeout
        while True:
            nl = self._buf.find(b"\n")
            if nl >= 0:
                raw = bytes(self._buf[:nl])
                del self._buf[:nl + 1]
                return raw.decode("ascii", errors="replace").rstrip("\r")
            chunk = self._ser.read(max(1, self._ser.in_waiting))
            if chunk:
                self._buf += chunk
            elif time.monotonic() >= deadline:
                return None

    def close(self) -> None:
        self._ser.close()


# USB vendor IDs of the chips found on ESP32-S3 boards. The Windows port name is
# not reliable (a CH343 and the ESP32's own USB can both show as "USB Serial
# Device"), but the vendor ID is.
USB_UART_VENDORS = {
    0x1A86: "WCH CH34x",          # CH343 on the local N16R8 board
    0x10C4: "Silicon Labs CP210x",  # CP2102N on the Espressif DevKitC-1
    0x0403: "FTDI",               # FT232 on the antenna-socket variant
}
ESPRESSIF_USB = 0x303A           # the ESP32-S3's built-in USB (GPIO19/20)


def classify_port(vid) -> str:
    """Which role a USB port plays for the rig, from its vendor ID."""
    if vid in USB_UART_VENDORS:
        return f"USB-UART ({USB_UART_VENDORS[vid]}): use this port for the rig"
    if vid == ESPRESSIF_USB:
        return "ESP32-S3 built-in USB: flashing only, the rig sends no data here"
    return "not an ESP32 board port"


def list_ports() -> list[tuple[str, str, str, str]]:
    """(device, description, "VID:PID", role) for every serial port."""
    from serial.tools import list_ports as lp

    out = []
    for p in lp.comports():
        ids = f"{p.vid:04X}:{p.pid:04X}" if p.vid is not None else "-"
        out.append((p.device, p.description, ids, classify_port(p.vid)))
    return out
