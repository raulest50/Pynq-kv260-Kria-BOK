from pynq import Overlay, allocate
import numpy as np
import matplotlib.pyplot as plt
import time
import sys
from pathlib import Path

# Reference implementation imports
sys.path.append('../Deep_Tissue_Imaging_Acceleration/dti_reference_implementation')
from deep_tissue_imaging.elementos.lasers import fuente_microscopia_1 as laser, campo_tem00
from deep_tissue_imaging.elementos.tejidos import cerebro_emb_pez_cebra as tejido
from deep_tissue_imaging.propagators.step_operators import adi_x, adi_y


def plot_magnitude(field, title):
    plt.figure()
    plt.imshow(np.abs(field), cmap='viridis')
    plt.colorbar()
    plt.title(title)
    plt.show()


# Helper to save arrays for debugging
def save_array(data, filename):
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(str(path), data)


# Cargar overlay
ol = Overlay('diffraction_ovr.bit')
ip = ol.diffraction_only_0

# Configurar dominio y campo inicial
Lz = np.float32(361e-6)
Nz = 361
dz = np.float32(Lz / Nz)
Lx = Ly = np.float32(45e-6)
Nx = Ny = 256
dx = np.float32(Lx / Nx)
dy = np.float32(Ly / Ny)
x = np.linspace(-Lx/2, Lx/2, Nx, dtype=np.float32)
y = np.linspace(-Ly/2, Ly/2, Ny, dtype=np.float32)
X, Y = np.meshgrid(x, y)
phi0 = campo_tem00(X, Y, laser.w0, laser.I_peak)

k0 = np.float32(2*np.pi / laser.wavelength)
k = np.float32(k0 * tejido.n_0)
eps = np.float32(1e-12)

# Guardar campo inicial
save_array(phi0, 'debug_data/phi_input.npy')
plot_magnitude(phi0, 'Perfil inicial |phi0|')

# Implementación en software usando ADI

def diffraction_sw(phi):
    tmp = adi_x(phi, Ny, eps, k, dz, dx)
    return adi_y(tmp, Nx, eps, k, dz, dy)


# Ejecutar en software
t0 = time.time()
sw_out = diffraction_sw(phi0)
sw_time = time.time() - t0
print(f'Software time: {sw_time*1e3:.2f} ms')
plot_magnitude(sw_out, '|phi| después de SW')
save_array(sw_out, 'debug_data/phi_sw_out.npy')


# Ejecutar en hardware
N = Nx * Ny
in_buffer = allocate(shape=(N,), dtype=np.complex64)
out_buffer = allocate(shape=(N,), dtype=np.complex64)
np.copyto(in_buffer, phi0.reshape(-1))

# Flush caches before HW access
in_buffer.flush()
out_buffer.invalidate()

# Program addresses (split into low/high 32-bit words)
ip.write(0x10, in_buffer.physical_address & 0xFFFFFFFF)
ip.write(0x14, (in_buffer.physical_address >> 32) & 0xFFFFFFFF)
ip.write(0x18, out_buffer.physical_address & 0xFFFFFFFF)
ip.write(0x1C, (out_buffer.physical_address >> 32) & 0xFFFFFFFF)

# Start IP
t0 = time.time()
ip.write(0x00, 1)
while (ip.read(0x00) & 0x2) == 0:
    pass

# Invalidate caches before reading result
out_buffer.invalidate()

hw_time = time.time() - t0
hw_out = np.array(out_buffer).reshape(Nx, Ny)
print(f'Hardware time: {hw_time*1e3:.2f} ms')
plot_magnitude(hw_out, '|phi| después de HW')
save_array(hw_out, 'debug_data/phi_hw_out.npy')

# Validación

# Save difference for debug
diff = np.abs(sw_out - hw_out)
save_array(diff, 'debug_data/diff.npy')
print('Max error:', diff.max())
print('HW faster by {:.2f}x'.format(sw_time / hw_time))
