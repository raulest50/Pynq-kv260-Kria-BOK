# Array Gain Overlay | Ejemplo 3

En este ejemplo se muestra como comunicarse con overlay desde el ps. En este caso los registros de control se manejan
por medio de la interfaz axi lite (que es una interfaz ligera) de la misma forma que en los ejemplos anteriores,
adder overlay test y scalar multiplier test.

Para el envio de arrays la interfaz axi lite ya no es la mas indicada. Para esto es mejor precisar de las interfaces
axi stream o de la interfaz axi4 completa (la interfaz axi lite es una version minimalista de axi4). 
Para la comunicacion por axi4 se debe agregar un puerto axi slave ademas del que ya se tiene para el axi interconnect.

en este ejemplo se bisca ilustrar como es el envio y recepcion de datos por axi4 mientras al mismo tiempo se tiene
presente que el tipo de dato tambien es importante (como se ilustra en el ejemplo del scalar multiplier), en este caso float32.

<img src="" width='70' />