# complex array convolution test

In this demo, we want to show how to send 2 complex arrays ans read the convolution result. 
The kernel implements convolution, so it is also done within the notebook to compare both results.
the arrays are send and read using again axi4 protocol.

there is many ways to use complex data type within hls kernel. the latest and most recomende is with

```
#include <hls_x_complex.h>
```

and 

```
hls::x_complex<float> 
```

---

but it is possible to use the std library also.

some code in the internet also use 
```
#include <complex>
```

and some others use 
```
#include <hls_complex.h>
```
but the later is supposed to be the old one way.


El test con el jupyter notebook funciono perfectamente.