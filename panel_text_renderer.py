from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops, ImageStat, ImageOps
import os, math, json
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
}



class AcrylicPanelTextRenderer:
    def __init__(self, image: Image.Image, panel_box: Tuple[int,int,int,int]):
        self.img = image.convert("RGBA")
        self.panel = panel_box
        self.w, self.h = self.img.size
    
    @staticmethod
    def _fit_font_to_box(draw, text, font_path, min_px, max_px, max_w, max_h, allow_ellipsis=True):
        """Return font, text_w, text_h, size, possibly ellipsized text."""
        # If max_px unset, start from height
        if max_px is None:
            max_px = int(max_h * 0.95)
        size = max(min_px, max_px)
        last_ok = None
        while size >= min_px:
            try:
                f = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
            except Exception:
                f = ImageFont.load_default()
            bbox = draw.textbbox((0,0), text, font=f)
            tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
            if tw <= max_w and th <= max_h:
                last_ok = (f, tw, th, size, text)
                break
            size -= 1
        if last_ok:
            return last_ok
        # Try ellipsis if still too big
        if allow_ellipsis:
            for cut in range(len(text), 0, -1):
                t = text[:cut] + "…"
                size = min_px
                try:
                    f = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
                except Exception:
                    f = ImageFont.load_default()
                bbox = draw.textbbox((0,0), t, font=f)
                tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
                if tw <= max_w and th <= max_h:
                    return f, tw, th, size, t
        # Fallback: smallest size, clipped
        try:
            f = ImageFont.truetype(font_path, min_px) if font_path else ImageFont.load_default()
        except Exception:
            f = ImageFont.load_default()
        bbox = draw.textbbox((0,0), text, font=f)
        return f, bbox[2]-bbox[0], bbox[3]-bbox[1], min_px, text
    
    def _auto_colors(self, cfg):
        bg = sample_avg_color(self.img, self.panel)
        lum = luminance(bg)
        if lum > 180:
            base = tuple(cfg["text_color_dark"])
            stroke = tuple(cfg["stroke_color_dark"])
            glow_color = (0,0,0,cfg["glow_opacity"])
        else:
            base = tuple(cfg["text_color_light"])
            stroke = tuple(cfg["stroke_color_light"])
            glow_color = (255,255,255,cfg["glow_opacity"])
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
        
        # Colors
        if cfg_full["auto_color"]:
            base_color, stroke_color, glow_color = self._auto_colors(cfg_full)
        else:
            base_color = tuple(cfg_full.get("text_color_light", (242,245,248,238)))
            stroke_color = tuple(cfg_full.get("stroke_color_light", (255,255,255,90)))
            glow_color = (0,0,0,cfg_full["glow_opacity"])
        
        # Content area (padding)
        x1,y1,x2,y2 = self.panel
        x1 += cfg_full["padding_px"]; y1 += cfg_full["padding_px"]
        x2 -= cfg_full["padding_px"]; y2 -= cfg_full["padding_px"]
        content = (x1,y1,x2,y2)
        cw, ch = (x2-x1, y2-y1)
        left_w = int(cw * cfg_full["left_ratio"])
        right_w = cw - left_w
        
        # Create layers
        text_layer  = Image.new("RGBA", self.img.size, (0,0,0,0))
        glow_layer  = Image.new("RGBA", self.img.size, (0,0,0,0))
        shadow_layer= Image.new("RGBA", self.img.size, (0,0,0,0))
        backplate_layer = Image.new("RGBA", self.img.size, (0,0,0,0))
        
        draw_text   = ImageDraw.Draw(text_layer)
        draw_glow   = ImageDraw.Draw(glow_layer)
        draw_shadow = ImageDraw.Draw(shadow_layer)
        draw_bp     = ImageDraw.Draw(backplate_layer)
        
        # Vertical alignment baseline
        if isinstance(cfg_full["v_align"], (int, float)):
            v_offset = int(cfg_full["v_align"])
            top = y1 + v_offset
            bottom = y2 + v_offset
        else:
            top, bottom = y1, y2
        
        # Fit fonts
        name_box_w = left_w
        name_box_h = (bottom - top)
        name_font, name_tw, name_th, name_fs, name_text = self._fit_font_to_box(
            draw_text, name, cfg_full["font_path_main"] or cfg_full["font_path_small"] or find_cjk_font(),
            cfg_full["name_min_px"], cfg_full["name_max_px"], name_box_w, name_box_h, allow_ellipsis=cfg_full["ellipsis"]
        )
        right_box_h = (bottom - top)
        # Two lines must fit together
        small_font_path = cfg_full["font_path_small"] or cfg_full["font_path_main"] or find_cjk_font()
        # We'll find a size that fits both, by binary search on size possibly
        def fit_small(text, max_w, max_h, min_px, max_px):
            # start high, go down
            if max_px is None: max_px = int(max_h*0.6)
            size = max_px
            ok = None
            while size >= min_px:
                try:
                    f = ImageFont.truetype(small_font_path, size) if small_font_path else ImageFont.load_default()
                except Exception:
                    f = ImageFont.load_default()
                bbox = draw_text.textbbox((0,0), text, font=f)
                tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
                if tw <= max_w and th <= max_h:
                    ok = (f, tw, th, size, text); break
                size -= 1
            if ok: return ok
            # try ellipsis
            t = text
            for cut in range(len(text), 0, -1):
                t = text[:cut] + "…"
                size = min_px
                try:
                    f = ImageFont.truetype(small_font_path, size) if small_font_path else ImageFont.load_default()
                except Exception:
                    f = ImageFont.load_default()
                bbox = draw_text.textbbox((0,0), t, font=f)
                tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
                if tw <= max_w and th <= max_h:
                    return (f, tw, th, size, t)
            try:
                f = ImageFont.truetype(small_font_path, min_px) if small_font_path else ImageFont.load_default()
            except Exception:
                f = ImageFont.load_default()
            bbox = draw_text.textbbox((0,0), text, font=f)
            return (f, bbox[2]-bbox[0], bbox[3]-bbox[1], min_px, text)
        
        # We'll first fit each line to half height minus gap; later enforce combined fit
        half_h = right_box_h//2
        rarity_pack = fit_small(rarity, right_w, half_h, cfg_full["small_min_px"], cfg_full["small_max_px"])
        number_pack = fit_small(number, right_w, half_h, cfg_full["small_min_px"], cfg_full["small_max_px"])
        rarity_font, rarity_tw, rarity_th, rarity_fs, rarity_text = rarity_pack
        number_font, number_tw, number_th, number_fs, number_text = number_pack
        
        # Ensure both lines + gap fit vertically
        line_gap = cfg_full["line_gap_px"] if cfg_full["line_gap_px"] is not None else max(2, int(min(rarity_fs, number_fs)*0.25))
        total_h = rarity_th + number_th + line_gap
        if total_h > right_box_h:
            # scale down proportionally
            scale = right_box_h / total_h
            new_size = max(cfg_full["small_min_px"], int(min(rarity_fs, number_fs) * scale))
            try:
                rarity_font = ImageFont.truetype(small_font_path, new_size)
                number_font = ImageFont.truetype(small_font_path, new_size)
            except Exception:
                rarity_font = number_font = ImageFont.load_default()
            rarity_bbox = draw_text.textbbox((0,0), rarity_text, font=rarity_font)
            number_bbox = draw_text.textbbox((0,0), number_text, font=number_font)
            rarity_tw, rarity_th = rarity_bbox[2]-rarity_bbox[0], rarity_bbox[3]-rarity_bbox[1]
            number_tw, number_th = number_bbox[2]-number_bbox[0], number_bbox[3]-number_bbox[1]
            line_gap = max(2, int(new_size*0.25))
            total_h = rarity_th + number_th + line_gap
        
        # Coordinates (base positions before offsets)
        left_x = x1
        if cfg_full["v_align"] == "top":
            left_y = top
        elif cfg_full["v_align"] == "bottom":
            left_y = bottom - name_th
        elif isinstance(cfg_full["v_align"], (int,float)):
            # already offset top/bottom above
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
        number_y = rarity_y + rarity_th + line_gap

        # Apply configured pixel offsets (tuple) — allow lists too
        def to_xy(v):
            if v is None: return (0,0)
            try:
                return (int(v[0]), int(v[1]))
            except Exception:
                return (0,0)

        off_name = to_xy(cfg_full.get("offset_name", (0,0)))
        off_rarity = to_xy(cfg_full.get("offset_rarity", (0,0)))
        off_number = to_xy(cfg_full.get("offset_number", (0,0)))

        left_x += off_name[0]; left_y += off_name[1]
        print("full cfg_full:", cfg_full)
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
        
        # Optional backplate (rounded rects behind left and right blocks)
        if cfg_full["backplate"]:
            bp_alpha = cfg_full["backplate_alpha"]
            bp_color = (0,0,0,bp_alpha) if luminance(sample_avg_color(self.img, self.panel))>180 else (255,255,255,bp_alpha)
            # Left plate
            left_plate = (left_x-6, left_y-4, left_x + name_tw + 6, left_y + name_th + 6)
            right_plate = (right_x_right - max(rarity_tw, number_tw) - 6, rarity_y-4, right_x_right + 6, number_y + number_th + 6)
            for plate in [left_plate, right_plate]:
                rx = cfg_full["backplate_radius"]
                shape = Image.new("L", self.img.size, 0)
                d = ImageDraw.Draw(shape)
                d.rounded_rectangle(plate, radius=rx, fill=255)
                colored = Image.new("RGBA", self.img.size, bp_color)
                backplate_layer = Image.composite(colored, Image.new("RGBA", self.img.size, (0,0,0,0)), shape)
                self.img = Image.alpha_composite(self.img, backplate_layer)
        
        # Shadow + Glow draw helpers
        def draw_text_effects(draw_target, text, pos, font, anchor):
            # Shadow
            if cfg_full["drop_shadow"]:
                sx, sy = cfg_full["shadow_offset"]
                sh_layer = Image.new("RGBA", self.img.size, (0,0,0,0))
                dsh = ImageDraw.Draw(sh_layer)
                dsh.text((pos[0]+sx, pos[1]+sy), text, font=font, fill=(0,0,0,cfg_full["shadow_opacity"]), anchor=anchor)
                sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(cfg_full["shadow_blur"]))
                self.img.paste(sh_layer, (0,0), sh_layer)
            # Glow
            if cfg_full["outer_glow"]:
                gl = Image.new("RGBA", self.img.size, (0,0,0,0))
                dgl = ImageDraw.Draw(gl)
                dgl.text(pos, text, font=font, fill=(255,255,255), anchor=anchor)  # stencil
                gl = gl.filter(ImageFilter.GaussianBlur(cfg_full["glow_radius"]))
                # tint glow
                tint = Image.new("RGBA", self.img.size, glow_color)
                gl = ImageChops.multiply(gl, tint)
                self.img.paste(gl, (0,0), gl)
            # Main text
            if cfg_full["use_stroke"]:
                draw_target.text(pos, text, font=font, fill=base_color, anchor=anchor,
                                 stroke_width=cfg_full["stroke_width"], stroke_fill=stroke_color)
            else:
                draw_target.text(pos, text, font=font, fill=base_color, anchor=anchor)
        
        # Draw texts with configurable anchors and offsets
        draw_text_effects(ImageDraw.Draw(self.img), name_text, (left_x, left_y), name_font, anchor_name)
        draw_text_effects(ImageDraw.Draw(self.img), rarity_text, (rarity_x, rarity_y), rarity_font, anchor_rarity)
        draw_text_effects(ImageDraw.Draw(self.img), number_text, (number_x, number_y), number_font, anchor_number)
        
        # Debug boxes
        if cfg_full["debug_draw_boxes"]:
            dbg = ImageDraw.Draw(self.img)
            dbg.rectangle(self.panel, outline=(0,255,0,200), width=2)  # panel
            dbg.rectangle((x1,y1,x2,y2), outline=(255,165,0,200), width=2)  # padded content
            # left and right content columns
            dbg.rectangle((x1, y1, x1+left_w, y2), outline=(0,0,255,200), width=1)
            dbg.rectangle((x1+left_w, y1, x2, y2), outline=(255,0,0,200), width=1)
        
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
    renderer = AcrylicPanelTextRenderer(base_img, panel_box)
    out = renderer.render(name, rarity, number, config or {})
    out.save(output_path)
    return output_path

if __name__ == "__main__":
    # Simple CLI: python panel_text_renderer.py in.png out.png '{"name":"...","rarity":"...","number":"...","panel_box_rel":[0.1,0.8,0.9,0.9]}'
    import sys, json
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    config_path = sys.argv[3]
    with open(config_path, "r", encoding="utf-8") as f:
        opts = json.load(f)
        print(opts)
    name = opts.get("name", "吴宣仪")
    rarity = opts.get("rarity", "N")
    number = opts.get("number", "No.001 / 100")
    panel_box = tuple(opts["panel_box"]) if "panel_box" in opts else None
    panel_box_rel = tuple(opts["panel_box_rel"]) if "panel_box_rel" in opts else None

    render_panel_text(input_path, output_path, name, rarity, number, panel_box, panel_box_rel, opts)