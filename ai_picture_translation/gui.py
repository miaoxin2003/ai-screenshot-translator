import os
import sys
import time
import threading
import keyboard
import pyautogui
import pyperclip
from PIL import Image, ImageGrab
import tkinter as tk
from tkinter import ttk, messagebox, Text, Button, Label, Frame, Entry, Toplevel, StringVar, Scale, IntVar, DoubleVar, HORIZONTAL, Checkbutton

# 从 core.py 导入核心功能和设置
from core import (
    load_settings, save_settings, analyze_and_translate_image,
    DEFAULT_SETTINGS, DEFAULT_API_KEY, DEFAULT_BASE_URL, BASE_URL_OPTIONS,
    is_custom_model, get_all_models_for_gui, AVAILABLE_MODELS_CORE
)

# --- 全局设置变量 ---
# 加载设置并解包到全局变量
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
custom_models = settings.get("custom_models", DEFAULT_SETTINGS["custom_models"]) # 加载历史自定义模型
use_streaming = settings.get("use_streaming", DEFAULT_SETTINGS["use_streaming"])
print("GUI: 设置加载完成")

# --- 区域截图类 ---
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

    def on_cancel(self, event=None): # 添加 event=None 允许无事件调用
        # 取消操作，销毁窗口
        self.root.destroy()
        if self.callback:
            self.callback(None, 0, 0)

