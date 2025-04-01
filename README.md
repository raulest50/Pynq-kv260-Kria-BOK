# Proyectos Pynq 

## Objetivo del repositorio
Guardar scripts de referencia para recordar como usar las diferentes caracteriticas y funcionalidades de pynq
ya que la documentacion y ejemplos es muy escasa y la interacion de la libreria con el PL puede ser muy
compleja.

## Creacion de los Overlays
el main.tcl se corre en la desktop machine (devm de ahora en adelante).

```
source .\scripts\main.tcl
```

la devm debe tener la suite full con vivado y vitis. Con vivado se recrea con source command usando
tcl command line de vivado el proyecto (el cual es una plataforma extensible). luego con vitis unified suite
se deben crear los kernels (como plataforma se puede seleccionar la extensible, para las funciones
de sintesis y packaging). luego el ip se debe importar nuevamente en vivado para conectar y hacer
la implementacion completa para generar bitstream y hwh.

un overlay consiste de un archivo .bit que es la informacion que usa pynq para programar el fpga fabric
y un archivo hwh, que contiene la informacion de hardware que pynq necesita para saber como esta constituido
el hardware, ip's registros, clocks, interrupciones etcetera


## Hacer respaldo de un proyecto de vivado (Overlay Hardware)



```
write_project_tcl -force ../scripts/main.tcl
```

organizar el proyect folder para que se vea asi:

```
./ 
├── scripts/ 
│    └── main.tcl 
└── ip/ 
     └── [Packaged HLS IP files and folders] 
```