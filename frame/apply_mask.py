from PIL import Image

def apply_mask_to_source(source_path, mask_path, output_path):
    """
    使用遮罩处理source图像，保留边框部分，使中间部分透明
    
    参数:
    source_path: 源图像路径
    mask_path: 遮罩图像路径
    output_path: 输出图像路径
    """
    # 打开源图像和遮罩
    source = Image.open(source_path).convert('RGB')
    mask = Image.open(mask_path)
    
    # 将遮罩转换为RGBA模式，以便我们可以使用它作为alpha通道
    mask_rgba = mask.convert('RGBA')
    
    # 创建一个带有透明背景的新图像
    result = Image.new('RGBA', source.size, (0, 0, 0, 0))
    
    # 将源图像粘贴到结果图像中，使用遮罩作为alpha通道
    result.paste(source, (0, 0), mask)
    
    # 保存结果
    result.save(output_path)
    print(f"结果图像已保存到 {output_path}")

if __name__ == "__main__":
    # 应用遮罩
    apply_mask_to_source("source.png", "mask.png", "frame_output.png")