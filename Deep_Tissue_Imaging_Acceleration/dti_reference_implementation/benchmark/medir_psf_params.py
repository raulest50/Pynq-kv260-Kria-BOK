"""
PSF parameter measurement for deep tissue imaging.

This module provides functions to measure various parameters of a Point Spread Function (PSF),
including FWHM lateral, FWHM axial, encircled energy, and sidelobes.
"""

import numpy as np
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt

def calcular_fwhm_lateral(psf, X, Y):
    """
    Calculate the lateral Full Width at Half Maximum (FWHM) of a PSF.

    Parameters:
        psf (ndarray): The point spread function (intensity)
        X, Y (ndarray): Spatial meshgrids (in meters)

    Returns:
        float: FWHM in meters
    """
    # Get the center of the PSF
    max_idx = np.unravel_index(np.argmax(psf), psf.shape)
    center_y, center_x = max_idx

    # Extract a horizontal line through the center
    horizontal_profile = psf[center_y, :]
    x_profile = X[center_y, :]

    # Extract a vertical line through the center
    vertical_profile = psf[:, center_x]
    y_profile = Y[:, center_x]

    # Calculate FWHM for horizontal profile
    max_value = horizontal_profile.max()
    half_max = max_value / 2.0

    # Interpolate to find more precise crossing points
    x_interp = interp1d(x_profile, horizontal_profile - half_max, kind='cubic')
    x_range = np.linspace(x_profile.min(), x_profile.max(), 1000)
    y_interp = x_interp(x_range)
    zero_crossings = np.where(np.diff(np.signbit(y_interp)))[0]

    if len(zero_crossings) >= 2:
        fwhm_x = x_range[zero_crossings[1]] - x_range[zero_crossings[0]]
    else:
        fwhm_x = float('nan')

    # Calculate FWHM for vertical profile
    y_interp = interp1d(y_profile, vertical_profile - half_max, kind='cubic')
    y_range = np.linspace(y_profile.min(), y_profile.max(), 1000)
    y_interp_values = y_interp(y_range)
    zero_crossings = np.where(np.diff(np.signbit(y_interp_values)))[0]

    if len(zero_crossings) >= 2:
        fwhm_y = y_range[zero_crossings[1]] - y_range[zero_crossings[0]]
    else:
        fwhm_y = float('nan')

    # Average the two directions
    fwhm_lateral = (fwhm_x + fwhm_y) / 2.0

    return fwhm_lateral

def calcular_fwhm_axial(psf_history, z_positions):
    """
    Calculate the axial Full Width at Half Maximum (FWHM) of a PSF.

    Parameters:
        psf_history (ndarray): The PSF at different z positions
        z_positions (ndarray): The z positions in meters

    Returns:
        float: FWHM in meters
    """
    # Find the maximum intensity at each z position
    max_intensities = np.array([np.max(np.abs(psf_z)**2) for psf_z in psf_history])

    # Find the overall maximum and its position
    max_value = max_intensities.max()
    max_pos = np.argmax(max_intensities)
    half_max = max_value / 2.0

    # Check if the profile crosses half-maximum
    if np.sum(max_intensities >= half_max) < 2:
        print("Warning: Axial profile doesn't cross half-maximum twice. FWHM calculation may be inaccurate.")
        # Try to estimate FWHM by finding the width at the highest level that is crossed twice
        for level in np.linspace(0.1, 0.4, 4):
            threshold = max_value * level
            if np.sum(max_intensities >= threshold) >= 2:
                print(f"Using {level*100:.0f}% of maximum instead of 50% for axial width estimation.")
                half_max = threshold
                break

    # Interpolate to find more precise crossing points
    try:
        z_interp = interp1d(z_positions, max_intensities - half_max, kind='cubic')
        z_range = np.linspace(z_positions.min(), z_positions.max(), 1000)
        z_interp_values = z_interp(z_range)
        zero_crossings = np.where(np.diff(np.signbit(z_interp_values)))[0]

        if len(zero_crossings) >= 2:
            fwhm_z = z_range[zero_crossings[1]] - z_range[zero_crossings[0]]
        else:
            # If we still don't have two crossings, estimate based on the simulation bounds
            print("Warning: Could not find two crossings of the threshold. Estimating from simulation bounds.")
            if max_pos < len(max_intensities) / 2:
                # Maximum is in the first half, so estimate width from start to where it drops below threshold
                below_threshold = np.where(max_intensities < half_max)[0]
                below_threshold = below_threshold[below_threshold > max_pos]
                if len(below_threshold) > 0:
                    fwhm_z = 2 * (z_positions[below_threshold[0]] - z_positions[max_pos])
                else:
                    fwhm_z = 2 * (z_positions[-1] - z_positions[max_pos])
            else:
                # Maximum is in the second half, so estimate width from where it rises above threshold to end
                below_threshold = np.where(max_intensities < half_max)[0]
                below_threshold = below_threshold[below_threshold < max_pos]
                if len(below_threshold) > 0:
                    fwhm_z = 2 * (z_positions[max_pos] - z_positions[below_threshold[-1]])
                else:
                    fwhm_z = 2 * (z_positions[max_pos] - z_positions[0])
    except Exception as e:
        print(f"Error calculating axial FWHM: {e}")
        fwhm_z = float('nan')

    return fwhm_z


