"""Run on Windows after building the native plugin and installing build requirements."""
from pathlib import Path
import shutil
import importlib.metadata
import json
import os
import tempfile
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent


def run(*args):
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
                    '--distpath', str(ROOT/'dist'), '--workpath', str(ROOT/'build-pyinstaller'),
                    '--specpath', str(ROOT/'build-pyinstaller'), *args], cwd=ROOT, check=True)


def collect_licenses(release):
    notices = release/'licenses'
    notices.mkdir(exist_ok=True)
    packages = []
    for distribution in importlib.metadata.distributions():
        name = distribution.metadata.get('Name', 'unknown')
        packages.append({'name': name, 'version': distribution.version})
        for item in distribution.files or []:
            if not any(word in str(item).lower() for word in ('license', 'copying', 'notice', 'copyright')):
                continue
            source = Path(distribution.locate_file(item))
            if not source.is_file():
                continue
            parts = [part for part in item.parts if part not in ('..', '.', '/', '\\')]
            target = notices/name/Path(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    (notices/'installed-distributions.json').write_text(json.dumps(sorted(packages, key=lambda p:p['name'].lower()), indent=2), encoding='utf-8')


def main():
    if sys.platform != 'win32':
        raise RuntimeError('El paquete se construye en Windows x64 con Python 3.12.')
    plugin = ROOT/'build_x64/RelWithDebInfo/kattbeauty-studio.dll'
    if not plugin.is_file():
        raise RuntimeError('Compila primero el complemento con CMake.')
    run('--onedir', '--windowed', '--name', 'KattBeautyMotor',
        '--collect-all', 'mediapipe', '--collect-all', 'cv2',
        '--runtime-hook', str(ROOT/'scripts/runtime_logging.py'),
        '--paths', str(ROOT/'motor'), str(ROOT/'motor/kattbeauty_motor_obs.py'))
    with tempfile.TemporaryDirectory() as settings:
        env=dict(os.environ,KATTBEAUTY_SETTINGS_DIR=settings)
        executable=str(ROOT/'dist/KattBeautyMotor/KattBeautyMotor.exe')
        subprocess.run([executable,'--self-test'],env=env,check=True,timeout=120)
        subprocess.run([executable,'--ui-smoke-test'],env=env,check=True,timeout=30)
    run('--onefile', '--windowed', '--name', 'Instalar_KattBeauty', str(ROOT/'installer/install.py'))
    release = ROOT/'release'
    if release.exists():
        shutil.rmtree(release)
    (release/'plugin').mkdir(parents=True)
    shutil.copytree(ROOT/'dist/KattBeautyMotor', release/'motor')
    shutil.copy2(ROOT/'dist/Instalar_KattBeauty.exe', release/'Instalar_KattBeauty.exe')
    shutil.copy2(plugin, release/'plugin'/plugin.name)
    for filename in ('LICENSE', 'THIRD_PARTY_NOTICES.md', 'requirements.txt'):
        shutil.copy2(ROOT/filename, release/filename)
    shutil.copy2(ROOT/'docs/USO.md', release/'LEEME.txt')
    collect_licenses(release)
    # Match GPL binary distribution with the corresponding source in the same release.
    with zipfile.ZipFile(release/'codigo-fuente-0.20.0.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in ROOT.rglob('*'):
            relative = path.relative_to(ROOT)
            if any(part.startswith('.') and part not in ('.github',) for part in relative.parts):
                continue
            if any(part in {'release', 'dist', 'build_x64', 'build-pyinstaller', '__pycache__', '.venv', '.deps'} or part.startswith('build_') for part in relative.parts):
                continue
            if path.is_file() and path.suffix.lower() not in {'.zip','.exe','.dll','.pdb','.pyc'}:
                archive.write(path, str(relative))
    output = ROOT/'KattBeautyStudio-0.20.0-windows-x64.zip'
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in release.rglob('*'):
            if path.is_file():
                archive.write(path, 'KattBeautyStudio/'+str(path.relative_to(release)))
    print('Paquete listo:', output)


if __name__ == '__main__':
    main()
