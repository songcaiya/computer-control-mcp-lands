# 📦 Computer Control MCP 发布指南

## 🎯 概述

本指南将帮助你将 Computer Control MCP 工具打包并发布到 PyPI，让用户可以通过 `pip install computer-control-mcp` 直接安装。

## 📋 前置条件

### 1. 安装必要工具
```bash
pip install --upgrade pip build twine
```

### 2. 注册 PyPI 账户
- **测试环境**: https://test.pypi.org/account/register/
- **正式环境**: https://pypi.org/account/register/

### 3. 生成 API Token
1. 登录 PyPI 账户
2. 进入 Account settings → API tokens
3. 创建新的 API token（建议选择 "Entire account" 范围）
4. 保存生成的 token（格式：`pypi-xxxxxxxxxxxx`）

### 4. 配置认证文件
将 `.pypirc.template` 复制到用户目录并重命名为 `.pypirc`：

**Windows**: `C:\Users\你的用户名\.pypirc`
**Linux/Mac**: `~/.pypirc`

编辑文件，替换 API token：
```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-你的正式环境API令牌

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-你的测试环境API令牌
```

## 🚀 发布流程

### 方法一：使用自动化脚本（推荐）

```bash
python release.py
```

选择操作：
- **选项1**: 完整发布流程（推荐新手）
- **选项2**: 仅构建和检查
- **选项3**: 上传到测试PyPI
- **选项4**: 上传到正式PyPI
- **选项5**: 从测试PyPI安装测试

### 方法二：手动执行步骤

#### 步骤1: 清理构建文件
```bash
# Windows PowerShell
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }

# Linux/Mac
rm -rf dist/ build/ *.egg-info/
```

#### 步骤2: 构建包
```bash
python -m build
```

#### 步骤3: 检查包质量
```bash
twine check dist/*
```

#### 步骤4: 上传到测试PyPI
```bash
twine upload --repository testpypi dist/*
```

#### 步骤5: 测试安装
```bash
pip install --index-url https://test.pypi.org/simple/ computer-control-mcp
```

#### 步骤6: 上传到正式PyPI
```bash
twine upload dist/*
```

## 📝 版本管理

### 更新版本号
编辑 `pyproject.toml` 文件中的版本号：
```toml
[project]
name = "computer-control-mcp"
version = "0.2.8"  # 更新这里
```

### 版本号规范
- **主版本号**: 不兼容的API修改
- **次版本号**: 向下兼容的功能性新增
- **修订号**: 向下兼容的问题修正

例如：`0.2.7` → `0.2.8`（修复bug）或 `0.3.0`（新功能）

## 🔍 验证发布

### 1. 检查PyPI页面
- 测试环境: https://test.pypi.org/project/computer-control-mcp/
- 正式环境: https://pypi.org/project/computer-control-mcp/

### 2. 测试安装
```bash
# 从正式PyPI安装
pip install computer-control-mcp

# 验证安装
computer-control-mcp --version
```

### 3. 测试功能
```bash
# 启动MCP服务器
computer-control-mcp

# 或者
computer-control-mcp-server
```

## ⚠️ 注意事项

1. **版本唯一性**: PyPI不允许重复上传相同版本号
2. **测试先行**: 建议先上传到测试PyPI验证
3. **文档更新**: 确保README.md和文档是最新的
4. **依赖检查**: 确认所有依赖都在pyproject.toml中正确声明
5. **许可证**: 确保LICENSE文件存在且正确

## 🛠️ 故障排除

### 常见错误

1. **403 Forbidden**: 检查API token是否正确
2. **400 Bad Request**: 检查包名是否已存在或版本号重复
3. **文件缺失**: 检查MANIFEST.in是否包含所有必要文件

### 调试命令
```bash
# 查看包内容
python -m zipfile -l dist/computer_control_mcp-0.2.7-py3-none-any.whl

# 详细检查
twine check --strict dist/*
```

## 📚 相关资源

- [Python打包指南](https://packaging.python.org/)
- [PyPI官方文档](https://pypi.org/help/)
- [Twine文档](https://twine.readthedocs.io/)
- [PEP 517 - 构建系统接口](https://pep.python.org/pep-0517/)

## 🎉 发布成功后

1. 更新项目README.md中的安装说明
2. 创建GitHub Release
3. 通知用户新版本发布
4. 更新文档和示例

---

**祝你发布顺利！** 🚀