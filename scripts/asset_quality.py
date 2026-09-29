"""
素材质检与筛选模块
- 图片质检：完整性/分辨率/色彩/损坏检测
- 视频质检：可播放性/时长/分辨率/帧率/编码/音轨
- 音频质检：可播放性/时长/采样率/声道
- 质量评分：0-100分
- 重复检测：基于文件hash
- 批量筛选：按质量/可用性/类型/标签筛选
"""
import os
import sys
import json
import hashlib
import subprocess
from typing import Dict, List, Optional, Tuple

FFPROBE = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe"
FFMPEG = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff'}
VIDEO_EXTS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv'}
AUDIO_EXTS = {'.mp3', '.wav', '.aac', '.ogg', '.flac', '.m4a', '.wma'}


def file_hash(filepath: str, algorithm: str = "md5", block_size: int = 65536) -> str:
    """计算文件hash（用于去重）"""
    h = hashlib.new(algorithm)
    with open(filepath, 'rb') as f:
        while True:
            block = f.read(block_size)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


# ==================== 图片质检 ====================

def inspect_image(filepath: str) -> Dict:
    """
    图片质检

    Returns:
        {
            "valid": bool,
            "width": int, "height": int,
            "mode": str, "format": str,
            "quality_score": int (0-100),
            "issues": [str],
            "file_hash": str,
        }
    """
    result = {
        "valid": False, "width": 0, "height": 0,
        "mode": "", "format": "",
        "quality_score": 0, "issues": [],
        "file_hash": "",
    }

    try:
        result["file_hash"] = file_hash(filepath)
    except Exception:
        pass

    try:
        from PIL import Image
        with Image.open(filepath) as img:
            img.verify()  # 验证文件完整性
        # verify后需要重新打开
        with Image.open(filepath) as img:
            w, h = img.size
            result["width"] = w
            result["height"] = h
            result["mode"] = img.mode
            result["format"] = img.format
            result["valid"] = True

            # 质量评分
            score = 50  # 基础分

            # 分辨率评分（>=1080p满分，<480扣分）
            min_dim = min(w, h)
            if min_dim >= 1080:
                score += 25
            elif min_dim >= 720:
                score += 18
            elif min_dim >= 480:
                score += 10
            else:
                score += 0
                result["issues"].append(f"低分辨率: {w}x{h}")

            # 比例评分（常见比例加分）
            from math import gcd
            g = gcd(w, h)
            ratio = f"{w//g}:{h//g}"
            if ratio in ("9:16", "16:9", "1:1", "3:4", "4:3"):
                score += 15
            else:
                score += 5
                result["issues"].append(f"非标准比例: {ratio}")

            # 色彩模式评分
            if img.mode in ("RGB", "RGBA"):
                score += 10
            elif img.mode == "L":
                score += 5
                result["issues"].append("灰度图")
            else:
                score += 3

            result["quality_score"] = min(100, score)

    except Exception as e:
        result["issues"].append(f"图片损坏或无法读取: {str(e)[:50]}")
        result["valid"] = False
        result["quality_score"] = 0

    return result


# ==================== 视频质检 ====================

