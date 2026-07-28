#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "run_board_session.sh must run as root." >&2
  exit 2
fi

export XILINX_XRT=/usr
export BOARD=KV260
export PYTHONDONTWRITEBYTECODE=1

PYTHON=/usr/local/share/pynq-venv/bin/python3
BASELINE=/home/ubuntu/jupyter_notebooks/bpm2d_kv260_kerr_fast_si
CANDIDATE=/home/ubuntu/jupyter_notebooks/bpm2d_kv260_kerr_interleaved_si
SESSIONS=/home/ubuntu/jupyter_notebooks/bpm2d_kv260_benchmark_sessions
STAMP=${1:-$(date -u +%Y%m%dT%H%M%SZ)}
SESSION=${SESSIONS}/aba_interleaved_${STAMP}
JUPYTER_LINK=/root/jupyter_notebooks/bpm2d_kv260_kerr_interleaved_si
RESTORED=0

mkdir -p "${SESSIONS}"
mkdir "${SESSION}"

restore_board() {
  status=$?
  set +e
  restore_status=0
  jupyter_status=0
  if [[ ${RESTORED} -eq 0 ]]; then
    "${PYTHON}" "${CANDIDATE}/restore_psf073.py" "${BASELINE}" \
      >"${SESSION}/restore_psf073.log" 2>&1
    restore_status=$?
    systemctl start jupyter.service \
      >"${SESSION}/jupyter_restart.log" 2>&1
    jupyter_status=$?
  fi
  chown -R ubuntu:ubuntu "${SESSION}"
  if [[ ${status} -eq 0 && ${restore_status} -ne 0 ]]; then
    status=${restore_status}
  fi
  if [[ ${status} -eq 0 && ${jupyter_status} -ne 0 ]]; then
    status=${jupyter_status}
  fi
  exit "${status}"
}
trap restore_board EXIT

ln -sfn "${CANDIDATE}" "${JUPYTER_LINK}"

"${PYTHON}" "${CANDIDATE}/session_tools.py" snapshot \
  --output "${SESSION}/session_before.json" \
  --package "psf073=${BASELINE}" \
  --package "interleaved=${CANDIDATE}"

for cpu in /sys/devices/system/cpu/cpu[0-9]*/cpufreq; do
  [[ $(<"${cpu}/scaling_governor") == userspace ]]
  [[ $(<"${cpu}/scaling_setspeed") == 1333333 ]]
done

systemctl stop jupyter.service
sleep 3
if pgrep -af 'jupyter-notebook|ipykernel_launcher' \
  >"${SESSION}/unexpected_jupyter_processes.log"; then
  echo "Jupyter processes remain after service stop." >&2
  exit 3
fi

cd "${CANDIDATE}"
"${PYTHON}" benchmark_bpm2d_kerr_interleaved_si.py \
  --warmups 1 \
  --repetitions 3 \
  --output-dir "${SESSION}/smoke_interleaved" \
  >"${SESSION}/smoke_interleaved.console.log" 2>&1

cd "${BASELINE}"
"${PYTHON}" benchmark_bpm2d_kerr_fast_si.py \
  --warmups 5 \
  --repetitions 100 \
  --output-dir "${SESSION}/psf073_before" \
  >"${SESSION}/psf073_before.console.log" 2>&1

cd "${CANDIDATE}"
"${PYTHON}" benchmark_bpm2d_kerr_interleaved_si.py \
  --warmups 5 \
  --repetitions 100 \
  --output-dir "${SESSION}/interleaved" \
  >"${SESSION}/interleaved.console.log" 2>&1

cd "${BASELINE}"
"${PYTHON}" benchmark_bpm2d_kerr_fast_si.py \
  --warmups 5 \
  --repetitions 100 \
  --output-dir "${SESSION}/psf073_after" \
  >"${SESSION}/psf073_after.console.log" 2>&1

for run in smoke_interleaved psf073_before interleaved psf073_after; do
  "${PYTHON}" "${CANDIDATE}/session_tools.py" manifest "${SESSION}/${run}"
done

"${PYTHON}" "${CANDIDATE}/session_tools.py" compare "${SESSION}" \
  >"${SESSION}/aba_comparison.console.log"

"${PYTHON}" "${CANDIDATE}/restore_psf073.py" "${BASELINE}" \
  >"${SESSION}/restore_psf073.log" 2>&1
systemctl start jupyter.service \
  >"${SESSION}/jupyter_restart.log" 2>&1
sleep 3

"${PYTHON}" "${CANDIDATE}/session_tools.py" snapshot \
  --output "${SESSION}/session_after.json" \
  --package "psf073=${BASELINE}" \
  --package "interleaved=${CANDIDATE}"

RESTORED=1
trap - EXIT

"${PYTHON}" "${CANDIDATE}/session_tools.py" manifest "${SESSION}" \
  --name SESSION_SHA256SUMS.txt

chown -R ubuntu:ubuntu "${SESSION}"
echo "${SESSION}"
