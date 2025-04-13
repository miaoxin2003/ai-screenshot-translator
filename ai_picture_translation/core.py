import os
import sys
import base64
from io import BytesIO
import json
from openai import OpenAI
from tkinter import messagebox # 保持messagebox导入，因为save_settings中使用了

# 默认API配置
DEFAULT_API_KEY = ""
DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1"

# 预设BASE_URL选项
BASE_URL_OPTIONS = [
    "https://api.siliconflow.cn/v1",
    "https://openrouter.ai/api/v1"
]

# 默认设置
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
    "custom_models": [],
    "use_streaming": True
}

# 可用的模型列表 (不包含 "自定义模型" 选项，这个由GUI处理)
AVAILABLE_MODELS_CORE = [
    "Qwen/Qwen2.5-VL-32B-Instruct",
    "Qwen/Qwen2.5-VL-72B-Instruct",
    "Pro/Qwen/Qwen2.5-VL-7B-Instruct",
    "Qwen/QVQ-72B-Preview",
    "deepseek-ai/deepseek-vl2",
    "moonshotai/kimi-vl-a3b-thinking:free",
    "google/gemma-3-4b-it:free",
    "qwen/qwen2.5-vl-32b-instruct:free",
    "qwen/qwen-2.5-vl-7b-instruct:free",
]

def get_settings_path():
    """获取设置文件的路径"""
    return os.path.join(os.path.dirname(sys.executable
        if getattr(sys, 'frozen', False) else os.path.dirname(__file__)), "settings.json")

def load_settings():
    """加载设置"""
    settings_file = get_settings_path()
    try:
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                # 合并默认设置，确保所有键都存在
                settings = DEFAULT_SETTINGS.copy()
                settings.update(loaded)
                return settings
        return DEFAULT_SETTINGS.copy() # 返回副本以防意外修改
    except Exception as e:
        print(f"加载设置失败: {e}")
        return DEFAULT_SETTINGS.copy() # 返回副本

def save_settings(settings):
    """保存设置"""
    settings_file = get_settings_path()
    try:
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"保存设置失败: {e}")
        messagebox.showwarning("设置保存失败",
                              f"无法保存设置到{settings_file}\n请尝试将程序移到非系统目录或以管理员身份运行。")
        return False

def is_custom_model(model_name, custom_models_list):
    """检查模型是否为自定义模型"""
    # 如果模型不在预设列表且不在历史自定义模型列表中，则认为是新的自定义模型
    # 或者如果模型在历史自定义模型列表中，也认为是自定义模型
    return model_name not in AVAILABLE_MODELS_CORE or model_name in custom_models_list

def get_all_models_for_gui(custom_models_list):
    """获取所有可用模型列表（供GUI使用），包括历史自定义模型和'自定义模型'选项"""
    all_models = AVAILABLE_MODELS_CORE.copy()
    if custom_models_list:
        # 添加不在预设列表中的自定义模型
        for cm in custom_models_list:
            if cm not in all_models:
                all_models.append(cm)
    all_models.append("自定义模型") # 最后添加选项
    return all_models

def convert_image_to_base64(image):
    """将PIL图像转换为Base64编码"""
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str

def analyze_and_translate_image(image, mode, api_key, base_url, model, image_detail, use_streaming, callback=None):
    """使用视觉AI模型分析图片内容并翻译，支持流式输出"""
    if not api_key or not base_url:
        return "翻译失败: API Key 或 Base URL 未配置。"

    base64_image = convert_image_to_base64(image)

    # 根据翻译模式设置提示词
    if mode == "zh-en":
        prompt = "这张截图中有文本内容。请提取出所有文本，然后将其翻译成英文。只返回翻译结果，不要有其他解释。"
    elif mode == "en-zh":
        prompt = "This screenshot contains text. Please extract all the text and translate it to Chinese. Only return the translation result without any explanation.The content should make sense.Colloquial: Use natural Chinese expressions, consistent with the character's personality."
    else: # 默认或未知模式
        prompt = "Please extract all the text from this image and translate it."

    try:
        # 在函数内部创建客户端，确保使用最新的配置
        client = OpenAI(api_key=api_key, base_url=base_url)

        # 构建请求
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}",
                            "detail": image_detail
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]

        if use_streaming and callback:
            # 使用流式输出
            full_text = ""
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True
            )
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    if content: # 确保 content 不为空
                        full_text += content
                        if callback:
                            # 回调只传递增量内容
                            callback(content)
            return full_text # 流式结束后返回完整文本
        else:
            # 非流式输出
            response = client.chat.completions.create(
                model=model,
                messages=messages
            )
            translated_text = response.choices[0].message.content
            return translated_text

    except Exception as e:
        return f"翻译失败: {str(e)}"