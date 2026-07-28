# BPM2D KV260 Kerr Fast SI: PYNQ Package

This directory is the deployable PYNQ package for the independent
`bpm2d_kv260_kerr_fast_si` overlay. It uses the physically consistent linear
absorption coefficient `alpha = 300 m^-1`, equivalent to `0.3 mm^-1`.

The accelerator performs:

```text
ADI-X -> two-photon absorption -> Kerr -> linear absorption
      -> ADI-Y -> two-photon absorption -> Kerr -> linear absorption
```

One invocation advances 120 steps of `1 um`. A complete PSF uses three
invocations and applies deterministic phase masks on the PS after updates 120,
240, and 360. The masks are not implemented in the PL.

## Contents

- `bpm2d_kv260_kerr_fast_si.bit`, `.hwh`, and `.xclbin`: matching overlay files
- `bpm2d_driver.py`: direct AXI4-Lite driver with 64-bit addresses and timeout
- `benchmark_bpm2d_kerr_fast_si.py`: official headless validation/benchmark
- `bpm2d_kv260_kerr_fast_si.ipynb`: interactive inspection and visualization
- `data`: native `64x64` input, masks, six CPU references, and metadata
- `results`: generated CSV, JSON, intermediate fields, and final fields
- `SHA256SUMS.txt`: integrity manifest for the deployable package
- `BENCHMARK_RESULTS.md`: verified HLS, Vivado, and physical-board result summary

The board's XRT 2.13 `xclbinutil` executable is not functional on the current
image. The matching `.xclbin` is therefore generated off-board from the HWH
memory topology and supplied as a sidecar. PYNQ loads it directly, avoiding any
system-package changes on the KV260. Its reproducible source is in
`xclbin_source`.

## Board Execution

The intended board path is:

```text
/home/ubuntu/jupyter_notebooks/bpm2d_kv260_kerr_fast_si
```

Run a short smoke test first:

```bash
cd /home/ubuntu/jupyter_notebooks/bpm2d_kv260_kerr_fast_si
python3 benchmark_bpm2d_kerr_fast_si.py --warmups 1 --repetitions 3
```

Run the official benchmark outside Jupyter:

```bash
cd /home/ubuntu/jupyter_notebooks/bpm2d_kv260_kerr_fast_si
python3 benchmark_bpm2d_kerr_fast_si.py --warmups 5 --repetitions 100
```

Overlay programming time is recorded separately and excluded from the official
per-PSF timing. The benchmark records every repetition and reports mean,
sample standard deviation, median, minimum, percentiles 5/95, and an
approximate 95% confidence interval.

The driver explicitly sets `fclk0` to `125 MHz` and verifies the effective
clock before any kernel launch. This is required because the PS clock can
retain the value used by a previously loaded overlay even when a new bitstream
is programmed.

The current board image exposes no temperature channel through Linux thermal,
hwmon, IIO, or the available XRT reports. The environment JSON records this as
`temperature_monitoring.available = false` and lists the checked sources;
temperature is not inferred from the Vivado power estimate.

## Timing Boundaries

The generated CSV reports:

- input copy and initial flush
- AP_START-to-AP_DONE time for each 120-step kernel call
- each output invalidation
- each in-place PS mask
- each inter-segment mask flush
- sum of the three kernel calls
- aggregate synchronization and PS times
- complete per-PSF time

Address programming is excluded from `kernel_*_s` but included in
`end_to_end_s`.

## Validation

Before timing, the script compares hardware fields before and after each mask
at 120, 240, and 360 updates. Every state must:

- contain no `NaN` or infinity
- satisfy relative L2 error `<= 1e-3`
- satisfy peak relative error `<= 1e-2`

Absolute RMS and maximum absolute error are also stored. All measured final
fields must have an identical SHA-256 value. A failed validation or a
two-second segment timeout aborts the official benchmark.

The two PYNQ buffers are `complex64[64,64]`, C-order, and run ping-pong as
`A -> B`, `B -> A`, and `A -> B`. The driver explicitly writes both halves of
the 64-bit physical addresses:

| Offset | Register |
| --- | --- |
| `0x00` | `AP_CTRL` |
| `0x10/0x14` | `phi_in`, low/high |
| `0x1C/0x20` | `phi_out`, low/high |

The retained official run is
`results/official_125mhz_20260724T2317Z`. It contains all 100 repetitions,
the six hardware validation fields, the 100 final fields, environment
metadata, and a separate SHA-256 manifest.
