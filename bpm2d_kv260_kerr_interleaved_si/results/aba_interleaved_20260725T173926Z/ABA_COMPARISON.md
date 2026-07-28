# KV260 A-B-A Physical Benchmark

| Run | Kernel mean (s) | End-to-end mean (s) |
| --- | ---: | ---: |
| psf073 before | 0.733905157 | 0.735705980 |
| Interleaved | 0.086814983 | 0.088164225 |
| psf073 after | 0.733903450 | 0.735638556 |

- psf073 end-to-end drift: 0.009165%.
- Interleaved speedup versus pooled psf073: 8.344340x end-to-end and 8.453660x for the three PL calls.
- Interleaved physical/HLS three-call ratio: 0.999921.
- Speedup versus historical psf073 result: 8.344147x.
- Acceptance passed: true.

The HLS value is a cycle-derived estimate. All other timing values in this
file are physical KV260 measurements from the headless benchmark.
