import os
import sys
import time
import threading
import keyboard
import pyautogui
import pyperclip
from PIL import Image, ImageGrab, ImageDraw
import base64
from io import BytesIO
import tkinter as tk
from openai import OpenAI
import json
from tkinter import messagebox, Text, Button, Label, Frame, Entry, Toplevel, StringVar, Scale, IntVar, DoubleVar, HORIZONTAL, Checkbutton

# 默认API配置
DEFAULT_API_KEY = ""
DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1"

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
    "custom_models": []
}

def load_settings():
    """加载设置"""
    settings_file = os.path.join(os.path.dirname(sys.executable 
        if getattr(sys, 'frozen', False) else __file__), "settings.json")
    try:
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return DEFAULT_SETTINGS
    except Exception as e:
        print(f"加载设置失败: {e}")
        return DEFAULT_SETTINGS

def save_settings(settings):
    """保存设置"""
    settings_file = os.path.join(os.path.dirname(sys.executable 
        if getattr(sys, 'frozen', False) else __file__), "settings.json")
    try:
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"保存设置失败: {e}")
        messagebox.showwarning("设置保存失败", 
                              f"无法保存设置到{settings_file}\n请尝试将程序移到非系统目录或以管理员身份运行。")
        return False

# 加载设置
print("开始加载设置...")
settings = load_settings()
screenshot_hotkey = settings.get("screenshot_hotkey", DEFAULT_SETTINGS["screenshot_hotkey"])
area_screenshot_hotkey = settings.get("area_screenshot_hotkey", DEFAULT_SETTINGS["area_screenshot_hotkey"])
translation_mode = settings.get("translation_mode", DEFAULT_SETTINGS["translation_mode"])
model = settings.get("model", DEFAULT_SETTINGS["model"])
image_detail = settings.get("image_detail", DEFAULT_SETTINGS["image_detail"])
result_opacity = settings.get("result_opacity", DEFAULT_SETTINGS["result_opacity"])
auto_minimize = settings.get("auto_minimize", DEFAULT_SETTINGS["auto_minimize"])
api_key = settings.get("api_key", DEFAULT_SETTINGS["api_key"])
base_url = settings.get("base_url", DEFAULT_SETTINGS["base_url"])
custom_models = settings.get("custom_models", DEFAULT_SETTINGS["custom_models"])
print("设置加载完成")

# 创建OpenAI客户端
client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

# 可用的模型列表
AVAILABLE_MODELS = [
    "Qwen/Qwen2.5-VL-32B-Instruct",
    "Qwen/Qwen2.5-VL-72B-Instruct",
    "Pro/Qwen/Qwen2.5-VL-7B-Instruct",
    "Qwen/QVQ-72B-Preview",
    "deepseek-ai/deepseek-vl2",
    "自定义模型"  # 添加自定义模型选项
]

# 检查模型是否在可用列表中，如果不在则可能是自定义模型
def is_custom_model(model_name):
    """检查模型是否为自定义模型"""
    # 排除预设模型列表中的选项（除了"自定义模型"选项本身）
    return model_name not in AVAILABLE_MODELS[:-1]

# 获取完整的模型列表，包括历史自定义模型
def get_all_models():
    """获取所有可用模型列表，包括历史自定义模型"""
    all_models = AVAILABLE_MODELS[:-1].copy()  # 复制除"自定义模型"外的所有预设模型
    
    # 添加历史自定义模型（如果有）
    if custom_models:
        all_models.extend(custom_models)
    
    # 最后添加"自定义模型"选项
    all_models.append("自定义模型")
    return all_models

def convert_image_to_base64(image):
    """将PIL图像转换为Base64编码"""
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str

