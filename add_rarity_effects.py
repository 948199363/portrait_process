#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为不同稀有度的图片添加自然且具有高级感的额外效果
支持粒子效果、闪箔效果等
"""

import os
import json
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import numpy as np
import random
from typing import Tuple, Dict, List
import math

# 稀有度配置
RARITY_CONFIG = {
    "common": {
        "name": "普通",
        "color": (255, 255, 255, 40),  # 适中的白色半透明
        "effects": ["subtle_glow"],
        "particle_count": 8,
        "foil_intensity": 0.1
    },
    "uncommon": {
        "name": "罕见",
        "color": (64, 224, 208, 45),  # 适中的青色
        "effects": ["glow", "particles"],
        "particle_count": 15,
        "foil_intensity": 0.2
    },
    "rare": {
        "name": "稀有",
        "color": (0, 128, 255, 50),  # 适中的蓝色
        "effects": ["glow", "particles", "foil"],
        "particle_count": 25,
        "foil_intensity": 0.3
    },
    "epic": {
        "name": "史诗",
        "color": (128, 0, 255, 55),  # 适中的紫色
        "effects": ["glow", "particles", "foil", "sparkle"],
        "particle_count": 40,
        "foil_intensity": 0.4
    },
    "legendary": {
        "name": "传奇",
        "color": (255, 215, 0, 60),  # 适中的金色
        "effects": ["glow", "particles", "foil", "sparkle", "aura"],
        "particle_count": 60,
        "foil_intensity": 0.5
    }
}

def create_glow_effect(image: Image.Image, color: Tuple[int, int, int, int], intensity: float = 1.0) -> Image.Image:
    """
    创建自然柔和的发光效果
    """
    # 创建多个发光层以实现更自然的效果
    glow_layers = []

    # 获取图片边界
    bbox = image.getbbox()
    if bbox:
        # 计算基础尺寸
        left, top, right, bottom = bbox
        width = right - left
        height = bottom - top
        
        # 创建多个不同强度和大小的发光层
        for i in range(4):  # 增加层数以获得更柔和的效果
            # 创建发光层
            glow = Image.new('RGBA', image.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(glow)
            
            # 根据层数调整参数
            layer_intensity = intensity * (0.6 ** i)  # 每层强度递减
            padding = int(25 * layer_intensity)  # 增加基础padding
            blur_radius = int(20 * layer_intensity)  # 增加模糊半径
            
            # 添加随机偏移使发光不规则
            offset_x = random.randint(-5, 5)
            offset_y = random.randint(-5, 5)
            
            # 扩大发光区域
            glow_left = left - padding + offset_x
            glow_top = top - padding + offset_y
            glow_right = right + padding + offset_x
            glow_bottom = bottom + padding + offset_y
            
            # 使用不规则形状绘制发光（椭圆+随机变形）
            if random.random() > 0.3:
                # 椭圆形状
                draw.ellipse([glow_left, glow_top, glow_right, glow_bottom], fill=color)
            else:
                # 矩形形状（带圆角）
                draw.rounded_rectangle([glow_left, glow_top, glow_right, glow_bottom], 
                                     radius=int(min(width, height) * 0.15), fill=color)
            
            # 应用不同程度的高斯模糊
            glow = glow.filter(ImageFilter.GaussianBlur(radius=blur_radius))
            glow_layers.append(glow)
        
        # 将所有发光层叠加
        combined_glow = Image.new('RGBA', image.size, (0, 0, 0, 0))
        for glow_layer in glow_layers:
            combined_glow = Image.alpha_composite(combined_glow, glow_layer)
        
        # 使用柔和的混合模式叠加发光效果
        # 降低发光层的整体透明度以获得更自然的效果
        glow_alpha = Image.new('L', image.size, int(180 * intensity))
        combined_glow.putalpha(glow_alpha)
        
        # 使用Screen混合模式使发光更自然
        result = Image.alpha_composite(image, combined_glow)
        return result
    
    # 如果没有边界框，直接返回原图
    return image

def create_particles(image: Image.Image, color: Tuple[int, int, int, int], count: int) -> Image.Image:
    """
    创建自然分布的粒子效果
    """
    particles = Image.new('RGBA', image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(particles)
    
    # 获取图片边界
    bbox = image.getbbox()
    if bbox:
        left, top, right, bottom = bbox
        width = right - left
        height = bottom - top
        
        # 在图片周围创建粒子，使用更自然的分布
        for _ in range(count):
            # 60% 的粒子在图片边界附近，30% 在稍远位置，10% 在图片内部
            rand = random.random()
            if rand < 0.6:
                # 在图片边界附近生成粒子
                side = random.randint(0, 3)  # 0: top, 1: right, 2: bottom, 3: left
                distance_factor = random.uniform(0.05, 0.15)  # 随机距离因子
                if side == 0:  # top
                    x = random.randint(left, right)
                    y = random.randint(int(top - height * distance_factor), top)
                elif side == 1:  # right
                    x = random.randint(right, int(right + width * distance_factor))
                    y = random.randint(top, bottom)
                elif side == 2:  # bottom
                    x = random.randint(left, right)
                    y = random.randint(bottom, int(bottom + height * distance_factor))
                else:  # left
                    x = random.randint(int(left - width * distance_factor), left)
                    y = random.randint(top, bottom)
            elif rand < 0.9:
                # 在稍远的位置生成粒子
                distance_factor = random.uniform(0.2, 0.4)
                x = random.randint(int(left - width * distance_factor), int(right + width * distance_factor))
                y = random.randint(int(top - height * distance_factor), int(bottom + height * distance_factor))
            else:
                # 在图片内部生成粒子（增强融合感）
                x = random.randint(int(left + width * 0.1), int(right - width * 0.1))
                y = random.randint(int(top + height * 0.1), int(bottom - height * 0.1))
            
            # 粒子大小（使用更自然的分布）
            size = max(1, int(random.expovariate(1.5)))
            
            # 粒子透明度（根据位置调整，边界更透明）
            if left <= x <= right and top <= y <= bottom:
                # 图片内部粒子较不透明
                alpha = random.randint(120, 220)
            else:
                # 边界粒子较透明
                alpha = random.randint(60, 150)
            
            particle_color = (color[0], color[1], color[2], alpha)
            
            # 绘制粒子（圆形或不规则形状）
            if random.random() > 0.7:
                # 不规则形状（椭圆）
                size_x = max(1, size + random.randint(-1, 1))
                size_y = max(1, size + random.randint(-1, 1))
                draw.ellipse([x-size_x, y-size_y, x+size_x, y+size_y], fill=particle_color)
            else:
                # 圆形
                draw.ellipse([x-size, y-size, x+size, y+size], fill=particle_color)
    
    # 将粒子效果叠加到原图
    result = Image.alpha_composite(image, particles)
    return result

def create_foil_effect(image: Image.Image, intensity: float = 0.5) -> Image.Image:
    """
    创建自然的闪箔效果
    """
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    # 创建闪箔层
    foil = Image.new('RGBA', image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(foil)
    
    # 获取图片边界
    bbox = image.getbbox()
    if bbox:
        left, top, right, bottom = bbox
        width = right - left
        height = bottom - top
        
        # 生成闪箔纹理（只在图片周围生成以提高性能）
        foil_count = int(120 * intensity)  # 减少数量以避免过于密集
        for _ in range(foil_count):
            # 闪箔位置（主要在图片边界附近）
            if random.random() < 0.6:  # 60% 在边界附近
                side = random.randint(0, 3)  # 0: top, 1: right, 2: bottom, 3: left
                distance_factor = random.uniform(0.05, 0.12)
                if side == 0:  # top
                    x = random.randint(left, right)
                    y = random.randint(int(top - height * distance_factor), top)
                elif side == 1:  # right
                    x = random.randint(right, int(right + width * distance_factor))
                    y = random.randint(top, bottom)
                elif side == 2:  # bottom
                    x = random.randint(left, right)
                    y = random.randint(bottom, int(bottom + height * distance_factor))
                else:  # left
                    x = random.randint(int(left - width * distance_factor), left)
                    y = random.randint(top, bottom)
            else:  # 40% 在图片内部或稍远
                if random.random() < 0.7:  # 图片内部
                    x = random.randint(int(left + width * 0.1), int(right - width * 0.1))
                    y = random.randint(int(top + height * 0.1), int(bottom - height * 0.1))
                else:  # 稍远位置
                    distance_factor = random.uniform(0.15, 0.3)
                    x = random.randint(int(left - width * distance_factor), int(right + width * distance_factor))
                    y = random.randint(int(top - height * distance_factor), int(bottom + height * distance_factor))
            
            # 闪箔大小（不规则大小，更自然）
            size_x = random.randint(1, 2)
            size_y = random.randint(1, 2)
            
            # 闪箔透明度（根据位置调整）
            if left <= x <= right and top <= y <= bottom:
                # 图片内部闪箔较不透明
                alpha = random.randint(int(80 * intensity), int(180 * intensity))
            else:
                # 边界闪箔较透明
                alpha = random.randint(int(40 * intensity), int(120 * intensity))
            
            # 根据稀有度调整闪箔颜色（不只是金色）
            # 获取原始图片的平均颜色作为参考
            # 简化处理：使用原始稀有度颜色，但调整亮度
            r, g, b = 255, 215, 0  # 默认金色
            # 根据稀有度调整颜色
            if intensity < 0.2:  # common/uncommon
                r, g, b = 200, 200, 200  # 银色
            elif intensity < 0.3:  # rare
                r, g, b = 100, 180, 255  # 蓝色
            elif intensity < 0.4:  # epic
                r, g, b = 180, 100, 255  # 紫色
            
            foil_color = (r, g, b, alpha)
            
            # 绘制不规则形状闪箔
            shape_type = random.choice(["ellipse", "rectangle"])
            if shape_type == "ellipse":
                draw.ellipse([x-size_x, y-size_y, x+size_x, y+size_y], fill=foil_color)
            else:
                # 细长三角形或菱形
                points = []
                angle_offset = random.randint(0, 360)
                for i in range(3):
                    angle = math.radians(angle_offset + i * 120)
                    px = x + size_x * math.cos(angle)
                    py = y + size_y * math.sin(angle)
                    points.append((px, py))
                draw.polygon(points, fill=foil_color)
    
    # 将闪箔效果叠加到原图
    result = Image.alpha_composite(image, foil)
    return result

def create_sparkle_effect(image: Image.Image, color: Tuple[int, int, int, int], intensity: float = 1.0) -> Image.Image:
    """
    创建自然的闪烁效果
    """
    sparkle = Image.new('RGBA', image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(sparkle)
    
    # 获取图片边界
    bbox = image.getbbox()
    if bbox:
        left, top, right, bottom = bbox
        width = right - left
        height = bottom - top
        
        # 创建星形闪烁效果
        sparkle_count = int(12 * intensity)  # 减少数量以避免过于密集
        for _ in range(sparkle_count):
            # 闪烁位置（主要在图片内部和边界）
            if random.random() < 0.6:  # 60% 在图片内部
                x = random.randint(int(left + width * 0.1), int(right - width * 0.1))
                y = random.randint(int(top + height * 0.1), int(bottom - height * 0.1))
            else:  # 40% 在边界附近
                side = random.randint(0, 3)  # 0: top, 1: right, 2: bottom, 3: left
                distance_factor = random.uniform(0.05, 0.15)
                if side == 0:  # top
                    x = random.randint(left, right)
                    y = random.randint(int(top - height * distance_factor), top)
                elif side == 1:  # right
                    x = random.randint(right, int(right + width * distance_factor))
                    y = random.randint(top, bottom)
                elif side == 2:  # bottom
                    x = random.randint(left, right)
                    y = random.randint(bottom, int(bottom + height * distance_factor))
                else:  # left
                    x = random.randint(int(left - width * distance_factor), left)
                    y = random.randint(top, bottom)
            
            # 闪烁大小（适中且不规则）
            size = random.randint(2, 4)
            
            # 随机选择形状：星形、菱形或光点
            shape_type = random.choice(["star", "diamond", "dot"])
            
            if shape_type == "star":
                # 绘制星形
                points = []
                for i in range(5):
                    # 外点
                    angle = math.radians(i * 72 + random.randint(-15, 15))  # 添加随机角度偏移
                    outer_x = x + size * math.cos(angle)
                    outer_y = y + size * math.sin(angle)
                    points.append((outer_x, outer_y))
                    
                    # 内点
                    angle = math.radians(i * 72 + 36 + random.randint(-15, 15))  # 添加随机角度偏移
                    inner_x = x + (size/2) * math.cos(angle)
                    inner_y = y + (size/2) * math.sin(angle)
                    points.append((inner_x, inner_y))
                
                # 绘制多边形（根据位置调整透明度）
                if left <= x <= right and top <= y <= bottom:
                    # 图片内部较不透明
                    alpha = random.randint(150, 240)
                else:
                    # 边界较透明
                    alpha = random.randint(100, 180)
                sparkle_color = (color[0], color[1], color[2], alpha)
                draw.polygon(points, fill=sparkle_color)
            elif shape_type == "diamond":
                # 绘制不规则菱形
                points = [
                    (x + random.randint(-size//2, size//2), y - size),      # 上（略微偏移）
                    (x + size, y + random.randint(-size//2, size//2)),      # 右（略微偏移）
                    (x + random.randint(-size//2, size//2), y + size),      # 下（略微偏移）
                    (x - size, y + random.randint(-size//2, size//2))       # 左（略微偏移）
                ]
                if left <= x <= right and top <= y <= bottom:
                    # 图片内部较不透明
                    alpha = random.randint(150, 240)
                else:
                    # 边界较透明
                    alpha = random.randint(100, 180)
                sparkle_color = (color[0], color[1], color[2], alpha)
                draw.polygon(points, fill=sparkle_color)
            else:  # dot
                # 绘制光点（圆形）
                if left <= x <= right and top <= y <= bottom:
                    # 图片内部较不透明
                    alpha = random.randint(180, 255)
                else:
                    # 边界较透明
                    alpha = random.randint(120, 200)
                sparkle_color = (color[0], color[1], color[2], alpha)
                size = random.randint(1, 2)  # 光点更小
                draw.ellipse([x-size, y-size, x+size, y+size], fill=sparkle_color)
    
    # 将闪烁效果叠加到原图
    result = Image.alpha_composite(image, sparkle)
    return result

def create_aura_effect(image: Image.Image, color: Tuple[int, int, int, int], intensity: float = 1.0) -> Image.Image:
    """
    创建柔和自然的光环效果
    """
    # 创建多个光环层以实现更自然的效果
    aura_layers = []
    
    # 获取图片边界
    bbox = image.getbbox()
    if bbox:
        # 计算基础尺寸
        left, top, right, bottom = bbox
        width = right - left
        height = bottom - top
        
        # 创建多个不同强度和大小的光环层
        for i in range(3):
            # 创建光环层
            aura = Image.new('RGBA', image.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(aura)
            
            # 根据层数调整参数
            layer_intensity = intensity * (0.8 ** i)  # 每层强度递减
            padding = int(30 * layer_intensity)
            blur_radius = int(8 * layer_intensity)
            
            # 扩大光环区域
            aura_left = left - padding
            aura_top = top - padding
            aura_right = right + padding
            aura_bottom = bottom + padding
            
            # 绘制不规则光环（使用柔和的渐变效果）
            # 外层光环
            draw.ellipse([aura_left, aura_top, aura_right, aura_bottom], 
                         outline=color, width=max(1, int(2 * layer_intensity)))
            
            # 添加一些随机的内部光环线以增强自然感
            if i == 0:  # 只在最外层添加
                for j in range(3):
                    inner_padding = padding - int(padding * 0.3 * (j + 1))
                    offset_x = random.randint(-2, 2)
                    offset_y = random.randint(-2, 2)
                    # 调整颜色透明度
                    inner_color = (color[0], color[1], color[2], max(20, int(color[3] * 0.7 * (1 - 0.2 * j))))
                    draw.ellipse([
                        left + inner_padding + offset_x, 
                        top + inner_padding + offset_y, 
                        right - inner_padding + offset_x, 
                        bottom - inner_padding + offset_y
                    ], outline=inner_color, width=1)
            
            # 应用不同程度的高斯模糊
            aura = aura.filter(ImageFilter.GaussianBlur(radius=blur_radius))
            aura_layers.append(aura)
        
        # 将所有光环层叠加
        combined_aura = Image.new('RGBA', image.size, (0, 0, 0, 0))
        for aura_layer in aura_layers:
            combined_aura = Image.alpha_composite(combined_aura, aura_layer)
        
        # 使用柔和的混合模式叠加光环效果
        result = Image.alpha_composite(image, combined_aura)
        return result
    
    # 如果没有边界框，直接返回原图
    return image

def apply_rarity_effects(image_path: str, rarity: str, output_path: str, enable_glow: bool = True, enable_aura: bool = True) -> None:
    """
    为指定稀有度的图片应用效果
    :param image_path: 输入图片路径
    :param rarity: 稀有度
    :param output_path: 输出图片路径
    :param enable_glow: 是否启用发光效果
    :param enable_aura: 是否启用光环效果
    """
    if rarity not in RARITY_CONFIG:
        raise ValueError(f"Unsupported rarity: {rarity}")
    
    config = RARITY_CONFIG[rarity]
    
    # 打开图片
    image = Image.open(image_path).convert('RGBA')
    
    # 应用效果
    if "subtle_glow" in config["effects"] and enable_glow:
        image = create_glow_effect(image, config["color"], 0.03)
    
    if "glow" in config["effects"] and enable_glow:
        image = create_glow_effect(image, config["color"], 0.05)
    
    if "particles" in config["effects"]:
        image = create_particles(image, config["color"], config["particle_count"])
    
    if "foil" in config["effects"]:
        image = create_foil_effect(image, config["foil_intensity"])
    
    if "sparkle" in config["effects"]:
        image = create_sparkle_effect(image, config["color"], 1.0)
    
    if "aura" in config["effects"] and enable_aura:
        image = create_aura_effect(image, config["color"], 1.0)
    
    # 保存结果
    image.save(output_path, "PNG")

def process_images(input_folder: str, output_folder: str, rarity_mapping: Dict[str, str], enable_glow: bool = True, enable_aura: bool = True) -> None:
    """
    处理文件夹中的所有图片
    :param input_folder: 输入文件夹路径
    :param output_folder: 输出文件夹路径
    :param rarity_mapping: 文件名到稀有度的映射
    :param enable_glow: 是否启用发光效果
    :param enable_aura: 是否启用光环效果
    """
    # 确保输出文件夹存在
    os.makedirs(output_folder, exist_ok=True)
    
    # 支持的图片格式
    supported_formats = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff')
    
    # 处理所有图片
    for filename in os.listdir(input_folder):
        if filename.lower().endswith(supported_formats):
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename)
            
            # 获取稀有度
            rarity = rarity_mapping.get(filename, "common")  # 默认为普通
            
            print(f"Processing {filename} with {RARITY_CONFIG[rarity]['name']} effects...")
            
            try:
                apply_rarity_effects(input_path, rarity, output_path, enable_glow, enable_aura)
                print(f"Saved {filename} with {RARITY_CONFIG[rarity]['name']} effects")
            except Exception as e:
                print(f"Error processing {filename}: {e}")

def create_sample_rarity_mapping(folder_path: str) -> Dict[str, str]:
    """
    创建示例稀有度映射
    """
    mapping = {}
    files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))]
    
    # 为示例分配不同稀有度
    rarities = list(RARITY_CONFIG.keys())
    for i, filename in enumerate(files):
        # 循环分配稀有度
        rarity = rarities[i % len(rarities)]
        mapping[filename] = rarity
    
    return mapping

def main():
    # 定义路径
    input_folder = "output_acrylic_text_with_icons"
    
    # 检查命令行参数
    import sys
    enable_glow = "--no-glow" not in sys.argv
    enable_aura = "--no-aura" not in sys.argv
    
    # 确定输出文件夹
    if not enable_glow and not enable_aura:
        print("Glow and aura effects disabled")
        output_folder = "output_rarity_effects_no_glow_no_aura"
    elif not enable_glow:
        print("Glow effects disabled")
        output_folder = "output_rarity_effects_no_glow"
    elif not enable_aura:
        print("Aura effects disabled")
        output_folder = "output_rarity_effects_no_aura"
    else:
        output_folder = "output_rarity_effects"
    
    # 创建示例稀有度映射文件
    mapping_file = "rarity_mapping.json"
    if not os.path.exists(mapping_file):
        print("Creating sample rarity mapping...")
        sample_mapping = create_sample_rarity_mapping(input_folder)
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(sample_mapping, f, ensure_ascii=False, indent=2)
        print(f"Sample rarity mapping saved to {mapping_file}")
        print("Please edit this file to set the correct rarity for each image.")
        return
    
    # 读取稀有度映射
    with open(mapping_file, 'r', encoding='utf-8') as f:
        rarity_mapping = json.load(f)
    
    # 处理图片
    print("Processing images with rarity effects...")
    process_images(input_folder, output_folder, rarity_mapping, enable_glow, enable_aura)
    print("All images processed!")

if __name__ == "__main__":
    main()