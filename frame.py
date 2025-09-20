from PIL import Image
import os
import argparse
import random
import re

def check_path_exists(path, description):
    """检查路径是否存在，如果不存在则抛出异常"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"{description} not found at {path}")

def get_rarity_code_from_frame_filename(frame_filename):
    """
    直接从frame文件名提取稀有度代码（例如 frame_C.png -> C）
    """
    # 移除扩展名
    name_without_ext = os.path.splitext(frame_filename)[0]
    
    # 提取稀有度标识 (如 frame_C.png -> C, frame_EPIC.png -> EPIC)
    rarity_match = re.search(r'frame_(.+)', name_without_ext, re.IGNORECASE)
    if rarity_match:
        return rarity_match.group(1).upper()
    return "C"  # 默认为C

def extract_name_and_index(filename):
    """
    从文件名中提取序号和人名
    文件名格式为: swapped_序号_人名_职业_数值1_数值2-batch_job_xxx-序号.png
    """
    # 移除扩展名
    name_without_ext = os.path.splitext(filename)[0]
    
    # 按照swapped_分割
    if name_without_ext.startswith("swapped_"):
        # 移除"swapped_"前缀
        name_part = name_without_ext[8:]  # "swapped_"是8个字符
        
        # 按照"-"分割，取第一部分
        dash_parts = name_part.split('-')
        main_part = dash_parts[0]
        
        # 按照"_"分割
        parts = main_part.split('_')
        if len(parts) >= 3:
            # 第一个部分是序号，第二个部分是人名
            index = parts[0]
            name = parts[1]
            return index, name
    
    # 如果无法解析，返回默认值
    return "0", "unknown"

def overlay_frames_on_images(input_dir, frame_dir, output_dir):
    """
    处理输入路径下的所有图片，随机选取边框叠加，并在生成的图片名中使用序号_人名_稀有度.png格式。
    稀有度直接使用frame文件名中的标识符（例如C）。
    """
    try:
        # 检查输入路径
        check_path_exists(input_dir, "Input directory")
        
        # 检查frame文件夹路径
        check_path_exists(frame_dir, "Frame directory")
        
        # 确保输出文件夹存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取所有边框文件
        frame_files = [
            f for f in os.listdir(frame_dir)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")) and f.lower().startswith("frame")
        ]
        
        if not frame_files:
            raise ValueError("No valid frame files found in the frame directory.")
        
        # 处理输入路径下的所有图片
        for input_filename in os.listdir(input_dir):
            if input_filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")):
                input_path = os.path.join(input_dir, input_filename)
                base_img = Image.open(input_path).convert("RGBA")
                
                # 随机选择一个边框
                frame_filename = random.choice(frame_files)
                frame_path = os.path.join(frame_dir, frame_filename)
                frame_img = Image.open(frame_path).convert("RGBA")
                
                # 调整frame大小以匹配输入图片
                frame_resized = frame_img.resize(base_img.size, Image.Resampling.LANCZOS)
                
                # 叠加
                combined = Image.alpha_composite(base_img, frame_resized)
                
                # 直接从frame文件名获取稀有度代码
                rarity_code = get_rarity_code_from_frame_filename(frame_filename)
                
                # 从输入文件名提取序号和人名
                index, person_name = extract_name_and_index(input_filename)
                
                # 生成新的文件名格式: 序号_人名_稀有度.png
                output_filename = f"{index}_{person_name}_{rarity_code}.png"
                output_path = os.path.join(output_dir, output_filename)
                combined.save(output_path)
                print(f"Processed {input_filename} with frame {frame_filename} and saved to {output_path}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # 使用命令行参数动态指定路径
    parser = argparse.ArgumentParser(description='Overlay random frames on images and mark rarity.')
    parser.add_argument('--input', required=True, help='Path to the input directory')
    parser.add_argument('--frame', required=True, help='Path to the frame directory')
    parser.add_argument('--output', required=True, help='Path to the output directory')
    args = parser.parse_args()
    
    overlay_frames_on_images(args.input, args.frame, args.output)
