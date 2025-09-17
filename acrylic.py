from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFilter
import numpy as np, colorsys

try:
    from PIL import Image as _Image
    LANCZOS = _Image.Resampling.LANCZOS
except Exception:
    LANCZOS = Image.LANCZOS

@dataclass
class AcrylicParams:
    # ---- 尺寸与位置 ----
    width_ratio: float = 0.68
    height_ratio: float = 0.17
    anchor: str = "bottom"      # top | center | bottom
    margin_px: int = 58
    x_center_ratio: float = 0.5
    x_offset_px: int = 0
    y_offset_px: int = 0

    # ---- 圆角与边缘 ----
    corner_radius_ratio: float = 0.35
    edge_feather: float = 0.8
    supersample: int = 4

    # ---- 磨砂质感 ----
    blur_radius: float = 11
    tint_alpha: int = 85         # 0~255（整体透明度）
    noise_strength: float = 0.28 # 0~1
    noise_alpha: float = 0.18
    highlight_strength: int = 55

    # ---- 阴影 ----
    shadow_alpha: int = 110
    shadow_blur: float = 8
    shadow_offset_x: int = 2
    shadow_offset_y: int = 3

    # ---- 与边框和谐（新增）----
    harmonize: bool = True               # 开启自动取色
    harmonize_mode: str = "bottom"       # bottom | ring
    harmonize_band: float = 0.05         # 取样带厚度占比（0~0.2 建议）
    harmonize_mix_white: float = 0.55    # 与白色混合比例（0=纯边框色, 1=纯白）
    harmonize_desaturate: float = 0.6    # 去饱和比例（<1 降低饱和）
    harmonize_lift: float = 0.22         # 提升亮度（0~1）
    manual_tint_rgb: tuple | None = None # 若想手动指定色调，传 (r,g,b)

    # 可选边框（默认不要）
    add_border: bool = False
    border_color: tuple = (255,255,255,120)
    border_width: int = 2

def _rounded_mask(w, h, radius, supersample=4, feather=0.8):
    big = Image.new("L", (w*supersample, h*supersample), 0)
    d = ImageDraw.Draw(big)
    d.rounded_rectangle((0,0,big.width,big.height), radius=int(radius*supersample), fill=255)
    mask = big.resize((w,h), LANCZOS)
    if feather>0: mask = mask.filter(ImageFilter.GaussianBlur(feather))
    return mask

def _make_noise(w, h, alpha=0.18):
    arr = (np.random.rand(h, w)*255).astype(np.uint8)
    g = Image.fromarray(arr, "L")
    return Image.merge("RGBA",(g,g,g, Image.new("L",(w,h), int(alpha*255))))

def _directional_highlight(w,h,strength=55):
    g = Image.new("L",(w,h),0); px=g.load()
    for j in range(h):
        for i in range(w):
            d=(i/w)*0.55+(j/h)*0.45
            px[i,j]=int(max(0,min(255,strength*(1-d))))
    return Image.merge("RGBA",(g,g,g,g))

def _sample_frame_rgb(img: Image.Image, mode="bottom", band=0.05):
    """返回 (r,g,b)，从图像边缘区域取主色；bottom 模式更贴近下边框。"""
    rgb = img.convert("RGB"); W,H = rgb.size
    arr = np.asarray(rgb, dtype=np.uint8)
    if mode=="bottom":
        t = max(1, int(H*band))
        x0, x1 = int(W*0.06), int(W*0.94)  # 避开四角
        region = arr[H-t:H-1, x0:x1, :]
    else:  # ring：四边取样
        t = max(1, int(min(W,H)*band))
        mask = np.zeros((H,W), dtype=bool)
        mask[:t,:]=True; mask[H-t:,:]=True; mask[:, :t]=True; mask[:, W-t:]=True
        region = arr[mask]
    if region.size==0: return (255,255,255)
    # 用中位数对抗噪点
    med = np.median(region.reshape(-1,3), axis=0)
    return tuple(int(v) for v in med)

def _harmonized_tint(rgb, mix_white=0.55, desat=0.6, lift=0.22):
    r,g,b = [c/255 for c in rgb]
    h,l,s = colorsys.rgb_to_hls(r,g,b)   # 注意 HLS
    s *= desat
    l = min(1.0, l + lift)
    r2,g2,b2 = colorsys.hls_to_rgb(h,l,s)
    # 与白色混合
    r3 = r2*(1-mix_white) + 1.0*mix_white
    g3 = g2*(1-mix_white) + 1.0*mix_white
    b3 = b2*(1-mix_white) + 1.0*mix_white
    return (int(r3*255), int(g3*255), int(b3*255))

