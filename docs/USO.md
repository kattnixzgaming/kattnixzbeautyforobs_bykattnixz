# KattBeauty Studio 0.20.0 — Uso

## Instalación

Descarga el ZIP compilado de Windows desde Releases, extrae todo y cierra OBS. Ejecuta `Instalar_KattBeauty.exe`. Selecciona la carpeta principal de OBS; puede ser una instalación convencional, portable o Steam, siempre que contenga `bin/64bit/obs64.exe` y `obs-plugins/64bit`.

El instalador copia `kattbeauty-studio.dll` a `obs-plugins/64bit` y el motor a `%LOCALAPPDATA%\KattBeautyStudio\runtime`. La configuración de arranque queda en `%LOCALAPPDATA%\KattBeauty\motor-path.txt`. La instalación es para la cuenta de Windows que instala.

Agrega **KattBeauty - Maquillaje OBS** directamente a tu cámara, en la sección superior de Filtros de audio/vídeo. Usa una sola instancia. El panel se abre al cargar el filtro. OBS conserva el acceso físico a la cámara.

El complemento gráfico **KattBeauty Studio - Belleza** es opcional y se agrega en la sección inferior de Filtros de efecto. Sus controles de suavizado, brillo, contraste y saturación se ajustan dentro de OBS.

## Panel

| Sección | Controles |
| --- | --- |
| Rostro | Afinado uniforme, sombra, rubor, intensidad general y labios carmesí |
| Nariz | Proyección de perfil, ancho de alas/punta, elevación y contorno con sombra/luz |
| Ojos | Nueve colores e intensidad de pupilentes |
| Delineado | Siete estilos, grosor, intensidad, posición general/por ojo, altura y largo de cola |
| Pestañas | Seis opciones, intensidad y largo |

Las páginas tienen desplazamiento si los controles no caben. **Natural, Stream y Glam** aplican puntos de partida. **Guardar perfil** exporta los ajustes a JSON; **Cargar perfil** los valida y aplica. **Restablecer** pide confirmación antes de volver a los valores iniciales.

Los cambios se guardan automáticamente en `%LOCALAPPDATA%\KattBeautyStudio\ajustes.json`. El registro del motor empaquetado queda en `motor.log` en esa carpeta y se renueva al iniciar.

**Comparar con original** afecta tanto la vista previa como la imagen enviada a OBS. Desactivar **Vista previa** pausa solo la imagen del panel; el maquillaje sigue activo en OBS. La **X minimiza** el panel, sin apagar el motor. Para cerrarlo usa el menú **Cerrar motor**; reinicia OBS si quieres volver a iniciarlo. Al salir de OBS se cierra el motor que el complemento inició.

## Ajustes recomendados para empezar

- Cámara a 640 × 480 y perfil Natural.
- Afinado uniforme a 10–20 %. Reduce frente, pómulos y mandíbula de manera pareja; también estrecha algo los ojos.
- Nariz: usa valores bajos primero. El contorno es maquillaje; los otros controles deforman localmente el vídeo en 2D. En perfiles extremos puede fallar.
- Delineado: un valor positivo en **Bajar delineado** lo baja. La altura de cola positiva la eleva y la negativa la baja. Los ajustes extra de ojo 1/2 son independientes.
- Los pupilentes preservan pupila y reflejos; el resultado depende de tu iris e iluminación.
- Las seis pestañas incluyen tres texturas originales y tres variantes: Foxy suave, Wispy densa y Volumen suave. El delineado se compone debajo de las pestañas.

## Problemas

**No aparece el filtro:** reinicia OBS, revisa que elegiste su carpeta correcta y busca en la sección superior sobre la cámara. Consulta Ayuda → Archivos de registro.

**El panel espera imagen:** deja visible una escena con la cámara. No agregues el filtro a una captura de juego, un grupo o una escena completa.

**El motor falla:** consulta `motor.log`. El panel puede seguir abierto y mostrar el error aunque el trabajador de vídeo se haya detenido. Reinicia OBS después de corregirlo.

**Pérdida de fluidez:** baja la resolución, pausa la vista previa y compara consumo/Estadísticas de OBS con los efectos activados y desactivados. Pausar la vista previa no detiene el procesado.

**Versión de desarrollo antigua:** el instalador respalda y retira `plugintemplate-for-obs.dll` solo si contiene el identificador de KattBeauty, evitando dos complementos con los mismos filtros. No modifica SkinSoft ni otros plugins. Para conservar ajustes antiguos, exporta un perfil si ya usabas el panel, o importa su JSON desde Cargar perfil.

## Desinstalar o restaurar

Cierra OBS. `%LOCALAPPDATA%\KattBeautyStudio\instalacion.json` contiene las rutas de OBS, runtime y respaldo. Elimina únicamente `kattbeauty-studio.dll` de `obs-plugins/64bit` y el filtro de la cámara. Puedes borrar el runtime que ya no utilices.

Para volver a una versión anterior, restaura la DLL y, si existe en el respaldo, `motor-path.txt`. Los ajustes y perfiles se conservan salvo que los borres. El instalador no limpia automáticamente respaldos ni runtimes anteriores.
