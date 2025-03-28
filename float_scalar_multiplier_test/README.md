# Multiplier Overlay

El proposito de este overlay es comprobar 2 cosas. la primera el especial cuidado
que se debe tener a la hora de enviar floats (ieee 754). ya que al final de cuentas
por pynq se envian bits, asi que si se envia numeros planos como 5 o 2, python
asigna un tipo por defecto pero el overleay retornara 0 como si no estuviera funcionando.

lo segundo es poder alternar entre fragmentos de codigo del adder y del multiplicador
para comprobar que en efecto el PL cambia. es decir, que si se programa el adder overlay 
y luego se corre el fragmento de codigo para el multiplier se deben obtener valores raros
que no correspondan a la multiplicaicon y viceversa.