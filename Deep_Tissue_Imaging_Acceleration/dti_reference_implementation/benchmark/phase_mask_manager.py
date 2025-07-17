"""
Phase mask manager for deep tissue imaging simulations.

This module provides a class to manage phase masks, ensuring they are
consistently generated and applied across different simulations.
"""

import os
import numpy as np
from scipy.ndimage import gaussian_filter
import pickle

class PhaseMaskManager:
    """
    Manages phase masks for deep tissue imaging simulations.
    
    This class handles the generation, storage, and retrieval of phase masks
    to ensure consistency between different simulation runs and between
    CPU and GPU implementations.
    """
    
    def __init__(self, save_dir="./phase_masks"):
        """
        Initialize the PhaseMaskManager.
        
        Parameters:
            save_dir (str): Directory to save phase masks for persistence
        """
        self.save_dir = save_dir
        self.masks = {}  # In-memory cache of masks
        
        # Create save directory if it doesn't exist
        os.makedirs(save_dir, exist_ok=True)
        
        # Metadata file to track mask information
        self.metadata_file = os.path.join(save_dir, "masks_metadata.pkl")
        self.metadata = self._load_metadata()
    
    def _load_metadata(self):
        """Load metadata about saved masks if it exists."""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"Warning: Could not load mask metadata: {e}")
        return {}
    
    def _save_metadata(self):
        """Save metadata about masks."""
        with open(self.metadata_file, 'wb') as f:
            pickle.dump(self.metadata, f)
    
    def get_mask_filename(self, mask_index):
        """Get the filename for a specific mask index."""
        return os.path.join(self.save_dir, f"phase_mask_{mask_index}.npy")
    
    def generate_mask(self, shape, X, Y, desviacion_fase, correlacion_m, mask_index):
        """
        Generate a new phase mask with the given parameters.
        
        Parameters:
            shape (tuple): Shape of the mask (Ny, Nx)
            X, Y (ndarray): Spatial meshgrids (in meters)
            desviacion_fase (float): Phase standard deviation in radians
            correlacion_m (float): Spatial correlation length in meters
            mask_index (int): Index of the mask (1, 2, or 3)
            
        Returns:
            ndarray: The generated phase mask (theta, not the complex exponential)
        """
        # Set a seed based on the mask index for reproducibility
        np.random.seed(42 + mask_index)  # Use a fixed base seed + mask index
        
        # Calculate dx and dy from the meshgrids (in meters)
        dx = np.float32(np.abs(X[0, 1] - X[0, 0]))  # meters
        dy = np.float32(np.abs(Y[1, 0] - Y[0, 0]))  # meters
        
        # Correlation length in pixels
        sigma_x = np.float32(correlacion_m / dx)
        sigma_y = np.float32(correlacion_m / dy)
        
        # Generate Gaussian noise with desired standard deviation
        ruido = np.random.normal(loc=0.0, scale=desviacion_fase, size=shape).astype(np.float32)
        
        # Smooth to mimic structural fluctuation
        theta = gaussian_filter(ruido, sigma=(sigma_y, sigma_x), mode='reflect')
        
        # Save the mask
        mask_file = self.get_mask_filename(mask_index)
        np.save(mask_file, theta)
        
        # Update metadata
        self.metadata[mask_index] = {
            'shape': shape,
            'desviacion_fase': desviacion_fase,
            'correlacion_m': correlacion_m,
            'created': np.datetime64('now')
        }
        self._save_metadata()
        
        return theta
    
    def get_mask(self, shape, X, Y, desviacion_fase, correlacion_m, mask_index):
        """
        Get a phase mask with the given index. If it doesn't exist, generate it.
        
        Parameters:
            shape (tuple): Shape of the mask (Ny, Nx)
            X, Y (ndarray): Spatial meshgrids (in meters)
            desviacion_fase (float): Phase standard deviation in radians
            correlacion_m (float): Spatial correlation length in meters
            mask_index (int): Index of the mask (1, 2, or 3)
            
        Returns:
            ndarray: The phase mask (theta, not the complex exponential)
        """
        # Check if mask is in memory
        if mask_index in self.masks:
            return self.masks[mask_index]
        
        # Check if mask exists on disk
        mask_file = self.get_mask_filename(mask_index)
        if os.path.exists(mask_file):
            try:
                theta = np.load(mask_file)
                # Verify the shape matches
                if theta.shape == shape:
                    self.masks[mask_index] = theta
                    return theta
                else:
                    print(f"Warning: Saved mask shape {theta.shape} doesn't match required shape {shape}. Regenerating.")
            except Exception as e:
                print(f"Warning: Could not load mask {mask_index}: {e}")
        
        # Generate new mask if not found or invalid
        theta = self.generate_mask(shape, X, Y, desviacion_fase, correlacion_m, mask_index)
        self.masks[mask_index] = theta
        return theta
    
    def initialize_masks(self, shape, X, Y, desviacion_fase, correlacion_m):
        """
        Initialize all three phase masks at the beginning of the simulation.
        
        Parameters:
            shape (tuple): Shape of the masks (Ny, Nx)
            X, Y (ndarray): Spatial meshgrids (in meters)
            desviacion_fase (float): Phase standard deviation in radians
            correlacion_m (float): Spatial correlation length in meters
            
        Returns:
            dict: Dictionary containing the three phase masks
        """
        print("Initializing phase masks...")
        masks = {}
        for i in range(1, 4):  # Generate masks with indices 1, 2, 3
            print(f"  Initializing mask {i}...")
            masks[i] = self.get_mask(shape, X, Y, desviacion_fase, correlacion_m, i)
        return masks
    
    def apply_mask(self, phi, mask_index):
        """
        Apply a pre-initialized phase mask to the complex field phi.
        
        Parameters:
            phi (ndarray): Complex field to which the mask will be applied
            mask_index (int): Index of the mask (1, 2, or 3)
            
        Returns:
            ndarray: The field with the phase mask applied
        """
        if mask_index not in self.masks:
            raise ValueError(f"Mask with index {mask_index} not initialized. Call initialize_masks first.")
        
        # Get the phase mask (theta)
        theta = self.masks[mask_index]
        
        # Apply the phase mask as a complex exponential
        mf = np.exp(np.complex64(1j * theta))
        
        # Apply the mask to the field
        return phi * mf