# BPM2D KV260 Kerr Naive SI Physical Benchmark

## Session

The retained headless session is:

```text
results/abca_naive_20260728T163422Z
```

It was executed on the KV260 as an A-B-C-A experiment:

1. psf073 before;
2. single-context sequential naive;
3. interleaved;
4. psf073 after.

Each official run used 5 warm-ups and 100 measured PSFs. The effective PL
clock was `124.99875 MHz`; all four Cortex-A53 cores used the `userspace`
governor at `1.333333 GHz`. The environment was PYNQ 3.0.1, Python 3.10.12,
NumPy 1.26.4, and Linux `5.15.0-1070-xilinx-zynqmp`.

The overlay-load time is excluded from the per-PSF result and reported
separately. The notebook was not used as the timing source.

## Physical Timing

End-to-end statistics:

| Run | Mean (s) | SD (s) | Median (s) | Min (s) | P5 (s) | P95 (s) | 95% CI half-width (s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| psf073 before | 0.735697582 | 0.000224241 | 0.735617761 | 0.735433154 | 0.735485800 | 0.736295968 | 0.000043951 |
| Naive | 1.427729151 | 0.000144739 | 1.427685556 | 1.427546903 | 1.427582109 | 1.428075980 | 0.000028369 |
| Interleaved | 0.088167506 | 0.000077930 | 0.088145007 | 0.088101325 | 0.088115315 | 0.088290744 | 0.000015274 |
| psf073 after | 0.735724919 | 0.000219845 | 0.735650050 | 0.735468616 | 0.735527656 | 0.736289740 | 0.000043090 |
| psf073 pooled | 0.735711251 | 0.000221919 | 0.735642102 | 0.735433154 | 0.735490005 | 0.736292508 | 0.000030756 |

Naive-specific measurements:

| Quantity | Physical result |
|---|---:|
| Three-call kernel mean | 1.425699326 s |
| Three-call kernel SD | 0.000010311 s |
| End-to-end mean | 1.427729151 s/PSF |
| Measured PS work mean | 0.001371576 s/PSF |
| Throughput | 0.700412960 PSF/s |
| Overlay load | 1.387017936 s |

The physical naive kernel lies inside the clock-adjusted HLS range
`1.419872847-1.428720295 s`. Its ratios to the lower and upper estimates are
`1.004104` and `0.997886`, respectively.

The contemporary end-to-end comparisons are:

- naive is `1.940611x` slower than pooled psf073;
- naive is `16.193371x` slower than interleaved;
- interleaved is `8.344472x` faster than pooled psf073;
- psf073 before/after drift is `0.003716%`.

The historical paper value of `1.567 s/PSF` is a separate physical result
from an earlier implementation. The new naive baseline is `0.139271 s`
faster (`8.8877%`, or `1.09755x`) and should not be described as a
reproduction of the historical hardware.

## Numerical Validation

All six pre/post-mask states are finite and pass `relative L2 <= 1e-3` and
`peak relative error <= 1e-2`:

| State | Relative L2 | Peak-relative | RMS absolute | Max absolute |
|---|---:|---:|---:|---:|
| 120 pre-mask | 8.427981e-06 | 1.001738e-05 | 0.068083 | 0.357007 |
| 120 post-mask | 8.425386e-06 | 1.000069e-05 | 0.068062 | 0.356412 |
| 240 pre-mask | 1.690596e-05 | 1.966086e-05 | 0.133959 | 0.343969 |
| 240 post-mask | 1.690549e-05 | 1.968606e-05 | 0.133955 | 0.344410 |
| 360 pre-mask | 2.554344e-05 | 2.703269e-05 | 0.189298 | 0.370429 |
| 360 post-mask | 2.554523e-05 | 2.712206e-05 | 0.189312 | 0.371654 |

All 100 naive outputs are bit-identical. Every architecture produced the
same validated final field:

```text
68d3e368b5cb2cb8599176c38669ec719cb491f73646782c1687be7bb0978442
```

## Acceptance And Preservation

All predefined criteria passed: numerical limits, determinism, expected
hash, baseline drift, HLS agreement, and the physical ordering
`interleaved < psf073 < naive`.

`SESSION_SHA256SUMS.txt` verifies the complete recovered result set. Package
manifests for naive, psf073, and interleaved passed both before and after the
session. The board was left with psf073 restored at `124.99875 MHz`,
`jupyter.service` active, and the FPGA manager in `operating` state.

No physical power or energy measurement was performed.
