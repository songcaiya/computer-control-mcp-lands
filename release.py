#!/usr/bin/env python3
"""
自动化发布脚本 - Computer Control MCP
用于构建和发布Python包到PyPI
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, cwd=None):
    """执行命令并返回结果"""
    print(f"执行命令: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, check=True, 
                              capture_output=True, text=True, encoding='utf-8')
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {e}")
        if e.stdout:
            print(f"标准输出: {e.stdout}")
        if e.stderr:
            print(f"错误输出: {e.stderr}")
        return False

def clean_build():
    """清理构建文件"""
    print("🧹 清理构建文件...")
    dirs_to_clean = ['dist', 'build', '*.egg-info']
    for pattern in dirs_to_clean:
        for path in Path('.').glob(pattern):
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                    print(f"删除目录: {path}")
                else:
                    path.unlink()
                    print(f"删除文件: {path}")

def build_package():
    """构建包"""
    print("📦 构建包...")
    return run_command("python -m build")

def check_package():
    """检查包质量"""
    print("🔍 检查包质量...")
    return run_command("twine check dist/*")

def upload_to_testpypi():
    """上传到测试PyPI"""
    print("🧪 上传到测试PyPI...")
    # 检查 .pypirc 文件是否存在
    pypirc_path = Path.home() / ".pypirc"
    local_pypirc = Path(".pypirc")
    
    if local_pypirc.exists():
        print("使用项目目录下的 .pypirc 配置文件")
        return run_command(f"twine upload --config-file .pypirc --repository testpypi dist/*")
    elif pypirc_path.exists():
        print("使用用户目录下的 .pypirc 配置文件")
        return run_command("twine upload --repository testpypi dist/*")
    else:
        print("⚠️  未找到 .pypirc 配置文件，使用交互式上传")
        return run_command("twine upload --repository testpypi dist/*")

def upload_to_pypi():
    """上传到正式PyPI"""
    print("🚀 上传到正式PyPI...")
    # 检查 .pypirc 文件是否存在
    pypirc_path = Path.home() / ".pypirc"
    local_pypirc = Path(".pypirc")
    
    if local_pypirc.exists():
        print("使用项目目录下的 .pypirc 配置文件")
        return run_command(f"twine upload --config-file .pypirc dist/*")
    elif pypirc_path.exists():
        print("使用用户目录下的 .pypirc 配置文件")
        return run_command("twine upload dist/*")
    else:
        print("⚠️  未找到 .pypirc 配置文件，使用交互式上传")
        return run_command("twine upload dist/*")

def test_install_from_testpypi():
    """从测试PyPI安装测试"""
    print("🧪 从测试PyPI安装测试...")
    return run_command("pip install --index-url https://test.pypi.org/simple/ computer-control-mcp-lands")

def setup_pypirc():
    """设置 .pypirc 配置文件"""
    print("🔧 设置 .pypirc 配置文件...")
    
    local_pypirc = Path(".pypirc")
    home_pypirc = Path.home() / ".pypirc"
    
    if local_pypirc.exists():
        print(f"✅ 项目目录下已存在 .pypirc 文件: {local_pypirc.absolute()}")
        choice = input("是否要复制到用户目录? (y/n): ").strip().lower()
        if choice == 'y':
            shutil.copy2(local_pypirc, home_pypirc)
            print(f"✅ 已复制到用户目录: {home_pypirc}")
    elif home_pypirc.exists():
        print(f"✅ 用户目录下已存在 .pypirc 文件: {home_pypirc}")
        choice = input("是否要复制到项目目录? (y/n): ").strip().lower()
        if choice == 'y':
            shutil.copy2(home_pypirc, local_pypirc)
            print(f"✅ 已复制到项目目录: {local_pypirc.absolute()}")
    else:
        print("❌ 未找到 .pypirc 配置文件")
        print("💡 请确保项目目录下有 .pypirc 文件，或者手动创建一个")

def check_config():
    """检查配置"""
    print("🔍 检查配置...")
    
    # 检查 pyproject.toml
    pyproject_path = Path("pyproject.toml")
    if pyproject_path.exists():
        print("✅ pyproject.toml 存在")
        # 读取包名
        with open(pyproject_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'name = "computer-control-mcp-lands"' in content:
                print("✅ 包名配置正确: computer-control-mcp-lands")
            else:
                print("⚠️  包名可能不正确，请检查 pyproject.toml")
    else:
        print("❌ pyproject.toml 不存在")
    
    # 检查 .pypirc
    local_pypirc = Path(".pypirc")
    home_pypirc = Path.home() / ".pypirc"
    
    if local_pypirc.exists():
        print(f"✅ 项目目录下存在 .pypirc: {local_pypirc.absolute()}")
    elif home_pypirc.exists():
        print(f"✅ 用户目录下存在 .pypirc: {home_pypirc}")
    else:
        print("❌ 未找到 .pypirc 配置文件")
    
    # 检查必要的工具
    tools = ['python', 'pip', 'twine', 'build']
    for tool in tools:
        if run_command(f"{tool} --version"):
            print(f"✅ {tool} 可用")
        else:
            print(f"❌ {tool} 不可用")

def main():
    """主函数"""
    print("🎯 Computer Control MCP 发布脚本")
    print("=" * 50)
    
    # 检查是否在正确的目录
    if not Path("pyproject.toml").exists():
        print("❌ 错误: 请在项目根目录运行此脚本")
        sys.exit(1)
    
    # 显示菜单
    print("\n请选择操作:")
    print("1. 完整发布流程 (清理 → 构建 → 检查 → 测试PyPI)")
    print("2. 仅构建和检查")
    print("3. 上传到测试PyPI")
    print("4. 上传到正式PyPI")
    print("5. 从测试PyPI安装测试")
    print("6. 清理构建文件")
    print("7. 检查配置")
    print("8. 设置 .pypirc 配置文件")
    print("0. 退出")
    
    choice = input("\n请输入选择 (0-8): ").strip()
    
    if choice == "1":
        # 完整发布流程
        steps = [
            ("清理构建文件", clean_build),
            ("构建包", build_package),
            ("检查包质量", check_package),
            ("上传到测试PyPI", upload_to_testpypi)
        ]
        
        for step_name, step_func in steps:
            print(f"\n🔄 {step_name}...")
            if callable(step_func):
                if not step_func():
                    print(f"❌ {step_name}失败，停止执行")
                    sys.exit(1)
            else:
                step_func()
            print(f"✅ {step_name}完成")
        
        print("\n🎉 测试发布完成！")
        print("💡 提示: 请测试从测试PyPI安装，确认无误后再上传到正式PyPI")
        
    elif choice == "2":
        clean_build()
        if build_package() and check_package():
            print("\n✅ 构建和检查完成")
        else:
            print("\n❌ 构建或检查失败")
            
    elif choice == "3":
        if upload_to_testpypi():
            print("\n✅ 上传到测试PyPI完成")
        else:
            print("\n❌ 上传到测试PyPI失败")
            
    elif choice == "4":
        confirm = input("⚠️  确认要上传到正式PyPI吗? (yes/no): ").strip().lower()
        if confirm == "yes":
            if upload_to_pypi():
                print("\n🎉 上传到正式PyPI完成！")
            else:
                print("\n❌ 上传到正式PyPI失败")
        else:
            print("取消上传")
            
    elif choice == "5":
        if test_install_from_testpypi():
            print("\n✅ 从测试PyPI安装成功")
        else:
            print("\n❌ 从测试PyPI安装失败")
            
    elif choice == "6":
        clean_build()
        print("\n✅ 清理完成")
        
    elif choice == "7":
        check_config()
        
    elif choice == "8":
        setup_pypirc()
        
    elif choice == "0":
        print("👋 再见！")
        
    else:
        print("❌ 无效选择")

if __name__ == "__main__":
    main()