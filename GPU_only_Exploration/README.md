# Summary

when running GPU_Exploration notebook no GPU was listed or found.

but zynq mpsoc ultra indeed has a GPU

# Por qué no se puede usar el GPU Mali desde Python

## 1.  Falta de soporte OpenCL

El Mali‑400 MP2 no implementa OpenCL, solo soporta OpenGL ES 2.0/1.1, según ARM 
Foros y repositorios confirman que Mali‑400 solo corre OpenGL ES, sin capacidad de ejecutar kernels OpenCL 

## 2. Mesa y el driver Lima

Lima, el driver open source de Mesa para GPUs Utgard (Mali‑4xx), está upstream en Mesa 19.1 y Linux 5.2 

La imagen Ubuntu stock para KV260 carece del módulo kernel lima y de la librería propietaria Xilinx (libmali-xlnx), por lo que no expone /dev/dri/card0 ni EGL 

## 3. Plataformas OpenCL existentes
clinfo lista la plataforma “Xilinx” (OpenCL 1.0 via XRT, Device Type: Accelerator) y Mesa Clover (OpenCL 1.1) 
Mesa Clover no soporta GPUs Utgard, por lo que no incluye el Mali‑400 entre sus dispositivos 

# Mejor alternativa: aceleración con PYNQ/XRT

## 1. Diseñar y generar el bitstream
Usa Vitis o Vitis HLS para crear tu kernel en C/C++ o OpenCL y generar un archivo .xclbin listo para el PL 

## 2. Cargar el overlay en Python

```
from pynq import Overlay
overlay = Overlay("my_accelerator.xclbin")  # :contentReference[oaicite:11]{index=11}
krnl = overlay.my_kernel_0                 # IP expuesta como atributo
```

## 3. Invocar el kernel desde Python
Reserva buffers con overlay.allocate_storage().
Ejecuta y espera al kernel con krnl.process().
Lee resultados en un arreglo NumPy 
Este flujo no requiere drivers gráficos ni módulos kernel adicionales y funciona sobre la imagen Ubuntu stock del KV260.

# Referencias
1. Arm Developer Community: Mali‑400 GPU’s does not have OpenCL support Stack Overflow

2. StackOverflow: Mali‑400 only supports OpenGL ES 2.0, not OpenCL Manjaro Linux Forum

3. GitHub Issue: “No, mali 400 doesnt support opencl.” Reddit

4. Wikipedia: Mali‑400 MP – OpenGL ES compliant multi-core GPU Red Hat Customer Portal

5. Phoronix: Lima driver merged into Mesa 19.1 Phoronix

6. Mesa Docs: Lima upstreamed in Mesa 19.1 and Linux kernel 5.2 docs.mesa3d.org

7. Xilinx Wiki: driver MALI 400MP consiste en kernel driver y librería propietaria Xilinx Wiki

8. GitHub (linux-xlnx): kernel de Xilinx no incluye módulo lima en drivers/gpu/drm GitHub

9. Adaptive Support (Xilinx): Mali400 en ZCU102 no soporta OpenCL GitHub

10. PYNQ Docs: Overview del Overlay PYNQ

11. PYNQ Forum: The Overlay class – objetos Python dinámicos PYNQ



---


## Tutorial: Crear una imagen PetaLinux personalizada en Windows para Kria KV260

Este tutorial explica paso a paso cómo, desde una máquina Windows, generar una **imagen Linux personalizada** que incluya el controlador Mali (libmali-xlnx) para la Kria KV260 y le permita exponer la GPU Mali-400 MP2. Se basa en **WSL2** + **PetaLinux Tools**, sin necesidad de rehacer la imagen de Ubuntu de forma manual. Los pasos incluyen instalación de herramientas, descarga del BSP, configuración de rootfs y construcción de la imagen final.

---

## Prerrequisitos

