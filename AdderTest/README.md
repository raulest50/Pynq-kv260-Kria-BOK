# Adder Overleay

este es el hola mundo de pynq. se puede ver como se usa la interfaz axi lite que es la mas sensilla.
para enviar y leer los datos, a la hora de crear el kernel en vitis, en la sintesis, muestran
la direccion de los registros a, b y c. sin embargo, usando la api de pynq se puede usar
register_map para acceder a las entradas y las salidas sin saber explicitamente estas direcciones.

tambien es importante de este ejemplo observar la necesidad de la linea:
addk.register_map.CTRL.AP_START = 1 # inportante, para indicar al kernel que comience a procesar
para iniciar el kernel.
