#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片处理流水线脚本
串联frame -> acrylic -> panel_text_renderer -> add_rarity_effects的完整流程
"""

import os
import argparse
import shutil
import sys

def run_command(command, description):
    """运行命令并检查结果"""
    print(f"\n{description}")
    print(f"执行命令: {command}")
    result = os.system(command)
    if result != 0:
        print(f"错误: {description} 失败")
        sys.exit(1)
    return result

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
        for directory in [output_frames, output_acrylic, output_acrylic_text, 
                         output_acrylic_text_with_icons, output_rarity_effects]:
            clear_directory(directory)
        if os.path.exists("rarity_mapping.json"):
            os.remove("rarity_mapping.json")

    print("开始执行图片处理流水线...")
    
    # 步骤1: frame.py - 在图片上叠加边框
    print("\n步骤1: 应用边框...")
    cmd1 = f'python frame.py --input "{args.input}" --frame "{args.frame_dir}" --output "{output_frames}"'
    run_command(cmd1, "应用边框步骤")
    
    # 步骤2: acrylic.py - 添加亚克力效果
    print("\n步骤2: 添加亚克力效果...")
    cmd2 = f'python acrylic.py'
    run_command(cmd2, "添加亚克力效果步骤")
    
    # 步骤3: panel_text_renderer.py - 添加文本和图标
    print("\n步骤3: 添加文本和图标...")
    cmd3 = f'python panel_text_renderer.py config.json'
    run_command(cmd3, "添加文本和图标步骤")
    
    # 步骤4: add_rarity_effects.py - 添加稀有度特效
    print("\n步骤4: 添加稀有度特效...")
    effect_flags = ""
    if args.no_glow:
        effect_flags += " --no-glow"
    if args.no_aura:
        effect_flags += " --no-aura"
    
    cmd4 = f'python add_rarity_effects.py{effect_flags}'
    run_command(cmd4, "添加稀有度特效步骤")
    
    # 最后一步: 复制最终结果到指定输出目录
    print("\n最后一步: 复制最终结果...")
    # 确保最终输出文件夹存在
    os.makedirs(args.output, exist_ok=True)
    
    # 复制所有处理完成的图片到最终输出目录
    try:
        for fname in os.listdir(output_rarity_effects):
            if fname.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp")):
                src = os.path.join(output_rarity_effects, fname)
                dst = os.path.join(args.output, fname)
                shutil.copy2(src, dst)
        
        print(f"\n所有处理完成！最终结果已保存在 {args.output} 文件夹中")
        print("\n处理流程总结:")
        print(f"1. 输入图片: {args.input}")
        print(f"2. 应用边框: {output_frames}")
        print(f"3. 添加亚克力效果: {output_acrylic}")
        print(f"4. 添加文本和图标: {output_acrylic_text_with_icons}")
        print(f"5. 添加稀有度特效: {output_rarity_effects}")
        print(f"6. 最终输出: {args.output}")
    except Exception as e:
        print(f"复制最终结果失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()