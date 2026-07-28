from __future__ import annotations

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

import bpm2d_driver as driver


class FakeFlags:
    c_contiguous = True


class FakeBuffer:
    def __init__(self, address: int) -> None:
        self.shape = driver.SHAPE
        self.dtype = driver.DTYPE
        self.flags = FakeFlags()
        self.physical_address = address


class FakeIP:
    def __init__(self, reads: list[int] | None = None) -> None:
        self.writes: list[tuple[int, int]] = []
        self.reads = list(reads or [driver.AP_IDLE])

    def write(self, offset: int, value: int) -> None:
        self.writes.append((offset, value))

    def read(self, offset: int) -> int:
        self.assert_ctrl_offset(offset)
        return self.reads.pop(0) if len(self.reads) > 1 else self.reads[0]

    @staticmethod
    def assert_ctrl_offset(offset: int) -> None:
        if offset != driver.AP_CTRL:
            raise AssertionError(f"Unexpected read offset 0x{offset:x}")


class DriverTests(unittest.TestCase):
    def test_discover_accelerator_by_unique_vlnv(self) -> None:
        accelerator = object()
        overlay = type(
            "Overlay",
            (),
            {
                "ip_dict": {
                    "a": {"type": driver.IP_VLNV},
                    "other": {"type": "vendor:library:other:1.0"},
                },
                "a": accelerator,
            },
        )()
        name, instance = driver.discover_accelerator(overlay)
        self.assertEqual(name, "a")
        self.assertIs(instance, accelerator)

    def test_program_buffers_writes_both_address_halves(self) -> None:
        overlay = object.__new__(driver.BPM2DOverlay)
        overlay.ip = FakeIP()
        source = FakeBuffer(0x123456789ABCDEF0)
        destination = FakeBuffer(0xFEDCBA9876543210)
        overlay.program_buffers(source, destination)
        self.assertEqual(
            overlay.ip.writes,
            [
                (driver.PHI_IN_LOW, 0x9ABCDEF0),
                (driver.PHI_IN_HIGH, 0x12345678),
                (driver.PHI_OUT_LOW, 0x76543210),
                (driver.PHI_OUT_HIGH, 0xFEDCBA98),
            ],
        )

    def test_rejects_wrong_buffer_dtype(self) -> None:
        buffer = FakeBuffer(0x1000)
        buffer.dtype = np.dtype(np.complex128)
        with self.assertRaisesRegex(ValueError, "complex64"):
            driver._validate_buffer(buffer, "buffer")

    def test_segment_timeout_reports_control_and_addresses(self) -> None:
        overlay = object.__new__(driver.BPM2DOverlay)
        overlay.ip = FakeIP()
        overlay.timeout_s = 1.0e-6
        source = FakeBuffer(0x1000)
        destination = FakeBuffer(0x2000)
        with self.assertRaisesRegex(driver.AcceleratorTimeout, "AP_CTRL"):
            overlay.run_segment(source, destination)

    def test_hwh_contract(self) -> None:
        hwh = PACKAGE_ROOT / f"{driver.OVERLAY_BASENAME}.hwh"
        root = ET.parse(hwh).getroot()
        module = root.find(".//MODULE[@INSTANCE='a']")
        self.assertIsNotNone(module)
        assert module is not None
        self.assertEqual(module.attrib["VLNV"], driver.IP_VLNV)

        registers = {
            register.attrib["NAME"]: int(
                register.find("./PROPERTY[@NAME='ADDRESS_OFFSET']").attrib["VALUE"]
            )
            for register in module.findall(".//REGISTER")
            if register.find("./PROPERTY[@NAME='ADDRESS_OFFSET']") is not None
        }
        self.assertEqual(registers["phi_in_1"], driver.PHI_IN_LOW)
        self.assertEqual(registers["phi_in_2"], driver.PHI_IN_HIGH)
        self.assertEqual(registers["phi_out_1"], driver.PHI_OUT_LOW)
        self.assertEqual(registers["phi_out_2"], driver.PHI_OUT_HIGH)

        base = module.find("./PARAMETERS/PARAMETER[@NAME='C_S_AXI_CONTROL_BASEADDR']")
        self.assertIsNotNone(base)
        assert base is not None
        self.assertEqual(base.attrib["VALUE"], "0x80000000")


if __name__ == "__main__":
    unittest.main()
