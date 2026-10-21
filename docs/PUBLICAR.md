# Subir a GitHub y preparar la primera publicación

## Repositorio

Nombre sugerido: **KattBeautyStudio**.

Descripción para copiar:

> Maquillaje local para OBS con panel visual: nueve pupilentes, delineados, pestañas, afinado uniforme y ajustes nasales. Gratis y sin marca de agua. Beta Windows x64.

Temas sugeridos: `obs-studio`, `obs-plugin`, `makeup`, `face-mesh`, `mediapipe`, `windows`.

1. Crea un repositorio vacío en tu cuenta de GitHub. No añadas otro README, licencia ni .gitignore: ya están incluidos.
2. Extrae el ZIP del repositorio en una carpeta nueva. No lo mezcles con el proyecto que tienes funcionando en tu PC.
3. Desde esa carpeta, ejecuta los siguientes comandos. Sustituye únicamente `TU_USUARIO` por tu usuario real de GitHub:

```bat
git init
git add .
git commit -m "Initial KattBeauty Studio public beta"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/KattBeautyStudio.git
git push -u origin main
```

GitHub puede pedir iniciar sesión. No pongas contraseñas ni tokens en archivos del repositorio.

## Crear el instalador con GitHub Actions

1. Abre **Actions → Build Windows package → Run workflow**.
2. Espera a que termine. Si falla, abre el primer paso rojo y comparte el error; no publiques un binario de una compilación fallida.
3. Descarga el artefacto `KattBeautyStudio-windows-x64`. Dentro estará el ZIP para usuarios.
4. Prueba el paquete siguiendo `BUILD.md`, idealmente también en un Windows sin Python ni Visual Studio.
5. Crea una Release con etiqueta **v0.20.0**, título **KattBeauty Studio 0.20.0 — Beta con panel visual**, marcada como **pre-release**.
6. Adjunta el ZIP compilado completo y copia las notas de `RELEASE_NOTES.md`. Mantén el código fuente correspondiente disponible.

El workflow no publica una Release ni modifica tu repositorio automáticamente. Su artefacto puede caducar según la retención de GitHub: adjunta el ZIP a la Release para distribuirlo de forma estable.

## Qué ya se probó y qué falta

La autora aprobó la versión de desarrollo 0.20 con panel visual en OBS Steam 32.2.2. La base anterior se probó también con Disney Dreamlight Valley y stream. Eso no certifica el nuevo empaquetado público.

Antes de anunciar «descarga e instala», verifica en Windows el nuevo nombre de DLL, el instalador de ruta seleccionable, el motor congelado y la migración del complemento anterior. No se incluyen binarios precompilados en este ZIP de repositorio.