# --- 设置对话框类 ---
class SettingsDialog:
    """设置对话框"""
    def __init__(self, parent, restart_callback): # 添加 restart_callback
        self.parent = parent
        self.restart_callback = restart_callback # 保存回调函数
        self.dialog = Toplevel(parent)
        self.dialog.title("设置")
        self.dialog.geometry("870x984")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 获取所有可用模型 (从 core 获取，传入当前 custom_models)
        self.all_models_gui = get_all_models_for_gui(custom_models)

        # 检查当前模型是否为自定义模型 (使用 core 的函数)
        current_is_custom = is_custom_model(model, custom_models)

        # 创建设置变量
        self.screenshot_hotkey_var = StringVar(value=screenshot_hotkey)
        self.area_screenshot_hotkey_var = StringVar(value=area_screenshot_hotkey)

        # 处理模型选择变量
        if current_is_custom:
            self.model_var = StringVar(value="自定义模型")
            self.custom_model_var = StringVar(value=model)
            self.is_custom_model = True
        else:
            # 确保当前模型在列表中，如果不在（可能是旧的自定义模型被删了），则设为默认
            if model not in self.all_models_gui[:-1]: # 排除 "自定义模型" 选项
                 current_model_value = DEFAULT_SETTINGS["model"]
            else:
                 current_model_value = model
            self.model_var = StringVar(value=current_model_value)
            self.custom_model_var = StringVar(value="")
            self.is_custom_model = False

        self.custom_model_checkbox_var = IntVar(value=1 if self.is_custom_model else 0)

        self.image_detail_var = StringVar(value=image_detail)
        self.result_opacity_var = DoubleVar(value=result_opacity)
        self.auto_minimize_var = IntVar(value=1 if auto_minimize else 0)
        self.use_streaming_var = IntVar(value=1 if use_streaming else 0)
        self.api_key_var = StringVar(value=api_key)
        self.base_url_var = StringVar(value=base_url)

        # 设置透明度
        self.dialog.attributes('-alpha', 0.95)

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

        # 添加鼠标滚轮事件绑定
        def _on_mousewheel(event):
            if sys.platform.startswith('win'):
                canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            elif sys.platform.startswith('darwin'):
                 canvas.yview_scroll(int(-1 * event.delta), "units")
            else: # Linux
                if event.num == 4:
                    canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    canvas.yview_scroll(1, "units")

        # 绑定滚轮事件到 Canvas 和其子控件
        canvas.bind_all("<MouseWheel>", _on_mousewheel) # Windows & macOS
        canvas.bind_all("<Button-4>", _on_mousewheel) # Linux scroll up
        canvas.bind_all("<Button-5>", _on_mousewheel) # Linux scroll down


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
        base_url_frame = Frame(api_frame)
        base_url_frame.grid(row=2, column=1, sticky=tk.W, pady=5)

        # Base URL下拉菜单 (使用 core 的 BASE_URL_OPTIONS)
        self.base_url_combo = tk.ttk.Combobox(base_url_frame,
                                            textvariable=self.base_url_var,
                                            values=BASE_URL_OPTIONS,
                                            width=50)
        self.base_url_combo.pack(side=tk.LEFT)
        self.base_url_combo.bind("<KeyRelease>", lambda e: self.base_url_var.set(self.base_url_combo.get()))

        # API设置说明
        api_help_text = "说明: 更改API设置后将立即生效。保存后会自动使用新的API配置。"
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
        Label(hotkey_frame, text="格式: ctrl+shift+a, alt+x, f1 等 (保存后需重启生效)", fg="gray").grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=5)

        # 模型设置组
        model_frame = Frame(frame, relief=tk.GROOVE, borderwidth=1, padx=10, pady=10)
        model_frame.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=(0, 15))

        Label(model_frame, text="模型设置", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))

        # 模型选择
        Label(model_frame, text="AI模型:").grid(row=1, column=0, sticky=tk.W, pady=5)

        # 添加模型选择容器框架
        model_select_frame = Frame(model_frame)
        model_select_frame.grid(row=1, column=1, sticky=tk.W, pady=5)

        # 创建下拉框 (使用 self.all_models_gui)
        model_dropdown = tk.OptionMenu(model_select_frame, self.model_var,
                                      *self.all_models_gui,
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
        model_help_text = "说明:\n- 高细节(high): 提供更精确的图像理解，但会消耗更多Token\n- 低细节(low): 速度更快，Token消耗更少\n- 自定义模型: 输入您想使用的任何模型名称"
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

        # 流式输出选项
        Checkbutton(ui_frame, text="启用流式输出（翻译结果实时显示）", variable=self.use_streaming_var).grid(
            row=3, column=0, columnspan=2, sticky=tk.W, pady=5)

        # 界面说明文本
        ui_help_text = "说明:\n- 透明度: 值越小越透明（0.3为非常透明，1.0为完全不透明）\n- 自动最小化: 勾选后程序启动完成将自动最小化到任务栏\n- 流式输出: 开启后翻译结果将实时显示，响应更快"
        ui_help_label = Label(ui_frame, text=ui_help_text, justify=tk.LEFT, fg="gray")
        ui_help_label.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=10)

        # 设置对话框透明度
        Label(ui_frame, text="设置界面透明度:").grid(row=5, column=0, sticky=tk.W, pady=5)
        settings_opacity_var = DoubleVar(value=0.95)
        settings_opacity_scale = Scale(ui_frame, from_=0.5, to=1.0, resolution=0.05, orient=HORIZONTAL,
                                     variable=settings_opacity_var, length=200,
                                     command=lambda v: self.dialog.attributes('-alpha', float(v)))
        settings_opacity_scale.grid(row=5, column=1, sticky=tk.W, pady=5)

        # 按钮
        button_frame = Frame(frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=15)

        Button(button_frame, text="保存", width=10, command=self.on_save).pack(side=tk.LEFT, padx=10)
        Button(button_frame, text="取消", width=10, command=self.on_cancel).pack(side=tk.LEFT, padx=10)
        Button(button_frame, text="重置API配置", width=12, command=self.reset_api).pack(side=tk.LEFT, padx=10)

        # 版本信息
        version_label = Label(frame, text="AI截图翻译工具 by-baishui-1.2.0", fg="gray")
        version_label.grid(row=7, column=0, columnspan=2, sticky=tk.E, pady=(10, 0))

    def reset_api(self):
        """重置API配置为默认值"""
        self.api_key_var.set(DEFAULT_API_KEY)
        self.base_url_var.set(DEFAULT_BASE_URL)
        messagebox.showinfo("重置成功", "API配置已重置为默认值")

    def on_save(self):
        # 声明需要修改的全局变量
        global screenshot_hotkey, area_screenshot_hotkey, model, image_detail, result_opacity, auto_minimize
        global api_key, base_url, custom_models, use_streaming, translation_mode, settings

        # 获取新值
        new_screenshot_hotkey = self.screenshot_hotkey_var.get().strip()
        new_area_screenshot_hotkey = self.area_screenshot_hotkey_var.get().strip()

        # 根据是否使用自定义模型决定使用哪个模型值
        if self.is_custom_model:
            new_model = self.custom_model_var.get().strip()
            if not new_model:
                messagebox.showerror("错误", "自定义模型名称不能为空")
                return

            # 将新的自定义模型添加到历史记录（如果不存在且不是预设模型）
            if new_model not in custom_models and new_model not in AVAILABLE_MODELS_CORE:
                custom_models.append(new_model)
                # 限制历史记录数量，保留最近的5个
                if len(custom_models) > 5:
                    custom_models = custom_models[-5:]
        else:
            new_model = self.model_var.get()
            # 如果用户选择了 "自定义模型" 但未勾选复选框，则使用第一个预设模型
            if new_model == "自定义模型":
                new_model = AVAILABLE_MODELS_CORE[0] if AVAILABLE_MODELS_CORE else DEFAULT_SETTINGS["model"]


        new_image_detail = self.image_detail_var.get()
        new_result_opacity = self.result_opacity_var.get()
        new_auto_minimize = bool(self.auto_minimize_var.get())
        new_use_streaming = bool(self.use_streaming_var.get())
        new_api_key = self.api_key_var.get().strip()
        new_base_url = self.base_url_var.get().strip()

        # 检查快捷键是否有效 (仅格式检查，实际注册在主程序)
        if not new_screenshot_hotkey:
             messagebox.showerror("错误", "全屏截图快捷键不能为空")
             return
        if not new_area_screenshot_hotkey:
             messagebox.showerror("错误", "区域截图快捷键不能为空")
             return

        # 检查两个快捷键是否相同
        if new_screenshot_hotkey == new_area_screenshot_hotkey:
            messagebox.showerror("错误", "两个快捷键不能相同")
            return

        # 检查API设置
        if not new_api_key:
            messagebox.showerror("错误", "API Key不能为空")
            return
        if not new_base_url:
            messagebox.showerror("错误", "Base URL不能为空")
            return

        # 记录旧快捷键，以便判断是否需要重启提示
        old_screenshot_hotkey = screenshot_hotkey
        old_area_screenshot_hotkey = area_screenshot_hotkey

        # 更新全局变量
        screenshot_hotkey = new_screenshot_hotkey
        area_screenshot_hotkey = new_area_screenshot_hotkey
        model = new_model
        image_detail = new_image_detail
        result_opacity = new_result_opacity
        auto_minimize = new_auto_minimize
        use_streaming = new_use_streaming
        api_key = new_api_key
        base_url = new_base_url
        # custom_models 列表已在上面处理

        # 保存到设置文件 (使用 core 的 save_settings)
        current_settings = {
            "screenshot_hotkey": screenshot_hotkey,
            "area_screenshot_hotkey": area_screenshot_hotkey,
            "translation_mode": translation_mode, # translation_mode 在主 App 中修改并保存
            "model": model,
            "image_detail": image_detail,
            "result_opacity": result_opacity,
            "auto_minimize": auto_minimize,
            "api_key": api_key,
            "base_url": base_url,
            "custom_models": custom_models,
            "use_streaming": use_streaming
        }
        settings = current_settings # 更新全局 settings 字典

        if save_settings(current_settings):
            # 检查快捷键是否更改
            hotkey_changed = (screenshot_hotkey != old_screenshot_hotkey or
                              area_screenshot_hotkey != old_area_screenshot_hotkey)
            if hotkey_changed:
                messagebox.showinfo("成功", "设置已保存。新的快捷键将在重启应用后生效。")
                # 调用回调函数以重新注册快捷键（如果主应用提供了此功能）
                if self.restart_callback:
                    self.restart_callback()
            else:
                 messagebox.showinfo("成功", "设置已保存。")
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
                # 如果当前选择的是"自定义模型"，切换到第一个预设模型或默认模型
                 default_model = AVAILABLE_MODELS_CORE[0] if AVAILABLE_MODELS_CORE else DEFAULT_SETTINGS["model"]
                 self.model_var.set(default_model)
            # 将自定义模型输入框设置为只读
            self.custom_model_entry.config(state="readonly")

    def on_model_select(self, selection):
        """当下拉框选择改变时的回调"""
        if selection == "自定义模型":
            # 如果选择了"自定义模型"，自动勾选复选框
            self.custom_model_checkbox_var.set(1)
            self.toggle_custom_model() # 更新UI状态
        else:
             # 如果选择了预设模型，取消勾选复选框
             self.custom_model_checkbox_var.set(0)
             self.toggle_custom_model() # 更新UI状态


