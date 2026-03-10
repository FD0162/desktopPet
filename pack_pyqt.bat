@echo off
cd /d D:\desktopPetAI\desktopPet
pyinstaller --onefile --windowed ^
    --add-data "png;png" ^
    --add-data "qt_plugins;PyQt5/Qt5/plugins" ^
    --hidden-import PyQt5.sip ^
    pet_pyqt.py
echo 打包完成，可执行文件在 dist 文件夹中。
pause