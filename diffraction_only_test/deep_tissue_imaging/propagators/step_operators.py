import numpy as np


def custom_thomas_solver(dp, dp1, dp2, do, b):
    """Solve a tridiagonal system using the Thomas algorithm."""
    n = len(b)
    c_prime = np.zeros(n - 1, dtype=b.dtype)
    d_prime = np.zeros(n, dtype=b.dtype)

    c_prime[0] = do / dp1
    d_prime[0] = b[0] / dp1

    for i in range(1, n - 1):
        denominator = dp - do * c_prime[i - 1]
        c_prime[i] = do / denominator
        d_prime[i] = (b[i] - do * d_prime[i - 1]) / denominator

    d_prime[n - 1] = (b[n - 1] - do * d_prime[n - 2]) / (dp2 - do * c_prime[n - 2])

    x = np.zeros(n, dtype=b.dtype)
    x[n - 1] = d_prime[n - 1]
    for i in range(n - 2, -1, -1):
        x[i] = d_prime[i] - c_prime[i] * x[i + 1]

    return x


def compute_b_vector(dp, dp1, dp2, do, x0):
    """Multiply a tridiagonal matrix with a vector."""
    n = len(x0)
    b = np.zeros(n, dtype=x0.dtype)
    b[0] = dp1 * x0[0] + do * x0[1]
    for i in range(1, n - 1):
        b[i] = do * x0[i - 1] + dp * x0[i] + do * x0[i + 1]
    b[n - 1] = do * x0[n - 2] + dp2 * x0[n - 1]
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