# --- 结果窗口类 ---
class ResultWindow:
    """翻译结果窗口类"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.result = ""
        self.min_width = 350
        self.min_height = 150
        self.padding = 20
        self.current_text = ""
        self.initial_size_set = False
        self.resize_timer_id = None

        # 创建窗口
        self.window = tk.Toplevel()
        self.window.title("翻译结果")
        self.window.attributes("-topmost", True)
        self.window.attributes('-alpha', result_opacity) # 使用全局设置

        # 初始窗口大小
        self.window.geometry(f"{self.min_width}x{self.min_height}+{x+10}+{y}")

        # 设置窗口失去焦点时自动关闭
        self.window.bind("<FocusOut>", self.on_focus_out)

        # 设置UI
        self.setup_ui()

    def on_focus_out(self, event):
        """当窗口失去焦点时关闭"""
        # 检查鼠标是否在窗口内，防止误关
        widget = self.window.winfo_containing(event.x_root, event.y_root)
        if widget is None: # 鼠标不在窗口内
             self.window.after(100, self.close_if_not_focused)

    def close_if_not_focused(self):
        """检查是否真的失去焦点并关闭窗口"""
        try:
            if not self.window.focus_displayof():
                self.window.destroy()
        except tk.TclError: # 窗口可能已被销毁
            pass

    def setup_ui(self):
        # 框架
        self.frame = Frame(self.window, padx=self.padding, pady=self.padding)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # 文本区域和滚动条
        self.text_frame = Frame(self.frame)
        self.text_frame.pack(fill=tk.BOTH, expand=True)

        self.result_text = Text(self.text_frame, wrap=tk.WORD, height=6, width=40)
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(self.text_frame, command=self.result_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.config(yscrollcommand=scrollbar.set)

        # 按钮框架
        self.button_frame = Frame(self.frame)
        self.button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        # 复制按钮
        Button(self.button_frame, text="复制结果",
               command=self.copy_to_clipboard).pack(side=tk.RIGHT)

    def stream_update(self, content_chunk, is_first_chunk):
        """流式更新结果，只追加增量内容"""
        if not content_chunk and not is_first_chunk: # 忽略空的非首块
             return

        try:
            self.result_text.config(state=tk.NORMAL) # 允许编辑
            if is_first_chunk:
                # 如果是第一个块，清空现有内容
                self.result_text.delete(1.0, tk.END)
                self.current_text = "" # 重置累积文本
                self.result = ""
                self.initial_size_set = False # 重置大小标记

            # 追加增量内容
            if content_chunk:
                self.result_text.insert(tk.END, content_chunk)
                self.current_text += content_chunk # 更新累积文本
                self.result = self.current_text # 更新完整结果
                self.result_text.see(tk.END) # 滚动到底部

            self.result_text.config(state=tk.DISABLED) # 设为只读

            # 延迟调整窗口大小 (只在文本变化时调整)
            if content_chunk: # 只有当实际有内容添加时才触发调整
                if self.resize_timer_id:
                    self.window.after_cancel(self.resize_timer_id)
                # 使用累积的 current_text 来判断大小
                self.resize_timer_id = self.window.after(200, lambda: self.adjust_window_size(self.current_text))

                if not self.initial_size_set and self.current_text:
                    self.initial_size_set = True
        except tk.TclError: # 窗口可能已关闭
            pass

    def update_result(self, result):
        """非流式更新结果"""
        self.result = result
        self.current_text = result
        try:
            self.result_text.config(state=tk.NORMAL)
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, result)
            self.result_text.see("1.0") # 滚动到顶部
            self.result_text.config(state=tk.DISABLED) # 设为只读

            self.adjust_window_size(result) # 立即调整
            self.initial_size_set = True
        except tk.TclError: # 窗口可能已关闭
            pass

    def adjust_window_size(self, text):
        """根据文本内容调整窗口大小"""
        try:
            # 计算文本所需大致尺寸
            lines = text.split('\n')
            max_line_length = max(len(line) for line in lines) if lines else 0
            num_lines = len(lines)

            # 估算像素尺寸 (这些值可能需要微调)
            char_width = 10
            line_height = 22
            text_width = max(max_line_length * char_width, 300)
            text_height = max(num_lines * line_height, 120)

            # 计算窗口总尺寸
            required_width = max(text_width + self.padding * 3 + 20, self.min_width) # +20 for scrollbar approx
            required_height = max(text_height + 80, self.min_height) # +80 for padding and button

            # 限制最大尺寸
            max_width = self.window.winfo_screenwidth() * 0.8
            max_height = self.window.winfo_screenheight() * 0.7
            required_width = int(min(required_width, max_width))
            required_height = int(min(required_height, max_height))

            # 获取当前窗口几何信息
            current_geometry = self.window.geometry() # "widthxheight+x+y"
            parts = current_geometry.split('+')
            size_parts = parts[0].split('x')
            current_width = int(size_parts[0])
            current_height = int(size_parts[1])
            current_x = int(parts[1])
            current_y = int(parts[2])


            # 只有当尺寸变化显著时才调整
            width_diff = abs(current_width - required_width)
            height_diff = abs(current_height - required_height)

            if width_diff > 30 or height_diff > 20 or not self.initial_size_set:
                # 调整窗口大小和位置，确保不超出屏幕
                screen_width = self.window.winfo_screenwidth()
                screen_height = self.window.winfo_screenheight()

                # 保持原始的 x, y 作为基准，但防止移出屏幕
                new_x = min(max(0, self.x + 10), screen_width - required_width)
                new_y = min(max(0, self.y), screen_height - required_height)

                self.window.geometry(f"{required_width}x{required_height}+{new_x}+{new_y}")
        except tk.TclError: # 窗口可能已关闭
            pass
        except Exception as e:
            print(f"Error adjusting window size: {e}")


    def copy_to_clipboard(self):
        """复制结果到剪贴板"""
        if self.result:
            try:
                pyperclip.copy(self.result)
                messagebox.showinfo("成功", "结果已复制到剪贴板", parent=self.window) # 指定父窗口
            except Exception as e:
                 messagebox.showerror("错误", f"无法复制到剪贴板: {e}", parent=self.window)
        else:
            messagebox.showinfo("提示", "暂无可复制的内容", parent=self.window)

# --- 主应用类 ---
class ScreenshotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI截图翻译工具 by-baishui-1.2.0")
        self.root.geometry("750x460")
        self.root.resizable(True, True)

        # 尝试设置图标 (如果 icon.ico 存在)
        icon_path = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), 'icon.ico')
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception as e:
                print(f"加载图标失败: {e}")

        self.setup_ui()
        self.running = True
        self.hotkey_listener_active = False # 标记监听器是否激活

        # 启动快捷键监听
        self.start_hotkey_listener()

        # 启动完成后自动最小化
        self.root.after(1000, self.auto_minimize_window)

    def auto_minimize_window(self):
        if auto_minimize:
            self.root.iconify()

    def setup_ui(self):
        # 控制面板
        control_frame = Frame(self.root)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        # 快捷键标签
        Label(control_frame, text="全屏截图:").pack(side=tk.LEFT, padx=(0, 5))
        self.hotkey_label = Label(control_frame, text=screenshot_hotkey)
        self.hotkey_label.pack(side=tk.LEFT, padx=(0, 20))

        Label(control_frame, text="区域截图:").pack(side=tk.LEFT, padx=(0, 5))
        self.area_hotkey_label = Label(control_frame, text=area_screenshot_hotkey)
        self.area_hotkey_label.pack(side=tk.LEFT, padx=(0, 20))

        # 翻译模式按钮
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

        # 结果文本区域
        self.result_text = Text(self.root, wrap=tk.WORD)
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.result_text.config(state=tk.DISABLED) # 初始设为只读

        # 状态栏
        self.status_label = Label(self.root, text="就绪，按下快捷键进行截图翻译", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    def open_settings(self):
        """打开设置对话框"""
        # 传递 restart_hotkey_listener 作为回调
        SettingsDialog(self.root, self.restart_hotkey_listener)
        # 设置对话框关闭后，更新UI上的快捷键显示 (虽然重启才生效，但UI应立即更新)
        self.hotkey_label.config(text=screenshot_hotkey)
        self.area_hotkey_label.config(text=area_screenshot_hotkey)
        # 更新结果窗口透明度（如果设置中修改了）
        # 注意：已打开的结果窗口透明度不会变，新窗口会使用新设置

    def toggle_translation_mode(self):
        global translation_mode, settings
        if translation_mode == "zh-en":
            translation_mode = "en-zh"
        else:
            translation_mode = "zh-en"
        self.mode_btn.config(text=f"当前模式: {translation_mode}")

        # 更新并保存设置
        settings["translation_mode"] = translation_mode
        save_settings(settings)
        self.update_status(f"翻译模式切换为: {translation_mode}")


    def clear_result(self):
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.config(state=tk.DISABLED)
        self.update_status("结果已清空")

    def update_status(self, message):
        self.status_label.config(text=message)
        # self.root.update_idletasks() # 使用 update_idletasks 避免潜在问题

    def _perform_translation(self, screenshot, x, y, is_area=False):
        """执行翻译任务（用于线程）"""
        if not screenshot:
            self.update_status("截图无效或已取消")
            return

        # 在截图位置旁边创建结果窗口
        # 需要在主线程中创建 Tkinter 窗口
        result_window = None
        def create_res_window():
            nonlocal result_window
            result_window = ResultWindow(x, y)
        self.root.after(0, create_res_window)

        # 等待窗口创建完毕
        while result_window is None:
            time.sleep(0.05)

        self.update_status("正在分析图片并翻译...")

        try:
            accumulated_text = "" # 在线程中累积文本，用于最终确认
            is_first = True # 标记是否是第一个块

            # 定义流式回调，接收增量块
            def streaming_callback(content_chunk):
                nonlocal accumulated_text, is_first
                if content_chunk:
                    accumulated_text += content_chunk
                    # 更新主界面和结果窗口都需要在主线程中进行
                    # 传递增量块和是否为第一个块的标记
                    self.root.after(0, lambda chunk=content_chunk, first=is_first: self._update_ui_streaming(chunk, result_window, is_area, first))
                    is_first = False # 后续不再是第一个块

            # 调用核心翻译函数 (传入当前 API 设置)
            final_result = analyze_and_translate_image(
                screenshot, translation_mode, api_key, base_url, model, image_detail, use_streaming,
                callback=streaming_callback if use_streaming else None
            )

            # 如果是非流式调用，或者需要最终确认（虽然通常不需要了）
            if not use_streaming and final_result is not None:
                 self.root.after(0, lambda res=final_result: self._update_ui_final(res, result_window, is_area))
            # 流式调用结束时，状态已在 _update_ui_streaming 中更新

            self.update_status("翻译完成")

        except Exception as e:
            error_msg = f"翻译出错: {str(e)}"
            print(error_msg) # 打印详细错误到控制台
            self.update_status(error_msg)
            # 在主线程更新结果窗口显示错误
            self.root.after(0, lambda: result_window.update_result(error_msg))


    def _update_ui_streaming(self, content_chunk, result_window, is_area, is_first_chunk):
        """在主线程中更新UI（流式），只追加增量内容"""
        try:
            self.result_text.config(state=tk.NORMAL) # 允许编辑以插入

            if is_first_chunk:
                # 如果是第一个块，添加时间戳 Header
                last_idx = self.result_text.index(tk.END) # 获取当前末尾位置
                timestamp_prefix = f"--- {time.strftime('%Y-%m-%d %H:%M:%S')}"
                area_suffix = " (区域截图)" if is_area else ""
                header = f"{timestamp_prefix}{area_suffix} ---\n"

                # 确保在插入 header 前有一个换行符，除非文本框为空或已是换行符
                if last_idx != "1.0":
                     last_char = self.result_text.get(f"{last_idx} - 1 char", last_idx)
                     if last_char != '\n':
                         self.result_text.insert(tk.END, "\n") # 添加换行符

                # 插入 Header
                self.result_text.insert(tk.END, header)

            # 追加增量内容
            if content_chunk: # 确保块不为空
                self.result_text.insert(tk.END, content_chunk)
                self.result_text.see(tk.END) # 滚动到底部

            self.result_text.config(state=tk.DISABLED) # 恢复只读

            # 更新结果窗口，传递增量块和 first 标记
            if result_window and result_window.window.winfo_exists():
                 result_window.stream_update(content_chunk, is_first_chunk)
        except tk.TclError:
            pass # 窗口可能已关闭
        except Exception as e:
            print(f"Error updating UI (streaming): {e}")


    def _update_ui_final(self, final_result, result_window, is_area):
        """在主线程中更新UI（最终确认/非流式）"""
        # 主要用于非流式情况，或确保流式结束后显示完整结果
        try:
            if final_result is None: # 避免 final_result 为 None 时出错
                return

            self.result_text.config(state=tk.NORMAL) # 允许编辑
            last_idx = self.result_text.index(tk.END) # 获取当前末尾位置
            timestamp_prefix = f"--- {time.strftime('%Y-%m-%d %H:%M:%S')}"
            area_suffix = " (区域截图)" if is_area else ""
            header = f"{timestamp_prefix}{area_suffix} ---\n"

            # 确保在插入 header 前有一个换行符
            if last_idx != "1.0":
                 last_char = self.result_text.get(f"{last_idx} - 1 char", last_idx)
                 if last_char != '\n':
                     self.result_text.insert(tk.END, "\n")

            # 插入 Header 和最终结果
            self.result_text.insert(tk.END, f"{header}{final_result}\n\n")
            self.result_text.see(tk.END) # 滚动到底部
            self.result_text.config(state=tk.DISABLED)

            # 更新结果窗口
            if result_window and result_window.window.winfo_exists():
                result_window.update_result(final_result)
        except tk.TclError:
            pass # 窗口可能已关闭
        except Exception as e:
            print(f"Error updating UI (final): {e}")


    def take_screenshot_and_translate(self):
        """全屏截图并翻译"""
        self.update_status("准备全屏截图...")
        try:
            screenshot = ImageGrab.grab()
            mouse_x, mouse_y = pyautogui.position()
            # 使用线程处理截图和翻译
            threading.Thread(target=self._perform_translation, args=(screenshot, mouse_x, mouse_y, False), daemon=True).start()
        except Exception as e:
            self.update_status(f"全屏截图出错: {str(e)}")

    def take_area_screenshot(self):
        """区域截图并翻译"""
        self.update_status("准备区域截图...")
        # 区域截图需要在主线程中启动UI
        AreaScreenshot(self.on_area_selected)

    def on_area_selected(self, screenshot, x, y):
        """区域截图完成后的回调函数"""
        if screenshot:
            self.update_status("区域截图完成，准备翻译...")
            # 使用线程处理翻译
            threading.Thread(target=self._perform_translation, args=(screenshot, x, y, True), daemon=True).start()
        else:
            self.update_status("区域截图已取消")

    def monitor_hotkeys(self):
        """监听快捷键的循环 (在单独线程中运行)"""
        print("Hotkey listener thread started.")
        # 注册快捷键
        try:
            keyboard.add_hotkey(screenshot_hotkey, self.take_screenshot_and_translate)
            keyboard.add_hotkey(area_screenshot_hotkey, self.take_area_screenshot)
            self.hotkey_listener_active = True
            print(f"Hotkeys registered: Fullscreen='{screenshot_hotkey}', Area='{area_screenshot_hotkey}'")
            self.root.after(0, lambda: self.update_status("快捷键监听已启动")) # 更新状态栏
        except Exception as e:
            self.hotkey_listener_active = False
            error_msg = f"注册快捷键失败: {str(e)}"
            print(error_msg)
            # 在主线程显示错误消息
            self.root.after(0, lambda: messagebox.showerror("快捷键错误", error_msg))
            self.root.after(0, lambda: self.update_status("快捷键注册失败，请检查设置或权限"))
            return # 注册失败则退出线程

        # 保持线程活动以监听快捷键
        keyboard.wait() # 使用 keyboard.wait() 来阻塞线程直到程序退出或 unhook_all
        self.hotkey_listener_active = False
        print("Hotkey listener thread finished.")


    def start_hotkey_listener(self):
        """启动快捷键监听线程"""
        if hasattr(self, 'hotkey_thread') and self.hotkey_thread.is_alive():
            print("Hotkey listener already running.")
            return

        # 清理旧的钩子（如果存在）
        keyboard.unhook_all()
        self.hotkey_listener_active = False

        self.hotkey_thread = threading.Thread(target=self.monitor_hotkeys, daemon=True)
        self.hotkey_thread.start()

    def stop_hotkey_listener(self):
        """停止快捷键监听"""
        if self.hotkey_listener_active:
            print("Stopping hotkey listener...")
            keyboard.unhook_all() # 这会解除阻塞并结束 wait()
            self.hotkey_listener_active = False
            # 等待线程结束 (可选，但有助于确保清理)
            if hasattr(self, 'hotkey_thread') and self.hotkey_thread.is_alive():
                 self.hotkey_thread.join(timeout=1.0)
            print("Hotkey listener stopped.")
            self.update_status("快捷键监听已停止")


    def restart_hotkey_listener(self):
        """重新启动快捷键监听（通常在设置更改后调用）"""
        print("Restarting hotkey listener...")
        self.stop_hotkey_listener()
        # 短暂延迟确保旧监听器完全停止
        time.sleep(0.2)
        self.start_hotkey_listener()
        # 更新UI上的标签
        self.hotkey_label.config(text=screenshot_hotkey)
        self.area_hotkey_label.config(text=area_screenshot_hotkey)


    def on_closing(self):
        """关闭应用"""
        print("Closing application...")
        self.running = False
        self.stop_hotkey_listener()
        self.root.destroy()

# --- 程序入口 ---
if __name__ == "__main__":
    root = tk.Tk()
    app = ScreenshotApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()