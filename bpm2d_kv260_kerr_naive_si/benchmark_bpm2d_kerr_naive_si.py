#!/usr/bin/env python3
"""Headless validation and timing benchmark for the naive KV260 overlay."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import socket
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, stdev
from time import perf_counter_ns
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np

from bpm2d_driver import (
    BPM2DOverlay,
    DTYPE,
    OVERLAY_BASENAME,
    SHAPE,
    TARGET_PL_CLOCK_MHZ,
    free_buffer,
    sync_from_device,
    sync_to_device,
)


RELATIVE_L2_LIMIT = 1.0e-3
PEAK_RELATIVE_LIMIT = 1.0e-2
SEGMENTS = (120, 240, 360)


def elapsed_s(start_ns: int) -> float:
    return (perf_counter_ns() - start_ns) * 1.0e-9


def timed_call(function: Any, *args: Any, **kwargs: Any) -> float:
    start_ns = perf_counter_ns()
    function(*args, **kwargs)
    return elapsed_s(start_ns)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def array_sha256(array: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(array)
    return hashlib.sha256(contiguous.view(np.uint8)).hexdigest()


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return None


def thermal_snapshot() -> Dict[str, float]:
    result: Dict[str, float] = {}
    thermal_root = Path("/sys/class/thermal")
    for zone in sorted(thermal_root.glob("thermal_zone*")):
        raw = read_text(zone / "temp")
        if raw is None:
            continue
        try:
            value = float(raw)
        except ValueError:
            continue
        if abs(value) > 1000.0:
            value /= 1000.0
        label = read_text(zone / "type") or zone.name
        result[f"{zone.name}:{label}"] = value
    return result


def cpu_governors() -> Dict[str, str]:
    governors: Dict[str, str] = {}
    for path in sorted(
        Path("/sys/devices/system/cpu").glob("cpu[0-9]*/cpufreq/scaling_governor")
    ):
        value = read_text(path)
        if value is not None:
            governors[path.parts[-3]] = value
    return governors


def cpu_frequencies_khz() -> Dict[str, Dict[str, int]]:
    frequencies: Dict[str, Dict[str, int]] = {}
    cpu_root = Path("/sys/devices/system/cpu")
    for cpu in sorted(cpu_root.glob("cpu[0-9]*")):
        cpufreq = cpu / "cpufreq"
        values: Dict[str, int] = {}
        for name in (
            "scaling_cur_freq",
            "scaling_min_freq",
            "scaling_max_freq",
            "scaling_setspeed",
        ):
            raw = read_text(cpufreq / name)
            if raw is None:
                continue
            try:
                values[name] = int(raw)
            except ValueError:
                continue
        if values:
            frequencies[cpu.name] = values
    return frequencies


def memory_snapshot_kb() -> Dict[str, int]:
    result: Dict[str, int] = {}
    wanted = {
        "MemTotal",
        "MemAvailable",
        "MemFree",
        "CmaTotal",
        "CmaFree",
        "SwapTotal",
        "SwapFree",
    }
    raw = read_text(Path("/proc/meminfo"))
    if raw is None:
        return result
    for line in raw.splitlines():
        key, separator, value = line.partition(":")
        if not separator or key not in wanted:
            continue
        token = value.strip().split()[0]
        try:
            result[key] = int(token)
        except ValueError:
            continue
    return result


def fpga_manager_state() -> str | None:
    return read_text(Path("/sys/class/fpga_manager/fpga0/state"))


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def clock_snapshot() -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    try:
        from pynq import Clocks

        for name in ("fclk0_mhz", "fclk1_mhz", "fclk2_mhz", "fclk3_mhz"):
            try:
                result[name] = float(getattr(Clocks, name))
            except (AttributeError, RuntimeError, TypeError, ValueError):
                pass
    except ImportError:
        pass
    return result


def collect_environment(root: Path, driver: BPM2DOverlay) -> Dict[str, Any]:
    uname = platform.uname()
    initial_temperatures = thermal_snapshot()
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "platform": {
            "system": uname.system,
            "node": uname.node,
            "release": uname.release,
            "version": uname.version,
            "machine": uname.machine,
            "processor": uname.processor,
        },
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pynq": package_version("pynq"),
        "overlay_load_s": driver.overlay_load_s,
        "ip_name": driver.ip_name,
        "ip_vlnv": driver.overlay.ip_dict[driver.ip_name].get("type"),
        "target_pl_clock_mhz": TARGET_PL_CLOCK_MHZ,
        "effective_pl_clock_mhz": driver.pl_clock_mhz,
        "pl_clocks_mhz": clock_snapshot(),
        "cpu_governors": cpu_governors(),
        "cpu_frequencies_khz": cpu_frequencies_khz(),
        "memory_kb_initial": memory_snapshot_kb(),
        "fpga_manager_state_initial": fpga_manager_state(),
        "load_average_initial": list(os.getloadavg()),
        "temperatures_c_initial": initial_temperatures,
        "temperature_monitoring": {
            "available": bool(initial_temperatures),
            "sources_checked": [
                "/sys/class/thermal/thermal_zone*/temp",
                "/sys/class/hwmon/hwmon*/temp*_input",
                "/sys/bus/iio/devices/*/*temp*",
                "xbutil examine reports",
            ],
        },
        "artifacts_sha256": {
            driver.bitfile.name: sha256_file(driver.bitfile),
            driver.hwhfile.name: sha256_file(driver.hwhfile),
            driver.xclbinfile.name: sha256_file(driver.xclbinfile),
        },
        "reference_metadata": json.loads(
            (root / "data" / "reference_meta.json").read_text(encoding="utf-8")
        ),
    }


def load_inputs(root: Path) -> Tuple[np.ndarray, List[np.ndarray]]:
    input_field = np.load(root / "data" / "phi_in_64.npy")
    masks = [
        np.load(root / "data" / f"phase_factor_{index}.npy")
        for index in range(1, 4)
    ]

    arrays = [input_field, *masks]
    for index, array in enumerate(arrays):
        if array.shape != SHAPE or array.dtype != DTYPE or not array.flags.c_contiguous:
            raise ValueError(
                f"Input array {index} must be C-order complex64{SHAPE}; "
                f"got shape={array.shape}, dtype={array.dtype}, "
                f"C-order={array.flags.c_contiguous}."
            )
        if not np.all(np.isfinite(array.real)) or not np.all(np.isfinite(array.imag)):
            raise ValueError(f"Input array {index} contains NaN or infinity.")
    return input_field, masks


def execute_psf(
    driver: BPM2DOverlay,
    first: Any,
    second: Any,
    input_field: np.ndarray,
    masks: Sequence[np.ndarray],
    *,
    capture_stages: bool = False,
) -> Tuple[Dict[str, float], Any, Dict[str, np.ndarray]]:
    row: Dict[str, float] = {}
    stages: Dict[str, np.ndarray] = {}
    end_to_end_start = perf_counter_ns()

    row["input_copy_s"] = timed_call(np.copyto, first, input_field)
    row["input_flush_s"] = timed_call(sync_to_device, first)

    source, destination = first, second
    for index, (update, mask) in enumerate(zip(SEGMENTS, masks), start=1):
        timing = driver.run_segment(source, destination)
        row[f"kernel_{index}_s"] = timing.seconds
        row[f"invalidate_{index}_s"] = timed_call(sync_from_device, destination)

        if capture_stages:
            stages[f"{update}_pre_mask"] = np.array(destination, copy=True)

        row[f"mask_{index}_s"] = timed_call(
            np.multiply, destination, mask, out=destination
        )

        if capture_stages:
            stages[f"{update}_post_mask"] = np.array(destination, copy=True)

        if index < len(SEGMENTS):
            row[f"mask_flush_{index}_s"] = timed_call(
                sync_to_device, destination
            )
        else:
            row[f"mask_flush_{index}_s"] = 0.0

        source, destination = destination, source

    row["end_to_end_s"] = elapsed_s(end_to_end_start)
    row["kernel_total_s"] = sum(row[f"kernel_{index}_s"] for index in range(1, 4))
    row["invalidate_total_s"] = sum(
        row[f"invalidate_{index}_s"] for index in range(1, 4)
    )
    row["flush_total_s"] = row["input_flush_s"] + sum(
        row[f"mask_flush_{index}_s"] for index in range(1, 4)
    )
    row["sync_total_s"] = row["invalidate_total_s"] + row["flush_total_s"]
    row["mask_total_s"] = sum(row[f"mask_{index}_s"] for index in range(1, 4))
    row["ps_measured_total_s"] = (
        row["input_copy_s"] + row["sync_total_s"] + row["mask_total_s"]
    )
    row["unattributed_overhead_s"] = max(
        0.0,
        row["end_to_end_s"]
        - row["kernel_total_s"]
        - row["ps_measured_total_s"],
    )
    return row, source, stages


def complex_error_metrics(
    actual: np.ndarray,
    reference: np.ndarray,
) -> Dict[str, Any]:
    actual128 = np.asarray(actual, dtype=np.complex128)
    reference128 = np.asarray(reference, dtype=np.complex128)
    difference = actual128 - reference128
    absolute_error = np.abs(difference)
    reference_magnitude = np.abs(reference128)

    finite = bool(
        np.all(np.isfinite(actual128.real)) and np.all(np.isfinite(actual128.imag))
    )
    rms_absolute = float(np.sqrt(np.mean(absolute_error * absolute_error)))
    l2_denominator = float(np.linalg.norm(reference128.ravel()))
    peak_denominator = float(np.max(reference_magnitude))
    relative_l2 = (
        float(np.linalg.norm(difference.ravel()) / l2_denominator)
        if l2_denominator > 0.0
        else math.inf
    )
    max_absolute = float(np.max(absolute_error))
    peak_relative = (
        max_absolute / peak_denominator if peak_denominator > 0.0 else math.inf
    )
    passed = (
        finite
        and relative_l2 <= RELATIVE_L2_LIMIT
        and peak_relative <= PEAK_RELATIVE_LIMIT
    )
    return {
        "finite": finite,
        "rms_absolute": rms_absolute,
        "relative_l2": relative_l2,
        "max_absolute": max_absolute,
        "peak_reference_magnitude": peak_denominator,
        "peak_relative_error": peak_relative,
        "limits": {
            "relative_l2": RELATIVE_L2_LIMIT,
            "peak_relative_error": PEAK_RELATIVE_LIMIT,
        },
        "passed": passed,
    }


def validate_stages(
    root: Path,
    stages: Dict[str, np.ndarray],
    output_dir: Path,
) -> Dict[str, Any]:
    report: Dict[str, Any] = {"stages": {}}
    for update in SEGMENTS:
        for position in ("pre_mask", "post_mask"):
            name = f"{update}_{position}"
            reference = np.load(root / "data" / f"ref_64_{name}.npy")
            report["stages"][name] = complex_error_metrics(stages[name], reference)
            np.save(output_dir / f"hardware_{name}.npy", stages[name])
    report["passed"] = all(
        metrics["passed"] for metrics in report["stages"].values()
    )
    return report


def percentile(values: np.ndarray, quantile: float) -> float:
    return float(np.percentile(values, quantile))


def summarize_values(values: Iterable[float]) -> Dict[str, float]:
    samples = [float(value) for value in values]
    sample_mean = mean(samples)
    sample_std = stdev(samples) if len(samples) > 1 else 0.0
    half_width = 1.96 * sample_std / math.sqrt(len(samples))
    return {
        "count": float(len(samples)),
        "mean": sample_mean,
        "std": sample_std,
        "median": median(samples),
        "min": min(samples),
        "p05": percentile(np.asarray(samples), 5.0),
        "p95": percentile(np.asarray(samples), 95.0),
        "ci95_half_width": half_width,
        "ci95_low": sample_mean - half_width,
        "ci95_high": sample_mean + half_width,
    }


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("No benchmark rows were produced.")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_result_manifest(root: Path) -> None:
    manifest = root / "RESULTS_SHA256SUMS.txt"
    lines = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path == manifest:
            continue
        lines.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def create_output_dir(root: Path, requested: Path | None) -> Path:
    if requested is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        result = root / "results" / f"run_{stamp}"
    else:
        result = requested.expanduser().resolve()
    result.mkdir(parents=True, exist_ok=False)
    return result


def run_benchmark(
    root: Path | str | None = None,
    *,
    warmups: int = 5,
    repetitions: int = 100,
    timeout_s: float = 2.0,
    output_dir: Path | str | None = None,
) -> Dict[str, Any]:
    if warmups < 0 or repetitions <= 0:
        raise ValueError("warmups must be nonnegative and repetitions positive.")

    package_root = (
        Path(root).expanduser().resolve()
        if root is not None
        else Path(__file__).resolve().parent
    )
    requested_output = (
        Path(output_dir) if output_dir is not None else None
    )
    result_dir = create_output_dir(package_root, requested_output)
    bitfile = package_root / f"{OVERLAY_BASENAME}.bit"

    driver = BPM2DOverlay(bitfile, timeout_s=timeout_s)
    environment = collect_environment(package_root, driver)
    write_json(result_dir / "environment.json", environment)

    input_field, masks = load_inputs(package_root)
    first = second = None
    rows: List[Dict[str, Any]] = []
    final_fields: List[np.ndarray] = []

    try:
        first, second = driver.allocate_buffers()

        _, _, validation_stages = execute_psf(
            driver,
            first,
            second,
            input_field,
            masks,
            capture_stages=True,
        )
        validation = validate_stages(package_root, validation_stages, result_dir)
        write_json(result_dir / "validation.json", validation)
        if not validation["passed"]:
            raise RuntimeError(
                f"Hardware validation failed; see {result_dir / 'validation.json'}."
            )

        for _ in range(warmups):
            execute_psf(driver, first, second, input_field, masks)

        for repetition in range(repetitions):
            timing_row, final_buffer, _ = execute_psf(
                driver, first, second, input_field, masks
            )
            final_field = np.array(final_buffer, copy=True)
            if not np.all(np.isfinite(final_field.real)) or not np.all(
                np.isfinite(final_field.imag)
            ):
                raise RuntimeError(
                    f"Measured repetition {repetition} contains NaN or infinity."
                )
            timing_row = {
                "repetition": repetition,
                **timing_row,
                "final_sha256": array_sha256(final_field),
            }
            rows.append(timing_row)
            final_fields.append(final_field)

        hashes = sorted({str(row["final_sha256"]) for row in rows})
        deterministic = len(hashes) == 1
        measured_fields = np.stack(final_fields, axis=0)
        np.save(result_dir / "measured_final_fields.npy", measured_fields)
        np.save(result_dir / "final_output.npy", measured_fields[-1])
        write_csv(result_dir / "repetitions.csv", rows)

        timing_names = [
            name
            for name in rows[0]
            if name != "repetition" and name != "final_sha256"
        ]
        statistics = {
            name: summarize_values(float(row[name]) for row in rows)
            for name in timing_names
        }
        end_to_end_mean = statistics["end_to_end_s"]["mean"]
        summary = {
            "warmups": warmups,
            "repetitions": repetitions,
            "timeout_s": timeout_s,
            "overlay_load_s": driver.overlay_load_s,
            "deterministic": deterministic,
            "final_sha256_values": hashes,
            "throughput_psf_per_s": 1.0 / end_to_end_mean,
            "timings_s": statistics,
            "validation_passed": validation["passed"],
            "result_directory": str(result_dir),
        }
        write_json(result_dir / "summary.json", summary)
        if not deterministic:
            raise RuntimeError(
                f"Measured outputs were not deterministic; see {result_dir}."
            )

        environment["load_average_final"] = list(os.getloadavg())
        environment["cpu_frequencies_khz_final"] = cpu_frequencies_khz()
        environment["memory_kb_final"] = memory_snapshot_kb()
        environment["fpga_manager_state_final"] = fpga_manager_state()
        final_temperatures = thermal_snapshot()
        environment["temperatures_c_final"] = final_temperatures
        environment["temperature_monitoring"]["available"] = bool(
            environment["temperatures_c_initial"] or final_temperatures
        )
        write_json(result_dir / "environment.json", environment)
        write_result_manifest(result_dir)
        return summary
    finally:
        if first is not None:
            free_buffer(first)
        if second is not None:
            free_buffer(second)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warmups", type=int, default=5)
    parser.add_argument("--repetitions", type=int, default=100)
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional new result directory; defaults to results/run_<UTC>.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_benchmark(
        warmups=args.warmups,
        repetitions=args.repetitions,
        timeout_s=args.timeout,
        output_dir=args.output_dir,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
