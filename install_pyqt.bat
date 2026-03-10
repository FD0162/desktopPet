@echo off
echo 正在安装 PyQt5、requests 和 pillow...
pip install PyQt5 requests pillow
if %errorlevel% neq 0 (
    echo 安装失败，请确保已安装 Python 并添加到 PATH。
    echo 如果下载慢，可以尝试使用国内镜像：
    echo pip install PyQt5 requests pillow -i https://pypi.tuna.tsinghua.edu.cn/simple
    pause
) else (
    echo 依赖安装完成！现在可以双击 run_pyqt.bat 启动桌宠。
    pause
)