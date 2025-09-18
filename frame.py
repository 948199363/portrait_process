from PIL import Image
import os

def overlay_frames_on_image(input_image_path, frame_dir, output_dir):
    """
    将frame_dir中的所有frame图片叠加到指定的input_image_path图片上，并保存到output_dir。
    支持常见图片格式。
    """
    base_img = Image.open(input_image_path).convert("RGBA")
    input_filename_base = os.path.splitext(os.path.basename(input_image_path))[0]

    for frame_filename in os.listdir(frame_dir):
        if frame_filename.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")) & (frame_filename.lower().startswith("frame")):
            frame_path = os.path.join(frame_dir, frame_filename)
            frame_img = Image.open(frame_path).convert("RGBA")
            
            # 调整frame大小以匹配输入图片
            frame_resized = frame_img.resize(base_img.size, Image.Resampling.LANCZOS)
            
            # 叠加
            combined = Image.alpha_composite(base_img, frame_resized)
            
            # 保存到output目录，文件名包含输入图片和frame图片的信息
            frame_filename_base = os.path.splitext(frame_filename)[0]
            output_filename = f"{input_filename_base}_{frame_filename_base}.png"
            output_path = os.path.join(output_dir, output_filename)
            combined.save(output_path)

if __name__ == "__main__":
    # 假设输入图片是 input/1.jpg，frame图片在 frame/ 目录下
    input_image = "F:/testpy/image/input/1.jpg"
    frame_folder = "F:/testpy/image/frame/"
    output_folder = "F:/testpy/image/output/"

    # 确保frame文件夹存在
    if not os.path.exists(frame_folder):
        print(f"Error: Frame directory not found at {frame_folder}")
    else:
        overlay_frames_on_image(input_image, frame_folder, output_folder)
        print(f"Processed frames from {frame_folder} onto {input_image} and saved to {output_folder}")
