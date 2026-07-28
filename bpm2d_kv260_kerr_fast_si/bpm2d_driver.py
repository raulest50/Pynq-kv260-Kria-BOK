"""Low-level PYNQ driver for the BPM2D KV260 Kerr Fast SI accelerator."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter_ns
from typing import Any, Tuple

import numpy as np

try:
    from pynq import Clocks, Overlay, allocate
except ImportError:  # Allows syntax/unit checks away from the Kria image.
    Clocks = None
    Overlay = None
    allocate = None


N = 64
SHAPE = (N, N)
DTYPE = np.dtype(np.complex64)
IP_VLNV = "fotonica109:hls:bpm2d_kv260_m_axi_kerr_fast_si:1.0"
TARGET_PL_CLOCK_MHZ = 125.0
PL_CLOCK_TOLERANCE_MHZ = 0.01

AP_CTRL = 0x00
PHI_IN_LOW = 0x10
PHI_IN_HIGH = 0x14
PHI_OUT_LOW = 0x1C
PHI_OUT_HIGH = 0x20

AP_START = 1 << 0
AP_DONE = 1 << 1
AP_IDLE = 1 << 2
AP_READY = 1 << 3


class AcceleratorTimeout(TimeoutError):
    """Raised when AP_DONE is not observed before the configured deadline."""


@dataclass(frozen=True)
class KernelTiming:
    seconds: float
    ctrl_before: int
    ctrl_after: int


def _buffer_address(buffer: Any) -> int:
    for attribute in ("device_address", "physical_address"):
        value = getattr(buffer, attribute, None)
        if value is not None:
            return int(value)
    raise TypeError("The object is not a PYNQ physically contiguous buffer.")


def _validate_buffer(buffer: Any, name: str) -> None:
    if tuple(buffer.shape) != SHAPE:
        raise ValueError(f"{name} must have shape {SHAPE}; got {buffer.shape}.")
    if np.dtype(buffer.dtype) != DTYPE:
        raise ValueError(f"{name} must have dtype complex64; got {buffer.dtype}.")
    if not buffer.flags.c_contiguous:
        raise ValueError(f"{name} must be C-contiguous.")
    _buffer_address(buffer)


def sync_to_device(buffer: Any) -> None:
    method = getattr(buffer, "sync_to_device", None)
    if method is not None:
        method()
        return
    fallback = getattr(buffer, "flush", None)
    if fallback is None:
        raise TypeError("The buffer provides neither sync_to_device() nor flush().")
    fallback()


def sync_from_device(buffer: Any) -> None:
    method = getattr(buffer, "sync_from_device", None)
    if method is not None:
        method()
        return
    fallback = getattr(buffer, "invalidate", None)
    if fallback is None:
        raise TypeError(
            "The buffer provides neither sync_from_device() nor invalidate()."
        )
    fallback()


def discover_accelerator(overlay: Any) -> Tuple[str, Any]:
    candidates = []
    for name, description in overlay.ip_dict.items():
        vlnv = str(description.get("type", description.get("vlnv", "")))
        if vlnv == IP_VLNV:
            candidates.append(name)

    if len(candidates) != 1:
        available = {
            name: str(description.get("type", description.get("vlnv", "")))
            for name, description in overlay.ip_dict.items()
        }
        raise RuntimeError(
            f"Expected exactly one '{IP_VLNV}' IP, found {candidates}. "
            f"Available IPs: {available}"
        )

    name = candidates[0]
    instance = overlay
    for component in name.split("/"):
        instance = getattr(instance, component)
    return name, instance


class BPM2DOverlay:
    """Programs the overlay and launches one fixed 120-update segment."""

    def __init__(
        self,
        bitfile: Path | str,
        *,
        timeout_s: float = 2.0,
        download: bool = True,
    ) -> None:
        if Overlay is None:
            raise RuntimeError("PYNQ is required to load the BPM2D overlay.")
        if Clocks is None:
            raise RuntimeError("PYNQ clock control is unavailable.")
        if timeout_s <= 0.0:
            raise ValueError("timeout_s must be positive.")

        self.bitfile = Path(bitfile).resolve()
        self.hwhfile = self.bitfile.with_suffix(".hwh")
        self.xclbinfile = self.bitfile.with_suffix(".xclbin")
        if not self.bitfile.is_file():
            raise FileNotFoundError(self.bitfile)
        if not self.hwhfile.is_file():
            raise FileNotFoundError(
                f"Matching HWH not found beside bitstream: {self.hwhfile}"
            )
        if not self.xclbinfile.is_file():
            raise FileNotFoundError(
                "Matching XCLBIN metadata sidecar not found beside bitstream: "
                f"{self.xclbinfile}"
            )

        Clocks.fclk0_mhz = TARGET_PL_CLOCK_MHZ
        self.pl_clock_mhz = float(Clocks.fclk0_mhz)
        if abs(self.pl_clock_mhz - TARGET_PL_CLOCK_MHZ) > PL_CLOCK_TOLERANCE_MHZ:
            raise RuntimeError(
                f"Could not set fclk0 to {TARGET_PL_CLOCK_MHZ:.6f} MHz; "
                f"measured {self.pl_clock_mhz:.6f} MHz."
            )

        load_start = perf_counter_ns()
        self.overlay = Overlay(str(self.bitfile), download=download)
        Clocks.fclk0_mhz = TARGET_PL_CLOCK_MHZ
        self.pl_clock_mhz = float(Clocks.fclk0_mhz)
        if abs(self.pl_clock_mhz - TARGET_PL_CLOCK_MHZ) > PL_CLOCK_TOLERANCE_MHZ:
            raise RuntimeError(
                "Could not restore fclk0 after overlay loading: "
                f"{self.pl_clock_mhz:.6f} MHz."
            )
        self.overlay_load_s = (perf_counter_ns() - load_start) * 1.0e-9
        self.ip_name, self.ip = discover_accelerator(self.overlay)
        self.timeout_s = float(timeout_s)

    def allocate_buffers(self) -> Tuple[Any, Any]:
        if allocate is None:
            raise RuntimeError("PYNQ allocate() is unavailable.")
        first = allocate(shape=SHAPE, dtype=DTYPE)
        second = allocate(shape=SHAPE, dtype=DTYPE)
        _validate_buffer(first, "first")
        _validate_buffer(second, "second")
        return first, second

    def _write_address(self, low_offset: int, high_offset: int, value: int) -> None:
        self.ip.write(low_offset, value & 0xFFFFFFFF)
        self.ip.write(high_offset, (value >> 32) & 0xFFFFFFFF)

    def program_buffers(self, source: Any, destination: Any) -> None:
        _validate_buffer(source, "source")
        _validate_buffer(destination, "destination")
        self._write_address(PHI_IN_LOW, PHI_IN_HIGH, _buffer_address(source))
        self._write_address(PHI_OUT_LOW, PHI_OUT_HIGH, _buffer_address(destination))

    def run_segment(
        self,
        source: Any,
        destination: Any,
        *,
        timeout_s: float | None = None,
    ) -> KernelTiming:
        """Run one 120-update segment.

        The caller owns cache coherency. Address writes are excluded from the
        returned kernel time; AP_START through AP_DONE is included.
        """

        timeout = self.timeout_s if timeout_s is None else float(timeout_s)
        if timeout <= 0.0:
            raise ValueError("timeout_s must be positive.")

        self.program_buffers(source, destination)
        ctrl_before = int(self.ip.read(AP_CTRL))
        start_ns = perf_counter_ns()
        deadline_ns = start_ns + int(timeout * 1.0e9)
        self.ip.write(AP_CTRL, AP_START)

        ctrl_after = 0
        while True:
            ctrl_after = int(self.ip.read(AP_CTRL))
            now_ns = perf_counter_ns()
            if ctrl_after & AP_DONE:
                return KernelTiming(
                    seconds=(now_ns - start_ns) * 1.0e-9,
                    ctrl_before=ctrl_before,
                    ctrl_after=ctrl_after,
                )
            if now_ns >= deadline_ns:
                raise AcceleratorTimeout(
                    "BPM2D segment exceeded "
                    f"{timeout:.3f} s; AP_CTRL=0x{ctrl_after:08x}, "
                    f"source=0x{_buffer_address(source):016x}, "
                    f"destination=0x{_buffer_address(destination):016x}."
                )


def free_buffer(buffer: Any) -> None:
    method = getattr(buffer, "freebuffer", None)
    if method is not None:
        method()
