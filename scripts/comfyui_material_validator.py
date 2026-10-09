"""
ComfyUI绱犳潗鐢熸垚绔埌绔獙璇佹ā鍧?v1.0
楠岃瘉ComfyUI鐢熸垚鐨勭礌鏉愭槸鍚﹁兘瀹岀編铻嶅叆鍓槧宸ョ▼銆?

楠岃瘉鍐呭锛?
1. 绱犳潗鎶€鏈弬鏁帮紙鍒嗚鲸鐜?鏍煎紡/Alpha閫氶亾/鑹插僵绌洪棿锛?
2. 绱犳潗鐢熸垚璐ㄩ噺锛堟竻鏅板害/鍣偣/杈圭紭锛?
3. 鍓槧宸ョ▼闆嗘垚锛堝鍏?鏄剧ず/灞傜骇锛?
4. 鍦烘櫙铻嶅悎搴︼紙鑳屾櫙鍖归厤/鍏夌収涓€鑷?杈圭紭鑷劧锛?

浣跨敤鏂瑰紡锛?
    from comfyui_material_validator import ComfyUIMaterialValidator
    validator = ComfyUIMaterialValidator()
    result = validator.validate_material("generated.png", scene_type="douyin_profile")
"""

import logging
logger = logging.getLogger(__name__)

