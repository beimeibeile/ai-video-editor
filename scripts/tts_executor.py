"""
P25执行器: TTS语音合成（Qwen3-TTS ComfyUI后端）
通过ComfyUI API调用Qwen3-TTS生成高质量语音，支持9种内置音色+风格指令
"""

import os
import json
import time
import uuid
import urllib.request
from typing import Dict, Any, List, Optional


COMFYUI_URL = "http://127.0.0.1:8188"

# 角色→Qwen3-TTS内置音色映射
CHARACTER_VOICE_MAP = {
    "豆包": "Serena",        # 温柔女声
    "顾客": "Vivian",        # 御姐女声
    "前台": "Ryan",          # 标准男声
    "机器人": "Aiden",       # 年轻男声
    "女杀手": "Vivian",      # 御姐女声
    "旁白": "Dylan",         # 沉稳男声
    "大叔": "Uncle_fu",      # 成熟大叔音
    "默认": "Serena",        # 温柔女声
}

# 情绪→instruct风格指令映射（拟人化描述）
EMOTION_INSTRUCT_MAP = {
    # 基础情绪
    "normal": "",
    "happy": "开心，活泼，语速快，带笑意",
    "sad": "悲伤，语速慢，低沉，带哭腔",
    "angry": "愤怒，大喊，语速快，情绪激动",
    "fear": "害怕，颤抖，语速快，声音小",
    "surprise": "惊讶，语速快，高音",
    "calm": "自然口语化，语速中等，语气平和，像日常对话，不要播音腔不要装",
    "excited": "兴奋，语速快，高音",
    "tired": "疲惫，语速慢，低沉，有气无力",
    "shout": "大喊，愤怒，用力",
    # 拟人化语气
    "心慌意乱": "心慌意乱，紧张，语速快，声音颤抖",
    "不紧不慢": "不紧不慢，从容，语速慢，沉稳",
    "结结巴巴": "结结巴巴，紧张，停顿多，不自信",
    "冷笑嘲讽": "冷笑，嘲讽，不屑，语速中等",
    "委屈抱怨": "委屈，抱怨，带哭腔，语速慢",
    "得意洋洋": "略带得意，语速中等，带轻微笑意，不要太夸张",
    "低声下气": "低声下气，卑微，语速慢，声音小",
    "暴跳如雷": "暴跳如雷，极度愤怒，大喊大叫，语速快",
    "无奈": "无奈，叹气，语速慢，低沉",
    "得意": "得意，自信，语速中等",
    "严肃": "严肃，庄重，语速慢，低沉",
    "调皮": "调皮，活泼，语速快，带笑意",
    "温柔": "温柔，轻声细语，语速慢",
    "坚定": "坚定，有力，语速中等，声音洪亮",
    "犹豫": "犹豫，停顿多，语速慢，不自信",
    "激动": "激动，语速快，高音，情绪饱满",
    "冷漠": "冷漠，面无表情，语速慢，平淡",
    "慌张": "慌张，语速快，声音颤抖，停顿多",
    "自信": "自信，从容，语速中等，声音洪亮",
    "抱怨": "抱怨，不满，语速中等，带情绪",
    "哀求": "哀求，卑微，语速慢，带哭腔",
    "怒吼": "怒吼，极度愤怒，大喊大叫，用力",
    "窃喜": "窃喜，小声，带笑意，语速中等",
    "凝重": "凝重，严肃，语速慢，低沉",
    "轻松": "轻松，愉快，语速中等，带笑意",
    "紧张": "紧张，语速快，声音颤抖，停顿多",
    "质问": "质问，语速快，语气强烈，带火气",
}


# ============ 角色→克隆音色配置（zero-shot voice cloning） ============
# 每个角色配置：ref_audio（参考音频路径，几秒即可）+ ref_text（参考音频里说的话，一字不差）
# 配置后该角色自动走克隆路径，不再用内置音色
CLONE_VOICE_MAP = {
    "周鸿祎": {
        "ref_audio": r"D:\DobaoWork_Project\Ai_Video_Editor\material\jianying out\周鸿祎.MP3",
        "ref_text": "但是这件事确实还是暴露出来，AI会对安全带来巨大的挑战，那这里边呢，我觉得有三层不同的安全的威胁，第一层呢，是AI开始有挖掘漏洞的能力，那这个自动挖掘漏洞的能力，是网络攻击的基本功",
    },
}

COMFY_INPUT_DIR = r"D:\Ai\ComfyUI-aki-v3.2\ComfyUI\input"


