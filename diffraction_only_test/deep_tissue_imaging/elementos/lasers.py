import numpy as np


def campo_tem00(X, Y, w0, I0, fase_inicial=0.0):
    """Genera un campo TEM00 gaussiano complejo E(x,y)."""
    R2 = X**2 + Y**2
    Ex = np.sqrt(np.float32(I0)) * np.exp(np.float32(-R2 / w0**2))
    fase = np.exp(np.complex64(-1j * fase_inicial))
    return np.complex64(Ex * fase)


class fuente_microscopia_1:
    wavelength = np.float32(800e-9)  # m longitud onda
    w0 = np.float32(3e-6)  # m beam waist 3um
    I_peak = np.float32(1e10)  # W/m**2
    NA = np.float32(0.1)  # NA de la lente
