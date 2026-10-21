# KattBeauty Studio

**Maquillaje local para OBS con panel visual, gratis y sin marca de agua.** Creado por **Kattnixz**.

Versión **0.20.0 · Beta · Windows x64**. La versión de desarrollo con panel fue probada y aprobada por la autora en OBS Steam 32.2.2. El nuevo instalador público debe validarse por separado antes de publicar binarios.

## Funciones

- Panel con botones y barras: Rostro, Nariz, Ojos, Delineado y Pestañas.
- Afinado horizontal uniforme de frente, pómulos y mandíbula.
- Contorno nasal, ajuste de proyección al girar, ancho de alas/punta y elevación de punta.
- Nueve pupilentes: verde, azul, olivo, azul grisáceo, avellana, miel, gris plata, jade y café.
- Siete delineados con controles de grosor, intensidad, posición por ojo y altura/largo de la cola.
- Seis opciones de pestañas: tres texturas y tres variantes de esas texturas.
- Labios carmesí, sombra y rubor.
- Perfiles Natural, Stream y Glam; exportación/importación JSON y guardado automático.
- Inicio del motor al cargar el filtro y cierre al salir de OBS.
- Suavizado, brillo, contraste y saturación mediante el filtro gráfico nativo de belleza.

El motor recibe los fotogramas de OBS por memoria compartida local: **no abre otra vez la webcam**. No incorpora telemetría ni subida de imágenes. No guarda fotografías o vídeos.

## Instalar y usar

Necesitas **Windows x64 y OBS Studio x64**. Empieza con la cámara a **640 × 480**.

1. Descarga el ZIP **compilado de Windows** en **Releases**, cuando haya una publicación. `Code → Download ZIP` descarga el código fuente, que no incluye ejecutables.
2. Extrae todo el paquete y cierra OBS.
3. Abre `Instalar_KattBeauty.exe` y selecciona la carpeta principal de OBS, que contiene `bin` y `obs-plugins`. Acepta el permiso de Windows si lo solicita.
4. En OBS, abre **Filtros** directamente sobre tu cámara.
5. En la sección superior **Filtros de audio/vídeo**, agrega **KattBeauty - Maquillaje OBS**. Usa una sola instancia.
6. Opcional: agrega **KattBeauty Studio - Belleza** en la sección inferior **Filtros de efecto**, para ajustar suavizado, brillo, contraste y saturación.

El panel se abre con el filtro. Empieza con **Natural** y ajusta con el ratón; ya no necesitas memorizar teclas. La **X minimiza el panel** y el motor continúa procesando. **Comparar con original también cambia la salida de OBS**.

[Uso del panel e instalación](docs/USO.md) · [Compilar](docs/BUILD.md) · [Publicar en GitHub](docs/PUBLICAR.md) · [Estado de pruebas](docs/VALIDACION.md)

## Requisitos y límites

El maquillaje y el seguimiento usan **CPU**; no requieren una RTX. Windows x64, una cámara y un rostro. Máximo 1920 × 1080; no se garantiza 30 FPS, consumo fijo o compatibilidad con cualquier cámara/versión de OBS. No se ha validado HDR.

Los ajustes de forma son aproximaciones **2D**, no una reconstrucción facial 3D. En perfiles extremos, poca luz u oclusiones pueden desalinearse. El afinado uniforme también estrecha ligeramente los ojos. Empieza con valores bajos.

La eliminación de fondo **no forma parte de este proyecto**. Puede combinarse con un filtro externo compatible, como el de NVIDIA instalado por separado. No incluimos ni redistribuimos NVIDIA Broadcast ni su SDK.

## Desarrollo

Python 3.12 x64, Tkinter, MediaPipe 0.10.21, OpenCV 4.11.0.86 y NumPy 1.26.4. El motor y sus modelos se empaquetan para que el usuario del ZIP compilado no necesite instalar Python o Visual Studio.

En **Actions → Build Windows package → Run workflow**, GitHub puede compilar la DLL, empaquetar el motor y generar el ZIP de Windows. El resultado queda como artefacto descargable; no se publica automáticamente una Release. Hay pruebas de carga de modelos y apertura/cierre del panel empaquetado. Las pruebas con cámara y stream se realizan aparte.

## Licencia y créditos

Código propio: **GPL-2.0-or-later**. [LICENSE](LICENSE) · [Avisos de terceros](THIRD_PARTY_NOTICES.md).

La infraestructura de compilación deriva del template oficial de OBS. Las pestañas usan un atlas generado con IA. No se distribuyen fotos personales ni las imágenes comerciales usadas como referencias. No es un producto oficial de OBS, NVIDIA, TikTok o BeautyCam.
