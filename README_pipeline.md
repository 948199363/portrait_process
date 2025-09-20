# 图片处理流水线使用说明

这个脚本将按顺序执行以下四个步骤的图片处理流程：

1. **frame.py** - 在图片上叠加边框，并根据边框文件名确定稀有度
2. **acrylic.py** - 为图片添加亚克力效果面板
3. **panel_text_renderer.py** - 在亚克力面板上添加文本（名称、稀有度、编号等）和图标
4. **add_rarity_effects.py** - 为不同稀有度的图片添加额外的视觉效果（粒子、闪箔、发光等）

## 使用方法

### 基本用法
```bash
python img_process_pipeline.py
```

### 自定义参数
```bash
# 指定输入文件夹、边框文件夹和输出文件夹
python img_process_pipeline.py --input my_input --frame my_frames --output my_output

# 禁用发光效果
python img_process_pipeline.py --no-glow

# 禁用光环效果
python img_process_pipeline.py --no-aura

# 同时禁用发光和光环效果
python img_process_pipeline.py --no-glow --no-aura

# 清空中间输出文件夹并重新开始处理
python img_process_pipeline.py --clear
```

### 参数说明
- `--input`: 输入图片文件夹路径（默认: input）
- `--frame-dir`: 边框图片文件夹路径（默认: frame）
- `--output`: 最终输出文件夹路径（默认: output_final）
- `--no-glow`: 禁用发光效果
- `--no-aura`: 禁用光环效果
- `--clear`: 清空中间输出文件夹

## 处理流程

1. **应用边框**: 读取 `input` 文件夹中的图片和 `frame` 文件夹中的边框，随机为每张图片选择一个边框进行叠加，并根据边框文件名确定稀有度。结果保存在 `output_frames` 文件夹中。

2. **添加亚克力效果**: 在已添加边框的图片底部添加亚克力效果面板。结果保存在 `output_acrylic` 文件夹中。

3. **添加文本和图标**: 在亚克力面板上添加文本（包括名称、稀有度和编号）和对应的图标。结果先保存在 `output_acrylic_text` 文件夹中，然后添加图标后保存在 `output_acrylic_text_with_icons` 文件夹中。

4. **添加稀有度特效**: 根据图片文件名中的稀有度信息，为图片添加相应的视觉特效（粒子、闪箔、发光、光环等）。最终结果保存在以下文件夹之一：
   - 启用所有效果：`output_rarity_effects`
   - 禁用发光效果：`output_rarity_effects_no_glow`
   - 禁用光环效果：`output_rarity_effects_no_aura`
   - 同时禁用发光和光环效果：`output_rarity_effects_no_glow_no_aura`

5. **复制最终结果**: 将处理完成的图片复制到指定的最终输出文件夹中。

## 文件名格式

为了正确识别稀有度，图片文件名应遵循以下格式：
- 添加边框后的图片：`序号_人名_稀有度.png`（例如：1_刘亦菲_MYTHIC.png）
- 添加亚克力效果后的图片：`acrylic_序号_人名_稀有度.png`（例如：acrylic_1_刘亦菲_MYTHIC.png）

稀有度代码：
- C: 普通 (Common)
- UC: 罕见 (Uncommon)
- SR: 稀有 (Rare)
- R/EPIC: 史诗 (Epic)
- MYTHIC/L: 传奇 (Legendary)

## 注意事项

1. 确保所有依赖库已安装：
   ```bash
   pip install Pillow numpy
   ```

2. 确保输入文件夹中有需要处理的图片文件

3. 确保边框文件夹中有命名规范的边框图片（如 frame_C.png, frame_UC.png 等）

4. 确保 icon 文件夹中有对应稀有度的图标文件（如 C.png, UC.png 等）

5. 如果需要自定义文本渲染参数，可以修改 config.json 文件