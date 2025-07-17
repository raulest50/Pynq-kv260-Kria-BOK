import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm


def campo_tem00(X, Y, w0, I0, fase_inicial=0.0):
    """
    Genera un campo TEM00 gaussiano complejo E(x,y) listo para usar en BPM.

    Parámetros:
        X, Y (ndarray): mallas 2D con coordenadas espaciales en metros.
        w0 (float): radio del waist (haz) en metros.
        I0 (float): intensidad pico en W/m².
        fase_inicial (float): fase global opcional (en radianes).

    Retorna:
        ndarray complejo: campo eléctrico complejo E(x,y)
    """
    R2 = X**2 + Y**2
    Ex = np.sqrt(np.float32(I0)) * np.exp(np.float32(-R2 / w0**2))
    fase = np.exp(np.complex64(-1j * fase_inicial))
    return np.complex64(Ex * fase)


class fuente_microscopia_1:
    wavelength = np.float32(800e-9)  # m longitud onda
    w0 = np.float32(3e-6)  # m beam waist 3um
    I_peak = np.float32(1e10)  # W/m**2
    NA = np.float32(0.1)  # NA de la lente


if __name__ == "__main__":
    # Parámetros del haz
    w0 = fuente_microscopia_1.w0  # Radio del haz en metros (3 µm)
    I0 = fuente_microscopia_1.I_peak   # Intensidad pico en W/m²

    # Crear malla de coordenadas
    L = 45e-6  # Tamaño del dominio (15 µm)
    N = 128     # Número de puntos en cada dimensión
    x = np.linspace(-L/2, L/2, N)
    y = np.linspace(-L/2, L/2, N)
    X, Y = np.meshgrid(x, y)

    # Generar el campo TEM00
    campo = campo_tem00(X, Y, w0, I0)

    # Calcular la intensidad (|E|²)
    intensidad = np.abs(campo)**2

    # Crear figura 3D
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    # Graficar superficie 2D
    surf = ax.plot_surface(X*1e6, Y*1e6, intensidad/I0, 
                          cmap=cm.viridis, linewidth=0, antialiased=True)

    # Configurar etiquetas y título
    ax.set_xlabel('X (µm)')
    ax.set_ylabel('Y (µm)')
    ax.set_zlabel('Intensidad normalizada')
    ax.set_title('Modo TEM00 - Perfil de intensidad')

    # Añadir barra de color
    fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5, label='Intensidad normalizada')

    # Mostrar gráfico
    plt.tight_layout()
    plt.show()

    # También crear una vista 2D (contorno)
    plt.figure(figsize=(8, 6))
    plt.contourf(X*1e6, Y*1e6, intensidad/I0, 50, cmap='viridis')
    plt.colorbar(label='Intensidad normalizada')
    plt.xlabel('X (µm)')
    plt.ylabel('Y (µm)')
    plt.title('Modo TEM00 - Vista superior')
    plt.axis('equal')
    plt.tight_layout()
    plt.show()