def analyze_and_translate_image(image, mode="zh-en"):
    """使用视觉AI模型分析图片内容并翻译"""
    base64_image = convert_image_to_base64(image)
    
    # 根据翻译模式设置提示词
    if mode == "zh-en":
        prompt = "这张截图中有文本内容。请提取出所有文本，然后将其翻译成英文。只返回翻译结果，不要有其他解释。"
    elif mode == "en-zh":
        prompt = "This screenshot contains text. Please extract all the text and translate it to Chinese. Only return the translation result without any explanation.The content should make sense.Colloquial: Use natural Chinese expressions, consistent with the character's personality."
    else:
        prompt = "Please extract all the text from this image and translate it."
    
    try:
        # 重新初始化客户端，确保使用最新的API配置
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        response = client.chat.completions.create(
            model=model,  # 使用设置中的模型
            messages=[
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
        )
        
        # 获取模型的回复
        translated_text = response.choices[0].message.content
        return translated_text
    except Exception as e:
        return f"翻译失败: {str(e)}"

class AreaScreenshot:
    """区域截图类"""
    def __init__(self, callback):
        self.start_x = 0
        self.start_y = 0
        self.current_x = 0
        self.current_y = 0
        self.callback = callback
        
        # 创建全屏透明窗口
        self.root = tk.Tk()
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-alpha', 0.3)
        self.root.attributes('-topmost', True)
        
        # 设置窗口背景为黑色
        self.root.configure(bg="black")
        
        # 创建画布
        self.canvas = tk.Canvas(self.root, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 绑定鼠标事件
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        
        # 绑定键盘事件（Esc键取消）
        self.root.bind("<Escape>", self.on_cancel)
        
        # 设置状态
        self.rect_id = None
        
        # 开始主循环
        self.root.mainloop()
    
    def on_press(self, event):
        # 记录起始点
        self.start_x = event.x
        self.start_y = event.y
        
        # 创建矩形
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="red", width=2, fill="blue", stipple="gray50"
        )
    
    def on_motion(self, event):
        # 更新当前点
        self.current_x = event.x
        self.current_y = event.y
        
        # 更新矩形
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, self.current_x, self.current_y)
    
    def on_release(self, event):
        # 确保矩形有效（宽度和高度大于10像素）
        width = abs(self.current_x - self.start_x)
        height = abs(self.current_y - self.start_y)
        
        if width > 10 and height > 10:
            # 计算左上角和右下角坐标
            left = min(self.start_x, self.current_x)
            top = min(self.start_y, self.current_y)
            right = max(self.start_x, self.current_x)
            bottom = max(self.start_y, self.current_y)
            
            # 销毁窗口
            self.root.destroy()
            
            # 截取选定区域的图像
            time.sleep(0.2)  # 等待窗口消失
            screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
            
            # 调用回调函数，传递截图和坐标
            if self.callback:
                self.callback(screenshot, left, top)
        else:
            # 如果矩形太小，取消操作
            self.on_cancel(None)
    
    def on_cancel(self, event):
        # 取消操作，销毁窗口
        self.root.destroy()
        if self.callback:
            self.callback(None, 0, 0)

