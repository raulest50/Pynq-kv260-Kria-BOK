# Proyectos Pynq 

el main.tcl se corre en la desktop machine (devm de ahora en adelante).
la devm debe tener la suite full con vivado y vitis. Con vivado se recrea con source command usando
tcl el proyecto, el cual es una plataforma extensible. luego con vitis unified suite
se deben crear los kernels (como plataforma se puede seleccionar la extensible, para las funciones
de sintesis y packaging). luego el ip se debe importar nuevamente en vivado para conectar y hacer
la implementacion completa para generar bitstream y hwh.