- **Windows 10/11** con soporte de virtualización y WSL2 habilitado ([doayee.co.uk](https://doayee.co.uk/petalinux-on-windows-via-wsl-and-git/?utm_source=chatgpt.com)).
- **WSL2** con Ubuntu 20.04 o 22.04 instalado desde Microsoft Store ([Centennial Software Solutions](https://www.centennialsoftwaresolutions.com/post/install-petalinux-tools-2023-1-on-wsl2-running-on-windows-10-build-and-run-the-vck190-bsp-on-qemu?utm_source=chatgpt.com)).
- **Espacio en disco**: al menos 100 GB para PetaLinux, Vivado/Vitis y cache de compilación .
- **Cuenta y credenciales** en [Xilinx Downloads](https://www.xilinx.com) para acceder a **PetaLinux Tools** y **KV260 BSP** ([AMD](https://www.xilinx.com/support/download/index.html/content/xilinx/en/downloadNav/embedded-design-tools.html?utm_source=chatgpt.com)).
- **Licencias**: Vivado/Vitis y PetaLinux Tools (pueden usar licencias de evaluación o de sitio) .

---

## 1. Configurar WSL2 en Windows

1. Abre **PowerShell** como Administrador y habilita WSL:
   ```powershell
   wsl --install
   ```
   Esto instalará WSL2 y Ubuntu 22.04 por defecto ([Centennial Software Solutions](https://www.centennialsoftwaresolutions.com/post/install-petalinux-tools-2023-1-on-wsl2-running-on-windows-10-build-and-run-the-vck190-bsp-on-qemu?utm_source=chatgpt.com)).
2. Reinicia Windows.
3. Inicia Ubuntu desde el menú Inicio y crea tu usuario local.

---

## 2. Instalar dependencias en Ubuntu (WSL2)

En la terminal de Ubuntu, ejecuta:

```bash
sudo apt update
sudo apt install -y \
  iproute2 gcc g++ make net-tools diffstat \
  chrpath socat xterm autoconf automake texinfo \
  libtool libglib2.0-dev libarchive-dev \
  python3 python3-pip python3-pexpect \

  python3-crypto wget diffstat vim \
  libncurses5-dev zlib1g-dev libssl-dev
```

Estos paquetes son requeridos por PetaLinux Tools para compilar y ensamblar kernels, device trees y rootfs .

---

## 3. Descargar e instalar PetaLinux Tools

1. Desde tu navegador Windows, **descarga** la versión de PetaLinux Tools (por ejemplo, 2023.2) en tu carpeta de usuario ([AMD](https://www.xilinx.com/support/download/index.html/content/xilinx/en/downloadNav/embedded-design-tools.html?utm_source=chatgpt.com)).
2. En WSL, copia el instalador al entorno:
   ```bash
   mkdir ~/petalinux
   cp /mnt/c/Users/<tu_usuario>/Downloads/petalinux-v2023.2-final-installer.run ~/petalinux/
   cd ~/petalinux
   chmod +x petalinux-v2023.2-final-installer.run
   ./petalinux-v2023.2-final-installer.run
   ```
3. Acepta el EULA y completa la instalación en `~/petalinux/2023.2` ([doayee.co.uk](https://doayee.co.uk/petalinux-on-windows-via-wsl-and-git/?utm_source=chatgpt.com)).

---

## 4. Descargar el BSP de Kria KV260

1. Accede al **Download Center** de Xilinx y ve a **Embedded Design Tools → Kria KV260 Starter Kit BSP** ([AMD](https://www.xilinx.com/support/download/index.html/content/xilinx/en/downloadNav/embedded-design-tools.html?utm_source=chatgpt.com)).
2. Descarga `kv260_v2023.2_bsp.tar.gz` (\~1.9 GB) y guarda en `~/petalinux/`
3. Extrae el BSP:
   ```bash
   cd ~/petalinux
   tar -xvf kv260_v2023.2_bsp.tar.gz
   ```

---

## 5. Crear y configurar el proyecto PetaLinux

```bash
# Carga las variables de entorno de PetaLinux
source ~/petalinux/2023.2/settings.sh

# Crea el proyecto usando el BSP descargado
petalinux-create -t project --name kv260_custom --bsp ~/petalinux/kv260_v2023.2

cd kv260_custom
```

Esto genera la estructura de tu proyecto basada en el SoM K26 y board KV260 ([Xilinx](https://xilinx.github.io/kria-apps-docs/kv260/2021.1/build/html/docs/build_petalinux.html?utm_source=chatgpt.com)).

---

## 6. Habilitar libmali-xlnx en rootfs

```bash
petalinux-config -c rootfs
```

En el menú **Filesystem Packages → libs**:

- **Selecciona** `libmali-xlnx` (controlador Mali propietario de Xilinx) ([Xilinx Wiki](https://xilinx-wiki.atlassian.net/wiki/spaces/A/pages/18841928/Xilinx%2BMALI%2Bdriver?utm_source=chatgpt.com)).
- Elige el **backend X11** y **libmali-xlnx-dev** si quieres headers.
- Marca `packagegroup-petalinux-matchbox` para un window manager ligero (opcional).

Guarda y sal (`Exit`).

---

## 7. Configurar el kernel y device tree

```bash
petalinux-config -c kernel
```

- Activa en **Device Drivers → Graphics support → GPU driver support** el módulo **DRM/KMS** (Mali) si está disponible.
- En **Device Tree → System-on-Chip Tree Settings**, marca el nodo **arm,mali-400** como `status = "okay"`.

Guarda y sal.

---

## 8. Construir la imagen completa

```bash
petalinux-build
```

Este comando compila el kernel, el device tree, el rootfs y genera un **image.ub** listo para boot ([Xilinx](https://xilinx.github.io/kria-apps-docs/kv260/2021.1/build/html/docs/build_petalinux.html?utm_source=chatgpt.com)).

---

## 9. Empaquetar para SD card

```bash
petalinux-package --boot --fpga --u-boot --kernel
```

Obtendrás **BOOT.BIN** y **image.ub** en `images/linux/`. Copia estos archivos y el rootfs (`rootfs.cpio.gz` si lo usas directo) a tu tarjeta SD:

1. Partición FAT32: `BOOT.BIN`, `image.ub`.
2. Partición ext4 (raíz): descomprime `rootfs` o usa un wic image.

---

## 10. Probar en la KV260

1. Inserta la SD en la **KV260** y enciéndela.
2. Conéctate por UART o SSH y, tras el arranque, verifica:
   ```bash
   glxinfo | grep "OpenGL renderer"
   ```
   Debería devolver algo similar a `Mali-400 MP` si todo está activo.

---

## Próximos pasos

- **Verificar** con un simple ejemplo Python/EGL (ver tutorial headless).
- **Personalizar** tu rootfs instalando paquetes adicionales (Python, OpenCV, PYNQ).
- **Automatizar** el build con scripts en Windows para regenerar la imagen tras cambios.

Con estos pasos podrás construir desde Windows una **imagen PetaLinux personalizada** que habilite el GPU Mali de la Kria KV260 para su uso desde Python o cualquier otra aplicación gráfica.
