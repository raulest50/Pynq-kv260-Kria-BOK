import numpy as np
from scipy.ndimage import gaussian_filter

from deep_tissue_imaging.elementos.plotting import plot_field_intensity_history, plot_field_intensity


## Operador Dispersion

def custom_thomas_solver(dp, dp1, dp2, do, b):
    """
    Solves a tridiagonal system with special structure using Thomas algorithm.

    Parameters:
    ----------
    dp : float
        Value for all elements in the main diagonal except first and last
    dp1 : float
        Value for the first element in the main diagonal [0,0]
    dp2 : float
        Value for the last element in the main diagonal [-1,-1]
    do : float
        Value for all elements in the off-diagonals
    b : numpy.ndarray
        Right-hand side vector

    Returns:
    -------
    x : numpy.ndarray
        Solution vector
    """
    n = len(b)

    # Create arrays for the modified coefficients
    c_prime = np.zeros(n-1, dtype=b.dtype)  # Upper diagonal
    d_prime = np.zeros(n, dtype=b.dtype)    # Modified right-hand side

    # Forward elimination
    # First row
    c_prime[0] = do / dp1
    d_prime[0] = b[0] / dp1

    # Middle rows
    for i in range(1, n-1):
        denominator = dp - do * c_prime[i-1]
        c_prime[i] = do / denominator
        d_prime[i] = (b[i] - do * d_prime[i-1]) / denominator

    # Last row
    d_prime[n-1] = (b[n-1] - do * d_prime[n-2]) / (dp2 - do * c_prime[n-2])

    # Back substitution
    x = np.zeros(n, dtype=b.dtype)
    x[n-1] = d_prime[n-1]

    for i in range(n-2, -1, -1):
        x[i] = d_prime[i] - c_prime[i] * x[i+1]

    return x


def compute_b_vector(dp, dp1, dp2, do, x0):
    """
    Multiplies a tridiagonal matrix with special structure by a vector.
    Optimized for vectors with dimensions > 3, but handles all cases.

    Parameters:
    ----------
    dp : float
        Value for all elements in the main diagonal except first and last
    dp1 : float
        Value for the first element in the main diagonal [0,0]
    dp2 : float
        Value for the last element in the main diagonal [-1,-1]
    do : float
        Value for all elements in the off-diagonals
    x0 : numpy.ndarray
        Input vector to be multiplied

    Returns:
    -------
    b : numpy.ndarray
        Result of the matrix-vector multiplication
    """
    n = len(x0)
    b = np.zeros(n, dtype=x0.dtype)

    # For n > 2, use the implementation with a for loop
    # First row: b[0] = dp1 * x0[0] + do * x0[1]
    b[0] = dp1 * x0[0] + do * x0[1]

    # Middle rows: b[i] = do * x0[i-1] + dp * x0[i] + do * x0[i+1]
    # Using a for loop as requested
    for i in range(1, n-1):
        b[i] = do * x0[i-1] + dp * x0[i] + do * x0[i+1]

    # Last row: b[n-1] = do * x0[n-2] + dp2 * x0[n-1]
    b[n-1] = do * x0[n-2] + dp2 * x0[n-1]

    return b


def adi_x(phi, Ny, eps, k, dz, dx):
    ung = np.complex64(1j * dz / (4 * k * dx**2))
    phi_inter = np.zeros_like(phi, dtype=np.complex64)
    for j in range(Ny):

        if abs(phi[1, j]) < eps:
            ratio_x0 = np.float32(1.0)
        else:
            ratio_x0 = phi[0, j] / phi[1, j]

        if abs(phi[-2, j]) < eps:
            ratio_xn = np.float32(1.0)
        else:
            ratio_xn = phi[-1, j] / phi[-2, j]

        dp1_B = -2 * ung + np.float32(1.0) + ung * ratio_x0
        dp2_B = -2 * ung + np.float32(1.0) + ung * ratio_xn
        dp_B = -2 * ung + np.float32(1.0)
        do_B = ung

        b = compute_b_vector(dp_B, dp1_B, dp2_B, do_B, phi[:, j])

        dp1_A = 2 * ung + np.float32(1.0) - ung * ratio_x0
        dp2_A = 2 * ung + np.float32(1.0) - ung * ratio_xn
        dp_A = 2 * ung + np.float32(1.0)
        do_A = -ung

        phi_inter[:, j] = custom_thomas_solver(dp_A, dp1_A, dp2_A, do_A, b)

    return phi_inter


