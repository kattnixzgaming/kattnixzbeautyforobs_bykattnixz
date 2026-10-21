"""Windows installer entry point; bundled releases need no external Python."""
from pathlib import Path
import ctypes
import datetime
import json
import os
import shutil
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

DLL = 'kattbeauty-studio.dll'
VERSION = '0.20.0'


def obs_running():
    result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq obs64.exe', '/NH'],
                            capture_output=True, text=True, errors='replace',
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    return 'obs64.exe' in result.stdout.lower()


def validate_obs(folder):
    folder = Path(folder).resolve()
    if not (folder/'bin/64bit/obs64.exe').is_file() or not (folder/'obs-plugins/64bit').is_dir():
        raise ValueError('Selecciona la carpeta principal de OBS, no bin ni obs-plugins.')
    return folder


def commit(source, obs, backup):
    if obs_running():
        raise RuntimeError('Cierra OBS antes de instalar.')
    obs = validate_obs(obs)
    source, backup = Path(source).resolve(), Path(backup).resolve()
    if source.name != DLL or not source.is_file():
        raise ValueError('Falta la DLL compilada del paquete.')
    target = obs/'obs-plugins/64bit'/DLL
    legacy = target.with_name('plugintemplate-for-obs.dll')
    backup.mkdir(parents=True, exist_ok=True)
    changed = []
    try:
        if target.exists():
            shutil.copy2(target, backup/DLL)
        if legacy.exists() and b'kattbeauty_studio_filter' in legacy.read_bytes():
            shutil.copy2(legacy, backup/legacy.name)
            legacy.unlink()
            changed.append(legacy)
        changed.append(target)
        shutil.copy2(source, target)
    except Exception:
        for dest in reversed(changed):
            previous = backup/dest.name
            if previous.exists():
                shutil.copy2(previous, dest)
            elif dest == target and dest.exists():
                dest.unlink()
        raise


def install():
    ui = tk.Tk(); ui.withdraw()
    if obs_running():
        raise RuntimeError('Cierra OBS y vuelve a abrir este instalador.')
    package = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent/'release'
    motor = package/'motor/KattBeautyMotor.exe'
    source = package/'plugin'/DLL
    if not motor.is_file() or not source.is_file():
        raise RuntimeError('Usa el ZIP compilado completo: extraelo antes de ejecutar el instalador. El ZIP del codigo fuente no incluye binarios.')
    defaults = [Path(os.environ.get('ProgramFiles', r'C:\Program Files'))/'obs-studio',
                Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'))/'Steam/steamapps/common/OBS Studio']
    initial = next((x for x in defaults if (x/'bin/64bit/obs64.exe').exists()), Path.home())
    selected = filedialog.askdirectory(title='Selecciona la carpeta principal de OBS (contiene bin y obs-plugins)', initialdir=str(initial))
    if not selected:
        return
    obs = validate_obs(selected)
    base = Path(os.environ['LOCALAPPDATA'])/'KattBeautyStudio'
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    runtime = base/'runtime'/stamp
    backup = base/'backups'/stamp
    runtime.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(package/'motor', runtime)
    try:
        commit(source, obs, backup)
    except PermissionError:
        env = os.environ.copy()
        env.update(KB_SETUP=sys.executable, KB_SOURCE=str(source), KB_OBS=str(obs), KB_BACKUP=str(backup))
        # Start-Process takes one quoted argument string, not shell-expanded paths.
        if getattr(sys, 'frozen', False):
            env['KB_ENTRY'] = ''
        else:
            env['KB_ENTRY'] = str(Path(__file__).resolve())
        command = '''$a = '--commit "' + $env:KB_SOURCE + '" "' + $env:KB_OBS + '" "' + $env:KB_BACKUP + '"'; if ($env:KB_ENTRY) {$a = '"' + $env:KB_ENTRY + '" ' + $a}; $p = Start-Process -FilePath $env:KB_SETUP -ArgumentList $a -Verb RunAs -Wait -PassThru; exit $p.ExitCode'''
        result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', command], env=env)
        if result.returncode:
            raise RuntimeError('No se completo la copia con permisos. No abras OBS hasta revisar el mensaje anterior.')
    config = Path(os.environ['LOCALAPPDATA'])/'KattBeauty/motor-path.txt'
    config.parent.mkdir(parents=True, exist_ok=True)
    if config.exists():
        backup.mkdir(parents=True, exist_ok=True)
        shutil.copy2(config, backup/'motor-path.txt')
    config.write_text(str(runtime/'KattBeautyMotor.exe')+'\n\n', encoding='utf-8-sig')
    base.mkdir(parents=True, exist_ok=True)
    (base/'instalacion.json').write_text(json.dumps(dict(version=VERSION, obs=str(obs), runtime=str(runtime), backup=str(backup)), indent=2), encoding='utf-8')
    messagebox.showinfo('KattBeauty Studio', 'Instalacion completada. Abre OBS y agrega el filtro a tu camara.\n\nLee LEEME.txt para los controles y las limitaciones.')
    ui.destroy()


if __name__ == '__main__':
    try:
        if len(sys.argv) == 5 and sys.argv[1] == '--commit':
            commit(*sys.argv[2:])
        else:
            install()
    except Exception as error:
        try:
            messagebox.showerror('KattBeauty Studio - Error', str(error))
        finally:
            sys.exit(1)
