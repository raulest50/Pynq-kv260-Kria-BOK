# BPM2D KV260 Kerr Fast SI: Verified Results

## Configuration

- Board: Kria KV260, host `kria`
- Kernel: Linux `5.15.0-1051-xilinx-zynqmp`
- PYNQ: `3.0.1`
- Python: `3.10.12`
- NumPy: `1.26.4`
- Grid: `64x64`, row-major `complex64`
- Propagation: three calls of 120 updates, `dz = 1 um`
- Phase masks: PS after updates 120, 240, and 360
- Physical parameters: `alpha = 300 m^-1`, `beta = 1e-11 m/W`,
  `n2 = 3e-20 m^2/W`

The final field includes the third phase mask, applied after update 360.

## HLS And Vivado

Vitis HLS 2025.2 C simulation against the 120-step CPU reference passed:

- Relative L2 error: `8.42798e-06`
- Peak relative error: `1.00174e-05`
- Absolute RMS error: `0.0680827`
- Maximum absolute error: `0.357007`

HLS estimated `30283977` to `30660297` cycles per invocation. Estimated
resources were 92 BRAM18, 422 DSP, 49423 FF, 54792 LUT, and zero URAM.

Vivado 2025.2 completed bitstream generation at `124.998749 MHz`:

- Post-route WNS: `+0.682 ns`
- TNS: `0`
- Routing errors: `0`
- Methodology findings: `0`
- Post-route utilization: 43375 LUT, 46496 FF, 24 RAMB36 plus 1 RAMB18,
  422 DSP, and zero URAM

The vectorless `3.607 W` result is a Vivado estimate, not a physical power
measurement.

## Official KV260 Benchmark

The official headless run used 5 warm-up PSFs followed by 100 measured PSFs.
Overlay programming was excluded from per-PSF timing and reported separately.

| Metric | Result |
| --- | ---: |
| Effective `fclk0` | `124.99875 MHz` |
| Overlay load | `1.539426892 s` |
| Kernel call 1 mean | `0.244025295 s` |
| Kernel call 2 mean | `0.244940611 s` |
| Kernel call 3 mean | `0.244940927 s` |
| Three-call kernel mean | `0.733906833 s` |
| Synchronization mean | `0.000549990 s` |
| Three PS masks mean | `0.000595522 s` |
| End-to-end mean | `0.735655277 s/PSF` |
| End-to-end standard deviation | `0.000124460 s` |
| End-to-end median | `0.735629440 s` |
| End-to-end minimum | `0.735447096 s` |
| End-to-end percentile 5 | `0.735481508 s` |
| End-to-end percentile 95 | `0.735887369 s` |
| Approximate 95% CI for mean | `[0.735630883, 0.735679671] s` |
| Throughput | `1.359332328 PSF/s` |

## Numerical Validation

All values were finite and all six states passed the required limits:
relative L2 `<= 1e-3` and peak relative error `<= 1e-2`.

| State | Relative L2 | Peak relative | RMS absolute | Max absolute |
| --- | ---: | ---: | ---: | ---: |
| 120 pre-mask | `8.427981e-06` | `1.001738e-05` | `0.0680827` | `0.3570067` |
| 120 post-mask | `8.425386e-06` | `1.000069e-05` | `0.0680617` | `0.3564119` |
| 240 pre-mask | `1.690596e-05` | `1.966086e-05` | `0.1339586` | `0.3439692` |
| 240 post-mask | `1.690549e-05` | `1.968606e-05` | `0.1339549` | `0.3444100` |
| 360 pre-mask | `2.554344e-05` | `2.703269e-05` | `0.1892984` | `0.3704289` |
| 360 post-mask | `2.554523e-05` | `2.712206e-05` | `0.1893117` | `0.3716536` |

The 100 measured final fields were bit-identical. Their common SHA-256 was:

```text
68d3e368b5cb2cb8599176c38669ec719cb491f73646782c1687be7bb0978442
```

## Environment Findings

A preliminary smoke test exposed an inherited PS clock of
`187.498125 MHz`. Its timing was discarded because the implementation was
closed at 125 MHz. The final driver programs the overlay, restores `fclk0` to
125 MHz, verifies the effective value, and only then permits kernel launches.

The board's XRT 2.13 `xclbinutil` executable segfaults. A matching XCLBIN
metadata sidecar was generated off-board from the HWH `PSDDR` topology and is
included in the package; no XRT package was replaced.

The current image exposes no temperature through thermal sysfs, hwmon, IIO, or
the available XRT reports. This is recorded as unavailable rather than
estimated.

## Artifacts

Board directory:

```text
/home/ubuntu/jupyter_notebooks/bpm2d_kv260_kerr_fast_si
```

Retained official result:

```text
results/official_125mhz_20260724T2317Z
```

`repetitions.csv`, `summary.json`, `validation.json`, `environment.json`,
the six hardware stage arrays, `measured_final_fields.npy`, and
`final_output.npy` are preserved in that directory.
