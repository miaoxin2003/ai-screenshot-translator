"""
设置文件处理助手
负责在EXE所在目录处理设置文件的读写，确保用户在任何电脑上都能保存设置
"""

import os
import sys
import json

# 默认API配置（安全起见，此处不放真实密钥）
DEFAULT_API_KEY = ""
DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1"

# 全局变量和默认设置
DEFAULT_SETTINGS = {
    "screenshot_hotkey": "alt+shift+s",
    "area_screenshot_hotkey": "f1",
    "translation_mode": "zh-en",
    "model": "Qwen/Qwen2.5-VL-32B-Instruct",
    "image_detail": "high",
    "result_opacity": 0.90,
    "auto_minimize": True,
    "api_key": DEFAULT_API_KEY,
    "base_url": DEFAULT_BASE_URL,
    "custom_models": []
}

def get_exe_directory():
    """获取EXE文件所在的目录"""
    if getattr(sys, 'frozen', False):
        # PyInstaller打包时的情况
        return os.path.dirname(sys.executable)
    else:
        # 开发环境下，使用脚本所在目录
        return os.path.dirname(os.path.abspath(__file__))

def get_settings_file_path():
    """获取设置文件的路径，固定在EXE目录下"""
    exe_dir = get_exe_directory()
    settings_path = os.path.join(exe_dir, "settings.json")
    return settings_path

def load_settings():
    """加载设置文件，如果不存在则创建默认设置"""
    settings_file = get_settings_file_path()
    
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                print(f"成功加载设置文件: {settings_file}")
                return settings
        except Exception as e:
            print(f"加载设置文件失败: {e}")
            # 如果加载失败，创建默认设置并保存
            save_settings(DEFAULT_SETTINGS)
            return DEFAULT_SETTINGS
    else:
        # 如果设置文件不存在，创建默认设置并保存
        print(f"设置文件不存在，创建默认设置: {settings_file}")
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS

def save_settings(settings):
    """保存设置到EXE所在目录的settings.json文件"""
    settings_file = get_settings_file_path()
    
    try:
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        print(f"设置已保存到: {settings_file}")
        return True
    except Exception as e:
        print(f"保存设置文件失败: {e}")
        try:
            # 尝试以管理员权限保存
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                print("尝试以管理员权限保存设置...")
                # 这里只能提示用户，无法自动提升权限
                print("请以管理员身份运行程序，或将程序移动到有写入权限的目录。")
        except:
            pass
        return False

# 测试代码，如果直接运行此脚本则执行测试
if __name__ == "__main__":
    print("测试设置文件处理...")
    
    # 获取设置文件路径
    settings_path = get_settings_file_path()
    print(f"设置文件路径: {settings_path}")
    
    # 测试加载设置
    settings = load_settings()
    print(f"加载的设置: {settings}")
    
    # 修改设置并保存
    settings["test_value"] = "这是一个测试值"
    save_result = save_settings(settings)
    print(f"保存结果: {'成功' if save_result else '失败'}")
    
    # 再次加载以验证保存是否成功
    new_settings = load_settings()
    if "test_value" in new_settings and new_settings["test_value"] == "这是一个测试值":
        print("测试通过：设置已成功保存和加载")
    else:
        print("测试失败：设置未能正确保存或加载") 