class TTSExecutor:
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or os.path.join(
            os.path.expanduser("~"), "Videos", "ai-video-editor-output", "director_engine_output", "tts"
        )
        os.makedirs(self.output_dir, exist_ok=True)
        self._comfyui_available = None

    def check_comfyui(self) -> bool:
        """检查ComfyUI是否可用"""
        if self._comfyui_available is not None:
            return self._comfyui_available
        try:
            urllib.request.urlopen(f"{COMFYUI_URL}/system_stats", timeout=3)
            self._comfyui_available = True
        except Exception:
            self._comfyui_available = False
        return self._comfyui_available

    def get_voice(self, character: str) -> str:
        return CHARACTER_VOICE_MAP.get(character, CHARACTER_VOICE_MAP["默认"])

    def get_instruct(self, emotion: str) -> str:
        return EMOTION_INSTRUCT_MAP.get(emotion, "")

    def _build_prompt(self, text: str, speaker: str, instruct: str,
                      seed: int = None) -> Dict:
        """构建ComfyUI API prompt"""
        if seed is None:
            seed = int(time.time() * 1000) % 2**31
        return {
            "109": {
                "class_type": "FB_Qwen3TTSCustomVoice",
                "inputs": {
                    "text": text,
                    "speaker": speaker,
                    "model_choice": "1.7B",
                    "device": "cuda",
                    "precision": "bf16",
                    "language": "Chinese",
                    "seed": seed,
                    "instruct": instruct,
                    "max_new_tokens": 2048,
                    "top_p": 0.8,
                    "top_k": 20,
                    "temperature": 1.0,
                    "repetition_penalty": 1.05,
                    "attention": "eager",
                    "unload_model_after_generate": False,
                    "custom_model_path": "",
                    "custom_speaker_name": "",
                }
            },
            "107": {
                "class_type": "SaveAudioMP3",
                "inputs": {
                    "audio": ["109", 0],
                    "filename_prefix": "audio/Qwen3-TTS",
                    "quality": "128k",
                }
            }
        }

    def _build_clone_prompt(self, text: str, ref_audio_filename: str,
                            ref_text: str, seed: int = None) -> Dict:
        """构建克隆音色的ComfyUI API prompt（FB_Qwen3TTSVoiceClone节点）"""
        if seed is None:
            seed = int(time.time() * 1000) % 2**31
        return {
            "10": {
                "class_type": "LoadAudio",
                "inputs": {
                    "audio": ref_audio_filename,
                }
            },
            "13": {
                "class_type": "FB_Qwen3TTSVoiceClone",
                "inputs": {
                    "ref_audio": ["10", 0],
                    "target_text": text,
                    "model_choice": "1.7B",
                    "device": "cuda",
                    "precision": "bf16",
                    "language": "Chinese",
                    "ref_text": ref_text,
                    "seed": seed,
                    "max_new_tokens": 2048,
                    "top_p": 0.85,
                    "top_k": 30,
                    "temperature": 1.1,
                    "repetition_penalty": 1.05,
                    "x_vector_only": False,
                    "attention": "eager",
                    "unload_model_after_generate": False,
                    "custom_model_path": "",
                }
            },
            "40": {
                "class_type": "SaveAudioMP3",
                "inputs": {
                    "audio": ["13", 0],
                    "filename_prefix": "audio/Qwen3-TTS-Clone",
                    "quality": "128k",
                }
            }
        }

    def _ensure_ref_audio(self, ref_audio_path: str) -> Optional[str]:
        """确保参考音频在ComfyUI input目录中，返回文件名"""
        if not os.path.exists(ref_audio_path):
            print(f"  ⚠️  参考音频不存在: {ref_audio_path}")
            return None
        filename = os.path.basename(ref_audio_path)
        dest = os.path.join(COMFY_INPUT_DIR, filename)
        if not os.path.exists(dest):
            import shutil
            shutil.copy2(ref_audio_path, dest)
            print(f"  📋 已复制参考音频到ComfyUI: {filename}")
        return filename

    def _submit_and_wait(self, prompt: Dict, timeout: int = 120) -> Optional[str]:
        """提交prompt到ComfyUI并等待完成，返回音频文件名"""
        client_id = str(uuid.uuid4())
        payload = json.dumps({"prompt": prompt, "client_id": client_id}).encode("utf-8")
        req = urllib.request.Request(
            f"{COMFYUI_URL}/prompt",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        prompt_id = result.get("prompt_id")
        if not prompt_id:
            return None

        # 轮询等待
        start = time.time()
        while time.time() - start < timeout:
            try:
                req = urllib.request.Request(f"{COMFYUI_URL}/history/{prompt_id}")
                resp = urllib.request.urlopen(req, timeout=5)
                history = json.loads(resp.read())
                if prompt_id in history:
                    outputs = history[prompt_id].get("outputs", {})
                    for node_id, node_out in outputs.items():
                        audio_files = node_out.get("audio", [])
                        if audio_files:
                            return audio_files[0]["filename"], audio_files[0].get("subfolder", "")
            except Exception:
                pass
            time.sleep(1)
        return None, None

    def _download_audio(self, filename: str, subfolder: str, local_path: str) -> bool:
        """从ComfyUI下载生成的音频"""
        try:
            url = f"{COMFYUI_URL}/view?filename={filename}&subfolder={subfolder}&type=output"
            urllib.request.urlretrieve(url, local_path)
            return os.path.exists(local_path) and os.path.getsize(local_path) > 0
        except Exception as e:
            print(f"  ⚠️  下载失败: {e}")
            return False

    def synthesize(self, text: str, character: str = "默认",
                   emotion: str = "normal", output_file: str = None) -> Optional[str]:
        """合成单条语音（自动判断克隆音色/内置音色）"""
        if not text:
            return None

        if not self.check_comfyui():
            print(f"  ⚠️  ComfyUI不可用，跳过TTS")
            return None

        # 检查是否配置了克隆音色
        clone_cfg = CLONE_VOICE_MAP.get(character)

        if output_file is None:
            safe_char = character.replace("/", "_")
            suffix = "clone" if clone_cfg else emotion
            output_file = os.path.join(
                self.output_dir, f"{safe_char}_{suffix}_{abs(hash(text)) % 10000}.mp3"
            )

        # 缓存：如果文件已存在且非空，直接复用
        if os.path.exists(output_file) and os.path.getsize(output_file) > 1000:
            print(f"  ✅ TTS缓存: {character}({'clone' if clone_cfg else emotion}) - {text[:20]}...")
            return output_file

        if clone_cfg:
            # ===== 克隆音色路径 =====
            ref_filename = self._ensure_ref_audio(clone_cfg["ref_audio"])
            if not ref_filename:
                print(f"  ⚠️  克隆音色参考音频不可用，降级内置音色")
                clone_cfg = None
            else:
                prompt = self._build_clone_prompt(
                    text, ref_filename, clone_cfg["ref_text"]
                )
                result = self._submit_and_wait(prompt)
                if result and result[0]:
                    filename, subfolder = result
                    if self._download_audio(filename, subfolder, output_file):
                        print(f"  ✅ TTS克隆: {character} - {text[:20]}...")
                        return output_file
                print(f"  ⚠️  克隆音色生成失败，降级内置音色")
                clone_cfg = None

        if not clone_cfg:
            # ===== 内置音色路径 =====
            speaker = self.get_voice(character)
            instruct = self.get_instruct(emotion)
            prompt = self._build_prompt(text, speaker, instruct)
            result = self._submit_and_wait(prompt)

            if result and result[0]:
                filename, subfolder = result
                if self._download_audio(filename, subfolder, output_file):
                    print(f"  ✅ TTS: {character}({speaker}/{emotion}) - {text[:20]}...")
                    return output_file

        print(f"  ⚠️  TTS失败: {character} - {text[:20]}")
        return None

    def execute(self, tts_instructions: List[Dict]) -> Dict[str, Any]:
        """批量执行TTS"""
        print(f"\n{'='*60}")
        print(f"TTS执行器 (Qwen3-TTS): {len(tts_instructions)}条指令")
        print(f"{'='*60}")

        if not self.check_comfyui():
            print("  ❌ ComfyUI未运行，TTS全部跳过")
            return {"status": "failed", "total": len(tts_instructions),
                    "success": 0, "failed": len(tts_instructions),
                    "output_dir": self.output_dir, "results": []}

        results = []
        for i, instr in enumerate(tts_instructions):
            text = instr.get("text", "")
            character = instr.get("character", "默认")
            emotion = instr.get("emotion", "normal")
            voice_style = instr.get("voice_style", "")
            # 优先用voice_style（P24自动检测的拟人化语气），如果在映射表中就用它
            if voice_style and voice_style in EMOTION_INSTRUCT_MAP:
                emotion = voice_style
            elif voice_style and voice_style not in EMOTION_INSTRUCT_MAP:
                # 不在映射表中，尝试作为自定义instruct
                emotion = voice_style

            output_file = os.path.join(
                self.output_dir, f"tts_{i:03d}_{character}_{emotion}.mp3"
            )
            path = self.synthesize(text, character, emotion, output_file)
            results.append({
                "text": text,
                "character": character,
                "emotion": emotion,
                "voice": self.get_voice(character),
                "output_path": path,
                "success": path is not None,
            })

        success_count = sum(1 for r in results if r["success"])
        print(f"\n  完成: {success_count}成功 / {len(results)-success_count}失败")
        return {
            "status": "success" if success_count == len(results) else "partial",
            "total": len(results),
            "success": success_count,
            "failed": len(results) - success_count,
            "output_dir": self.output_dir,
            "results": results,
        }


if __name__ == "__main__":
    executor = TTSExecutor()
    test = [
        {"text": "你们外卖凭啥不让送上楼！", "character": "顾客", "emotion": "angry"},
        {"text": "女士，这是酒店规定。", "character": "前台", "emotion": "calm"},
        {"text": "行，那我自己去拿！", "character": "顾客", "emotion": "得意"},
    ]
    result = executor.execute(test)
    print(f"结果: {result['status']}")
