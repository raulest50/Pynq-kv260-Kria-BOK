# BPM2D KV260 Kerr Naive SI

Independent PYNQ package for the single-context sequential BPM2D baseline.
It preserves psf073 and interleaved without modification.

One accelerator call executes 120 updates:

```text
ADI-X -> two-photon absorption -> Kerr -> linear absorption
      -> ADI-Y -> two-photon absorption -> Kerr -> linear absorption
```

One PSF uses three calls. The PS applies deterministic phase masks after
updates 120, 240, and 360.

## Hardware Contract

- Grid: `complex64[64,64]`, C-order.
- VLNV: `fotonica109:hls:bpm2d_kv260_m_axi_kerr_naive_si:1.0`.
- Instance: `a`.
- AXI4-Lite base: `0x80000000`.
- Input address: `0x10/0x14`.
- Output address: `0x1C/0x20`.
- PL clock: 125 MHz.
- Timeout: 2 seconds per 120-step segment.

The `.bit`, `.hwh`, and `.xclbin` files must share the basename
`bpm2d_kv260_kerr_naive_si`.

## Local Verification

```powershell
cmd /c build_xclbin.cmd
python -m unittest discover -s tests -v
python make_package_manifest.py --write
python make_package_manifest.py --check
```

## KV260 Deployment

Target directory:

```text
/home/ubuntu/jupyter_notebooks/bpm2d_kv260_kerr_naive_si
```

Runtime:

```text
XILINX_XRT=/usr
BOARD=KV260
/usr/local/share/pynq-venv/bin/python3
```

The official headless session is executed as root:

```bash
./run_board_session.sh
```

It runs psf073, naive, interleaved, and psf073 again with 5 warm-ups and 100
measured PSFs per implementation. The script stops Jupyter, fixes the CPU
frequency, verifies package hashes, restores psf073, restores CPU state, and
restarts Jupyter even when an intermediate command fails.

The notebook is intended only for interactive inspection. Official timing
comes from the headless A-B-C-A session.

## Retained Physical Result

The accepted session is
`results/abca_naive_20260728T163422Z`. For 100 measured PSFs:

- naive three-call kernel mean: `1.425699326 s`;
- naive end-to-end mean: `1.427729151 s/PSF`;
- throughput: `0.700412960 PSF/s`;
- pooled psf073 control: `0.735711251 s/PSF`;
- interleaved: `0.088167506 s/PSF`;
- psf073 before/after drift: `0.003716%`.

All outputs were deterministic and matched the validated final SHA-256.
Complete statistics and numerical metrics are in `BENCHMARK_RESULTS.md`.

## Acceptance

- Six pre/post-mask states pass `relative L2 <= 1e-3` and
  `peak relative error <= 1e-2`.
- No state contains NaN or infinity.
- All measured outputs are deterministic and match the validated final hash.
- Contemporary psf073 drift is below 1%.
- Naive kernel time is within 5% of the clock-adjusted HLS maximum estimate.
- Physical order is interleaved, psf073, naive from fastest to slowest.

No physical power or energy measurement is performed.