def inspect_video(filepath: str) -> Dict:
    """
    视频质检

    Returns:
        {
            "valid": bool,
            "width": int, "height": int,
            "duration_sec": float, "fps": float,
            "codec": str, "has_audio": bool,
            "quality_score": int (0-100),
            "issues": [str],
            "file_hash": str,
        }
    """
    result = {
        "valid": False, "width": 0, "height": 0,
        "duration_sec": 0, "fps": 0, "codec": "",
        "has_audio": False, "quality_score": 0,
        "issues": [], "file_hash": "",
    }

    try:
        result["file_hash"] = file_hash(filepath)
    except Exception:
        pass

    try:
        cmd = [FFPROBE, "-v", "quiet", "-print_format", "json",
               "-show_format", "-show_streams", filepath]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        info = json.loads(proc.stdout)

        video_stream = next((s for s in info.get("streams", [])
                             if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in info.get("streams", [])
                             if s.get("codec_type") == "audio"), None)

        if not video_stream:
            result["issues"].append("无视频流")
            return result

        w = int(video_stream.get("width", 0))
        h = int(video_stream.get("height", 0))
        duration = float(info.get("format", {}).get("duration", 0))
        fps_str = video_stream.get("r_frame_rate", "0/1")
        try:
            num, den = fps_str.split("/")
            fps = round(float(num) / float(den), 2) if float(den) > 0 else 0
        except Exception:
            fps = 0

        result.update({
            "valid": True, "width": w, "height": h,
            "duration_sec": round(duration, 2),
            "fps": fps, "codec": video_stream.get("codec_name", ""),
            "has_audio": audio_stream is not None,
        })

        # 质量评分
        score = 40  # 基础分（能被ffprobe读取）

        # 分辨率评分
        min_dim = min(w, h)
        if min_dim >= 1080:
            score += 20
        elif min_dim >= 720:
            score += 14
        elif min_dim >= 480:
            score += 8
        else:
            score += 0
            result["issues"].append(f"低分辨率: {w}x{h}")

        # 帧率评分
        if fps >= 50:
            score += 15
        elif fps >= 24:
            score += 12
        elif fps >= 15:
            score += 6
        else:
            score += 0
            result["issues"].append(f"低帧率: {fps}fps")

        # 时长评分
        if 1 <= duration <= 300:
            score += 10
        elif duration > 300:
            score += 5
            result["issues"].append(f"时长过长: {duration:.0f}s")
        elif duration < 1:
            score += 2
            result["issues"].append(f"时长过短: {duration:.2f}s")

        # 编码评分
        if video_stream.get("codec_name") in ("h264", "hevc", "vp9", "av1"):
            score += 10
        else:
            score += 3
            result["issues"].append(f"非标准编码: {video_stream.get('codec_name')}")

        # 音轨
        if audio_stream:
            score += 5
        else:
            result["issues"].append("无音轨")

        result["quality_score"] = min(100, score)

        # 实际可播放性检测（尝试解码第一帧）
        try:
            decode_cmd = [FFMPEG, "-v", "error", "-i", filepath,
                          "-frames:v", "1", "-f", "null", "-"]
            decode_proc = subprocess.run(decode_cmd, capture_output=True,
                                          text=True, timeout=10)
            if decode_proc.returncode != 0:
                result["issues"].append("解码失败")
                result["quality_score"] = max(0, result["quality_score"] - 30)
        except Exception:
            pass

    except Exception as e:
        result["issues"].append(f"视频无法读取: {str(e)[:50]}")
        result["valid"] = False

    return result


# ==================== 音频质检 ====================

def inspect_audio(filepath: str) -> Dict:
    """
    音频质检

    Returns:
        {
            "valid": bool,
            "duration_sec": float,
            "sample_rate": int, "channels": int,
            "codec": str, "bit_rate": int,
            "quality_score": int (0-100),
            "issues": [str],
            "file_hash": str,
        }
    """
    result = {
        "valid": False, "duration_sec": 0,
        "sample_rate": 0, "channels": 0,
        "codec": "", "bit_rate": 0,
        "quality_score": 0, "issues": [],
        "file_hash": "",
    }

    try:
        result["file_hash"] = file_hash(filepath)
    except Exception:
        pass

    try:
        cmd = [FFPROBE, "-v", "quiet", "-print_format", "json",
               "-show_format", "-show_streams", filepath]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        info = json.loads(proc.stdout)

        audio_stream = next((s for s in info.get("streams", [])
                             if s.get("codec_type") == "audio"), None)

        if not audio_stream:
            result["issues"].append("无音频流")
            return result

        duration = float(info.get("format", {}).get("duration", 0))
        sample_rate = int(audio_stream.get("sample_rate", 0))
        channels = int(audio_stream.get("channels", 0))
        bit_rate = int(info.get("format", {}).get("bit_rate", 0))

        result.update({
            "valid": True,
            "duration_sec": round(duration, 2),
            "sample_rate": sample_rate,
            "channels": channels,
            "codec": audio_stream.get("codec_name", ""),
            "bit_rate": bit_rate,
        })

        # 质量评分
        score = 40

        if sample_rate >= 44100:
            score += 20
        elif sample_rate >= 22050:
            score += 12
        else:
            score += 5
            result["issues"].append(f"低采样率: {sample_rate}Hz")

        if channels >= 2:
            score += 15
        else:
            score += 8
            result["issues"].append("单声道")

        if bit_rate >= 192000:
            score += 15
        elif bit_rate >= 128000:
            score += 10
        else:
            score += 5

        if 1 <= duration <= 600:
            score += 10
        else:
            score += 5

        result["quality_score"] = min(100, score)

    except Exception as e:
        result["issues"].append(f"音频无法读取: {str(e)[:50]}")
        result["valid"] = False

    return result


# ==================== 统一质检入口 ====================

