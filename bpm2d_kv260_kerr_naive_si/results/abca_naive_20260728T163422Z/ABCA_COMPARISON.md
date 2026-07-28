# KV260 A-B-C-A Physical Benchmark

| Run | Kernel mean (s) | End-to-end mean (s) |
| --- | ---: | ---: |
| psf073 before | 0.733904893 | 0.735697582 |
| Naive | 1.425699326 | 1.427729151 |
| Interleaved | 0.086815814 | 0.088167506 |
| psf073 after | 0.733906467 | 0.735724919 |

- psf073 end-to-end drift: 0.003716%.
- Naive slowdown versus pooled psf073: 1.940611x end-to-end and 1.942619x for the PL calls.
- Interleaved speedup versus pooled psf073: 8.344472x end-to-end and 8.453594x for the PL calls.
- Naive slowdown versus interleaved: 16.193371x end-to-end.
- Naive physical/HLS maximum estimate ratio: 0.997886.
- Interleaved physical/HLS three-call ratio: 0.999930.
- Naive/historical 1.567 s ratio: 1.940758.
- Acceptance passed: true.

The HLS value is a cycle-derived estimate. All other timing values in this
file are physical KV260 measurements from the headless benchmark.
