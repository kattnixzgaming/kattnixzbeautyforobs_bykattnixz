# Compilar en Windows x64

## Requisitos de desarrollo

- Git, Python **3.12 x64** y CMake 3.30 o superior.
- Visual Studio con **Desarrollo para el escritorio con C++**, compilador MSVC x64 y Windows SDK. El workflow usa Visual Studio 2022; la autora usó Visual Studio 2026.
- Conexión para descargar dependencias durante la primera compilación. El motor no necesita conexión para procesar vídeo después de instalarse.

Desde una terminal en la raíz del repositorio:

```bat
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Con Visual Studio 2022:

```bat
cmake --preset windows-x64 -G "Visual Studio 17 2022" -A x64 -DENABLE_QT=OFF -DENABLE_FRONTEND_API=OFF
cmake --build build_x64 --config RelWithDebInfo --parallel
```

Con Visual Studio 2026, usa `-G "Visual Studio 18 2026"`. No cambies de generador sobre la misma carpeta de compilación: usa una carpeta nueva o limpia la anterior si sabes que no contiene archivos propios.

La primera configuración descarga libobs 31.1.1 y obs-deps con los hashes declarados en `buildspec.json`. Esto es el SDK de compilación; no instala ni sustituye tu aplicación OBS.

Para empaquetar el motor, el instalador y el código correspondiente:

```bat
.venv\Scripts\python.exe scripts\build_release.py
```

El script ejecuta PyInstaller, comprueba que el motor empaquetado pueda cargar el modelo facial y las seis texturas, abre/cierra el panel sin cámara, y genera `KattBeautyStudio-0.20.0-windows-x64.zip`. El paquete incluye el motor completo; no repartas solo su EXE ni solo el instalador. PyInstaller debe conservar sus dependencias y modelos.

## Prueba de aceptación antes de publicar

1. Instala en Windows x64 con OBS cerrado. Prueba una instalación convencional y otra Steam si están disponibles.
2. Comprueba el arranque automático desde una cámara real y que OBS conserve la cámara abierta.
3. Cambia ojos, delineados, pestañas, nariz y labios desde el panel; cierra y abre OBS para comprobar los ajustes.
4. Comprueba que no aparezcan los textos del motor en la salida de OBS.
5. Usa el menú Cerrar motor: la cámara debe volver al vídeo sin maquillaje. La X solo minimiza el panel. Reinicia OBS para recuperar el motor.
6. Cierra OBS: no debe quedar el motor iniciado por el filtro. Comprueba que el motor no parpadea durante pausas normales entre fotogramas.
7. Mide con juego y grabación/transmisión; no extrapoles resultados de un equipo a todos.
8. Prueba respaldo, actualización y restauración. Anota las versiones exactas de Windows y OBS.

La prueba automatizada del modelo empaquetado no demuestra compatibilidad con una cámara ni con OBS. Hasta completar estos pasos, etiqueta el paquete como **beta / pre-release**.

## Estructura

- `src/`: filtros nativos y arranque del motor.
- `motor/`: maquillaje y transporte local; el atlas de pestañas está embebido.
- `installer/`: instalación de binarios; no requiere compilar en el equipo del usuario final.
- `scripts/`: empaquetado y registro de errores.
- `tests/`: protocolo, vista previa y operaciones del instalador.
- `.github/workflows/build-windows.yml`: compilación manual o por etiqueta y artefacto descargable.

## Límites de la distribución

El instalador no está firmado digitalmente. La firma de código requiere un certificado que este repositorio no incluye. No anuncies el paquete como aprobado por Microsoft ni prometas ausencia de alertas.

Revisa las licencias de los componentes efectivamente incluidos por PyInstaller antes de distribuir los binarios. Mantén los avisos de dependencias y el código fuente de esta versión junto con la publicación.
