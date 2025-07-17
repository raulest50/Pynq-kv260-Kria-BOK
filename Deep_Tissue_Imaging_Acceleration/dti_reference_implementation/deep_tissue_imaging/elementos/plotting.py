import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.widgets import Slider

def plot_field_intensity(phi, X, Y):
    """
    Plot the field intensity in a 2D color map with units in micrometers.

    Parameters:
    -----------
    phi : ndarray
        The complex field to plot (typically phi1 from propagation)
    X : ndarray
        The X coordinates meshgrid in meters
    Y : ndarray
        The Y coordinates meshgrid in meters

    Returns:
    --------
    fig, ax : tuple
        The figure and axis objects for further customization if needed
    """
    # Convert X and Y from meters to micrometers for display
    X_um = X * 1e6
    Y_um = Y * 1e6

    # Calculate the intensity (absolute square of the field)
    intensity = np.abs(phi)**2

    # Create the figure and axis
    fig, ax = plt.subplots(figsize=(10, 8))

    # Plot the intensity as a 2D color map
    im = ax.pcolormesh(X_um, Y_um, intensity, cmap='viridis', shading='auto')

    # Add a colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Intensity (W/m²)')

    # Set labels with units in micrometers
    ax.set_xlabel('X (μm)')
    ax.set_ylabel('Y (μm)')
    ax.set_title('Field Intensity (W/m²)')

    # Make the plot look nice
    plt.tight_layout()

    plt.show()

    return fig, ax

def plot_field_phase(phi, X, Y):
    """
    Plot the phase of phi1 field in a 2D color map with units in micrometers.

    Parameters:
    -----------
    phi : ndarray
        The complex field to plot (typically phi1 from propagation)
    X : ndarray
        The X coordinates meshgrid in meters
    Y : ndarray
        The Y coordinates meshgrid in meters

    Returns:
    --------
    fig, ax : tuple
        The figure and axis objects for further customization if needed
    """
    # Convert X and Y from meters to micrometers for display
    X_um = X * 1e6
    Y_um = Y * 1e6

    # Calculate the phase of the field
    phase = np.angle(phi)

    # Create the figure and axis
    fig, ax = plt.subplots(figsize=(10, 8))

    # Plot the phase as a 2D color map
    im = ax.pcolormesh(X_um, Y_um, phase, cmap='twilight', shading='auto')

    # Add a colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Phase (rad)')

    # Set labels with units in micrometers
    ax.set_xlabel('X (μm)')
    ax.set_ylabel('Y (μm)')
    ax.set_title('Phi1 Field Phase')

    # Make the plot look nice
    plt.tight_layout()

    plt.show()

    return fig, ax

def plot_field_intensity_history(phi_history, X, Y):
    """
    Plot the field intensity in a 2D color map with a slider to navigate through different steps.

    Parameters:
    -----------
    phi_history : ndarray
        The history of complex fields from propagation, shape (n_steps, ny, nx)
    X : ndarray
        The X coordinates meshgrid in meters
    Y : ndarray
        The Y coordinates meshgrid in meters

    Returns:
    --------
    fig, ax : tuple
        The figure and axis objects for further customization if needed
    """
    # Convert X and Y from meters to micrometers for display
    X_um = X * 1e6
    Y_um = Y * 1e6

    # Get the number of steps
    n_steps = phi_history.shape[0]

    # Create the figure and axes
    fig, ax = plt.subplots(figsize=(10, 8))
    plt.subplots_adjust(bottom=0.25)  # Make room for the slider

    # Calculate the intensity for the first step
    intensity = np.abs(phi_history[0])**2

    # Plot the intensity as a 2D color map
    im = ax.pcolormesh(X_um, Y_um, intensity, cmap='viridis', shading='auto')

    # Add a colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Intensity (W/m²)')

    # Set labels with units in micrometers
    ax.set_xlabel('X (μm)')
    ax.set_ylabel('Y (μm)')
    ax.set_title(f'Field Intensity (W/m²) - Step 0/{n_steps-1}')

    # Create a slider axis
    ax_slider = plt.axes([0.25, 0.1, 0.65, 0.03], facecolor='lightgoldenrodyellow')

    # Create the slider
    slider = Slider(
        ax=ax_slider,
        label='Step',
        valmin=0,
        valmax=n_steps-1,
        valinit=0,
        valstep=1
    )

    # Update function for the slider
    def update(val):
        step = int(slider.val)
        intensity = np.abs(phi_history[step])**2
        im.set_array(intensity.ravel())
        im.set_clim(intensity.min(), intensity.max())
        ax.set_title(f'Field Intensity (W/m²) - Step {step}/{n_steps-1}')
        fig.canvas.draw_idle()

    # Register the update function with the slider
    slider.on_changed(update)

    # No es necesario tight_layout() cuando se usan ejes personalizados para sliders
    # plt.tight_layout()  # Removed to avoid warning with custom slider axes

    plt.show()

    return fig, ax
