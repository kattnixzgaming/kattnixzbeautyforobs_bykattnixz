# Créditos y dependencias

KattBeauty Studio es un proyecto de Kattnixz y colaboradores. El código propio se ofrece bajo GPL-2.0-or-later; véase LICENSE. Conserva los avisos de cada componente.

## Infraestructura de OBS

El sistema de compilación deriva de [obsproject/obs-plugintemplate](https://github.com/obsproject/obs-plugintemplate), revisión `3e7d7ac3b5342cd7d9b88890b9c70b472d1520fc`, con su licencia GPL y avisos originales. [OBS Studio/libobs](https://github.com/obsproject/obs-studio) es una dependencia externa. El paquete no contiene la aplicación OBS completa.

## Motor Python

| Componente | Versión directa | Licencia principal / avisos |
| --- | --- | --- |
| Python | 3.12 | PSF; https://docs.python.org/3/license.html |
| MediaPipe | 0.10.21 | Apache-2.0; https://github.com/google-ai-edge/mediapipe |
| opencv-contrib-python | 4.11.0.86 | Avisos del empaquetado y OpenCV Apache-2.0; https://github.com/opencv/opencv-python |
| NumPy | 1.26.4 | BSD-3-Clause y avisos de bibliotecas incluidas; https://github.com/numpy/numpy |
| PyInstaller | 6.11.1, herramienta de build | GPL con excepción para distribuir los paquetes generados; https://pyinstaller.org/ |

Estas son dependencias directas, no un inventario completo del binario. MediaPipe y los hooks de empaquetado pueden añadir dependencias transitivas. El script de distribución exporta los textos de licencia disponibles en los paquetes instalados a `licenses/`; revisa también los avisos que acompañan a los archivos incluidos por PyInstaller. Las licencias de terceros no se sustituyen por la licencia del proyecto.

## Texturas y referencias

Las tres texturas de pestañas incluidas en el atlas embebido se generaron con IA para este proyecto. Se autoriza su uso y redistribución como parte de KattBeauty bajo los mismos términos que el proyecto en la medida en que existan derechos aplicables. Las fotos y capturas personales usadas como referencias no forman parte del repositorio.

No se incluyen modelos ni recursos extraídos de TikTok o BeautyCam. Los nombres solo describen referencias visuales. No existe afiliación con esas empresas.

## NVIDIA

No se distribuye NVIDIA Broadcast ni el Video Effects SDK. La eliminación de fondo es una función externa opcional que el usuario instala bajo sus términos y requisitos propios.
