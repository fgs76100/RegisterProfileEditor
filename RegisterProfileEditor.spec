# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['cli.py'],
             pathex=['C:\\Users\\berdych\\PycharmProjects\\RegisterProfileEditor\\venv\\Lib\\site-packages\\PyQt5', 'C:\\Users\\berdych\\PycharmProjects\\RegisterProfileEditor'],
             binaries=[],
             datas=[
                ('C:\\Users\\berdych\\PycharmProjects\\RegisterProfileEditor\\RegisterProfileEditor\\templates', 'RegisterProfileEditor\\templates' ),
                ('C:\\Users\\berdych\\PycharmProjects\\RegisterProfileEditor\\venv\\Lib\\site-packages\\PyQt5', 'PyQt5'),
                ('C:\\Users\\berdych\\PycharmProjects\\RegisterProfileEditor\\RegisterProfileEditor\\styles', 'RegisterProfileEditor\\styles' )
             ],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='RegisterProfileEditor',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='RegisterProfileEditor')