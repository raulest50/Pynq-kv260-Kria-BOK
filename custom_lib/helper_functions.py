"""
Módulo custom_lib.helper_functions
-----------------------------------
Este módulo proporciona funciones auxiliares para convertir números de punto flotante 
(32 bits) a su representación en entero sin signo (32 bits) y viceversa, lo que es útil 
al interactuar con registros de hardware a través de AXI en PYNQ.

Funciones disponibles:
    - float_to_uint32: Convierte un float32 a su representación en entero sin signo de 32 bits.
    - uint32_to_float: Convierte un entero sin signo de 32 bits a su valor float32.
"""

import numpy as np


def float_to_uint32(f):
    """
    Convierte un número de punto flotante de 32 bits a su representación en entero sin signo de 32 bits.

    Parámetros:
      f (float): Número de punto flotante que se convertirá a float32 y luego se interpretará
                 como un entero de 32 bits en formato IEEE 754.

    Retorna:
      int: Valor entero de 32 bits que representa el número float32.
    
    Ejemplo:
      >>> float_to_uint32(2.0)
      1073741824
    """
    return int(np.frombuffer(np.float32(f).tobytes(), dtype=np.uint32)[0])


def uint32_to_float(u):
    """
    Convierte un entero sin signo de 32 bits a su valor de punto flotante de 32 bits.

    Parámetros:
      u (int): Valor entero de 32 bits que representa un número float32 en formato IEEE 754.

    Retorna:
      float: El número de punto flotante de 32 bits correspondiente.
    
    Ejemplo:
      >>> uint32_to_float(1073741824)
      2.0
    """
    return np.frombuffer(np.uint32(u).tobytes(), dtype=np.float32)[0]