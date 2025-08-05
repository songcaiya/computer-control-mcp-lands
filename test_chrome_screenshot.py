#!/usr/bin/env python3
"""
测试谷歌浏览器后台截图功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from computer_control_mcp.core import take_screenshot

def test_chrome_screenshot():
    """测试谷歌浏览器后台截图"""
    print("开始测试谷歌浏览器后台截图...")
    
    try:
        # 调用截图函数
        result = take_screenshot(
            title_pattern="Google Chrome",
            with_ocr_text_and_coords=True,
            save_to_downloads=True
        )
        
        print("截图测试完成！")
        print(f"结果类型: {type(result)}")
        
        if hasattr(result, 'data'):
            print(f"截图数据大小: {len(result.data)} bytes")
        
        return result
        
    except Exception as e:
        print(f"截图测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_chrome_screenshot()