# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Чтение зависимостей из requirements.txt и добавление в hiddenimports
import pkg_resources
import seleniumwire
import os
from PyInstaller.utils.hooks import collect_data_files

data_files = collect_data_files('seleniumwire')

with open('requirements.txt', 'r') as f:
    packages = [str(pkg_resources.Requirement.parse(line.strip()).project_name) for line in f if line.strip()]

# Основной анализ для PyInstaller
a = Analysis(['main.py'],
             pathex=['.'],
             binaries=[],
             datas=[
                 ('chrome.png', '.'),   # Убедитесь, что иконка включена
                 *data_files
             ],
             hiddenimports=packages,
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='ProxyBrowser',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,  # Смените на True, если хотите видеть сообщения об ошибках в консоли
          icon='chrome.png')
