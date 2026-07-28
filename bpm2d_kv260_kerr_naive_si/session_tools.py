#!/usr/bin/env python3
"""Session metadata, manifests, and A-B-C-A comparison for the KV260 benchmark."""

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
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any, Dict, Iterable, List


HISTORICAL_PSF073_END_TO_END_S = 0.73565527665
NAIVE_HLS_MIN_CYCLES_PER_CALL = 59160777
NAIVE_HLS_MAX_CYCLES_PER_CALL = 59529417
INTERLEAVED_HLS_THREE_CALL_S = 0.086821848
BASELINE_DRIFT_LIMIT = 0.01
HLS_RATIO_TOLERANCE = 0.05
EXPECTED_FINAL_SHA256 = (
    "68d3e368b5cb2cb8599176c38669ec719cb491f73646782c1687be7bb0978442"
)


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def cpu_state() -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for cpu in sorted(Path("/sys/devices/system/cpu").glob("cpu[0-9]*")):
        cpufreq = cpu / "cpufreq"
        values: Dict[str, Any] = {}
        governor = read_text(cpufreq / "scaling_governor")
        if governor is not None:
            values["governor"] = governor
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
                values[name] = raw
        if values:
            result[cpu.name] = values
    return result


def memory_state_kb() -> Dict[str, int]:
    wanted = {
        "MemTotal",
        "MemAvailable",
        "MemFree",
        "CmaTotal",
        "CmaFree",
        "SwapTotal",
        "SwapFree",
    }
    result: Dict[str, int] = {}
    raw = read_text(Path("/proc/meminfo"))
    if raw is None:
        return result
    for line in raw.splitlines():
        key, separator, value = line.partition(":")
        if not separator or key not in wanted:
            continue
        try:
            result[key] = int(value.strip().split()[0])
        except (IndexError, ValueError):
            continue
    return result


def clock_state() -> Dict[str, float]:
    result: Dict[str, float] = {}
    try:
        from pynq import Clocks

        for name in ("fclk0_mhz", "fclk1_mhz", "fclk2_mhz", "fclk3_mhz"):
            try:
                result[name] = float(getattr(Clocks, name))
            except (AttributeError, RuntimeError, TypeError, ValueError):
                continue
    except ImportError:
        pass
    return result


def service_state(name: str) -> str:
    completed = subprocess.run(
        ["systemctl", "is-active", name],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() or completed.stderr.strip()


def package_hashes(root: Path) -> Dict[str, str]:
    hashes: Dict[str, str] = {}
    for suffix in (".bit", ".hwh", ".xclbin"):
        for path in sorted(root.glob(f"*{suffix}")):
            hashes[path.name] = sha256_file(path)
    manifest = root / "SHA256SUMS.txt"
    if manifest.is_file():
        hashes[manifest.name] = sha256_file(manifest)
    return hashes


def snapshot(output: Path, packages: Iterable[str]) -> None:
    package_data: Dict[str, Any] = {}
    for specification in packages:
        name, separator, raw_path = specification.partition("=")
        if not separator:
            raise ValueError(f"Package must use NAME=PATH syntax: {specification}")
        root = Path(raw_path).expanduser().resolve()
        package_data[name] = {
            "path": str(root),
            "artifacts_sha256": package_hashes(root),
        }

    uname = platform.uname()
    data = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "platform": {
            "system": uname.system,
            "node": uname.node,
            "release": uname.release,
            "version": uname.version,
            "machine": uname.machine,
        },
        "python": platform.python_version(),
        "numpy": package_version("numpy"),
        "pynq": package_version("pynq"),
        "cpu": cpu_state(),
        "memory_kb": memory_state_kb(),
        "load_average": list(os.getloadavg()),
        "pl_clocks_mhz": clock_state(),
        "fpga_manager_state": read_text(
            Path("/sys/class/fpga_manager/fpga0/state")
        ),
        "jupyter_service": service_state("jupyter.service"),
        "packages": package_data,
    }
    write_json(output, data)


def write_manifest(root: Path, name: str) -> None:
    root = root.resolve()
    manifest = root / name
    lines = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if path == manifest:
            continue
        lines.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    manifest.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))


