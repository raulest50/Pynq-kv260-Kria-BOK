#!/usr/bin/env python3
"""Session metadata, manifests, and A-B-A comparison for the KV260 benchmark."""

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
INTERLEAVED_HLS_THREE_CALL_S = 0.086821848
BASELINE_DRIFT_LIMIT = 0.01


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
        before = metric_values(roots["psf073_before"], metric)
        candidate = metric_values(roots["interleaved"], metric)
        after = metric_values(roots["psf073_after"], metric)
        before_stats = summarize(before)
        candidate_stats = summarize(candidate)
        after_stats = summarize(after)
        pooled_baseline = summarize([*before, *after])
        drift = relative_drift(before_stats["mean"], after_stats["mean"])
        timing[metric] = {
            "psf073_before": before_stats,
            "interleaved": candidate_stats,
            "psf073_after": after_stats,
            "psf073_pooled": pooled_baseline,
            "baseline_drift_fraction": drift,
            "baseline_drift_percent": drift * 100.0,
            "speedup_vs_pooled_psf073": (
                pooled_baseline["mean"] / candidate_stats["mean"]
            ),
        }

    candidate_kernel = timing["kernel_total_s"]["interleaved"]["mean"]
    candidate_end = timing["end_to_end_s"]["interleaved"]["mean"]
    before_end = timing["end_to_end_s"]["psf073_before"]["mean"]
    after_end = timing["end_to_end_s"]["psf073_after"]["mean"]
    drift_ok = all(
        timing[name]["baseline_drift_fraction"] < BASELINE_DRIFT_LIMIT
        for name in timing
    )
    validations_ok = all(report.get("passed", False) for report in validations.values())
    deterministic = all(
        bool(summary.get("deterministic", False)) for summary in summaries.values()
    )
    faster_than_both = candidate_end < before_end and candidate_end < after_end

    result = {
        "session_root": str(session_root.resolve()),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "timing_s": timing,
        "interleaved_hls_three_call_estimate_s": INTERLEAVED_HLS_THREE_CALL_S,
        "interleaved_kernel_mean_s": candidate_kernel,
        "interleaved_kernel_vs_hls_ratio": (
            candidate_kernel / INTERLEAVED_HLS_THREE_CALL_S
        ),
        "historical_psf073_end_to_end_s": HISTORICAL_PSF073_END_TO_END_S,
        "interleaved_speedup_vs_historical_psf073": (
            HISTORICAL_PSF073_END_TO_END_S / candidate_end
        ),
        "acceptance": {
            "baseline_drift_below_1_percent": drift_ok,
            "all_validations_passed": validations_ok,
            "all_runs_deterministic": deterministic,
            "interleaved_faster_than_both_psf073_controls": faster_than_both,
            "passed": drift_ok and validations_ok and deterministic and faster_than_both,
        },
    }
    write_json(session_root / "aba_comparison.json", result)
    write_comparison_markdown(session_root / "ABA_COMPARISON.md", result)
    return result


def write_comparison_markdown(path: Path, result: Dict[str, Any]) -> None:
    kernel = result["timing_s"]["kernel_total_s"]
    end = result["timing_s"]["end_to_end_s"]
    acceptance = result["acceptance"]
    lines = [
        "# KV260 A-B-A Physical Benchmark",
        "",
        "| Run | Kernel mean (s) | End-to-end mean (s) |",
        "| --- | ---: | ---: |",
        (
            f"| psf073 before | {kernel['psf073_before']['mean']:.9f} | "
            f"{end['psf073_before']['mean']:.9f} |"
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
            "- Interleaved speedup versus pooled psf073: "
            f"{end['speedup_vs_pooled_psf073']:.6f}x end-to-end and "
            f"{kernel['speedup_vs_pooled_psf073']:.6f}x for the three PL calls."
        ),
        (
            "- Interleaved physical/HLS three-call ratio: "
            f"{result['interleaved_kernel_vs_hls_ratio']:.6f}."
        ),
        (
            "- Speedup versus historical psf073 result: "
            f"{result['interleaved_speedup_vs_historical_psf073']:.6f}x."
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