def calcular_energia_encerrada(psf, X, Y, radios):
    """
    Calculate the encircled energy at different radii.

    Parameters:
        psf (ndarray): The point spread function (intensity)
        X, Y (ndarray): Spatial meshgrids (in meters)
        radios (list): List of radii at which to calculate encircled energy

    Returns:
        dict: Dictionary mapping radii to encircled energy fractions
    """
    # Get the center of the PSF
    max_idx = np.unravel_index(np.argmax(psf), psf.shape)
    center_y, center_x = max_idx
    center_coords = (Y[center_y, center_x], X[center_y, center_x])

    # Calculate distance from center for each point
    distances = np.sqrt((Y - center_coords[0])**2 + (X - center_coords[1])**2)

    # Calculate total energy
    total_energy = np.sum(psf)

    # Calculate encircled energy for each radius
    encircled_energies = {}
    for radius in radios:
        mask = distances <= radius
        encircled_energy = np.sum(psf[mask]) / total_energy
        encircled_energies[radius] = encircled_energy

    return encircled_energies

def calcular_radio_energia(psf, X, Y, porcentaje=0.8):
    """
    Calculate the radius that contains a specific percentage of the total energy.

    Parameters:
        psf (ndarray): The point spread function (intensity)
        X, Y (ndarray): Spatial meshgrids (in meters)
        porcentaje (float): Target percentage of energy (0.0 to 1.0)

    Returns:
        float: Radius in meters that contains the specified percentage of energy
    """
    # Get the center of the PSF
    max_idx = np.unravel_index(np.argmax(psf), psf.shape)
    center_y, center_x = max_idx
    center_coords = (Y[center_y, center_x], X[center_y, center_x])

    # Calculate distance from center for each point
    distances = np.sqrt((Y - center_coords[0])**2 + (X - center_coords[1])**2)

    # Calculate total energy
    total_energy = np.sum(psf)

    # Sort points by distance from center
    flat_distances = distances.flatten()
    flat_psf = psf.flatten()
    sorted_indices = np.argsort(flat_distances)
    sorted_distances = flat_distances[sorted_indices]
    sorted_energies = flat_psf[sorted_indices]

    # Calculate cumulative energy
    cumulative_energy = np.cumsum(sorted_energies) / total_energy

    # Find the index where cumulative energy exceeds the target percentage
    target_idx = np.searchsorted(cumulative_energy, porcentaje)

    # Return the corresponding radius
    if target_idx < len(sorted_distances):
        return sorted_distances[target_idx]
    else:
        return sorted_distances[-1]  # Return the maximum radius if target not reached

def calcular_sidelobes(psf, X, Y):
    """
    Calculate the sidelobe levels of a PSF.

    Parameters:
        psf (ndarray): The point spread function (intensity)
        X, Y (ndarray): Spatial meshgrids (in meters)

    Returns:
        dict: Dictionary with sidelobe information
    """
    # Get the center of the PSF
    max_idx = np.unravel_index(np.argmax(psf), psf.shape)
    center_y, center_x = max_idx

    # Extract horizontal and vertical profiles
    horizontal_profile = psf[center_y, :]
    vertical_profile = psf[:, center_x]

    # Find local maxima in horizontal profile
    h_peaks = []
    for i in range(1, len(horizontal_profile)-1):
        if (horizontal_profile[i] > horizontal_profile[i-1] and 
            horizontal_profile[i] > horizontal_profile[i+1]):
            h_peaks.append((i, horizontal_profile[i]))

    # Find local maxima in vertical profile
    v_peaks = []
    for i in range(1, len(vertical_profile)-1):
        if (vertical_profile[i] > vertical_profile[i-1] and 
            vertical_profile[i] > vertical_profile[i+1]):
            v_peaks.append((i, vertical_profile[i]))

    # Sort peaks by intensity
    h_peaks.sort(key=lambda x: x[1], reverse=True)
    v_peaks.sort(key=lambda x: x[1], reverse=True)

    # Main peak should be the first one
    main_peak_h = h_peaks[0][1] if h_peaks else 0
    main_peak_v = v_peaks[0][1] if v_peaks else 0

    # Get sidelobes (all peaks except the main one)
    h_sidelobes = h_peaks[1:] if len(h_peaks) > 1 else []
    v_sidelobes = v_peaks[1:] if len(v_peaks) > 1 else []

    # Calculate sidelobe levels relative to main peak
    h_sidelobe_levels = [(pos, intensity / main_peak_h) for pos, intensity in h_sidelobes]
    v_sidelobe_levels = [(pos, intensity / main_peak_v) for pos, intensity in v_sidelobes]

    # Find the highest sidelobe
    max_sidelobe_h = max(h_sidelobe_levels, key=lambda x: x[1])[1] if h_sidelobes else 0
    max_sidelobe_v = max(v_sidelobe_levels, key=lambda x: x[1])[1] if v_sidelobes else 0
    max_sidelobe = max(max_sidelobe_h, max_sidelobe_v)

    return {
        'max_sidelobe_ratio': max_sidelobe,
        'horizontal_sidelobes': h_sidelobe_levels,
        'vertical_sidelobes': v_sidelobe_levels
    }

