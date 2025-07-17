from numpy import ndarray

class Domain:
    X: ndarray
    Y: ndarray
    Nx: int
    Ny: int
    Nz: int
    dx: float
    dy: float
    dz: float
    eps: float
    k0: float
    k: float
    sigma_phi: float
    sigma_x: float

    def __init__(self,
                 X, Y, Nx, Ny, Nz, dx, dy, dz, eps,
                 k0, k, sigma_phi, sigma_x
                 ):
        self.X = X
        self.Y = Y
        self.Nx = Nx
        self.Ny = Ny
        self.Nz = Nz
        self.dx = dx
        self.dy = dy
        self.dz = dz
        self.eps = eps
        self.k0 = k0
        self.k = k
        self.sigma_phi = sigma_phi
        self.sigma_x = sigma_x