def acrylic_overlay(in_path: str, out_path: str, p: AcrylicParams = AcrylicParams()):
    base = Image.open(in_path).convert("RGBA"); W,H = base.size
    rect_w, rect_h = int(p.width_ratio*W), int(p.height_ratio*H)
    radius = max(6, int(p.corner_radius_ratio*rect_h))
    cx = int(p.x_center_ratio*W) + p.x_offset_px
    x = max(0, min(W-rect_w, int(cx-rect_w/2)))
    if p.anchor=="top": y = p.margin_px
    elif p.anchor=="center": y = int((H-rect_h)/2)
    else: y = H - p.margin_px - rect_h
    y = max(0, min(H-rect_h, y + p.y_offset_px))

    rr_mask = _rounded_mask(rect_w, rect_h, radius, p.supersample, p.edge_feather)
    region = base.crop((x,y,x+rect_w,y+rect_h)).filter(ImageFilter.GaussianBlur(p.blur_radius))

    # ==== 关键：用边框色调生成亚克力填充色 ====
    if p.manual_tint_rgb is not None:
        tint_rgb = _harmonized_tint(p.manual_tint_rgb, p.harmonize_mix_white, p.harmonize_desaturate, p.harmonize_lift)
    elif p.harmonize:
        frame_rgb = _sample_frame_rgb(base, p.harmonize_mode, p.harmonize_band)
        tint_rgb = _harmonized_tint(frame_rgb, p.harmonize_mix_white, p.harmonize_desaturate, p.harmonize_lift)
    else:
        tint_rgb = (255,255,255)  # 纯白

    tint = Image.new("RGBA",(rect_w,rect_h), (*tint_rgb, p.tint_alpha))
    region = Image.alpha_composite(region, tint)

    # 纹理（内缩，避免边缘粗糙）
    noise = _make_noise(rect_w, rect_h, p.noise_alpha)
    if p.noise_strength>0:
        inset=6; inner=Image.new("L",(rect_w,rect_h),0)
        d=ImageDraw.Draw(inner)
        d.rounded_rectangle((inset,inset,rect_w-inset,rect_h-inset),
                            radius=max(3, radius-inset), fill=int(255*p.noise_strength))
        region = Image.alpha_composite(region, Image.composite(noise, Image.new("RGBA",(rect_w,rect_h),(0,0,0,0)), inner))

    if p.highlight_strength>0:
        region = Image.alpha_composite(region, _directional_highlight(rect_w,rect_h,p.highlight_strength))

    overlay = Image.new("RGBA", base.size, (0,0,0,0))
    overlay.paste(region, (x,y), rr_mask)

    # 阴影
    out = base
    if p.shadow_alpha>0 and p.shadow_blur>0:
        sh = rr_mask.filter(ImageFilter.GaussianBlur(3)).filter(ImageFilter.GaussianBlur(p.shadow_blur))
        sh_rgba = Image.new("RGBA",(rect_w,rect_h),(0,0,0,p.shadow_alpha)); sh_rgba.putalpha(sh)
        shadow_canvas = Image.new("RGBA", base.size, (0,0,0,0))
        shadow_canvas.paste(sh_rgba,(x+p.shadow_offset_x, y+p.shadow_offset_y), sh)
        out = Image.alpha_composite(out, shadow_canvas)

    out = Image.alpha_composite(out, overlay)

    # 可选描边（默认为关）
    if p.add_border and p.border_width>0:
        d=ImageDraw.Draw(out)
        d.rounded_rectangle((x,y,x+rect_w,y+rect_h), radius=radius,
                            outline=p.border_color, width=p.border_width)

    out.save(out_path,"PNG"); return out_path


if __name__ == "__main__":
    # ===== 示例 1：与你当前需求相同 =====
    params = AcrylicParams(
        width_ratio=0.68,
        height_ratio=0.10,
        anchor="bottom",      # 贴近下边框
        margin_px=90,         # “往上一点点”，可微调 40~80 之间
        x_center_ratio=0.5,
        x_offset_px=0,
        y_offset_px=0,
        corner_radius_ratio=0.35,
        edge_feather=0.8,
        supersample=4,
        blur_radius=11,
        # tint_white_alpha=55,  # 半透明度（整体明亮/磨砂感）
        noise_strength=0.28,  # 亚克力纹理强度（0 关 / 0.15~0.35 轻微）
        noise_alpha=0.18,
        highlight_strength=55,
        shadow_alpha=0,     # 阴影透明度（0 关）
        shadow_blur=8,
        shadow_offset_x=2,
        shadow_offset_y=3,
        add_border=False,      # 你要求不要描边
        harmonize=True, harmonize_mode="bottom",
        harmonize_band=0.05,           # 取样带厚度
        harmonize_mix_white=0.0,      # 与白色混合程度
        harmonize_desaturate=0.6,      # 降饱和
        harmonize_lift=0.22,           # 提亮
    )

    in_img = "output/1.jpg"      # ← 换成你的原图路径
    out_img = "output_acrylic.png"
    print(acrylic_overlay(in_img, out_img, params))

    # ===== 示例 2：放到顶部、更小、更透明 =====
    # params2 = AcrylicParams(width_ratio=0.6, height_ratio=0.14, anchor="top", margin_px=36,
    #                         tint_white_alpha=70, shadow_alpha=90)
    # print(acrylic_overlay("input.png", "output_top.png", params2))
