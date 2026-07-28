# BPM2D KV260 Kerr Interleaved SI: Physical Results

## Measurement

The official headless A-B-A session ran on the KV260 with:

- Linux `5.15.0-1070-xilinx-zynqmp`;
- PYNQ 3.0.1, Python 3.10.12, and NumPy 1.26.4;
- effective PL clock `124.99875 MHz`;
- four CPUs in `userspace` mode at `1.333333 GHz`;
- 5 warm-up and 100 measured PSFs per official run;
- identical `64x64` input and deterministic phase masks.

Jupyter was stopped during measurement. Overlay load time was recorded
separately and excluded from per-PSF timing.

## A-B-A Comparison

| Run | Three PL calls (s) | End-to-end (s/PSF) |
| --- | ---: | ---: |
| psf073 before | 0.733905157 | 0.735705980 |
| Interleaved | 0.086814983 | 0.088164225 |
| psf073 after | 0.733903450 | 0.735638556 |

- Pooled psf073 end-to-end mean: `0.735672268 s/PSF`.
- psf073 end-to-end drift: `0.009165%`.
- Interleaved speedup versus pooled psf073: `8.453660x` for the three PL
  calls and `8.344340x` end-to-end.
- Interleaved speedup versus the historical psf073 result:
  `8.344147x`.
- HLS three-call estimate: `0.086821848 s`.
- Physical/HLS ratio: `0.999921`.
- Throughput: `11.342469 PSF/s`.

Interleaved end-to-end statistics:

| Statistic | Time (s) |
| --- | ---: |
| Mean | 0.088164225 |
| Standard deviation | 0.000092145 |
| Median | 0.088134734 |
| Minimum | 0.088095033 |
| Percentile 5 | 0.088104680 |
| Percentile 95 | 0.088322868 |
| Approximate 95% CI | [0.088146164, 0.088182285] |

The mean time spent in synchronization was `0.000377558 s`; the three PS
masks required `0.000522951 s`.

## Numerical Validation

All six pre/post-mask hardware states were finite and passed
`relative L2 <= 1e-3` and `peak relative error <= 1e-2`.

| State | Relative L2 | Peak relative | RMS absolute | Maximum absolute |
| --- | ---: | ---: | ---: | ---: |
| 120 pre-mask | 8.427981e-06 | 1.001738e-05 | 0.0680827 | 0.357007 |
| 120 post-mask | 8.425386e-06 | 1.000069e-05 | 0.0680617 | 0.356412 |
| 240 pre-mask | 1.690596e-05 | 1.966086e-05 | 0.133959 | 0.343969 |
| 240 post-mask | 1.690549e-05 | 1.968606e-05 | 0.133955 | 0.344410 |
| 360 pre-mask | 2.554344e-05 | 2.703269e-05 | 0.189298 | 0.370429 |
| 360 post-mask | 2.554523e-05 | 2.712206e-05 | 0.189312 | 0.371654 |

All 100 final fields were bit-identical. Their common SHA-256 was:

```text
68d3e368b5cb2cb8599176c38669ec719cb491f73646782c1687be7bb0978442
```

This is also the retained psf073 final-field hash for the same input and
masks.

## Provenance and Limits

The complete session is under
`results/aba_interleaved_20260725T173926Z`. Its 64 retained files passed the
board-generated `SESSION_SHA256SUMS.txt` after transfer back to the workspace.

The benchmark acceptance criteria passed. No physical power or energy value
was measured. The full 120-step C/RTL co-simulation remains incomplete; this
physical validation directly tests the deployed RTL for the retained
deterministic case but is not presented as exhaustive verification.
