"""
混合模式合成器 — Python像素级合成
替代剪映混合模式（jianying-editor不支持blend_mode API）
"""
from PIL import Image
import os

def multiply_blend(upper_path, lower_path, output_path):
    """
    正片叠底：result = upper × lower / 255
    黑色背景(0)→结果黑色；白色轮廓(255)→显示下层彩色
    
    适用：黑底白边轮廓图 + 彩色纹理 → 黑底彩色轮廓
    """
    return composite(upper_path, lower_path, output_path, "multiply")


def screen_blend(upper_path, lower_path, output_path):
    """
    滤色：result = 255 - (255-upper) × (255-lower) / 255
    黑色背景→透出下层；白色→结果白色
    
    适用：黑底发光素材 + 背景 → 发光叠加
    """
    return composite(upper_path, lower_path, output_path, "screen")


def composite(upper_path, lower_path, output_path, mode="multiply"):
    """
    通用混合模式合成
    
    Args:
        upper_path: 上层图片路径
        lower_path: 下层图片路径
        output_path: 输出路径
        mode: multiply(正片叠底)/screen(滤色)/overlay(叠加)
    """
    upper = Image.open(upper_path).convert('RGB')
    lower = Image.open(lower_path).convert('RGB')
    if upper.size != lower.size:
        lower = lower.resize(upper.size)
    
    result = Image.new('RGB', upper.size)
    up = upper.load()
    lp = lower.load()
    rp = result.load()
    w, h = upper.size
    
    for y in range(h):
        for x in range(w):
            u = up[x, y]
            l = lp[x, y]
            if mode == "multiply":
                rp[x, y] = (int(u[0]*l[0]/255), int(u[1]*l[1]/255), int(u[2]*l[2]/255))
            elif mode == "screen":
                rp[x, y] = (255-int((255-u[0])*(255-l[0])/255),
                            255-int((255-u[1])*(255-l[1])/255),
                            255-int((255-u[2])*(255-l[2])/255))
            elif mode == "overlay":
                rp[x, y] = tuple(
                    int(2*l[i]*u[i]/255) if l[i] < 128
                    else int(255 - 2*(255-l[i])*(255-u[i])/255)
                    for i in range(3)
                )
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    result.save(output_path)
    return output_path