def medir_psf_params(psf, X, Y, psf_history=None, z_positions=None, plot=False):
    """
    Measure various parameters of a Point Spread Function (PSF).

    Parameters:
        psf (ndarray): The point spread function (intensity) at focal plane
        X, Y (ndarray): Spatial meshgrids (in meters)
        psf_history (ndarray, optional): The PSF at different z positions
        z_positions (ndarray, optional): The z positions in meters
        plot (bool): Whether to plot the results

    Returns:
        dict: Dictionary with all PSF parameters
    """
    # Ensure we're working with intensity
    if np.iscomplexobj(psf):
        psf = np.abs(psf)**2

    # Calculate lateral FWHM
    fwhm_lateral = calcular_fwhm_lateral(psf, X, Y)

    # Calculate axial FWHM if history is provided
    fwhm_axial = None
    if psf_history is not None and z_positions is not None:
        # Convert to intensity if complex
        if np.iscomplexobj(psf_history):
            psf_history = np.abs(psf_history)**2
        fwhm_axial = calcular_fwhm_axial(psf_history, z_positions)


    # Calculate encircled energy at different radii
    # Use fractions of the FWHM as radii
    radios = [0.5 * fwhm_lateral, 1.0 * fwhm_lateral, 1.5 * fwhm_lateral]
    energia_encerrada = calcular_energia_encerrada(psf, X, Y, radios)

    # Calculate radius containing 80% of energy
    radio_80 = calcular_radio_energia(psf, X, Y, 0.8)

    # Calculate sidelobe levels
    sidelobes = calcular_sidelobes(psf, X, Y)

    # Compile results
    resultados = {
        'fwhm_lateral': fwhm_lateral,
        'fwhm_axial': fwhm_axial,
        'energia_encerrada': energia_encerrada,
        'radio_80': radio_80,
        'sidelobes': sidelobes
    }

    # Print results
    print("\n=== PSF Parameters ===")
    print(f"FWHM Lateral: {fwhm_lateral*1e6:.2f} µm")
    if fwhm_axial is not None:
        print(f"FWHM Axial: {fwhm_axial*1e6:.2f} µm")
    print(f"\nRadius containing 80% of energy: {radio_80*1e6:.2f} µm")
    print("\nEncircled Energy:")
    for radius, energy in energia_encerrada.items():
        print(f"  Radius {radius*1e6:.2f} µm: {energy*100:.1f}%")
    print(f"\nMax Sidelobe Level: {sidelobes['max_sidelobe_ratio']*100:.1f}% of peak")

    # Plot if requested
    if plot:
        plt.figure(figsize=(12, 10))

        # Plot the PSF
        plt.subplot(2, 2, 1)
        plt.imshow(psf, extent=[X.min()*1e6, X.max()*1e6, Y.min()*1e6, Y.max()*1e6])
        plt.colorbar(label='Intensity')
        plt.title('PSF Intensity')
        plt.xlabel('X (µm)')
        plt.ylabel('Y (µm)')

        # Plot horizontal and vertical profiles
        center_y, center_x = np.unravel_index(np.argmax(psf), psf.shape)

        plt.subplot(2, 2, 2)
        plt.plot(X[center_y, :]*1e6, psf[center_y, :] / np.max(psf))
        plt.axhline(0.5, color='r', linestyle='--', label='Half Maximum')
        plt.title('Horizontal Profile')
        plt.xlabel('X (µm)')
        plt.ylabel('Normalized Intensity')
        plt.grid(True)
        plt.legend()

        plt.subplot(2, 2, 3)
        plt.plot(Y[:, center_x]*1e6, psf[:, center_x] / np.max(psf))
        plt.axhline(0.5, color='r', linestyle='--', label='Half Maximum')
        plt.title('Vertical Profile')
        plt.xlabel('Y (µm)')
        plt.ylabel('Normalized Intensity')
        plt.grid(True)
        plt.legend()

        # Plot axial profile if available
        if psf_history is not None and z_positions is not None:
            plt.subplot(2, 2, 4)
            max_intensities = np.array([np.max(np.abs(psf_z)**2) for psf_z in psf_history])
            plt.plot(z_positions*1e6, max_intensities / np.max(max_intensities))
            plt.axhline(0.5, color='r', linestyle='--', label='Half Maximum')
            plt.title('Axial Profile')
            plt.xlabel('Z (µm)')
            plt.ylabel('Normalized Intensity')
            plt.grid(True)
            plt.legend()

        plt.tight_layout()
        plt.show()

    return resultados
