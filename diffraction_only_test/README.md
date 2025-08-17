# Diffraction Only Overlay | Ejemplo

Este directorio contiene los artefactos del componente **DiffractionOnly_v1**. Coloca aquí los archivos `DiffractionOnly_v1.bit` y `DiffractionOnly_v1.hwh` generados por Vivado/Vitis.

El notebook `diffraction_only_test.ipynb` carga el overlay, envía datos de prueba, compara la salida con una implementación en software y mide los tiempos de ejecución de ambas versiones.

Para facilitar la depuración se incluye el script `diffraction_overlay_debug.py`, el cual guarda en la carpeta `debug_data` los campos de entrada y las salidas de software y hardware en formato `.npy`.