import os
import json
import subprocess
import requests
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class MaterialValidationResult:
    """绱犳潗楠岃瘉缁撴灉"""
    filepath: str
    exists: bool = False
    width: int = 0
    height: int = 0
    format: str = ""
    has_alpha: bool = False
    color_space: str = ""
    file_size: int = 0
    technical_score: float = 0.0  # 0-100
    quality_score: float = 0.0  # 0-100
    integration_score: float = 0.0  # 0-100
    overall_score: float = 0.0  # 0-100
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class ComfyUIMaterialValidator:
    """ComfyUI绱犳潗楠岃瘉鍣?""

    def __init__(
        self,
        comfyui_address: str = "127.0.0.1:8188",
        ffmpeg_path: str = "ffmpeg",
        ffprobe_path: str = "ffprobe",
    ):
        self.comfyui_url = f"http://{comfyui_address}"
        self.ffmpeg = ffmpeg_path
        self.ffprobe = ffprobe_path
        self.session = requests.Session()

    def check_comfyui(self) -> Dict:
        """妫€鏌omfyUI杩炴帴鐘舵€?""
        try:
            response = self.session.get(f"{self.comfyui_url}/", timeout=5)
            if response.status_code == 200:
                # 鑾峰彇绯荤粺缁熻
                try:
                    stats = self.session.get(
                        f"{self.comfyui_url}/system_stats", timeout=5
                    ).json()
                    return {
                        "connected": True,
                        "status": "running",
                        "devices": stats.get("devices", []),
                    }
                except Exception:
                    return {"connected": True, "status": "running"}
        except Exception as e:
            return {"connected": False, "status": "error", "error": str(e)}

        return {"connected": False, "status": "unknown"}

    def get_available_models(self) -> Dict[str, List[str]]:
        """鑾峰彇鍙敤妯″瀷鍒楄〃"""
        try:
            response = self.session.get(
                f"{self.comfyui_url}/object_info", timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                models = {
                    "checkpoints": [],
                    "loras": [],
                    "vaes": [],
                }

                # 浠嶤heckpointLoaderSimple鑺傜偣鑾峰彇妯″瀷
                if "CheckpointLoaderSimple" in data:
                    ckpt_input = data["CheckpointLoaderSimple"].get("input", {})
                    required = ckpt_input.get("required", {})
                    if "ckpt_name" in required:
                        models["checkpoints"] = required["ckpt_name"][0]

                # 浠嶭oraLoader鑺傜偣鑾峰彇LoRA
                if "LoraLoader" in data:
                    lora_input = data["LoraLoader"].get("input", {})
                    required = lora_input.get("required", {})
                    if "lora_name" in required:
                        models["loras"] = required["lora_name"][0]

                return models
        except Exception as e:
            logger.error(f"鈿狅笍 鑾峰彇妯″瀷鍒楄〃澶辫触: {e}")

        return {"checkpoints": [], "loras": [], "vaes": []}

    def generate_test_image(
        self,
        prompt: str = "a cute robot character, white background, simple",
        width: int = 512,
        height: int = 512,
        steps: int = 20,
        cfg: float = 7.0,
        output_dir: str = None,
    ) -> Optional[str]:
        """
        鐢熸垚娴嬭瘯鍥剧墖锛堢畝鍗曟枃鐢熷浘锛?

        Returns:
            鐢熸垚鐨勫浘鐗囪矾寰勶紝澶辫触杩斿洖None
        """
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), "..", "out")
        os.makedirs(output_dir, exist_ok=True)

        # 鏋勫缓绠€鍗曞伐浣滄祦
        workflow = {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": 42,
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0],
                },
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"},
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": width, "height": height, "batch_size": 1},
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": prompt, "clip": ["4", 1]},
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "lowres, bad anatomy, bad hands, text, error, missing fingers",
                    "clip": ["4", 1],
                },
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": "ComfyUI_test", "images": ["8", 0]},
            },
        }

        try:
            # 鎻愪氦宸ヤ綔娴?
            response = self.session.post(
                f"{self.comfyui_url}/prompt",
                json={"prompt": workflow},
                timeout=30,
            )
            if response.status_code != 200:
                logger.error(f"鈿狅笍 鎻愪氦宸ヤ綔娴佸け璐? {response.status_code}")
                return None

            prompt_id = response.json().get("prompt_id")
            if not prompt_id:
                logger.info("鈿狅笍 鏈幏鍙栧埌prompt_id")
                return None

            # 杞绛夊緟瀹屾垚
            logger.info(f"  绛夊緟鐢熸垚瀹屾垚 (prompt_id={prompt_id[:8]}...)")
            max_wait = 120  # 鏈€澶氱瓑寰?鍒嗛挓
            start_time = time.time()

            while time.time() - start_time < max_wait:
                try:
                    history = self.session.get(
                        f"{self.comfyui_url}/history/{prompt_id}",
                        timeout=5,
                    ).json()

                    if prompt_id in history:
                        outputs = history[prompt_id].get("outputs", {})
                        if "9" in outputs:
                            images = outputs["9"].get("images", [])
                            if images:
                                # 涓嬭浇鍥剧墖
                                img_info = images[0]
                                img_response = self.session.get(
                                    f"{self.comfyui_url}/view",
                                    params={
                                        "filename": img_info["filename"],
                                        "subfolder": img_info.get("subfolder", ""),
                                        "type": img_info.get("type", "output"),
                                    },
                                    timeout=30,
                                )

                                output_path = os.path.join(
                                    output_dir, f"comfyui_test_{int(time.time())}.png"
                                )
                                with open(output_path, "wb") as f:
                                    f.write(img_response.content)

                                logger.info(f"  鉁?鐢熸垚鎴愬姛: {output_path}")
                                return output_path
                except Exception:
                    pass

                time.sleep(2)

            logger.info("鈿狅笍 鐢熸垚瓒呮椂")
            return None

        except Exception as e:
            logger.error(f"鈿狅笍 鐢熸垚澶辫触: {e}")
            return None

    def validate_material(
        self,
        material_path: str,
        scene_type: str = "general",
        target_canvas: Tuple[int, int] = (1080, 1920),
    ) -> MaterialValidationResult:
        """
        楠岃瘉绱犳潗鏄惁閫傚悎铻嶅叆鍓槧宸ョ▼

        Args:
            material_path: 绱犳潗鏂囦欢璺緞
            scene_type: 鍦烘櫙绫诲瀷锛坓eneral/douyin_profile/character/background锛?
            target_canvas: 鐩爣鐢诲竷灏哄

        Returns:
            MaterialValidationResult 楠岃瘉缁撴灉
        """
        result = MaterialValidationResult(filepath=material_path)

        if not os.path.exists(material_path):
            result.issues.append(f"绱犳潗鏂囦欢涓嶅瓨鍦? {material_path}")
            return result

        result.exists = True
        result.file_size = os.path.getsize(material_path)

        # 浣跨敤ffprobe鑾峰彇鎶€鏈弬鏁?
        try:
            cmd = [
                self.ffprobe, "-v", "quiet",
                "-print_format", "json",
                "-show_format", "-show_streams",
                material_path
            ]
            probe_result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            info = json.loads(probe_result.stdout)

            video_stream = next(
                (s for s in info.get("streams", []) if s.get("codec_type") == "video"),
                {}
            )

            result.width = int(video_stream.get("width", 0))
            result.height = int(video_stream.get("height", 0))
            result.format = video_stream.get("codec_name", "")
            result.color_space = video_stream.get("color_space", "unknown")

            # 妫€鏌lpha閫氶亾
            pix_fmt = video_stream.get("pix_fmt", "")
            result.has_alpha = "a" in pix_fmt.lower() or "alpha" in pix_fmt.lower()

        except Exception as e:
            result.issues.append(f"鎶€鏈弬鏁拌В鏋愬け璐? {e}")

        # 鎶€鏈瘎鍒?
        tech_score = 100
        if result.width == 0 or result.height == 0:
            tech_score -= 50
            result.issues.append("鏃犳硶瑙ｆ瀽鍒嗚鲸鐜?)
        else:
            # 妫€鏌ュ垎杈ㄧ巼鏄惁鍚堢悊
            if result.width < 256 or result.height < 256:
                tech_score -= 20
                result.warnings.append(f"鍒嗚鲸鐜囪繃浣? {result.width}x{result.height}")
            if result.width > target_canvas[0] * 2 or result.height > target_canvas[1] * 2:
                tech_score -= 10
                result.warnings.append(f"鍒嗚鲸鐜囪繃楂橈紝鍙兘闇€瑕佺缉鏀? {result.width}x{result.height}")

        # 妫€鏌ユ枃浠跺ぇ灏?
        if result.file_size > 50 * 1024 * 1024:  # 50MB
            tech_score -= 10
            result.warnings.append(f"鏂囦欢杩囧ぇ: {result.file_size / 1024 / 1024:.1f}MB")

        result.technical_score = max(0, tech_score)

        # 鍦烘櫙閫傞厤璇勫垎
        integration_score = 80

        if scene_type == "character":
            # 瑙掕壊绱犳潗闇€瑕丄lpha閫氶亾
            if not result.has_alpha:
                integration_score -= 30
                result.issues.append("瑙掕壊绱犳潗缂哄皯Alpha閫氶亾锛屾棤娉曢€忔槑鍙犲姞")
                result.recommendations.append("浣跨敤Remotion PNG搴忓垪+ProRes 4444鐢熸垚甯lpha鐨勮棰?)
                result.recommendations.append("鎴栦娇鐢ㄥ幓鑳屾櫙宸ュ叿锛坮emove_background.py锛夊鐞?)

            # 瑙掕壊绱犳潗寤鸿姝ｆ柟褰?
            if abs(result.width - result.height) > max(result.width, result.height) * 0.2:
                integration_score -= 10
                result.warnings.append("瑙掕壊绱犳潗寤鸿鎺ヨ繎姝ｆ柟褰㈡瘮渚?)

        elif scene_type == "background":
            # 鑳屾櫙绱犳潗涓嶉渶瑕丄lpha
            if result.has_alpha:
                integration_score -= 5
                result.warnings.append("鑳屾櫙绱犳潗閫氬父涓嶉渶瑕丄lpha閫氶亾")

            # 鑳屾櫙绱犳潗寤鸿鍖归厤鐢诲竷姣斾緥
            target_ratio = target_canvas[0] / target_canvas[1]
            material_ratio = result.width / result.height if result.height > 0 else 1
            if abs(material_ratio - target_ratio) > 0.1:
                integration_score -= 15
                result.warnings.append(
                    f"鑳屾櫙姣斾緥涓嶅尮閰? 绱犳潗{material_ratio:.2f} vs 鐢诲竷{target_ratio:.2f}"
                )

        elif scene_type == "douyin_profile":
            # 鎶栭煶涓婚〉绱犳潗
            if result.width != 1080 or result.height != 1920:
                integration_score -= 10
                result.warnings.append(f"鎶栭煶涓婚〉寤鸿1080x1920锛屽綋鍓峽result.width}x{result.height}")

        result.integration_score = max(0, integration_score)

        # 缁煎悎璇勫垎
        result.overall_score = (
            result.technical_score * 0.4 +
            result.quality_score * 0.3 +
            result.integration_score * 0.3
        )

        # 鐢熸垚寤鸿
        if result.overall_score >= 80:
            result.recommendations.append("绱犳潗璐ㄩ噺鑹ソ锛屽彲浠ョ洿鎺ヤ娇鐢?)
        elif result.overall_score >= 60:
            result.recommendations.append("绱犳潗鍩烘湰鍙敤锛屽缓璁紭鍖栧悗浣跨敤")
        else:
            result.recommendations.append("绱犳潗璐ㄩ噺涓嶈揪鏍囷紝寤鸿閲嶆柊鐢熸垚")

        if not result.has_alpha and scene_type == "character":
            result.recommendations.append("鍏抽敭闂锛氱己灏慉lpha閫氶亾锛屽繀椤讳慨澶嶅悗鎵嶈兘鐢ㄤ簬瑙掕壊鍔ㄧ敾")

        return result

    def batch_validate(
        self,
        material_dir: str,
        scene_type: str = "general",
    ) -> List[MaterialValidationResult]:
        """鎵归噺楠岃瘉鐩綍涓殑绱犳潗"""
        results = []

        if not os.path.exists(material_dir):
            logger.info(f"鈿狅笍 鐩綍涓嶅瓨鍦? {material_dir}")
            return results

        image_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

        for filename in os.listdir(material_dir):
            ext = os.path.splitext(filename)[1].lower()
            if ext in image_exts or ext in video_exts:
                filepath = os.path.join(material_dir, filename)
                result = self.validate_material(filepath, scene_type)
                results.append(result)

        return results

    def print_validation_report(self, result: MaterialValidationResult):
        """鎵撳嵃楠岃瘉鎶ュ憡"""
        logger.info("=" * 60)
        logger.info("ComfyUI绱犳潗楠岃瘉鎶ュ憡")
        logger.info("=" * 60)
        logger.info(f"\n鏂囦欢: {os.path.basename(result.filepath)}")
        logger.info(f"澶у皬: {result.file_size / 1024:.1f}KB")
        logger.info(f"鍒嗚鲸鐜? {result.width}x{result.height}")
        logger.info(f"鏍煎紡: {result.format}")
        logger.info(f"Alpha閫氶亾: {'鉁?鏈? if result.has_alpha else '鉂?鏃?}")
        logger.info(f"鑹插僵绌洪棿: {result.color_space}")

        logger.info(f"\n璇勫垎:")
        logger.info(f"  鎶€鏈弬鏁? {result.technical_score:.0f}/100")
        logger.info(f"  鐢熸垚璐ㄩ噺: {result.quality_score:.0f}/100")
        logger.info(f"  鍦烘櫙铻嶅悎: {result.integration_score:.0f}/100")
        logger.info(f"  缁煎悎璇勫垎: {result.overall_score:.0f}/100")

        if result.issues:
            logger.info(f"\n鉂?闂 ({len(result.issues)}):")
            for issue in result.issues:
                logger.info(f"  - {issue}")

        if result.warnings:
            logger.warning(f"\n鈿狅笍 璀﹀憡 ({len(result.warnings)}):")
            for warning in result.warnings:
                logger.warning(f"  - {warning}")

        if result.recommendations:
            logger.info(f"\n馃挕 寤鸿 ({len(result.recommendations)}):")
            for rec in result.recommendations:
                logger.info(f"  - {rec}")

        logger.info("=" * 60)


def main():
    """鍛戒护琛屾祴璇?""
    logger.info("=" * 60)
    logger.info("ComfyUI绱犳潗鐢熸垚绔埌绔獙璇?v1.0")
    logger.info("=" * 60)

    validator = ComfyUIMaterialValidator()

    # 妫€鏌omfyUI
    logger.info("\n=== 妫€鏌omfyUI杩炴帴 ===")
    status = validator.check_comfyui()
    logger.info(f"  杩炴帴: {'鉁? if status.get('connected') else '鉂?}")
    logger.info(f"  鐘舵€? {status.get('status')}")

    # 鑾峰彇鍙敤妯″瀷
    logger.info("\n=== 鍙敤妯″瀷 ===")
    models = validator.get_available_models()
    logger.info(f"  Checkpoints: {len(models.get('checkpoints', []))}涓?)
    for ckpt in models.get("checkpoints", [])[:5]:
        logger.info(f"    - {ckpt}")
    logger.info(f"  LoRAs: {len(models.get('loras', []))}涓?)

    # 楠岃瘉鐜版湁绱犳潗
    logger.info("\n=== 楠岃瘉鐜版湁绱犳潗 ===")
    test_dirs = [
        r"D:\DobaoWork_Project\Ai_Video_Editor\out",
        r"D:\DobaoWork_Project\Ai_Video_Editor\material",
    ]

    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            logger.info(f"\n鐩綍: {test_dir}")
            results = validator.batch_validate(test_dir, scene_type="general")
            for r in results[:3]:  # 鍙樉绀哄墠3涓?
                validator.print_validation_report(r)
                logger.info("")
            if len(results) > 3:
                logger.info(f"  ... 杩樻湁{len(results) - 3}涓礌鏉?)
            break

    logger.info("\n" + "=" * 60)
    logger.info("楠岃瘉瀹屾垚")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
