#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
示例脚本：展示如何使用 overlay_icon 和 batch_overlay_icons 函数
"""

import os
from panel_text_renderer import overlay_icon, batch_overlay_icons

def example_batch_processing():
    """批量处理图片示例"""
    # 批量处理所有图片
    batch_overlay_icons(
        base_folder="output_acrylic_text",
        icon_folder="icon",
        output_folder="output_acrylic_text_with_icons",
        icon_size=(100, 100),  # 图标大小为 100x100 像素
        position=(120, 100),   # 图标位置距离右上角 100, 100 像素
        padding=20             # 图标与边缘的间距为 20 像素
    )
    print("批量图片处理完成")

if __name__ == "__main__":
    # 创建输出文件夹
    os.makedirs("output_acrylic_text_with_icons", exist_ok=True)
    
    # 运行示例
    example_batch_processing()