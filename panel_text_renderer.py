from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops, ImageStat, ImageOps
import os, math, json
import numpy as np
import colorsys
from typing import Tuple, Optional, Dict

# ------------- Utilities -------------
def find_cjk_font(preferred: Optional[str] = None):
    """Return a font path that supports CJK. If preferred path is valid, use it."""
    if preferred and os.path.exists(preferred):
        return preferred
    keywords = [
        "SourceHanSerifTC-Regular", "STFANGSO", "NotoSansCJK", "Noto Sans CJK",
        "NotoSansSC", "Noto Sans SC", "PingFang", "SimHei", "WenQuanYi",
        "DroidSansFallback", "NotoSerifCJK"
    ]
    search_dirs = [
        "./"
    ]
    for base in search_dirs:
        if not os.path.isdir(base): 
            continue
        for root, _, files in os.walk(base):
            for f in files:
                lf = f.lower()
                if not (lf.endswith(".ttf") or lf.endswith(".otf") or lf.endswith(".ttc")):
                    continue
                full = os.path.join(root, f)
                for kw in keywords:
                    if kw.lower().replace(" ","") in lf.replace(" ",""):
                        return full
    # Fallback to DejaVuSans if present
    for base in search_dirs:
        if not os.path.isdir(base): 
            continue
        for root, _, files in os.walk(base):
            for f in files:
                if "DejaVuSans" in f and (f.endswith(".ttf") or f.endswith(".otf")):
                    return os.path.join(root, f)
    return None

def sample_avg_color(img: Image.Image, box: Tuple[int,int,int,int]):
    region = img.crop(box).convert("RGB")
    stat = ImageStat.Stat(region)
    r, g, b = [int(x) for x in stat.mean]
    return r, g, b

def luminance(rgb):
    r,g,b = rgb
    return 0.2126*r + 0.7152*g + 0.0722*b

def clamp(v, a, b): 
    return max(a, min(b, v))

def rel_to_abs(box_rel, w, h):
    x1 = int(box_rel[0] * w)
    y1 = int(box_rel[1] * h)
    x2 = int(box_rel[2] * w)
    y2 = int(box_rel[3] * h)
    return (x1, y1, x2, y2)

def expand_box(b, dx, dy):
    x1,y1,x2,y2 = b
    return (x1-dx, y1-dy, x2+dx, y2+dy)

# ------------- Core Renderer -------------
DEFAULT_CONFIG = {
    # Layout
    "left_ratio": 0.60,           # 左区宽度比例（名字列）
    "padding_px": 16,             # panel 内边距（像素）
    "v_align": "center",          # 'center' | 'top' | 'bottom' | 数字(像素偏移，向下为正)
    "line_gap_px": 100,          # 右侧两行间距；默认按小字号的 0.25 倍
    
    # Typography
    "font_path_main": None,       # 大标题字体路径
    "font_path_small": None,      # 右侧字体路径
    "name_min_px": 18,
    "name_max_px": None,          # 若 None，自动基于可用空间
    "small_min_px": 14,
    "small_max_px": None,
    "rarity_min_px": 14,
    "rarity_max_px": None,
    "number_min_px": 14,
    "number_max_px": None,
    "ellipsis": True,             # 如无法缩小到适应，末尾加省略号
    
    # Colors (auto or manual)
    "auto_color": True,           # 从 panel 内采样背景，自动选择浅/深文字色
    "text_color_light": (242,245,248,238),
    "text_color_dark":  (30,33,36,238),
    "stroke_color_light": (255,255,255,90),
    "stroke_color_dark":  (0,0,0,90),
    "use_stroke": True,
    "stroke_width": 1,
    
    # Effects
    "drop_shadow": True,
    "shadow_offset": (0,1),
    "shadow_blur": 2.0,
    "shadow_opacity": 120,  # 0-255
    "outer_glow": True,
    "glow_radius": 3.0,
    "glow_opacity": 60,     # 0-255
    "backplate": True,      # 在文字下铺一层轻微半透明圆角底
    "backplate_alpha": 70,  # 0-255
    "backplate_radius": 10,
    
    # Debug
    "debug_draw_boxes": False,  # 绘制 panel 和内容框辅助线
    # Positioning (pixel offsets applied after layout). Each is (x_px, y_px).
    # Positive x moves right, positive y moves down. Anchors use Pillow text anchor strings.
    "offset_name": (0, 0),
    "offset_rarity": (0, 0),
    "offset_number": (0, 0),
    # Anchor for each text. Default keeps previous behavior: name left-top, rarity/number right-top
    "anchor_name": "lt",
    "anchor_rarity": "rt",
    "anchor_number": "rt",

    # Super-sampling for anti-aliasing
    "supersample_factor": 4,
}



