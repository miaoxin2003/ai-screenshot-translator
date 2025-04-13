"""
安装PyInstaller打包可能需要的额外依赖
"""

import os
import sys
import subprocess

def install_package(package):
    """安装指定的包"""
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    print(f"已安装: {package}")

def main():
    """安装所有可能需要的额外依赖"""
    print("正在安装打包所需的额外依赖...")
    
    # 基本依赖
    packages = [
        "pyinstaller>=5.6.2",
        "pywin32",
        "pywin32-ctypes",
        "pefile"
    ]
    
    # 安装所有依赖
    for package in packages:
        try:
            install_package(package)
        except Exception as e:
            print(f"安装 {package} 时出错: {str(e)}")
    
    print("\n所有额外依赖安装完成！现在可以运行 setup.py 进行打包。")
    print("命令: python setup.py")

if __name__ == "__main__":
    main() 