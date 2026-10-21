# Estado de validación — 0.20.0

La autora probó y aprobó la versión de desarrollo con panel en OBS Steam 32.2.2 en Windows x64. La base anterior también se probó con Disney Dreamlight Valley y stream, en un equipo con RTX 5060 y Ryzen 7. Eso no equivale a una medición formal de rendimiento o a compatibilidad universal.

El repositorio público pasó **17 pruebas automatizadas**, incluidas **441 combinaciones de renderizado**. Se comprobaron afinado uniforme, posición del delineado, deformación nasal localizada, variantes de pestañas, normalización de ajustes, cola de un fotograma, arranque del panel mediante el módulo de entrada, salida limpia hacia OBS, protocolo BGRA/orientación/frescura y respaldo/restauración del instalador.

La sintaxis Python y el YAML del workflow se comprobaron. Aquí no se ejecutaron la nueva compilación nativa de Windows, PyInstaller, UAC ni el instalador público sobre una cámara real. El workflow de Windows incluye carga de modelos/texturas y apertura/cierre del panel empaquetado; la prueba de aceptación con OBS se hace después.

Antes de distribuir un binario, completa la lista de `BUILD.md` y publica como beta/pre-release mientras se amplía la validación.
