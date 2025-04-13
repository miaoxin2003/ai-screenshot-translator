"""
AI截图翻译工具打包脚本
使用PyInstaller将应用打包为单个exe文件，确保可以在任何电脑上使用并保存设置
"""

import os
import sys
import subprocess
import shutil
from PyInstaller.__main__ import run

def check_and_install_requirements():
    """检查并安装依赖"""
    try:
        import PyInstaller
    except ImportError:
        print("正在安装PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller>=5.6.2"])

if __name__ == "__main__":
    # 检查依赖
    check_and_install_requirements()
    
    # 应用图标路径（如果有）
    # icon_path = os.path.abspath(os.path.join("resources", "icon.ico"))
    
    # 确保打包前没有残留的settings.json文件
    temp_settings_path = os.path.join("dist", "temp_settings.json")
    if os.path.exists("settings.json"):
        print("备份当前设置文件...")
        try:
            shutil.copy("settings.json", temp_settings_path)
        except Exception as e:
            print(f"备份设置文件失败: {e}")
    
    # PyInstaller参数
    args = [
        "gui.py",  # 主脚本 (已修改为新的入口点)
        "--name=AI截图翻译工具",  # 输出文件名
        "--onefile",  # 打包为单个exe文件
        "--noconsole",  # 不显示控制台窗口
        "--clean",  # 清理临时文件
        # f"--icon={icon_path}",  # 应用图标（如果有）
        "--hidden-import=PIL._tkinter_finder",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.filedialog",
        "--hidden-import=tkinter.messagebox", 
        "--hidden-import=keyboard",
        "--hidden-import=PIL.Image",
        "--hidden-import=PIL.ImageGrab",
        "--hidden-import=PIL.ImageDraw",
        "--hidden-import=ctypes",
        "--collect-submodules=OpenAI",
    ]
    
    print("=" * 60)
    print("开始打包AI截图翻译工具...")
    print("=" * 60)
    
    # 运行PyInstaller
    run(args)
    
    print("\n" + "=" * 60)
    print("打包完成！输出文件位于dist目录下。")
    print("文件名: AI截图翻译工具.exe")
    print("=" * 60)
    
    # 恢复设置文件（如果有备份）
    if os.path.exists(temp_settings_path):
        try:
            shutil.copy(temp_settings_path, "settings.json")
            os.remove(temp_settings_path)
            print("已恢复原始设置文件")
        except Exception as e:
            print(f"恢复设置文件失败: {e}")
    
    # 创建使用说明文件
    readme_path = os.path.join("dist", "使用说明.txt")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("""
====== AI截图翻译工具使用说明 ======

【基本使用】
1. 将此exe文件复制到你想要的任何位置（最好是非系统目录）
2. 双击运行程序
3. 首次运行时，程序会自动在exe所在目录创建settings.json文件
4. 在【设置】中设置API密钥和其他选项
5. 所有设置会自动保存在exe同目录下的settings.json文件中

【快捷键】
- 全屏截图：Alt+Shift+S (默认)
- 区域截图：F1 (默认)
- 可在设置中自定义快捷键

【注意事项】
- 如果设置无法保存，请尝试将程序移到非系统目录
- 或右键选择"以管理员身份运行"
- 请勿删除exe同目录下的settings.json文件，否则设置将丢失

【分享给他人】
- 只需要分享exe文件即可
- 对方首次运行会自动创建设置文件
- 对方可以设置自己的API密钥和偏好
        """)
    
    print(f"使用说明已创建: {readme_path}")
    print("打包任务全部完成！") 