class AcrylicPanelTextRenderer:
    def __init__(self, image: Image.Image, panel_box: Tuple[int,int,int,int]):
        self.img = image.convert("RGBA")
        self.panel = panel_box
        self.w, self.h = self.img.size
    
    @staticmethod
    def _fit_font_to_box(draw, text, font_path, min_px, max_px, max_w, max_h, allow_ellipsis=True, scale_factor: int = 1):
        """Return font, text_w, text_h, size, possibly ellipsized text."""
        # Scale input dimensions for fitting
        min_px_scaled = min_px * scale_factor
        max_w_scaled = max_w * scale_factor
        max_h_scaled = max_h * scale_factor
        
        # If max_px unset, start from height
        if max_px is None:
            max_px_scaled = int(max_h_scaled * 0.95)
        else:
            max_px_scaled = max_px * scale_factor

        size_scaled = max(min_px_scaled, max_px_scaled)
        last_ok = None
        while size_scaled >= min_px_scaled:
            try:
                f = ImageFont.truetype(font_path, size_scaled) if font_path else ImageFont.load_default()
            except Exception:
                f = ImageFont.load_default()
            bbox = draw.textbbox((0,0), text, font=f)
            tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
            if tw <= max_w_scaled and th <= max_h_scaled:
                last_ok = (f, tw, th, size_scaled, text)
                break
            size_scaled -= 1
        if last_ok:
            return last_ok
        # Try ellipsis if still too big
        if allow_ellipsis:
            for cut in range(len(text), 0, -1):
                t = text[:cut] + "…"
                size_scaled = min_px_scaled
                try:
                    f = ImageFont.truetype(font_path, size_scaled) if font_path else ImageFont.load_default()
                except Exception:
                    f = ImageFont.load_default()
                bbox = draw.textbbox((0,0), t, font=f)
                tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
                if tw <= max_w_scaled and th <= max_h_scaled:
                    return (f, tw, th, size_scaled, t)
            try:
                f = ImageFont.truetype(font_path, min_px_scaled) if font_path else ImageFont.load_default()
            except Exception:
                f = ImageFont.load_default()
            bbox = draw.textbbox((0,0), text, font=f)
            return (f, bbox[2]-bbox[0], bbox[3]-bbox[1], min_px_scaled, text)
    
    def _sample_frame_color(self, img: Image.Image, mode="bottom", band=0.05):
        """返回 (r,g,b)，从图像边缘区域取主色；bottom 模式更贴近下边框。"""
        rgb = img.convert("RGB")
        W, H = rgb.size
        arr = np.asarray(rgb, dtype=np.uint8)
        if mode == "bottom":
            t = max(1, int(H * band))
            x0, x1 = int(W * 0.06), int(W * 0.94)  # 避开四角
            region = arr[H-t:H-1, x0:x1, :]
        else:  # ring：四边取样
            t = max(1, int(min(W, H) * band))
            mask = np.zeros((H, W), dtype=bool)
            mask[:t, :] = True
            mask[H-t:, :] = True
            mask[:, :t] = True
            mask[:, W-t:] = True
            region = arr[mask]
        if region.size == 0:
            return (255, 255, 255)
        # 用中位数对抗噪点
        med = np.median(region.reshape(-1, 3), axis=0)
        return tuple(int(v) for v in med)

    def _auto_colors(self, cfg):
        # 从边框取样颜色
        frame_rgb = self._sample_frame_color(self.img)
        print("frame_rgb", frame_rgb)
        
        # 将边框颜色转换为HSL色彩空间，以便更容易调整
        frame_r, frame_g, frame_b = frame_rgb
        frame_h, frame_l, frame_s = colorsys.rgb_to_hls(frame_r/255.0, frame_g/255.0, frame_b/255.0)
        
        # 根据边框亮度调整文字亮度，但保持在同一色调范围内
        # 如果边框较亮，文字稍微暗一些；如果边框较暗，文字稍微亮一些
        if frame_l > 0.7:
            # 边框很亮，文字稍微暗一些
            text_l = max(0.6, frame_l - 0.2)
        elif frame_l < 0.5:
            # 边框很暗，文字稍微亮一些
            text_l = min(0.6, frame_l + 0.2)
        else:
            # 边框中等，文字保持中等亮度
            text_l = frame_l
        
        # 保持一定的饱和度以确保文字颜色丰富
        text_s = max(0.3, frame_s)
        
        # # 特殊处理：如果边框是接近灰色的，给文字增加一些色彩
        # if frame_s < 0.15:
        #     # 边框接近灰色，给文字增加一些色彩
        #     text_s = max(0.3, text_s + 0.4)
        
        # 转换回RGB色彩空间
        text_r, text_g, text_b = colorsys.hls_to_rgb(frame_h, text_l, text_s)
        
        # 调整RGB值确保足够的对比度但保持色调一致
        text_rgb = (int(text_r * 255), int(text_g * 255), int(text_b * 255))
        
        # 进一步调整确保对比度
        frame_lum = luminance(frame_rgb)
        text_lum = luminance(text_rgb)
        
        # 检查对比度，如果不够则进一步调整
        if frame_lum > text_lum:
            contrast = frame_lum / (text_lum + 0.1)
        else:
            contrast = text_lum / (frame_lum + 0.1)
            
        if contrast < 2.0:  # 最小对比度要求（比之前更低）
            if frame_lum > 128:
                # 边框亮，文字稍微暗一些
                text_rgb = (
                    max(0, min(255, int(text_rgb[0] * 0.85))), 
                    max(0, min(255, int(text_rgb[1] * 0.85))), 
                    max(0, min(255, int(text_rgb[2] * 0.85)))
                )
            else:
                # 边框暗，文字稍微亮一些
                text_rgb = (
                    max(0, min(255, int(255 - (255 - text_rgb[0]) * 0.7))), 
                    max(0, min(255, int(255 - (255 - text_rgb[1]) * 0.7))), 
                    max(0, min(255, int(255 - (255 - text_rgb[2]) * 0.7)))
                )
        
        # 确定描边颜色（基于文字颜色但稍微加强对比度）
        text_lum_final = luminance(text_rgb)
        if text_lum_final > 128:
            # 文字较亮，使用稍暗的描边
            stroke_rgb = (
                max(0, int(text_rgb[0] * 0.7)), 
                max(0, int(text_rgb[1] * 0.7)), 
                max(0, int(text_rgb[2] * 0.7))
            )
            glow_color = (0, 0, 0, cfg["glow_opacity"])
        else:
            # 文字较暗，使用稍亮的描边
            stroke_rgb = (
                min(255, int(255 - (255 - text_rgb[0]) * 0.7)), 
                min(255, int(255 - (255 - text_rgb[1]) * 0.7)), 
                min(255, int(255 - (255 - text_rgb[2]) * 0.7))
            )
            glow_color = (255, 255, 255, cfg["glow_opacity"])

        # 如果base亮度不够，统一拉高
        if luminance(text_rgb) < 150:
            text_rgb = tuple(clamp(c + 60, 0, 255) for c in text_rgb)

        # 添加透明度
        base = (*text_rgb, 238)
        stroke = (*stroke_rgb, 120)  # 增加描边透明度
        
        return base, stroke, glow_color
    
    def render(self, name, rarity, number, cfg: Dict):
        # Load config from config.json if exists
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                file_config = json.load(f)
            cfg_full = dict(DEFAULT_CONFIG)
            cfg_full.update(file_config)
            cfg_full.update(cfg or {})
        else:
            cfg_full = dict(DEFAULT_CONFIG)
            cfg_full.update(cfg or {})
        
        scale_factor = cfg_full.get("supersample_factor", 1)
        scaled_w, scaled_h = self.w * scale_factor, self.h * scale_factor
        scaled_panel = tuple(int(c * scale_factor) for c in self.panel)

        # Colors
        if cfg_full["auto_color"]:
            base_color, stroke_color, glow_color = self._auto_colors(cfg_full)
        else:
            base_color = tuple(cfg_full.get("text_color_light", (242,245,248,238)))
            stroke_color = tuple(cfg_full.get("stroke_color_light", (255,255,255,90)))
            glow_color = (0,0,0,cfg_full["glow_opacity"])
        
        # Content area (padding) - scaled
        x1,y1,x2,y2 = scaled_panel
        padding_px_scaled = cfg_full["padding_px"] * scale_factor
        x1 += padding_px_scaled; y1 += padding_px_scaled
        x2 -= padding_px_scaled; y2 -= padding_px_scaled
        content = (x1,y1,x2,y2)
        cw, ch = (x2-x1, y2-y1)
        left_w = int(cw * cfg_full["left_ratio"])
        right_w = cw - left_w
        
        # Create high-resolution layers
        text_layer_hr  = Image.new("RGBA", (scaled_w, scaled_h), (0,0,0,0))
        glow_layer_hr  = Image.new("RGBA", (scaled_w, scaled_h), (0,0,0,0))
        shadow_layer_hr= Image.new("RGBA", (scaled_w, scaled_h), (0,0,0,0))
        backplate_layer_hr = Image.new("RGBA", (scaled_w, scaled_h), (0,0,0,0))
        
        draw_text_hr   = ImageDraw.Draw(text_layer_hr)
        draw_glow_hr   = ImageDraw.Draw(glow_layer_hr)
        draw_shadow_hr = ImageDraw.Draw(shadow_layer_hr)
        draw_bp_hr     = ImageDraw.Draw(backplate_layer_hr)
        
        # Vertical alignment baseline - scaled
        if isinstance(cfg_full["v_align"], (int, float)):
            v_offset = int(cfg_full["v_align"] * scale_factor)
            top = y1 + v_offset
            bottom = y2 + v_offset
        else:
            top, bottom = y1, y2
        
        # Fit fonts - passing scale_factor
        name_box_w = left_w
        name_box_h = (bottom - top)
        name_font, name_tw, name_th, name_fs, name_text = self._fit_font_to_box(
            draw_text_hr, name, cfg_full["font_path_main"] or cfg_full["font_path_small"] or find_cjk_font(),
            cfg_full["name_min_px"], cfg_full["name_max_px"], name_box_w, name_box_h, allow_ellipsis=cfg_full["ellipsis"], scale_factor=scale_factor
        )
        right_box_h = (bottom - top)
        # Two lines must fit together
        small_font_path = cfg_full["font_path_small"] or cfg_full["font_path_main"] or find_cjk_font()
        # We'll find a size that fits both, by binary search on size possibly
        def fit_small_scaled(text, max_w, max_h, min_px, max_px, scale_factor):
            min_px_scaled = min_px * scale_factor
            max_w_scaled = max_w * scale_factor
            max_h_scaled = max_h * scale_factor

            if max_px is None: max_px_scaled = int(max_h_scaled*0.6)
            else: max_px_scaled = max_px * scale_factor

            size_scaled = max(min_px_scaled, max_px_scaled)
            ok = None
            while size_scaled >= min_px_scaled:
                try:
                    f = ImageFont.truetype(small_font_path, size_scaled) if small_font_path else ImageFont.load_default()
                except Exception:
                    f = ImageFont.load_default()
                bbox = draw_text_hr.textbbox((0,0), text, font=f)
                tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
                if tw <= max_w_scaled and th <= max_h_scaled:
                    ok = (f, tw, th, size_scaled, text); break
                size_scaled -= 1
            if ok: return ok
            # try ellipsis
            t = text
            for cut in range(len(text), 0, -1):
                t = text[:cut] + "…"
                size_scaled = min_px_scaled
                try:
                    f = ImageFont.truetype(small_font_path, size_scaled) if font_path else ImageFont.load_default()
                except Exception:
                    f = ImageFont.load_default()
                bbox = draw_text_hr.textbbox((0,0), t, font=f)
                tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
                if tw <= max_w_scaled and th <= max_h_scaled:
                    return (f, tw, th, size_scaled, t)
            try:
                f = ImageFont.truetype(small_font_path, min_px_scaled) if font_path else ImageFont.load_default()
            except Exception:
                f = ImageFont.load_default()
            bbox = draw_text_hr.textbbox((0,0), text, font=f)
            return (f, bbox[2]-bbox[0], bbox[3]-bbox[1], min_px_scaled, text)
        
        # We'll first fit each line to half height minus gap; later enforce combined fit
        half_h = right_box_h//2
        rarity_pack = fit_small_scaled(rarity, right_w, half_h, cfg_full["rarity_min_px"], cfg_full["rarity_max_px"], scale_factor)
        number_pack = fit_small_scaled(number, right_w, half_h, cfg_full["number_min_px"], cfg_full["number_max_px"], scale_factor)
        rarity_font, rarity_tw, rarity_th, rarity_fs, rarity_text = rarity_pack
        number_font, number_tw, number_th, number_fs, number_text = number_pack
        
        # Ensure both lines + gap fit vertically - scaled
        line_gap_scaled = (cfg_full["line_gap_px"] * scale_factor) if cfg_full["line_gap_px"] is not None else max(2, int(min(rarity_fs, number_fs)*0.25))
        total_h = rarity_th + number_th + line_gap_scaled
        if total_h > right_box_h:
            # scale down proportionally
            scale = right_box_h / total_h
            # Calculate new sizes based on their respective min_px and the overall scale
            new_rarity_size_scaled = max(cfg_full["rarity_min_px"] * scale_factor, int(rarity_fs * scale))
            new_number_size_scaled = max(cfg_full["number_min_px"] * scale_factor, int(number_fs * scale))
            try:
                rarity_font = ImageFont.truetype(small_font_path, new_rarity_size_scaled)
                number_font = ImageFont.truetype(small_font_path, new_number_size_scaled)
            except Exception:
                rarity_font = number_font = ImageFont.load_default()
            rarity_bbox = draw_text_hr.textbbox((0,0), rarity_text, font=rarity_font)
            number_bbox = draw_text_hr.textbbox((0,0), number_text, font=number_font)
            rarity_tw, rarity_th = rarity_bbox[2]-rarity_bbox[0], rarity_bbox[3]-rarity_bbox[1]
            number_tw, number_th = number_bbox[2]-number_bbox[0], number_bbox[3]-number_bbox[1]
            # Recalculate line_gap based on potentially different new font sizes
            line_gap_scaled = (cfg_full["line_gap_px"] * scale_factor) if cfg_full["line_gap_px"] is not None else max(2, int(min(new_rarity_size_scaled, new_number_size_scaled)*0.25))
            total_h = rarity_th + number_th + line_gap_scaled
        
        # Coordinates (base positions before offsets) - scaled
        left_x = x1
        if cfg_full["v_align"] == "top":
            left_y = top
        elif cfg_full["v_align"] == "bottom":
            left_y = bottom - name_th
        elif isinstance(cfg_full["v_align"], (int,float)):  # already offset top/bottom above
            left_y = top + (right_box_h - name_th)//2
        else: # center
            left_y = top + (right_box_h - name_th)//2

        right_x_right = x2
        if cfg_full["v_align"] == "top":
            rarity_y = top
        elif cfg_full["v_align"] == "bottom":
            rarity_y = bottom - total_h
        else:
            rarity_y = top + (right_box_h - total_h)//2
        number_y = rarity_y + rarity_th + line_gap_scaled

        # Apply configured pixel offsets (tuple) — allow lists too - scaled
        def to_xy_scaled(v, scale):
            if v is None: return (0,0)
            try:
                return (int(v[0] * scale), int(v[1] * scale))
            except Exception:
                return (0,0)

        off_name = to_xy_scaled(cfg_full.get("offset_name", (0,0)), scale_factor)
        off_rarity = to_xy_scaled(cfg_full.get("offset_rarity", (0,0)), scale_factor)
        off_number = to_xy_scaled(cfg_full.get("offset_number", (0,0)), scale_factor)

        left_x += off_name[0]; left_y += off_name[1]
        # rarity aligned to right_x_right (rt by default) so x is right edge
        right_x_right = right_x_right + off_rarity[0]  # keep base
        rarity_x = right_x_right
        rarity_y = rarity_y + off_rarity[1]
        number_x = right_x_right 
        number_y = number_y + off_number[1]

        # Anchors
        anchor_name = cfg_full.get("anchor_name", "lt")
        anchor_rarity = cfg_full.get("anchor_rarity", "rt")
        anchor_number = cfg_full.get("anchor_number", "rt")
        
        # Optional backplate (rounded rects behind left and right blocks) - scaled
        if cfg_full["backplate"]:
            bp_alpha = cfg_full["backplate_alpha"]
            bp_color = (0,0,0,bp_alpha) if luminance(sample_avg_color(self.img, self.panel))>180 else (255,255,255,bp_alpha)
            # Left plate
            left_plate = (left_x-6*scale_factor, left_y-4*scale_factor, left_x + name_tw + 6*scale_factor, left_y + name_th + 6*scale_factor)
            right_plate = (right_x_right - max(rarity_tw, number_tw) - 6*scale_factor, rarity_y-4*scale_factor, right_x_right + 6*scale_factor, number_y + number_th + 6*scale_factor)
            for plate in [left_plate, right_plate]:
                rx = cfg_full["backplate_radius"] * scale_factor
                shape = Image.new("L", (scaled_w, scaled_h), 0)
                d = ImageDraw.Draw(shape)
                d.rounded_rectangle(plate, radius=rx, fill=255)
                colored = Image.new("RGBA", (scaled_w, scaled_h), bp_color)
                backplate_layer_hr = Image.composite(colored, Image.new("RGBA", (scaled_w, scaled_h), (0,0,0,0)), shape)
                backplate_layer = backplate_layer_hr.resize((self.w, self.h), Image.Resampling.LANCZOS)
                self.img = Image.alpha_composite(self.img, backplate_layer)
        
        # Shadow + Glow draw helpers
        def draw_text_effects_hr(draw_target_hr, text, pos_hr, font_hr, anchor):
            # Shadow
            if cfg_full["drop_shadow"]:
                sx, sy = cfg_full["shadow_offset"]
                draw_shadow_hr.text((pos_hr[0]+sx*scale_factor, pos_hr[1]+sy*scale_factor), text, font=font_hr, fill=(0,0,0,cfg_full["shadow_opacity"]), anchor=anchor)
            # Glow
            if cfg_full["outer_glow"]:
                draw_glow_hr.text(pos_hr, text, font=font_hr, fill=(255,255,255), anchor=anchor)  # stencil
            # Main text
            if cfg_full["use_stroke"]:
                draw_target_hr.text(pos_hr, text, font=font_hr, fill=base_color, anchor=anchor,
                                 stroke_width=cfg_full["stroke_width"] * scale_factor, stroke_fill=stroke_color)
            else:
                draw_target_hr.text(pos_hr, text, font=font_hr, fill=base_color, anchor=anchor)
        
        # Draw texts with configurable anchors and offsets on high-res layers
        draw_text_effects_hr(draw_text_hr, name_text, (left_x, left_y), name_font, anchor_name)
        draw_text_effects_hr(draw_text_hr, rarity_text, (rarity_x, rarity_y), rarity_font, anchor_rarity)
        draw_text_effects_hr(draw_text_hr, number_text, (number_x, number_y), number_font, anchor_number)

        # Apply filters, downscale and composite layers
        if cfg_full["drop_shadow"]:
            shadow_layer_hr = shadow_layer_hr.filter(ImageFilter.GaussianBlur(cfg_full["shadow_blur"] * scale_factor))
            shadow_layer = shadow_layer_hr.resize((self.w, self.h), Image.Resampling.LANCZOS)
            self.img = Image.alpha_composite(self.img, shadow_layer)

        if cfg_full["outer_glow"]:
            glow_layer_hr = glow_layer_hr.filter(ImageFilter.GaussianBlur(cfg_full["glow_radius"] * scale_factor))
            tint_hr = Image.new("RGBA", (scaled_w, scaled_h), glow_color)
            glow_layer_hr = ImageChops.multiply(glow_layer_hr, tint_hr)
            glow_layer = glow_layer_hr.resize((self.w, self.h), Image.Resampling.LANCZOS)
            self.img = Image.alpha_composite(self.img, glow_layer)

        text_layer = text_layer_hr.resize((self.w, self.h), Image.Resampling.LANCZOS)
        self.img = Image.alpha_composite(self.img, text_layer)
        
        # Debug boxes - scaled
        if cfg_full["debug_draw_boxes"]:
            dbg = ImageDraw.Draw(self.img)
            # Need to scale panel and content box coordinates back down for debug drawing on self.img
            original_panel = tuple(int(c / scale_factor) for c in scaled_panel)
            original_content_box = tuple(int(c / scale_factor) for c in content)
            original_left_col = tuple(int(c / scale_factor) for c in (x1, y1, x1+left_w, y2))
            original_right_col = tuple(int(c / scale_factor) for c in (x1+left_w, y1, x2, y2))

            dbg.rectangle(original_panel, outline=(0,255,0,200), width=2)  # panel
            dbg.rectangle(original_content_box, outline=(255,165,0,200), width=2)  # padded content
            # left and right content columns
            dbg.rectangle(original_left_col, outline=(0,0,255,200), width=1)
            dbg.rectangle(original_right_col, outline=(255,0,0,200), width=1)
        
        return self.img