class SettingsDialog:
    """设置对话框"""
    def __init__(self, parent):
        self.parent = parent
        self.dialog = Toplevel(parent)
        self.dialog.title("设置")
        self.dialog.geometry("870x984")  # 增加窗口尺寸
        self.dialog.resizable(True, True)  # 允许用户调整窗口大小
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 获取所有可用模型，包括历史自定义模型
        self.all_models = get_all_models()
        
        # 检查当前模型是否为自定义模型
        current_is_custom = is_custom_model(model)
        
        # 创建设置变量
        self.screenshot_hotkey_var = StringVar(value=screenshot_hotkey)
        self.area_screenshot_hotkey_var = StringVar(value=area_screenshot_hotkey)
        
        # 处理模型选择变量
        if current_is_custom:
            # 如果是自定义模型，则为自定义模型变量赋值
            self.model_var = StringVar(value="自定义模型")
            self.custom_model_var = StringVar(value=model)
            self.is_custom_model = True
        else:
            # 否则使用预设模型
            self.model_var = StringVar(value=model)
            self.custom_model_var = StringVar(value="")
            self.is_custom_model = False
            
        self.custom_model_checkbox_var = IntVar(value=1 if self.is_custom_model else 0)
        
        self.image_detail_var = StringVar(value=image_detail)
        self.result_opacity_var = DoubleVar(value=result_opacity)
        self.auto_minimize_var = IntVar(value=1 if auto_minimize else 0)
        self.api_key_var = StringVar(value=api_key)
        self.base_url_var = StringVar(value=base_url)
        
        # 设置透明度
        self.dialog.attributes('-alpha', 0.95)  # 设置对话框透明度
        
        # 创建界面
        self.create_widgets()
        
        # 设置模态
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.dialog.bind("<Escape>", lambda event: self.on_cancel())
    
    def create_widgets(self):
        # 使用带滚动条的容器以适应更多内容
        canvas = tk.Canvas(self.dialog)
        scrollbar = tk.Scrollbar(self.dialog, orient="vertical", command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        # 创建框架容器
        main_frame = Frame(canvas)
        canvas.create_window((0, 0), window=main_frame, anchor="nw")
        
        # 添加鼠标滚轮事件绑定，根据操作系统绑定不同的事件
        def _on_mousewheel_windows(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
        def _on_mousewheel_linux(event):
            if event.num == 4:  # 向上滚动
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:  # 向下滚动
                canvas.yview_scroll(1, "units")
                
        def _on_mousewheel_macos(event):
            canvas.yview_scroll(int(-1 * event.delta), "units")
            
        # 根据系统类型绑定不同的事件
        if sys.platform.startswith('win'):
            # Windows平台
            canvas.bind_all("<MouseWheel>", _on_mousewheel_windows)
        elif sys.platform.startswith('darwin'):
            # macOS平台
            canvas.bind_all("<MouseWheel>", _on_mousewheel_macos)
        else:
            # Linux和其他平台
            canvas.bind_all("<Button-4>", _on_mousewheel_linux)
            canvas.bind_all("<Button-5>", _on_mousewheel_linux)
        
        # 创建标签和输入框
        frame = Frame(main_frame, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = Label(frame, text="AI截图翻译工具设置", font=("Arial", 12, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 15))
        
        # API设置组
        api_frame = Frame(frame, relief=tk.GROOVE, borderwidth=1, padx=10, pady=10)
        api_frame.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(0, 15))
        
        Label(api_frame, text="API设置", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        # API Key
        Label(api_frame, text="API Key:").grid(row=1, column=0, sticky=tk.W, pady=5)
        api_key_entry = Entry(api_frame, textvariable=self.api_key_var, width=60)
        api_key_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Base URL
        Label(api_frame, text="Base URL:").grid(row=2, column=0, sticky=tk.W, pady=5)
        base_url_entry = Entry(api_frame, textvariable=self.base_url_var, width=60)
        base_url_entry.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # API设置说明
        api_help_text = "说明: 更改API设置后将立即生效，用于连接到不同的AI服务提供商。保存后会自动使用新的API配置。"
        Label(api_frame, text=api_help_text, justify=tk.LEFT, fg="gray").grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # 快捷键设置组
        hotkey_frame = Frame(frame, relief=tk.GROOVE, borderwidth=1, padx=10, pady=10)
        hotkey_frame.grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=(0, 15))
        
        Label(hotkey_frame, text="快捷键设置", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        # 全屏截图快捷键
        Label(hotkey_frame, text="全屏截图快捷键:").grid(row=1, column=0, sticky=tk.W, pady=5)
        Entry(hotkey_frame, textvariable=self.screenshot_hotkey_var, width=20).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # 区域截图快捷键
        Label(hotkey_frame, text="区域截图快捷键:").grid(row=2, column=0, sticky=tk.W, pady=5)
        Entry(hotkey_frame, textvariable=self.area_screenshot_hotkey_var, width=20).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # 快捷键格式提示
        Label(hotkey_frame, text="格式: ctrl+shift+a, alt+x, f1 等", fg="gray").grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # 模型设置组
        model_frame = Frame(frame, relief=tk.GROOVE, borderwidth=1, padx=10, pady=10)
        model_frame.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=(0, 15))
        
        Label(model_frame, text="模型设置", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        # 模型选择
        Label(model_frame, text="AI模型:").grid(row=1, column=0, sticky=tk.W, pady=5)
        
        # 添加模型选择容器框架
        model_select_frame = Frame(model_frame)
        model_select_frame.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # 创建下拉框
        model_dropdown = tk.OptionMenu(model_select_frame, self.model_var, 
                                      *self.all_models, 
                                      command=self.on_model_select)
        model_dropdown.pack(side=tk.LEFT)
        model_dropdown.config(width=30)
        
        # 创建自定义模型切换复选框
        custom_model_checkbox = Checkbutton(model_select_frame, text="自定义模型", 
                                         variable=self.custom_model_checkbox_var,
                                         command=self.toggle_custom_model)
        custom_model_checkbox.pack(side=tk.LEFT, padx=(10, 0))
        
        # 创建自定义模型输入框
        Label(model_frame, text="自定义模型名称:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.custom_model_entry = Entry(model_frame, textvariable=self.custom_model_var, width=60)
        self.custom_model_entry.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # 根据当前模式设置组件状态
        self.update_model_ui_state()
        
        # 图像细节级别
        Label(model_frame, text="图像细节级别:").grid(row=3, column=0, sticky=tk.W, pady=5)
        detail_options = ["high", "low"]
        detail_dropdown = tk.OptionMenu(model_frame, self.image_detail_var, *detail_options)
        detail_dropdown.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # 模型说明文本
        model_help_text = "说明:\n- 高细节(high): 提供更精确的图像理解，但会消耗更多Token\n- 低细节(low): 速度更快，Token消耗更少\n- 自定义模型: 输入您想使用的任何模型名称，可以使用API提供商支持的其他模型"
        model_help_label = Label(model_frame, text=model_help_text, justify=tk.LEFT, fg="gray")
        model_help_label.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        # 界面设置组
        ui_frame = Frame(frame, relief=tk.GROOVE, borderwidth=1, padx=10, pady=10)
        ui_frame.grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=(0, 15))
        
        Label(ui_frame, text="界面设置", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        # 结果窗口透明度
        Label(ui_frame, text="结果窗口透明度:").grid(row=1, column=0, sticky=tk.W, pady=5)
        opacity_scale = Scale(ui_frame, from_=0.3, to=1.0, resolution=0.05, orient=HORIZONTAL,
                             variable=self.result_opacity_var, length=200)
        opacity_scale.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # 自动最小化
        Checkbutton(ui_frame, text="启动后自动最小化主窗口", variable=self.auto_minimize_var).grid(
            row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # 界面说明文本
        ui_help_text = "说明:\n- 透明度: 值越小越透明（0.3为非常透明，1.0为完全不透明）\n- 自动最小化: 勾选后程序启动完成将自动最小化到任务栏"
        ui_help_label = Label(ui_frame, text=ui_help_text, justify=tk.LEFT, fg="gray")
        ui_help_label.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        # 设置对话框透明度
        Label(ui_frame, text="设置界面透明度:").grid(row=4, column=0, sticky=tk.W, pady=5)
        settings_opacity_var = DoubleVar(value=0.95)
        settings_opacity_scale = Scale(ui_frame, from_=0.5, to=1.0, resolution=0.05, orient=HORIZONTAL,
                                     variable=settings_opacity_var, length=200,
                                     command=lambda v: self.dialog.attributes('-alpha', float(v)))
        settings_opacity_scale.grid(row=4, column=1, sticky=tk.W, pady=5)
        
        # 按钮
        button_frame = Frame(frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=15)
        
        Button(button_frame, text="保存", width=10, command=self.on_save).pack(side=tk.LEFT, padx=10)
        Button(button_frame, text="取消", width=10, command=self.on_cancel).pack(side=tk.LEFT, padx=10)
        Button(button_frame, text="重置API配置", width=12, command=self.reset_api).pack(side=tk.LEFT, padx=10)
        
        # 版本信息
        version_label = Label(frame, text="AI截图翻译工具 by-baishui", fg="gray")
        version_label.grid(row=6, column=0, columnspan=2, sticky=tk.E, pady=(10, 0))
    
    def reset_api(self):
        """重置API配置为默认值"""
        self.api_key_var.set(DEFAULT_API_KEY)
        self.base_url_var.set(DEFAULT_BASE_URL)
        messagebox.showinfo("重置成功", "API配置已重置为默认值")
    
    def on_save(self):
        # 获取并保存设置
        global screenshot_hotkey, area_screenshot_hotkey, model, image_detail, result_opacity, auto_minimize
        global api_key, base_url, custom_models
        
        # 获取新值
        new_screenshot_hotkey = self.screenshot_hotkey_var.get()
        new_area_screenshot_hotkey = self.area_screenshot_hotkey_var.get()
        
        # 根据是否使用自定义模型决定使用哪个模型值
        if self.is_custom_model:
            new_model = self.custom_model_var.get().strip()
            if not new_model:
                messagebox.showerror("错误", "自定义模型名称不能为空")
                return
                
            # 将新的自定义模型添加到历史记录（如果不存在）
            if new_model not in custom_models and new_model not in AVAILABLE_MODELS[:-1]:
                custom_models.append(new_model)
                # 限制历史记录数量，保留最近的5个
                if len(custom_models) > 5:
                    custom_models = custom_models[-5:]
        else:
            new_model = self.model_var.get()
            if new_model == "自定义模型":  # 防止误选"自定义模型"但未勾选复选框的情况
                new_model = AVAILABLE_MODELS[0]
            
        new_image_detail = self.image_detail_var.get()
        new_result_opacity = self.result_opacity_var.get()
        new_auto_minimize = bool(self.auto_minimize_var.get())
        new_api_key = self.api_key_var.get()
        new_base_url = self.base_url_var.get()
        
        # 检查快捷键是否有效
        try:
            # 测试快捷键是否有效，尝试注册后立即解除
            keyboard.add_hotkey(new_screenshot_hotkey, lambda: None)
            keyboard.remove_hotkey(new_screenshot_hotkey)
            
            keyboard.add_hotkey(new_area_screenshot_hotkey, lambda: None)
            keyboard.remove_hotkey(new_area_screenshot_hotkey)
        except Exception as e:
            messagebox.showerror("错误", f"快捷键格式无效: {str(e)}")
            return
        
        # 检查两个快捷键是否相同
        if new_screenshot_hotkey == new_area_screenshot_hotkey:
            messagebox.showerror("错误", "两个快捷键不能相同")
            return
        
        # 检查API设置
        if not new_api_key.strip():
            messagebox.showerror("错误", "API Key不能为空")
            return
        
        if not new_base_url.strip():
            messagebox.showerror("错误", "Base URL不能为空")
            return
        
        # 更新全局变量
        screenshot_hotkey = new_screenshot_hotkey
        area_screenshot_hotkey = new_area_screenshot_hotkey
        model = new_model
        image_detail = new_image_detail
        result_opacity = new_result_opacity
        auto_minimize = new_auto_minimize
        api_key = new_api_key
        base_url = new_base_url
        
        # 立即更新API客户端
        try:
            global client
            client = OpenAI(api_key=api_key, base_url=base_url)
        except Exception as e:
            messagebox.showerror("错误", f"API客户端初始化失败: {str(e)}")
            return
        
        # 保存到设置文件
        settings = {
            "screenshot_hotkey": screenshot_hotkey,
            "area_screenshot_hotkey": area_screenshot_hotkey,
            "translation_mode": translation_mode,
            "model": model,
            "image_detail": image_detail,
            "result_opacity": result_opacity,
            "auto_minimize": auto_minimize,
            "api_key": api_key,
            "base_url": base_url,
            "custom_models": custom_models  # 保存自定义模型历史
        }
        
        if save_settings(settings):
            messagebox.showinfo("成功", "设置已保存，请重启应用以应用新的快捷键设置")
        else:
            messagebox.showerror("错误", "设置保存失败")
        
        # 关闭对话框
        self.dialog.destroy()
    
    def on_cancel(self):
        # 关闭对话框
        self.dialog.destroy()
    
    def toggle_custom_model(self):
        """切换自定义模型和预设模型"""
        self.is_custom_model = bool(self.custom_model_checkbox_var.get())
        self.update_model_ui_state()
    
    def update_model_ui_state(self):
        """更新模型相关UI组件的状态"""
        if self.is_custom_model:
            # 启用自定义模型输入框，设置下拉菜单为"自定义模型"
            self.custom_model_entry.config(state=tk.NORMAL)
            self.model_var.set("自定义模型")
        else:
            # 禁用自定义模型输入框，保持下拉菜单的选择
            if self.model_var.get() == "自定义模型":
                # 如果当前选择的是"自定义模型"，切换到默认模型
                self.model_var.set(AVAILABLE_MODELS[0])
            # 将自定义模型输入框设置为只读，以视觉上指示未被选中
            self.custom_model_entry.config(state="readonly")

    def on_model_select(self, selection):
        """当下拉框选择改变时的回调"""
        if selection == "自定义模型":
            # 如果选择了"自定义模型"，自动勾选复选框
            self.custom_model_checkbox_var.set(1)
            self.toggle_custom_model()  # 更新UI状态

class ResultWindow:
    """翻译结果窗口类，分离出来提高响应速度"""
    def __init__(self, x, y, loading=True):
        self.x = x
        self.y = y
        self.result = ""
        self.min_width = 250  # 最小宽度
        self.min_height = 100  # 最小高度
        self.padding = 20  # 文本周围的内边距
        
        # 创建窗口
        self.window = tk.Toplevel()
        self.window.title("翻译结果")
        self.window.attributes("-topmost", True)
        self.window.attributes('-alpha', result_opacity)  # 半透明效果
        
        # 初始窗口大小
        self.window.geometry(f"{self.min_width}x{self.min_height}+{x+10}+{y}")
        
        # 设置窗口失去焦点时自动关闭
        self.window.bind("<FocusOut>", self.on_focus_out)
        
        # 快速设置窗口
        self.setup_ui()
        
        # 如果是加载状态，显示加载信息
        if loading:
            self.show_loading()
    
    def on_focus_out(self, event):
        """当窗口失去焦点时关闭"""
        # 延迟关闭以避免某些特殊情况
        self.window.after(100, self.close_if_not_focused)
    
    def close_if_not_focused(self):
        """检查是否真的失去焦点并关闭窗口"""
        if not self.window.focus_displayof():
            self.window.destroy()
    
    def setup_ui(self):
        # 创建框架以获得更好的内边距控制
        self.frame = Frame(self.window, padx=self.padding, pady=self.padding)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # 添加文本显示区域 - 移除滚动条
        self.result_text = Text(self.frame, wrap=tk.WORD, height=4, width=30)
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
        # 按钮框架 - 不再固定高度
        self.button_frame = Frame(self.frame)
        self.button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        # 复制按钮
        Button(self.button_frame, text="复制结果", 
               command=self.copy_to_clipboard).pack(side=tk.RIGHT)
    
    def show_loading(self):
        """显示加载中状态"""
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "正在分析图像，请稍候...")
        self.result_text.config(state=tk.DISABLED)  # 禁止编辑
    
    def update_result(self, result):
        """更新结果并调整窗口大小"""
        self.result = result
        self.result_text.config(state=tk.NORMAL)  # 允许编辑
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, result)
        
        # 获取文本的实际大小
        self.result_text.update_idletasks()  # 确保文本渲染完成
        
        # 计算文本需要的行数和每行的字符数
        lines = result.split('\n')
        max_line_length = max(len(line) for line in lines)
        num_lines = len(lines)
        
        # 计算所需的窗口大小（考虑中文字符宽度和行高）
        char_width = 10  # 增加每个字符平均宽度为10像素，更好地支持中文
        line_height = 22  # 每行高度为22像素，增加行间距
        
        # 计算文本区域尺寸
        text_width = max_line_length * char_width
        text_height = num_lines * line_height
        
        # 计算所需的宽度和高度（加上内边距和按钮区域）
        required_width = max(text_width + self.padding * 3, self.min_width + 50)
        required_height = max(text_height + 100, self.min_height)  # 调整高度，自然适应按钮高度
        
        # 限制最大尺寸，防止窗口过大
        max_width = 900
        max_height = 600
        required_width = min(required_width, max_width)
        required_height = min(required_height, max_height)
        
        # 调整窗口大小和位置
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        # 确保窗口不会超出屏幕
        x_pos = min(self.x + 10, screen_width - required_width)
        y_pos = min(self.y, screen_height - required_height)
        
        # 调整窗口大小和位置
        self.window.geometry(f"{required_width}x{required_height}+{x_pos}+{y_pos}")
        
        # 确保文本完全可见
        self.result_text.see("1.0")
        
        # 文本区域可以编辑以便用户可以选择和复制
        self.result_text.config(state=tk.NORMAL)
    
    def copy_to_clipboard(self):
        """复制结果到剪贴板"""
        if self.result:
            pyperclip.copy(self.result)
            messagebox.showinfo("成功", "结果已复制到剪贴板")
        else:
            messagebox.showinfo("提示", "暂无可复制的内容")

class ScreenshotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI截图翻译工具 by-baishui")
        self.root.geometry("750x460")  # 调整为宽750高460
        self.root.resizable(True, True)
        
        # 设置图标 (如果有的话)
        # self.root.iconbitmap('icon.ico')
        
        self.setup_ui()
        self.running = True
        
        # 启动快捷键监听线程
        self.hotkey_thread = threading.Thread(target=self.monitor_hotkey)
        self.hotkey_thread.daemon = True
        self.hotkey_thread.start()
        
        # 启动完成后自动最小化
        self.root.after(1000, self.auto_minimize_window)
    
    def auto_minimize_window(self):
        if auto_minimize:
            self.root.iconify()  # 最小化主窗口
    
    def setup_ui(self):
        # 创建顶部控制面板
        control_frame = Frame(self.root)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # 快捷键标签和显示
        Label(control_frame, text="全屏截图:").pack(side=tk.LEFT, padx=(0, 5))
        self.hotkey_label = Label(control_frame, text=screenshot_hotkey)
        self.hotkey_label.pack(side=tk.LEFT, padx=(0, 20))
        
        Label(control_frame, text="区域截图:").pack(side=tk.LEFT, padx=(0, 5))
        self.area_hotkey_label = Label(control_frame, text=area_screenshot_hotkey)
        self.area_hotkey_label.pack(side=tk.LEFT, padx=(0, 20))
        
        # 翻译模式切换按钮
        self.mode_btn = Button(control_frame, text=f"当前模式: {translation_mode}", 
                             command=self.toggle_translation_mode)
        self.mode_btn.pack(side=tk.LEFT)
        
        # 设置按钮
        settings_btn = Button(control_frame, text="⚙️ 设置", command=self.open_settings)
        settings_btn.pack(side=tk.RIGHT, padx=5)
        
        # 清空按钮
        clear_btn = Button(control_frame, text="清空", command=self.clear_result)
        clear_btn.pack(side=tk.RIGHT, padx=5)
        
        # 最小化按钮
        Button(control_frame, text="最小化", command=lambda: self.root.iconify()).pack(side=tk.RIGHT, padx=5)
        
        # 创建文本显示区域
        self.result_text = Text(self.root, wrap=tk.WORD)
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建底部状态栏
        self.status_label = Label(self.root, text="就绪，按下快捷键进行截图翻译", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)
    
    def open_settings(self):
        """打开设置对话框"""
        SettingsDialog(self.root)
        # 更新UI上的快捷键显示
        self.hotkey_label.config(text=screenshot_hotkey)
        self.area_hotkey_label.config(text=area_screenshot_hotkey)
    
    def toggle_translation_mode(self):
        global translation_mode, settings
        if translation_mode == "zh-en":
            translation_mode = "en-zh"
        else:
            translation_mode = "zh-en"
        self.mode_btn.config(text=f"当前模式: {translation_mode}")
        
        # 更新设置
        settings["translation_mode"] = translation_mode
        save_settings(settings)
    
    def clear_result(self):
        self.result_text.delete(1.0, tk.END)
    
    def update_status(self, message):
        self.status_label.config(text=message)
        self.root.update()
    
    def show_result_window(self, result, x, y):
        """在截图位置旁边显示结果窗口"""
        # 使用分离的ResultWindow类来加快响应速度
        ResultWindow(x, y, loading=False)
    
    def take_screenshot_and_translate(self):
        self.update_status("准备截图...")
        
        try:
            # 获取屏幕截图
            screenshot = ImageGrab.grab()
            mouse_x, mouse_y = pyautogui.position()  # 获取鼠标位置
            
            # 在截图位置旁边显示加载中的结果窗口
            result_window = ResultWindow(mouse_x, mouse_y, loading=True)
            
            # 分析和翻译截图内容
            self.update_status("正在分析图片并翻译...")
            
            # 使用线程进行翻译，避免界面卡顿
            def translate_task():
                try:
                    result = analyze_and_translate_image(screenshot, translation_mode)
                    
                    # 在主界面显示结果
                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                    self.result_text.insert(tk.END, f"--- {timestamp} ---\n{result}\n\n")
                    
                    # 更新结果窗口
                    result_window.update_result(result)
                    
                    self.update_status("翻译完成")
                except Exception as e:
                    error_msg = f"翻译出错: {str(e)}"
                    self.update_status(error_msg)
                    result_window.update_result(error_msg)
            
            # 启动翻译线程
            threading.Thread(target=translate_task, daemon=True).start()
            
        except Exception as e:
            self.update_status(f"截图出错: {str(e)}")
    
    def take_area_screenshot(self):
        """区域截图并翻译"""
        self.update_status("准备区域截图...")
        
        # 启动区域截图
        AreaScreenshot(self.on_area_selected)
    
    def on_area_selected(self, screenshot, x, y):
        """区域截图完成后的回调函数"""
        if screenshot:
            try:
                # 在截图位置旁边显示加载中的结果窗口
                result_window = ResultWindow(x, y, loading=True)
                
                # 分析和翻译截图内容
                self.update_status("正在分析图片并翻译...")
                
                # 使用线程进行翻译，避免界面卡顿
                def translate_task():
                    try:
                        result = analyze_and_translate_image(screenshot, translation_mode)
                        
                        # 在主界面显示结果
                        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                        self.result_text.insert(tk.END, f"--- {timestamp} (区域截图) ---\n{result}\n\n")
                        
                        # 更新结果窗口
                        result_window.update_result(result)
                        
                        self.update_status("翻译完成")
                    except Exception as e:
                        error_msg = f"翻译出错: {str(e)}"
                        self.update_status(error_msg)
                        result_window.update_result(error_msg)
                
                # 启动翻译线程
                threading.Thread(target=translate_task, daemon=True).start()
                
            except Exception as e:
                self.update_status(f"处理截图出错: {str(e)}")
        else:
            self.update_status("区域截图已取消")
    
    def monitor_hotkey(self):
        """监听截图快捷键"""
        # 注册快捷键
        try:
            keyboard.add_hotkey(screenshot_hotkey, self.take_screenshot_and_translate)
            keyboard.add_hotkey(area_screenshot_hotkey, self.take_area_screenshot)
        except Exception as e:
            messagebox.showerror("错误", f"注册快捷键失败: {str(e)}")
        
        while self.running:
            time.sleep(0.1)
    
    def restart_hotkey_listener(self):
        """重新注册快捷键"""
        keyboard.unhook_all()  # 取消所有快捷键
        
        try:
            keyboard.add_hotkey(screenshot_hotkey, self.take_screenshot_and_translate)
            keyboard.add_hotkey(area_screenshot_hotkey, self.take_area_screenshot)
            self.update_status("快捷键已更新")
        except Exception as e:
            messagebox.showerror("错误", f"注册快捷键失败: {str(e)}")
    
    def on_closing(self):
        """关闭应用"""
        self.running = False
        keyboard.unhook_all()  # 取消所有快捷键
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ScreenshotApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
