# BPM2D KV260 Kerr Interleaved SI

This independent PYNQ package deploys the post-psf073 interleaved BPM2D
architecture on the KV260. It does not modify the measured
`bpm2d_kv260_kerr_fast_si` package.

One accelerator invocation performs 120 updates using:

```text
ADI-X -> two-photon absorption -> Kerr -> linear absorption
      -> ADI-Y -> two-photon absorption -> Kerr -> linear absorption
```

A complete PSF uses three invocations. The PS applies the same deterministic
phase masks after updates 120, 240, and 360. The masks are not implemented in
the PL.

## Hardware Contract

- Grid and storage: `complex64[64,64]`, C-order.
- HLS IP: `fotonica109:hls:bpm2d_kv260_m_axi_kerr_interleaved_si:1.0`.
- Accelerator instance: `a`.
- AXI4-Lite base address: `0x80000000`.
- `phi_in` address: `0x10/0x14`.
- `phi_out` address: `0x1C/0x20`.
- Target PL clock: 125 MHz.
- Segment timeout: 2 seconds.

The `.bit`, `.hwh`, and `.xclbin` basenames must remain identical. The XCLBIN
is a PYNQ/XRT memory-topology sidecar containing the proven `PSDDR` topology;
the actual programmable logic image is the Vivado-generated bitstream.

## Local Verification

Generate the XCLBIN sidecar:

```powershell
cmd /c build_xclbin.cmd
```

Run the host-side tests:

```powershell
python -m unittest discover -s tests -v
```

`SHA256SUMS.txt` is the package integrity manifest used before and after
deployment.

## Board Deployment

The intended target is:

```text
/home/ubuntu/jupyter_notebooks/bpm2d_kv260_kerr_interleaved_si
```

Runtime requirements:

```text
XILINX_XRT=/usr
BOARD=KV260
/usr/local/share/pynq-venv/bin/python3
```

Run a standalone smoke test with:

```bash
python3 benchmark_bpm2d_kerr_interleaved_si.py \
  --warmups 1 --repetitions 3
```

The official measurement is executed by `run_board_session.sh` as root. It:

1. records the initial environment;
2. stops Jupyter and confirms that no notebook kernels remain;
3. validates the interleaved overlay with a smoke test;
4. measures psf073, interleaved, and psf073 again;
5. restores psf073 and restarts Jupyter;
6. writes A-B-A comparison and SHA-256 manifests.

Each official run uses 5 warm-up PSFs and 100 measured PSFs. The notebook is
for inspection and visualization; it is not the official timing source.

## Official Physical Result

The retained A-B-A session is:

```text
results/aba_interleaved_20260725T173926Z
```

At an effective PL clock of `124.99875 MHz`, the interleaved implementation
measured:

- three-call kernel mean: `0.086814983 s`;
- end-to-end mean: `0.088164225 s/PSF`;
- end-to-end standard deviation: `0.000092145 s`;
- throughput: `11.342469 PSF/s`;
- speedup versus pooled contemporary psf073: `8.344340x` end-to-end.

The two psf073 controls measured `0.735705980 s/PSF` and
`0.735638556 s/PSF`, a drift of `0.009165%`. The physical three-call result
was `0.999921` times the HLS cycle estimate.

All six validation states passed and all 100 final fields were bit-identical.
See `BENCHMARK_RESULTS.md` and the session manifests for complete statistics
and provenance.

## Acceptance

Every pre/post-mask state must be finite and satisfy:

- relative L2 error `<= 1e-3`;
- peak relative error `<= 1e-2`.

All 100 final interleaved fields must be deterministic. The two contemporary
psf073 controls must differ by less than 1%, and the interleaved end-to-end
mean must be below both controls to declare a physical performance
improvement.

The full 120-step C/RTL co-simulation remains incomplete. Board validation
tests the deployed RTL directly for the retained deterministic case, but is
not described as exhaustive co-simulation or as a physical power measurement.