def render_panel_text(
    input_path: str,
    output_path: str,
    name: str,
    rarity: str,
    number: str,
    # Panel box：可以传 panel_box 或 panel_box_rel (0-1)
    panel_box: Optional[Tuple[int,int,int,int]] = None,
    panel_box_rel: Optional[Tuple[float,float,float,float]] = None,
    config: Optional[Dict] = None
):
    base_img = Image.open(input_path).convert("RGBA")
    w, h = base_img.size
    if panel_box is None and panel_box_rel is None:
        # 默认猜测：图底部中间区域（相对安全）
        panel_box_rel = (0.10, 0.78, 0.90, 0.90)
    if panel_box is None:
        panel_box = rel_to_abs(panel_box_rel, w, h)
    
    # Load full config including defaults and any file-based config
    full_config = dict(DEFAULT_CONFIG)
    config_file_path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_file_path):
        with open(config_file_path, "r", encoding="utf-8") as f:
            file_config = json.load(f)
        full_config.update(file_config)
    full_config.update(config or {}) # Overlay user-provided config last

    renderer = AcrylicPanelTextRenderer(base_img, panel_box)
    out = renderer.render(name, rarity, number, full_config)
    out.save(output_path)
    return output_path

if __name__ == "__main__":
        # 批量处理 output_acrylic 文件夹中所有图片
        import sys, json, os
        config_path = sys.argv[1]
        with open(config_path, "r", encoding="utf-8") as f:
            opts = json.load(f)
        name = opts.get("name", "吴宣仪")
        rarity = opts.get("rarity", "N")
        number = opts.get("number", "No.001 / 100")
        panel_box = tuple(opts["panel_box"]) if "panel_box" in opts else None
        panel_box_rel = tuple(opts["panel_box_rel"]) if "panel_box_rel" in opts else None

        input_folder = "output_acrylic"
        output_folder = "output_acrylic_text"
        os.makedirs(output_folder, exist_ok=True)

        for fname in os.listdir(input_folder):
            if fname.lower().endswith((".png", ".jpg", ".jpeg")):
                input_path = os.path.join(input_folder, fname)
                output_path = os.path.join(output_folder, fname)
                print(f"Processing {input_path} -> {output_path}")
                render_panel_text(input_path, output_path, name, rarity, number, panel_box, panel_box_rel, opts)