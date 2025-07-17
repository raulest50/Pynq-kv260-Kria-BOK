import numpy as np
import deep_tissue_imaging.propagators.step_operators as so

def full_step_within_tissue(phi, tejido, d):
    phi = so.adi_x(phi, d.Ny, d.eps, d.k, d.dz, d.dx)
    phi = so.half_2photon_absorption(phi, tejido.beta, d.dz)
    phi = so.half_nonlinear(phi, d.k, tejido.n2, d.dz)
    phi = so.half_linear_absorption(phi, tejido.alpha, d.dz)

    phi = so.adi_y(phi, d.Nx, d.eps, d.k, d.dz, d.dy)
    phi = so.half_2photon_absorption(phi, tejido.beta, d.dz)
    phi = so.half_nonlinear(phi, d.k, tejido.n2, d.dz)
    phi = so.half_linear_absorption(phi, tejido.alpha, d.dz)
    return phi

def full_propagation_within_tissue(phi, tejido, d, mask_manager=None):
    """
    Perform full propagation within tissue with optional phase mask management.

    Parameters:
        phi (ndarray): Initial complex field
        tejido: Tissue properties
        d: Domain properties
        mask_manager (PhaseMaskManager, optional): Phase mask manager for consistent masks

    Returns:
        ndarray: History of the field propagation
    """
    spm = int(tejido.l_s/d.dz)
    phi_history = np.zeros((d.Nz + 1, *phi.shape), dtype=np.complex64)
    phi_history[0] = phi

    # Initialize masks at the beginning if mask_manager is provided
    if mask_manager is not None:
        mask_manager.initialize_masks(phi.shape, d.X, d.Y, d.sigma_phi, d.sigma_x)

    # Track which mask to use (1, 2, 3)
    mask_counter = 0

    for k in range(0, d.Nz):
        phi = full_step_within_tissue(phi, tejido, d)
        if k % spm == 0 and k != 0:
            # Increment mask counter (1, 2, 3, 1, 2, 3, ...)
            mask_counter = (mask_counter % 3) + 1

            if mask_manager is not None:
                # Use the mask manager with the current mask index
                phi = mask_manager.apply_mask(phi, mask_counter)
                print(f"aplicada mascara aleatoria {mask_counter} en z = {k}")
            else:
                # Use the original function if no mask manager is provided
                phi = so.aplicar_mascara_fase_aleatoria(phi, d.X, d.Y, d.sigma_phi, d.sigma_x)
                print(f"aplicada mascara aleatoria en z = {k}")

        phi_history[k + 1] = phi

    return phi_history

def compute_psf(phi, tejido, dominio):
    pass
