#!/usr/bin/env python3
# remove-bg.py — 去除图片背景，输出透明 PNG
# 用法: python3 remove-bg.py "<图片路径或URL>" ["<输出.png>"] ["<容差0-255>"] [--edge-to-edge] [--min-area=N] [--dominant-frac=F]
#
# 用途：AI 文生图（autoglm-generate-image）产出的 logo 通常带纯色背景 / 卡片 / 水印，
# 无法直接放到不同底色上。两种模式：
#   1) 默认 flood（泛洪）：从四边泛洪，抠掉“与边缘连通且同色”的背景。保留 logo 内部
#      被包裹的同色区域（如彩色 logo 上的白字）。
#   2) --edge-to-edge（全局抠图 + 清理）：把整张图里所有“主体纯色背景色”都抠成透明，
#      包括被边框包住、边缘够不到的卡片底/圆角瓷贴（app-icon 那种白/彩色圆角卡片）。
#      背景色不假设为白色——从四角采样，并自动识别覆盖面积最大的几种纯色（页面底 + 卡片底
#      可以是不同颜色，两色都会被抠）。抠完再做连通域清理，丢掉细边框残影 / 小水印，
#      只留下 logo 主体。
#
# 只依赖 Pillow（PIL），不需要联网模型。
# Source: AutoClaw skill `autoglm-remove-bg` (copied verbatim for local use).

import os
import sys
import tempfile
import urllib.request
import warnings
from collections import deque

warnings.filterwarnings("ignore", category=DeprecationWarning)

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("ERROR: 需要 Pillow。请先 `pip3 install pillow`。")
    sys.exit(1)

DEFAULT_TOLERANCE = 40
# 一种颜色占全图比例 >= 该值，视为“主体纯色背景”（页面底 / 卡片底）
DEFAULT_DOMINANT_FRAC = 0.06
# 背景连通域面积 >= 该比例（或触边）才真正抠掉：只吃大块背景（页面 / 卡片），
# 保留 logo 内部“被彩色包住的浅色/白色小块”（如笔画高光、丝带），不误伤 logo。
DEFAULT_BIG_AREA_FRAC = 0.03
# 不透明碎块清理：面积 < min_area 的孤立不透明碎块丢掉。默认取全图像素的该比例（有绝对下限）
DEFAULT_MIN_AREA_FRAC = 0.0008
MIN_AREA_ABS_FLOOR = 24


def load_source(src):
    """本地路径直接用；URL 先下载到临时文件。返回 (本地路径, 建议输出名基名)。"""
    if src.startswith(("http://", "https://")):
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".img")
        tmp.close()
        urllib.request.urlretrieve(src, tmp.name)
        base = os.path.splitext(os.path.basename(src.split("?")[0]))[0] or "image"
        return tmp.name, base
    if not os.path.isfile(src):
        print(f"ERROR: 文件不存在: {src}")
        sys.exit(1)
    return src, os.path.splitext(os.path.basename(src))[0]


def color_dist(a, b):
    """RGB 欧氏距离的平方（省一次 sqrt，比较时用 tolerance**2）。"""
    dr = a[0] - b[0]
    dg = a[1] - b[1]
    db = a[2] - b[2]
    return dr * dr + dg * dg + db * db


def pick_sentinel(rgb_img):
    """选一个原图里没用到的“哨兵色”，泛洪时用它标记背景。"""
    used = set(rgb_img.getdata())
    for c in [(0, 255, 1), (255, 0, 255), (1, 255, 0), (255, 1, 254), (7, 247, 131)]:
        if c not in used:
            return c
    for r in range(0, 256, 7):
        for g in range(0, 256, 7):
            for b in range(0, 256, 7):
                if (r, g, b) not in used:
                    return (r, g, b)
    return (0, 255, 1)


