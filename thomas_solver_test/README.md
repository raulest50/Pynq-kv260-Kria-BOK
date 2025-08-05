# Test para Overlay Thomas Solver

Este es un solver para una matriz tridiagonal con el vector x[64], soporta vlaores complejos.

la matriz se modela con 4 constantes, dp representa los valores de la diagonal principal excepto los valores m[1][1] y m[64][64] (donde m representa la matriz solo en este readme)
ya que los valores de la diagonal principal en en las esquinas esta representado por dp1 y dp2 respectivamente. los valores de las offsediagonals esta representado por do.
de esta forma se ahorra espacio al no representar la matriz como un arreglo multidimensional sino como un set de constantes, aprovechando la estructura simple y simetrica de la matriz.

el overlay recive las constantes que representan la matriz y el vector b, tambien de size 64 y retorna x, que es la solucion del sistema. basicamente implementa linsolve en la FPGA fabric