def inspect_asset(filepath: str) -> Dict:
    """统一质检入口：根据文件类型自动选择质检方法"""
    ext = os.path.splitext(filepath)[1].lower()
    if ext in IMAGE_EXTS:
        result = inspect_image(filepath)
        result["type"] = "image"
    elif ext in VIDEO_EXTS:
        result = inspect_video(filepath)
        result["type"] = "video"
    elif ext in AUDIO_EXTS:
        result = inspect_audio(filepath)
        result["type"] = "audio"
    else:
        result = {"valid": False, "type": "unknown", "issues": ["不支持的文件类型"],
                  "quality_score": 0, "file_hash": ""}

    result["path"] = filepath
    result["filename"] = os.path.basename(filepath)
    result["size_bytes"] = os.path.getsize(filepath) if os.path.exists(filepath) else 0
    return result


def batch_inspect(filepaths: List[str], show_progress: bool = True) -> List[Dict]:
    """批量质检"""
    results = []
    total = len(filepaths)
    for i, fp in enumerate(filepaths):
        if show_progress and (i + 1) % 10 == 0:
            print(f"  质检进度: {i+1}/{total}")
        results.append(inspect_asset(fp))
    return results


# ==================== 筛选 ====================

def filter_assets(assets: List[Dict],
                  min_quality: int = 0,
                  only_valid: bool = True,
                  asset_type: str = None,
                  min_resolution: int = 0,
                  max_duration: float = None,
                  min_duration: float = None,
                  exclude_issues: List[str] = None) -> List[Dict]:
    """
    多条件筛选素材

    Args:
        assets: 质检结果列表
        min_quality: 最低质量分（0-100）
        only_valid: 只保留有效素材
        asset_type: 类型过滤
        min_resolution: 最小分辨率（短边像素）
        max_duration/min_duration: 时长范围（视频/音频）
        exclude_issues: 排除包含指定问题的素材

    Returns:
        筛选后的素材列表
    """
    filtered = []
    for a in assets:
        if only_valid and not a.get("valid", False):
            continue
        if a.get("quality_score", 0) < min_quality:
            continue
        if asset_type and a.get("type") != asset_type:
            continue
        if min_resolution:
            w = a.get("width", 0)
            h = a.get("height", 0)
            if min(w, h) < min_resolution:
                continue
        dur = a.get("duration_sec", 0)
        if max_duration and dur > max_duration:
            continue
        if min_duration and dur < min_duration:
            continue
        if exclude_issues:
            issues = a.get("issues", [])
            if any(any(ex in iss for iss in issues) for ex in exclude_issues):
                continue
        filtered.append(a)
    return filtered


def find_duplicates(assets: List[Dict]) -> Dict[str, List[Dict]]:
    """
    检测重复素材（基于file_hash）

    Returns:
        {hash: [asset1, asset2, ...]} 只返回有重复的组
    """
    hash_map = {}
    for a in assets:
        h = a.get("file_hash", "")
        if h:
            hash_map.setdefault(h, []).append(a)
    return {h: group for h, group in hash_map.items() if len(group) > 1}


def quality_report(assets: List[Dict]) -> Dict:
    """生成质量报告"""
    valid = [a for a in assets if a.get("valid")]
    invalid = [a for a in assets if not a.get("valid")]

    quality_scores = [a.get("quality_score", 0) for a in valid]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

    # 问题统计
    issue_counts = {}
    for a in assets:
        for issue in a.get("issues", []):
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

    # 质量分布
    quality_bands = {"excellent(90-100)": 0, "good(70-89)": 0,
                     "fair(50-69)": 0, "poor(<50)": 0}
    for s in quality_scores:
        if s >= 90:
            quality_bands["excellent(90-100)"] += 1
        elif s >= 70:
            quality_bands["good(70-89)"] += 1
        elif s >= 50:
            quality_bands["fair(50-69)"] += 1
        else:
            quality_bands["poor(<50)"] += 1

    duplicates = find_duplicates(assets)

    return {
        "total": len(assets),
        "valid": len(valid),
        "invalid": len(invalid),
        "avg_quality": round(avg_quality, 1),
        "quality_distribution": quality_bands,
        "top_issues": sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:10],
        "duplicate_groups": len(duplicates),
        "duplicate_files": sum(len(g) for g in duplicates.values()),
    }


if __name__ == "__main__":
    print("素材质检与筛选模块已加载")
    print("功能: inspect_image / inspect_video / inspect_audio / inspect_asset")
    print("      batch_inspect / filter_assets / find_duplicates / quality_report")
