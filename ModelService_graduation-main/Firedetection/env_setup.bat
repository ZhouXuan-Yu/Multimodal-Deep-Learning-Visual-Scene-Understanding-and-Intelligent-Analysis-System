@echo off
REM 自动修复环境脚本

echo 正在修复Python环境...

REM 安装必要的依赖包
pip install numpy==1.18.5
pip install h5py==2.10.0
pip install opencv-python
pip install matplotlib
pip install tqdm

echo 环境修复完成，请重新运行您的程序。