def adi_y(phi, Nx, eps, k, dz, dy):
    ung = np.complex64(1j * dz / (4 * k * dy**2))
    phi_inter = np.zeros_like(phi, dtype=np.complex64)
    for i in range(Nx):

        if abs(phi[i, 1]) < eps:
            ratio_y0 = np.float32(1.0)
        else:
            ratio_y0 = phi[i, 0] / phi[i, 1]

        if abs(phi[i, -2]) < eps:
            ratio_yn = np.float32(1.0)
        else:
            ratio_yn = phi[i, -1] / phi[i, -2]

        dp1_B = -2 * ung + np.float32(1.0) + ung * ratio_y0
        dp2_B = -2 * ung + np.float32(1.0) + ung * ratio_yn
        dp_B = -2 * ung + np.float32(1.0)
        do_B = ung

        b = compute_b_vector(dp_B, dp1_B, dp2_B, do_B, phi[i, :])

        dp1_A = 2 * ung + np.float32(1.0) - ung * ratio_y0
        dp2_A = 2 * ung + np.float32(1.0) - ung * ratio_yn
        dp_A = 2 * ung + np.float32(1.0)
        do_A = -ung

        phi_inter[i, :] = custom_thomas_solver(dp_A, dp1_A, dp2_A, do_A, b)

    return phi_inter


## Operador N - Kerr

def half_nonlinear(phi, k_sample, n2_sample, dz):
   phase = np.exp(np.complex64(1j * k_sample * n2_sample * dz/2 * np.abs(phi)**2))
   return phase * phi


## Operadores de absorcion

# absorcion lineal
def half_linear_absorption(phi, alpha, dz):
   return np.exp(np.float32(-alpha * dz/4)) * phi

# absorcion de 2 fotones
def half_2photon_absorption(phi, beta, dz):
   return np.exp(np.float32(-beta * dz/4 * np.abs(phi)**2)) * phi


## Mascara de fase aleatoria

def aplicar_mascara_fase_aleatoria(phi, X, Y, desviacion_fase=0.3, correlacion_m=5e-6, semilla=None):
    """
    Aplica una máscara de fase aleatoria suave al campo complejo phi.

    Parámetros:
        phi (ndarray): campo complejo original (E o phi).
        X, Y (ndarray): mallas espaciales 2D (en metros).
        desviacion_fase (float): desviación estándar de la fase en radianes.
        correlacion_m (float): longitud de correlación espacial en metros.
        semilla (int, opcional): semilla para reproducibilidad.

    Retorna:
        ndarray: campo complejo phi con fase aleatoria aplicada.
    """
    if semilla is not None:
        np.random.seed(semilla)

    shape = X.shape

    # Calcular dx y dy a partir de las mallas (en metros)
    dx = np.float32(np.abs(X[0, 1] - X[0, 0]))  # metros
    dy = np.float32(np.abs(Y[1, 0] - Y[0, 0]))  # metros

    # Longitud de correlación en número de píxeles
    sigma_x = np.float32(correlacion_m / dx)
    sigma_y = np.float32(correlacion_m / dy)

    # Ruido gaussiano con desviación deseada
    ruido = np.random.normal(loc=0.0, scale=desviacion_fase, size=shape).astype(np.float32)

    # Suavizado para imitar fluctuación estructural
    theta = gaussian_filter(ruido, sigma=(sigma_y, sigma_x), mode='reflect')
    mf = np.exp(np.complex64(1j * theta))
    # plot_field_intensity(np.real(mf), X, Y)

    # Aplicar la fase aleatoria como exponente complejo
    phi_modulado = phi * mf

    return phi_modulado
