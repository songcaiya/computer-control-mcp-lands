# Computer Control MCP Lands

🖥️ **一个强大的计算机控制MCP服务器，提供鼠标、键盘、OCR等计算机控制功能**

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![PyPI](https://img.shields.io/pypi/v/computer-control-mcp-lands.svg)](https://pypi.org/project/computer-control-mcp-lands/)

## 📖 简介

Computer Control MCP Lands 是一个基于 Model Context Protocol (MCP) 的服务器，提供全面的计算机控制功能。它使用 PyAutoGUI、RapidOCR、ONNXRuntime 等技术，类似于 Anthropic 的 'computer-use' 功能，但具有零外部依赖的特点。

## ✨ 主要功能

### 🖱️ 鼠标控制
- 鼠标移动和点击
- 拖拽操作
- 滚轮控制
- 多种点击模式（左键、右键、双击）

### ⌨️ 键盘控制
- 文本输入
- 按键模拟
- 组合键支持
- 特殊键处理

### 📸 屏幕截图
- 全屏截图
- 窗口截图
- 区域截图
- 支持多显示器

### 🔍 OCR文字识别
- 高精度文字识别
- 支持中英文
- 坐标定位
- 置信度检测
- 边界框绘制

### 🪟 窗口管理
- 窗口列表获取
- 窗口激活
- 窗口查找
- 模糊匹配

## 🚀 快速开始

### 安装

```bash
pip install computer-control-mcp-lands
```

### 基本使用

#### 作为MCP服务器运行

```bash
computer-control-mcp-server
```

#### 作为命令行工具使用

```bash
computer-control-mcp --help
```

### 配置示例

在你的MCP客户端配置中添加：

```json
{
  "mcpServers": {
    "computer-control": {
      "command": "computer-control-mcp-server",
      "args": []
    }
  }
}
```

## 🛠️ 可用工具

### 鼠标操作
- `click_screen(x, y)` - 点击屏幕指定位置
- `move_mouse(x, y)` - 移动鼠标到指定位置
- `drag_mouse(from_x, from_y, to_x, to_y)` - 拖拽鼠标

### 键盘操作
- `type_text(text)` - 输入文本
- `press_key(key)` - 按下指定按键

### 屏幕操作
- `take_screenshot()` - 截取屏幕
- `get_screen_size()` - 获取屏幕尺寸

### 窗口管理
- `list_windows()` - 列出所有窗口
- `activate_window(title_pattern)` - 激活指定窗口

## 📋 系统要求

- Python 3.12+
- Windows

## 🔧 依赖项

- `pyautogui` - 鼠标键盘控制
- `mcp[cli]` - MCP协议支持
- `pillow` - 图像处理
- `pygetwindow` - 窗口管理
- `fuzzywuzzy` - 模糊匹配
- `rapidocr` - OCR文字识别
- `onnxruntime` - AI推理引擎
- `opencv-python` - 计算机视觉

## 🔒 安全说明

此工具具有完整的系统控制权限，请：
- 仅在受信任的环境中使用
- 避免在生产系统上运行未经测试的脚本
- 定期检查和更新依赖项

⭐ 如果这个项目对你有帮助，请给它一个星标！