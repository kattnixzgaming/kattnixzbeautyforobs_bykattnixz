"""PyInstaller runtime hook: retain startup errors for support."""
import os
import sys
from pathlib import Path
folder = Path(os.environ.get('KATTBEAUTY_SETTINGS_DIR', str(Path(os.environ.get('LOCALAPPDATA', str(Path.home())))/'KattBeautyStudio')))
folder.mkdir(parents=True, exist_ok=True)
log = open(folder/'motor.log', 'w', encoding='utf-8', buffering=1)
sys.stdout = sys.stderr = log
