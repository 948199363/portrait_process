from PIL import Image
import os

def overlay_frame_on_images(frame_path, input_dir, output_dir):
    """
    将frame.png叠加到input_dir中的所有图片上，并保存到output_dir。
    支持常见图片格式。
    """
    frame = Image.open(frame_path).convert("RGBA")
    for filename in os.listdir(input_dir):
        if filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")):
            img_path = os.path.join(input_dir, filename)
            img = Image.open(img_path).convert("RGBA")
            # 调整frame大小以匹配图片
            frame_resized = frame.resize(img.size)
            # 叠加
            combined = Image.alpha_composite(img, frame_resized)
            # 保存到output目录
            output_path = os.path.join(output_dir, filename)
            combined.convert("RGB").save(output_path)

if __name__ == "__main__":
    overlay_frame_on_images("frame.png", "input", "output")