def flood_mode(img, tolerance):
    """默认模式：四边泛洪，抠掉与边缘连通且同色的背景。返回 RGBA。"""
    w, h = img.size
    sentinel = pick_sentinel(img)
    seeds = [
        (0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
        (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2),
    ]
    for x, y in seeds:
        ImageDraw.floodfill(img, (x, y), sentinel, thresh=tolerance)

    new_data = [
        (0, 0, 0, 0) if px == sentinel else (px[0], px[1], px[2], 255)
        for px in img.getdata()
    ]
    rgba = Image.new("RGBA", (w, h))
    rgba.putdata(new_data)
    return rgba


def detect_bg_colors(img, tolerance, dominant_frac):
    """采样背景色：四角颜色 + 覆盖面积超过 dominant_frac 的主体纯色。
    去重（tolerance 内合并）。不假设白色，支持页面底 / 卡片底不同颜色。"""
    w, h = img.size
    px = img.load()
    tol2 = tolerance * tolerance
    total = w * h

    candidates = []

    # 四角小块取样（避开抗锯齿单点噪声）
    for cx, cy in [(2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3)]:
        cx = max(0, min(w - 1, cx))
        cy = max(0, min(h - 1, cy))
        candidates.append(px[cx, cy])

    # 直方图找主体纯色（页面底 + 卡片底都是大面积纯色）
    colors = img.getcolors(maxcolors=1 << 24)
    if colors:
        for count, c in colors:
            if count >= dominant_frac * total:
                candidates.append(c)

    # tolerance 内去重
    bg = []
    for c in candidates:
        if not any(color_dist(c, e) <= tol2 for e in bg):
            bg.append(c)
    return bg


def build_candidate_bg(img, bg_colors, tolerance):
    """标记候选背景像素：接近任一背景色 → 1（候选），否则 0。返回 bytearray。"""
    tol2 = tolerance * tolerance
    data = img.getdata()
    cand = bytearray(len(data))
    for i, p in enumerate(data):
        for c in bg_colors:
            if color_dist(p, c) <= tol2:
                cand[i] = 1
                break
    return cand


def remove_bg_regions(cand, w, h, big_area):
    """对候选背景做连通域分析（4-邻接）。只有“触边”或“面积够大”的连通块才真正抠掉，
    保留被 logo 彩色包住的浅色小块（笔画高光 / 丝带）。返回 transp bytearray（1=透明）。"""
    visited = bytearray(w * h)
    transp = bytearray(w * h)
    for start in range(w * h):
        if cand[start] == 0 or visited[start]:
            continue
        comp = []
        dq = deque((start,))
        visited[start] = 1
        touch = False
        while dq:
            idx = dq.popleft()
            comp.append(idx)
            x = idx % w
            y = idx // w
            if x == 0 or y == 0 or x == w - 1 or y == h - 1:
                touch = True
            if x > 0:
                n = idx - 1
                if cand[n] and not visited[n]:
                    visited[n] = 1
                    dq.append(n)
            if x < w - 1:
                n = idx + 1
                if cand[n] and not visited[n]:
                    visited[n] = 1
                    dq.append(n)
            if y > 0:
                n = idx - w
                if cand[n] and not visited[n]:
                    visited[n] = 1
                    dq.append(n)
            if y < h - 1:
                n = idx + w
                if cand[n] and not visited[n]:
                    visited[n] = 1
                    dq.append(n)
        if touch or len(comp) >= big_area:
            for idx in comp:
                transp[idx] = 1
    return transp


def cleanup_components(alpha, w, h, min_area):
    """连通域清理：4-邻接，丢掉面积 < min_area 的不透明碎块（边框残影 / 水印）。"""
    visited = bytearray(w * h)
    keep = bytearray(w * h)
    for start in range(w * h):
        if alpha[start] == 0 or visited[start]:
            continue
        comp = []
        dq = deque((start,))
        visited[start] = 1
        while dq:
            idx = dq.popleft()
            comp.append(idx)
            x = idx % w
            y = idx // w
            if x > 0:
                n = idx - 1
                if alpha[n] and not visited[n]:
                    visited[n] = 1
                    dq.append(n)
            if x < w - 1:
                n = idx + 1
                if alpha[n] and not visited[n]:
                    visited[n] = 1
                    dq.append(n)
            if y > 0:
                n = idx - w
                if alpha[n] and not visited[n]:
                    visited[n] = 1
                    dq.append(n)
            if y < h - 1:
                n = idx + w
                if alpha[n] and not visited[n]:
                    visited[n] = 1
                    dq.append(n)
        if len(comp) >= min_area:
            for idx in comp:
                keep[idx] = 255
    return keep


def edge_to_edge_mode(img, tolerance, dominant_frac, big_area, min_area):
    """全局抠图 + 大块背景连通域移除 + 碎块清理。返回 RGBA。
    只抠掉大块 / 触边的背景连通块（页面底、卡片底），保留 logo 内部浅色小块。"""
    w, h = img.size
    bg_colors = detect_bg_colors(img, tolerance, dominant_frac)
    cand = build_candidate_bg(img, bg_colors, tolerance)
    transp = remove_bg_regions(cand, w, h, big_area)

    alpha = bytearray(w * h)
    for i in range(w * h):
        alpha[i] = 0 if transp[i] else 255

    if min_area > 1:
        alpha = cleanup_components(alpha, w, h, min_area)

    rgb = img.getdata()
    new_data = [
        (rgb[i][0], rgb[i][1], rgb[i][2], 255) if alpha[i] else (0, 0, 0, 0)
        for i in range(w * h)
    ]
    rgba = Image.new("RGBA", (w, h))
    rgba.putdata(new_data)
    return rgba


def main():
    if len(sys.argv) < 2:
        print('用法: python3 remove-bg.py "<图片路径或URL>" ["<输出.png>"] ["<容差0-255>"] [--edge-to-edge] [--min-area=N] [--dominant-frac=F]')
        sys.exit(1)

    edge_to_edge = False
    min_area_override = None
    dominant_frac = DEFAULT_DOMINANT_FRAC
    positional = []

    for a in sys.argv[1:]:
        if a in ("--edge-to-edge", "--edge2edge", "-e"):
            edge_to_edge = True
        elif a.startswith("--min-area="):
            try:
                min_area_override = int(a.split("=", 1)[1])
            except ValueError:
                pass
        elif a.startswith("--dominant-frac="):
            try:
                dominant_frac = float(a.split("=", 1)[1])
            except ValueError:
                pass
        else:
            positional.append(a)

    src_arg = positional[0]
    out_arg = positional[1] if len(positional) > 1 and positional[1].strip() else None
    try:
        tolerance = int(positional[2]) if len(positional) > 2 else DEFAULT_TOLERANCE
    except ValueError:
        tolerance = DEFAULT_TOLERANCE

    local_path, base = load_source(src_arg)
    img = Image.open(local_path).convert("RGB")
    w, h = img.size

    if edge_to_edge:
        big_area = max(MIN_AREA_ABS_FLOOR, int(DEFAULT_BIG_AREA_FRAC * w * h))
        if min_area_override is not None:
            min_area = min_area_override
        else:
            min_area = max(MIN_AREA_ABS_FLOOR, int(DEFAULT_MIN_AREA_FRAC * w * h))
        rgba = edge_to_edge_mode(img, tolerance, dominant_frac, big_area, min_area)
    else:
        rgba = flood_mode(img, tolerance)

    # 裁掉透明边，让 logo 更贴边
    bbox = rgba.getbbox()
    if bbox:
        rgba = rgba.crop(bbox)

    if out_arg:
        out_path = out_arg
    else:
        out_dir = os.path.dirname(local_path) if not src_arg.startswith(("http", "https")) else os.getcwd()
        out_path = os.path.join(out_dir or ".", f"{base}-transparent.png")

    rgba.save(out_path, "PNG")
    print(out_path)


if __name__ == "__main__":
    main()
