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
NAIVE=/home/ubuntu/jupyter_notebooks/bpm2d_kv260_kerr_naive_si
INTERLEAVED=/home/ubuntu/jupyter_notebooks/bpm2d_kv260_kerr_interleaved_si
SESSIONS=/home/ubuntu/jupyter_notebooks/bpm2d_kv260_benchmark_sessions
STAMP=${1:-$(date -u +%Y%m%dT%H%M%SZ)}
SESSION=${SESSIONS}/abca_naive_${STAMP}
JUPYTER_LINK=/root/jupyter_notebooks/bpm2d_kv260_kerr_naive_si
CPU_STATE=${SESSION}/cpu_state_before.tsv
RESTORED=0

mkdir -p "${SESSIONS}"
mkdir "${SESSION}"

capture_and_configure_cpu() {
  : >"${CPU_STATE}"
  for cpu in /sys/devices/system/cpu/cpu[0-9]*/cpufreq; do
    governor=$(<"${cpu}/scaling_governor")
    setspeed=$(cat "${cpu}/scaling_setspeed" 2>/dev/null || true)
    printf '%s\t%s\t%s\n' "${cpu}" "${governor}" "${setspeed}" \
      >>"${CPU_STATE}"
    echo userspace >"${cpu}/scaling_governor"
    echo 1333333 >"${cpu}/scaling_setspeed"
    [[ $(<"${cpu}/scaling_governor") == userspace ]]
    [[ $(<"${cpu}/scaling_setspeed") == 1333333 ]]
  done
}

restore_cpu() {
  [[ -f "${CPU_STATE}" ]] || return 0
  while IFS=$'\t' read -r cpu governor setspeed; do
    [[ -d "${cpu}" ]] || continue
    if [[ "${governor}" == userspace ]]; then
      echo userspace >"${cpu}/scaling_governor"
      if [[ -n "${setspeed}" ]]; then
        echo "${setspeed}" >"${cpu}/scaling_setspeed"
      fi
    else
      echo "${governor}" >"${cpu}/scaling_governor"
    fi
  done <"${CPU_STATE}"
}

restore_board() {
  status=$?
  set +e
  restore_status=0
  jupyter_status=0
  if [[ ${RESTORED} -eq 0 ]]; then
    "${PYTHON}" "${NAIVE}/restore_psf073.py" "${BASELINE}" \
      >"${SESSION}/restore_psf073.log" 2>&1
    restore_status=$?
    systemctl start jupyter.service \
      >"${SESSION}/jupyter_restart.log" 2>&1
    jupyter_status=$?
    restore_cpu
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

ln -sfn "${NAIVE}" "${JUPYTER_LINK}"

"${PYTHON}" -c \
  'import numpy, pynq; assert numpy.__version__ == "1.26.4"; assert pynq.__version__ == "3.0.1"'
"${PYTHON}" "${NAIVE}/make_package_manifest.py" --check \
  >"${SESSION}/naive_package_check_before.log"
(cd "${BASELINE}" && sha256sum -c SHA256SUMS.txt) \
  >"${SESSION}/psf073_package_check_before.log"
(cd "${INTERLEAVED}" && sha256sum -c SHA256SUMS.txt) \
  >"${SESSION}/interleaved_package_check_before.log"

"${PYTHON}" "${NAIVE}/session_tools.py" snapshot \
  --output "${SESSION}/session_before.json" \
  --package "psf073=${BASELINE}" \
  --package "naive=${NAIVE}" \
  --package "interleaved=${INTERLEAVED}"

capture_and_configure_cpu

systemctl stop jupyter.service
sleep 3
if pgrep -af 'jupyter-notebook|ipykernel_launcher' \
  >"${SESSION}/unexpected_jupyter_processes.log"; then
  echo "Jupyter processes remain after service stop." >&2
  exit 3
fi

cd "${NAIVE}"
"${PYTHON}" benchmark_bpm2d_kerr_naive_si.py \
  --warmups 1 \
  --repetitions 3 \
  --timeout 2.0 \
  --output-dir "${SESSION}/smoke_naive" \
  >"${SESSION}/smoke_naive.console.log" 2>&1

cd "${BASELINE}"
"${PYTHON}" benchmark_bpm2d_kerr_fast_si.py \
  --warmups 5 \
  --repetitions 100 \
  --output-dir "${SESSION}/psf073_before" \
  >"${SESSION}/psf073_before.console.log" 2>&1

cd "${NAIVE}"
"${PYTHON}" benchmark_bpm2d_kerr_naive_si.py \
  --warmups 5 \
  --repetitions 100 \
  --timeout 2.0 \
  --output-dir "${SESSION}/naive" \
  >"${SESSION}/naive.console.log" 2>&1

cd "${INTERLEAVED}"
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

for run in smoke_naive psf073_before naive interleaved psf073_after; do
  "${PYTHON}" "${NAIVE}/session_tools.py" manifest "${SESSION}/${run}"
done

"${PYTHON}" "${NAIVE}/session_tools.py" compare "${SESSION}" \
  >"${SESSION}/abca_comparison.console.log"

"${PYTHON}" "${NAIVE}/make_package_manifest.py" --check \
  >"${SESSION}/naive_package_check_after.log"
(cd "${BASELINE}" && sha256sum -c SHA256SUMS.txt) \
  >"${SESSION}/psf073_package_check_after.log"
(cd "${INTERLEAVED}" && sha256sum -c SHA256SUMS.txt) \
  >"${SESSION}/interleaved_package_check_after.log"

"${PYTHON}" "${NAIVE}/restore_psf073.py" "${BASELINE}" \
  >"${SESSION}/restore_psf073.log" 2>&1
systemctl start jupyter.service \
  >"${SESSION}/jupyter_restart.log" 2>&1
restore_cpu
sleep 3

"${PYTHON}" "${NAIVE}/session_tools.py" snapshot \
  --output "${SESSION}/session_after.json" \
  --package "psf073=${BASELINE}" \
  --package "naive=${NAIVE}" \
  --package "interleaved=${INTERLEAVED}"

RESTORED=1
trap - EXIT

"${PYTHON}" "${NAIVE}/session_tools.py" manifest "${SESSION}" \
  --name SESSION_SHA256SUMS.txt

chown -R ubuntu:ubuntu "${SESSION}"
echo "${SESSION}"