def load_rows(root: Path) -> List[Dict[str, str]]:
    with (root / "repetitions.csv").open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def percentile(values: List[float], quantile: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * quantile / 100.0
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def summarize(values: Iterable[float]) -> Dict[str, float]:
    samples = [float(value) for value in values]
    average = mean(samples)
    deviation = stdev(samples) if len(samples) > 1 else 0.0
    half_width = 1.96 * deviation / math.sqrt(len(samples))
    return {
        "count": float(len(samples)),
        "mean": average,
        "std": deviation,
        "median": median(samples),
        "min": min(samples),
        "p05": percentile(samples, 5.0),
        "p95": percentile(samples, 95.0),
        "ci95_half_width": half_width,
        "ci95_low": average - half_width,
        "ci95_high": average + half_width,
    }


def metric_values(root: Path, name: str) -> List[float]:
    return [float(row[name]) for row in load_rows(root)]


def relative_drift(first: float, second: float) -> float:
    midpoint = (abs(first) + abs(second)) / 2.0
    return abs(second - first) / midpoint if midpoint > 0.0 else math.inf


def compare(session_root: Path) -> Dict[str, Any]:
    roots = {
        "psf073_before": session_root / "psf073_before",
        "naive": session_root / "naive",
        "interleaved": session_root / "interleaved",
        "psf073_after": session_root / "psf073_after",
    }
    summaries = {
        name: load_json(root / "summary.json") for name, root in roots.items()
    }
    validations = {
        name: load_json(root / "validation.json") for name, root in roots.items()
    }

    timing: Dict[str, Any] = {}
    for metric in ("kernel_total_s", "end_to_end_s"):
        samples = {
            name: metric_values(root, metric) for name, root in roots.items()
        }
        stats = {name: summarize(values) for name, values in samples.items()}
        pooled_baseline = summarize(
            [*samples["psf073_before"], *samples["psf073_after"]]
        )
        drift = relative_drift(
            stats["psf073_before"]["mean"],
            stats["psf073_after"]["mean"],
        )
        timing[metric] = {
            **stats,
            "psf073_pooled": pooled_baseline,
            "baseline_drift_fraction": drift,
            "baseline_drift_percent": drift * 100.0,
            "naive_slowdown_vs_pooled_psf073": (
                stats["naive"]["mean"] / pooled_baseline["mean"]
            ),
            "interleaved_speedup_vs_pooled_psf073": (
                pooled_baseline["mean"] / stats["interleaved"]["mean"]
            ),
            "naive_slowdown_vs_interleaved": (
                stats["naive"]["mean"] / stats["interleaved"]["mean"]
            ),
        }

    naive_kernel = timing["kernel_total_s"]["naive"]["mean"]
    naive_end = timing["end_to_end_s"]["naive"]["mean"]
    interleaved_kernel = timing["kernel_total_s"]["interleaved"]["mean"]
    interleaved_end = timing["end_to_end_s"]["interleaved"]["mean"]
    before_end = timing["end_to_end_s"]["psf073_before"]["mean"]
    after_end = timing["end_to_end_s"]["psf073_after"]["mean"]
    naive_environment = load_json(roots["naive"] / "environment.json")
    effective_clock_mhz = float(naive_environment["effective_pl_clock_mhz"])
    naive_hls_min_s = (
        3.0 * NAIVE_HLS_MIN_CYCLES_PER_CALL / (effective_clock_mhz * 1.0e6)
    )
    naive_hls_max_s = (
        3.0 * NAIVE_HLS_MAX_CYCLES_PER_CALL / (effective_clock_mhz * 1.0e6)
    )
    naive_kernel_vs_hls_max = naive_kernel / naive_hls_max_s

    drift_ok = all(
        timing[name]["baseline_drift_fraction"] < BASELINE_DRIFT_LIMIT
        for name in timing
    )
    validations_ok = all(report.get("passed", False) for report in validations.values())
    deterministic = all(
        bool(summary.get("deterministic", False)) for summary in summaries.values()
    )
    final_hashes_match = all(
        summary.get("final_sha256_values") == [EXPECTED_FINAL_SHA256]
        for summary in summaries.values()
    )
    performance_order_ok = (
        interleaved_end < before_end
        and interleaved_end < after_end
        and before_end < naive_end
        and after_end < naive_end
    )
    hls_ratio_ok = abs(naive_kernel_vs_hls_max - 1.0) <= HLS_RATIO_TOLERANCE

    result = {
        "session_root": str(session_root.resolve()),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "timing_s": timing,
        "effective_pl_clock_mhz": effective_clock_mhz,
        "naive_hls_adjusted_range_s": {
            "min": naive_hls_min_s,
            "max": naive_hls_max_s,
        },
        "naive_kernel_mean_s": naive_kernel,
        "naive_kernel_vs_hls_max_ratio": naive_kernel_vs_hls_max,
        "interleaved_hls_three_call_estimate_s": INTERLEAVED_HLS_THREE_CALL_S,
        "interleaved_kernel_mean_s": interleaved_kernel,
        "interleaved_kernel_vs_hls_ratio": (
            interleaved_kernel / INTERLEAVED_HLS_THREE_CALL_S
        ),
        "historical_psf073_end_to_end_s": HISTORICAL_PSF073_END_TO_END_S,
        "naive_vs_historical_psf073_ratio": (
            naive_end / HISTORICAL_PSF073_END_TO_END_S
        ),
        "interleaved_speedup_vs_historical_psf073": (
            HISTORICAL_PSF073_END_TO_END_S / interleaved_end
        ),
        "acceptance": {
            "baseline_drift_below_1_percent": drift_ok,
            "all_validations_passed": validations_ok,
            "all_runs_deterministic": deterministic,
            "all_final_hashes_match_expected": final_hashes_match,
            "naive_kernel_within_5_percent_of_hls_max": hls_ratio_ok,
            "performance_order_interleaved_psf073_naive": performance_order_ok,
            "passed": (
                drift_ok
                and validations_ok
                and deterministic
                and final_hashes_match
                and hls_ratio_ok
                and performance_order_ok
            ),
        },
    }
    write_json(session_root / "abca_comparison.json", result)
    write_comparison_markdown(session_root / "ABCA_COMPARISON.md", result)
    return result


def write_comparison_markdown(path: Path, result: Dict[str, Any]) -> None:
    kernel = result["timing_s"]["kernel_total_s"]
    end = result["timing_s"]["end_to_end_s"]
    acceptance = result["acceptance"]
    lines = [
        "# KV260 A-B-C-A Physical Benchmark",
        "",
        "| Run | Kernel mean (s) | End-to-end mean (s) |",
        "| --- | ---: | ---: |",
        (
            f"| psf073 before | {kernel['psf073_before']['mean']:.9f} | "
            f"{end['psf073_before']['mean']:.9f} |"
        ),
        (
            f"| Naive | {kernel['naive']['mean']:.9f} | "
            f"{end['naive']['mean']:.9f} |"
        ),
        (
            f"| Interleaved | {kernel['interleaved']['mean']:.9f} | "
            f"{end['interleaved']['mean']:.9f} |"
        ),
        (
            f"| psf073 after | {kernel['psf073_after']['mean']:.9f} | "
            f"{end['psf073_after']['mean']:.9f} |"
        ),
        "",
        f"- psf073 end-to-end drift: {end['baseline_drift_percent']:.6f}%.",
        (
            "- Naive slowdown versus pooled psf073: "
            f"{end['naive_slowdown_vs_pooled_psf073']:.6f}x end-to-end and "
            f"{kernel['naive_slowdown_vs_pooled_psf073']:.6f}x for the PL calls."
        ),
        (
            "- Interleaved speedup versus pooled psf073: "
            f"{end['interleaved_speedup_vs_pooled_psf073']:.6f}x end-to-end "
            f"and {kernel['interleaved_speedup_vs_pooled_psf073']:.6f}x "
            "for the PL calls."
        ),
        (
            "- Naive slowdown versus interleaved: "
            f"{end['naive_slowdown_vs_interleaved']:.6f}x end-to-end."
        ),
        (
            "- Naive physical/HLS maximum estimate ratio: "
            f"{result['naive_kernel_vs_hls_max_ratio']:.6f}."
        ),
        (
            "- Interleaved physical/HLS three-call ratio: "
            f"{result['interleaved_kernel_vs_hls_ratio']:.6f}."
        ),
        (
            "- Naive/historical 1.567 s ratio: "
            f"{result['naive_vs_historical_psf073_ratio']:.6f}."
        ),
        f"- Acceptance passed: {str(acceptance['passed']).lower()}.",
        "",
        "The HLS value is a cycle-derived estimate. All other timing values in this",
        "file are physical KV260 measurements from the headless benchmark.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot_parser = subparsers.add_parser("snapshot")
    snapshot_parser.add_argument("--output", type=Path, required=True)
    snapshot_parser.add_argument("--package", action="append", default=[])

    manifest_parser = subparsers.add_parser("manifest")
    manifest_parser.add_argument("root", type=Path)
    manifest_parser.add_argument(
        "--name",
        default="RESULTS_SHA256SUMS.txt",
    )

    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("session_root", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "snapshot":
        snapshot(args.output, args.package)
    elif args.command == "manifest":
        write_manifest(args.root, args.name)
    elif args.command == "compare":
        print(json.dumps(compare(args.session_root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
