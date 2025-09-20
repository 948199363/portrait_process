#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片处理流水线脚本
串联frame -> acrylic -> panel_text_renderer -> add_rarity_effects的完整流程
"""

import os
import argparse
import shutil
from PIL import Image
import json

# 导入各个处理模块
import frame
import acrylic
from panel_text_renderer import process_images_multithreaded, process_images_with_icons
from add_rarity_effects import process_images as process_rarity_effects, create_sample_rarity_mapping

def clear_directory(directory):
    """清空目录"""
    if os.path.exists(directory):
        shutil.rmtree(directory)
    os.makedirs(directory, exist_ok=True)

def main():
    parser = argparse.ArgumentParser(description='图片处理流水线')
    parser.add_argument('--input', default='input', help='输入图片文件夹路径')
    parser.add_argument('--frame-dir', default='frame', help='边框图片文件夹路径')
    parser.add_argument('--output', default='output_final', help='最终输出文件夹路径')
    parser.add_argument('--no-glow', action='store_true', help='禁用发光效果')
    parser.add_argument('--no-aura', action='store_true', help='禁用光环效果')
    parser.add_argument('--clear', action='store_true', help='清空中间输出文件夹')
    args = parser.parse_args()

    # 定义各个步骤的输出目录
    output_frames = "output_frames"
    output_acrylic = "output_acrylic"
    output_acrylic_text = "output_acrylic_text"
    output_acrylic_text_with_icons = "output_acrylic_text_with_icons"
    
    # 确定最终输出文件夹（根据效果选项）
    if args.no_glow and args.no_aura:
        output_rarity_effects = "output_rarity_effects_no_glow_no_aura"
    elif args.no_glow:
        output_rarity_effects = "output_rarity_effects_no_glow"
    elif args.no_aura:
        output_rarity_effects = "output_rarity_effects_no_aura"
    else:
        output_rarity_effects = "output_rarity_effects"
    
    # 如果指定了清空选项，则清空所有中间和输出目录
    if args.clear:
        print("清空中间输出文件夹...")
        clear_directory(output_frames)
        clear_directory(output_acrylic)
        clear_directory(output_acrylic_text)
        clear_directory(output_acrylic_text_with_icons)
        clear_directory(output_rarity_effects)
        if os.path.exists("rarity_mapping.json"):
            os.remove("rarity_mapping.json")

    print("开始执行图片处理流水线...")
    
    # 步骤1: frame.py - 在图片上叠加边框
    print("\n步骤1: 应用边框...")
    try:
        frame.overlay_frames_on_images(args.input, args.frame_dir, output_frames)
        print(f"边框应用完成，结果保存在 {output_frames} 文件夹中")
    except Exception as e:
        print(f"边框应用失败: {e}")
        return

    # 步骤2: acrylic.py - 添加亚克力效果
    print("\n步骤2: 添加亚克力效果...")
    try:
        # 创建acrylic参数
        params = acrylic.AcrylicParams(
            width_ratio=0.68,
            height_ratio=0.10,
            anchor="bottom",
            margin_px=90,
            x_center_ratio=0.5,
            x_offset_px=0,
            y_offset_px=0,
            corner_radius_ratio=0.35,
            edge_feather=0.8,
            supersample=4,
            blur_radius=11,
            noise_strength=0.28,
            noise_alpha=0.18,
            highlight_strength=55,
            shadow_alpha=0,
            shadow_blur=8,
            shadow_offset_x=2,
            shadow_offset_y=3,
            add_border=False,
            harmonize=True,
            harmonize_mode="bottom",
            harmonize_band=0.05,
            harmonize_mix_white=0.0,
            harmonize_desaturate=0.6,
            harmonize_lift=0.22,
        )
        
        # 确保输出文件夹存在
        os.makedirs(output_acrylic, exist_ok=True)
        
        # 处理所有图片
        for fname in os.listdir(output_frames):
            if fname.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp")):
                in_img = os.path.join(output_frames, fname)
                out_img = os.path.join(output_acrylic, f"acrylic_{fname}")
                print(f"处理 {fname} -> {out_img}")
                acrylic.acrylic_overlay(in_img, out_img, params)
        
        print(f"亚克力效果添加完成，结果保存在 {output_acrylic} 文件夹中")
    except Exception as e:
        print(f"亚克力效果添加失败: {e}")
        return

    # 步骤3: panel_text_renderer.py - 添加文本和图标
    print("\n步骤3: 添加文本和图标...")
    try:
        # 处理文本
        config_path = "config.json"
        successful, failed = process_images_multithreaded(
            input_folder=output_acrylic,
            output_folder=output_acrylic_text,
            config_path=config_path
        )
        print(f"文本添加完成: 成功 {successful} 张，失败 {failed} 张")
        
        # 添加图标
        process_images_with_icons()
        print(f"图标添加完成，结果保存在 {output_acrylic_text_with_icons} 文件夹中")
    except Exception as e:
        print(f"文本和图标添加失败: {e}")
        return

    # 步骤4: add_rarity_effects.py - 添加稀有度特效
    print("\n步骤4: 添加稀有度特效...")
    try:
        # 确保输出文件夹存在
        os.makedirs(args.output, exist_ok=True)
        
        # 处理稀有度特效
        process_rarity_effects(
            input_folder=output_acrylic_text_with_icons,
            output_folder=output_rarity_effects,
            rarity_mapping=None,  # 我们现在从文件名中提取稀有度
            enable_glow=not args.no_glow,
            enable_aura=not args.no_aura
        )
        
        print(f"稀有度特效添加完成，结果保存在 {output_rarity_effects} 文件夹中")
    except Exception as e:
        print(f"稀有度特效添加失败: {e}")
        return

    # 最后一步: 复制最终结果到指定输出目录
    print("\n最后一步: 复制最终结果...")
    try:
        # 确保最终输出文件夹存在
        os.makedirs(args.output, exist_ok=True)
        
        # 复制所有处理完成的图片到最终输出目录
        for fname in os.listdir(output_rarity_effects):
            if fname.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp")):
                src = os.path.join(output_rarity_effects, fname)
                dst = os.path.join(args.output, fname)
                shutil.copy2(src, dst)
        
        print(f"所有处理完成！最终结果已保存在 {args.output} 文件夹中")
        print("\n处理流程总结:")
        print(f"1. 输入图片: {args.input}")
        print(f"2. 应用边框: {output_frames}")
        print(f"3. 添加亚克力效果: {output_acrylic}")
        print(f"4. 添加文本和图标: {output_acrylic_text_with_icons}")
        print(f"5. 添加稀有度特效: {output_rarity_effects}")
        print(f"6. 最终输出: {args.output}")
    except Exception as e:
        print(f"复制最终结果失败: {e}")
        return

if __name__ == "__main__":
    main()