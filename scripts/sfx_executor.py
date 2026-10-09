"""
音效执行器（SFX Executor）
三层音效生成架构：
  层1: TTS拟声词（砰/啪/嗖/叮咚，Qwen3-TTS，零延迟）
  层2: ffmpeg合成音效（铃声/警报/音调/噪声，快速）
  层3: AI生成（Stable Audio 3 Small SFX，复杂环境音/场景音）

生成的音效自动入库评级：
  TTS拟声词 → B级
  ffmpeg合成 → C级
  Stable Audio 3 → A级
  调用时优先检索库中高级别素材，未命中才生成
"""

import os
import sys
import subprocess
import json
import uuid
from typing import Dict, List, Optional

# 添加脚本目录到路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from sound_library import SoundLibrary
import logging
logger = logging.getLogger(__name__)


# 音效词典：动作/情绪 → 音效类型
# layer: 3=SA3优先(AI生成A级), 2=ffmpeg合成(C级), 1=TTS拟声词(B级)
# 层3失败自动降级到层2→层1
SFX_DICT = {
    # 攻击类（层3优先）
    "打": {"type": "impact", "ai": "impact", "tts": "砰！", "tags": ["撞击", "打斗"], "layer": 3},
    "踢": {"type": "impact", "ai": "impact", "tts": "嘭！", "tags": ["撞击", "打斗"], "layer": 3},
    "扇": {"type": "slap", "ai": "slap", "tts": "啪！", "tags": ["掌掴", "打斗"], "layer": 3},
    "揍": {"type": "impact", "ai": "impact", "tts": "砰！啪！", "tags": ["撞击", "打斗"], "layer": 3},
    "拍桌": {"type": "slam", "ai": "slam", "tts": "砰！", "tags": ["拍桌", "愤怒"], "layer": 3},
    "捶": {"type": "impact", "ai": "impact", "tts": "咚！", "tags": ["撞击", "打斗"], "layer": 3},
    "砸": {"type": "crash", "ai": "explosion", "tts": "哐当！", "tags": ["砸摔", "破碎"], "layer": 3},
    "撞": {"type": "impact", "ai": "impact", "tts": "砰！", "tags": ["撞击"], "layer": 3},
    "推": {"type": "push", "ai": "whoosh", "tts": "咻！", "tags": ["推动"], "layer": 3},
    # 环境类（层3优先）
    "开门": {"type": "door", "ai": "door", "synth": "door_open", "tags": ["开门", "环境"], "layer": 3},
    "关门": {"type": "door", "ai": "door", "synth": "door_close", "tags": ["关门", "环境"], "layer": 3},
    "门铃": {"type": "doorbell", "ai": "door", "synth": "doorbell", "tags": ["门铃", "提示"], "layer": 3},
    "电话": {"type": "phone", "ai": "phone", "synth": "phone_ring", "tags": ["电话", "提示"], "layer": 3},
    "警报": {"type": "alarm", "ai": "alarm", "synth": "alarm", "tags": ["警报", "紧急"], "layer": 3},
    "铃声": {"type": "bell", "ai": "bell", "synth": "bell", "tags": ["铃声", "提示"], "layer": 3},
    "脚步声": {"type": "footstep", "ai": "footstep", "synth": "footstep", "tags": ["脚步", "环境"], "layer": 3},
    "人群": {"type": "crowd", "ai": "crowd_chatter", "tags": ["人群", "环境"], "layer": 3},
    "街道": {"type": "street", "ai": "street_ambience", "tags": ["街道", "环境"], "layer": 3},
    "雨声": {"type": "rain", "ai": "rain", "tags": ["雨声", "环境"], "layer": 3},
    "风声": {"type": "wind", "ai": "wind", "tags": ["风声", "环境"], "layer": 3},
    "餐厅嘈杂声": {"type": "restaurant", "ai": "restaurant_ambience", "tags": ["餐厅", "嘈杂", "环境"], "layer": 3},
    "餐具碰撞": {"type": "cutlery", "ai": "cutlery_clinking", "tags": ["餐具", "碰撞", "餐厅"], "layer": 3},
    "掌声": {"type": "applause", "ai": "applause", "tags": ["掌声", "人群"], "layer": 3},
    "欢呼声": {"type": "cheer", "ai": "crowd_cheering", "tags": ["欢呼", "人群"], "layer": 3},
    "爆炸声": {"type": "explosion", "ai": "explosion", "tags": ["爆炸", "冲击"], "layer": 3},
    "玻璃破碎": {"type": "glass_break", "ai": "glass_breaking", "tags": ["玻璃", "破碎"], "layer": 3},
    "水流声": {"type": "water", "ai": "water_flowing", "tags": ["水流", "环境"], "layer": 3},
    "鸟鸣": {"type": "birds", "ai": "birds_chirping", "tags": ["鸟鸣", "自然"], "layer": 3},
    "汽车喇叭": {"type": "car_horn", "ai": "car_horn", "tags": ["汽车", "喇叭", "城市"], "layer": 3},
    "键盘敲击": {"type": "keyboard", "ai": "keyboard_typing", "tags": ["键盘", "办公"], "layer": 3},
    "写字声": {"type": "writing", "ai": "pen_writing", "tags": ["写字", "办公"], "layer": 3},
    "翻书声": {"type": "page_turn", "ai": "page_turning", "tags": ["翻书", "办公"], "layer": 3},
    "敲门声": {"type": "knock", "ai": "door_knock", "synth": "knock", "tags": ["敲门", "提示"], "layer": 3},
    "咳嗽声": {"type": "cough", "tts": "咳咳", "tags": ["咳嗽", "人声"], "layer": 1},
    "叹气声": {"type": "sigh", "tts": "唉……", "tags": ["叹气", "情绪"], "layer": 1},
    # 情绪类（层1=TTS人声拟声词，更自然）
    "惊讶": {"type": "gasp", "tts": "啊！", "tags": ["惊讶", "情绪"], "layer": 1},
    "叹气": {"type": "sigh", "tts": "唉……", "tags": ["叹气", "情绪"], "layer": 1},
    "冷笑": {"type": "scoff", "tts": "哼。", "tags": ["冷笑", "情绪"], "layer": 1},
    "哭泣": {"type": "cry", "tts": "呜呜……", "tags": ["哭泣", "情绪"], "layer": 1},
    "笑声": {"type": "laugh", "tts": "哈哈哈！", "tags": ["笑声", "情绪"], "layer": 1},
    "尖叫": {"type": "scream", "tts": "啊——！", "tags": ["尖叫", "情绪"], "layer": 1},
    # 转场类（层3优先）
    "嗖": {"type": "whoosh", "ai": "whoosh", "tts": "嗖——", "tags": ["转场", "速度"], "layer": 3},
    "叮": {"type": "ding", "ai": "ding", "synth": "ding", "tags": ["提示", "转场"], "layer": 3},
    "闪白": {"type": "flash", "ai": "flash", "synth": "flash", "tags": ["闪白", "转场"], "layer": 3},
}


class SFXExecutor:
    """音效执行器"""

    def __init__(self, work_dir: str = None, comfyui_url: str = "http://127.0.0.1:8188"):
        self.work_dir = work_dir or os.path.join(
            r"D:\DobaoWork_Project\Ai_Video_Editor", "ai-video-editor-runtime", "sfx_output"
        )
        os.makedirs(self.work_dir, exist_ok=True)
        self.library = SoundLibrary()
        self.comfyui_url = comfyui_url
        self.ffmpeg = r"D:\Ai\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"
        self.python = r"C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe"

        # TTS执行器（延迟导入，避免循环依赖）
        self._tts_executor = None

    @property
    def tts_executor(self):
        if self._tts_executor is None:
            try:
                from tts_executor import TTSExecutor
                self._tts_executor = TTSExecutor()
            except Exception as e:
                logger.info(f"  ⚠️ TTS执行器不可用: {e}")
        return self._tts_executor

    def generate(self, sfx_type: str, emotion: str = "normal",
                 duration: float = 1.0) -> Optional[Dict]:
        """
        生成音效（优先检索库，未命中才生成）

        Args:
            sfx_type: 音效类型（对应SFX_DICT的key）
            emotion: 情绪（影响TTS拟声词语气）
            duration: 期望时长（秒）

        Returns:
            {path, name, source, rating, duration, from_cache}
        """
        # 1. 先检索库
        cached = self._search_library(sfx_type, emotion)
        if cached:
            return {
                "path": cached["path"],
                "name": cached["name"],
                "source": cached["source"],
                "rating": cached["rating"],
                "duration": cached["duration"],
                "from_cache": True,
            }

        # 2. 未命中，按层级生成
        config = SFX_DICT.get(sfx_type)
        if not config:
            # 未知类型，优先用AI生成（layer=3），失败降级到TTS拟声词
            config = {"type": sfx_type, "ai": sfx_type, "tts": sfx_type, "tags": [sfx_type], "layer": 3}

        layer = config.get("layer", 1)
        result = None

        # 按层级尝试生成，高层失败自动降级
        if layer >= 3 and "ai" in config:
            result = self._gen_stable_audio_3(config, duration)
            if result:
                return result
            logger.info(f"  ⚠️ 层3(AI生成)失败，降级到层2/层1")

        if layer >= 2 and "synth" in config:
            result = self._gen_ffmpeg_synth(config, duration)
            if result:
                return result
            logger.info(f"  ⚠️ 层2(ffmpeg合成)失败，降级到层1")

        if "tts" in config:
            result = self._gen_tts_onomatopoeia(config, emotion)
        else:
            # 无TTS配置，用默认拟声词
            fallback_config = dict(config)
            fallback_config["tts"] = "叮！"
            result = self._gen_tts_onomatopoeia(fallback_config, emotion)

        return result

    def _search_library(self, sfx_type: str, emotion: str) -> Optional[Dict]:
        """检索音效库"""
        tags = [sfx_type]
        if emotion and emotion != "normal":
            tags.append(emotion)
        result = self.library.get_best(query=sfx_type, tags=tags)
        if result and os.path.exists(result["path"]):
            return result
        return None

    def _gen_tts_onomatopoeia(self, config: Dict, emotion: str) -> Optional[Dict]:
        """层1: TTS拟声词"""
        if not self.tts_executor:
            return None

        text = config.get("tts", "砰！")
        tags = config.get("tags", [])
        sfx_type = config.get("type", "unknown")

        try:
            # 用TTS生成拟声词，情绪参数影响语气
            result = self.tts_executor.synthesize(
                text=text,
                character="旁白",  # 用旁白音色
                emotion=emotion if emotion != "normal" else "平静",
            )
            if result and os.path.exists(result):
                # 入库（B级）
                name = f"{sfx_type}_tts_{uuid.uuid4().hex[:6]}"
                sound_id = self.library.add_sound(
                    name=name, path=result, tags=tags + ["tts", "拟声词"],
                    source="tts", rating="B",
                    duration=self._get_audio_duration(result),
                    description=f"TTS拟声词: {text}",
                    quality_score=0.6,
                )
                return {
                    "path": result, "name": name, "source": "tts",
                    "rating": "B", "duration": self._get_audio_duration(result),
                    "from_cache": False, "sound_id": sound_id,
                }
        except Exception as e:
            logger.info(f"  ⚠️ TTS拟声词生成失败: {e}")
        return None

    def _gen_ffmpeg_synth(self, config: Dict, duration: float) -> Optional[Dict]:
        """层2: ffmpeg合成音效"""
        synth_type = config.get("synth", "ding")
        tags = config.get("tags", [])
        sfx_type = config.get("type", "unknown")

        output_path = os.path.join(self.work_dir, f"{sfx_type}_synth_{uuid.uuid4().hex[:6]}.mp3")

        # ffmpeg合成命令映射
        commands = {
            "ding": f'-f lavfi -i "sine=frequency=880:duration={duration}" -af "afade=t=out:st={duration*0.5}:d={duration*0.5}"',
            "doorbell": f'-f lavfi -i "sine=frequency=523:duration=0.3" -f lavfi -i "sine=frequency=659:duration=0.3" -filter_complex "[0][1]concat=n=2:v=0:a=1"',
            "phone_ring": f'-f lavfi -i "sine=frequency=440:duration=0.2" -f lavfi -i "sine=frequency=480:duration=0.2" -filter_complex "[0][1]concat=n=2:v=0:a=1[out]" -af "aloop=loop=3:size=8820"',
            "alarm": f'-f lavfi -i "sine=frequency=880:duration=0.15" -f lavfi -i "sine=frequency=660:duration=0.15" -filter_complex "[0][1]concat=n=2:v=0:a=1[out]" -af "aloop=loop=4:size=6615"',
            "bell": f'-f lavfi -i "sine=frequency=1046:duration={duration}" -af "afade=t=out:st=0:d={duration}"',
            "door_open": f'-f lavfi -i "sine=frequency=200:duration={duration}" -af "afade=t=in:st=0:d=0.1,afade=t=out:st={duration*0.7}:d={duration*0.3}"',
            "door_close": f'-f lavfi -i "sine=frequency=150:duration={duration}" -af "afade=t=out:st=0:d={duration}"',
            "footstep": f'-f lavfi -i "anoisesrc=d={duration}:c=pink:r=44100" -af "atempo=2.0,volume=0.3"',
            "flash": f'-f lavfi -i "sine=frequency=1200:duration=0.1" -af "afade=t=out:st=0:d=0.1"',
        }

        cmd_args = commands.get(synth_type, commands["ding"])

        try:
            full_cmd = f'"{self.ffmpeg}" -y {cmd_args} -acodec libmp3lame -q:a 4 "{output_path}"'
            subprocess.run(full_cmd, shell=True, capture_output=True, timeout=15)

            if os.path.exists(output_path):
                # 入库（C级）
                name = f"{sfx_type}_synth_{uuid.uuid4().hex[:6]}"
                sound_id = self.library.add_sound(
                    name=name, path=output_path, tags=tags + ["synth", "ffmpeg"],
                    source="synth", rating="C",
                    duration=self._get_audio_duration(output_path),
                    description=f"ffmpeg合成: {synth_type}",
                    quality_score=0.4,
                )
                return {
                    "path": output_path, "name": name, "source": "synth",
                    "rating": "C", "duration": self._get_audio_duration(output_path),
                    "from_cache": False, "sound_id": sound_id,
                }
        except Exception as e:
            logger.info(f"  ⚠️ ffmpeg合成失败: {e}")
        return None

    def _gen_stable_audio_3(self, config: Dict, duration: float) -> Optional[Dict]:
        """层3: Stable Audio 3 Small SFX AI生成（ComfyUI API调用）"""
        import urllib.request
        import urllib.error

        ai_prompt = config.get("ai", config.get("type", "sound effect"))
        tags = config.get("tags", [])
        sfx_type = config.get("type", "unknown")
        duration = min(duration, 30.0)

        # 英文提示词效果更好
        prompt_map = {
            "crowd_chatter": "crowd of people talking, ambient room noise",
            "street_ambience": "city street ambience, traffic, distant cars",
            "rain": "gentle rain falling, soft rainfall",
            "wind": "wind blowing through trees",
            "fire": "crackling fire, burning wood",
            "ocean": "ocean waves crashing on beach",
            "forest": "forest ambience, birds chirping",
            "thunder": "thunder rumbling, lightning",
            "applause": "crowd applause, clapping",
            "explosion": "deep explosion, boom",
            "impact": "punch impact with deep bass hit, cinematic trailer style",
            "slap": "sharp slap impact, quick decay",
            "whoosh": "fast whoosh passing by, doppler effect",
            "door": "wooden door creaking open slowly",
            "footstep": "footsteps on hard floor, steady walking pace",
        }
        en_prompt = prompt_map.get(ai_prompt, f"{ai_prompt} sound effect")
        text_prompt = f"{en_prompt}, high quality, clean audio. Length: {int(duration)} seconds"

        output_path = os.path.join(self.work_dir, f"{sfx_type}_ai_{uuid.uuid4().hex[:6]}.flac")

        try:
            logger.info(f"  ⏳ Stable Audio 3生成中: {en_prompt} ({duration}s)")

            # 构建ComfyUI工作流
            workflow = {
                '1': {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': 'stable-audio-3-small-sfx.safetensors'}},
                '2': {'class_type': 'CLIPLoader', 'inputs': {'clip_name': 't5gemma_b_b_ul2.safetensors', 'type': 'stable_audio', 'device': 'default'}},
                '3': {'class_type': 'CLIPTextEncode', 'inputs': {'text': text_prompt, 'clip': ['2', 0]}},
                '4': {'class_type': 'EmptyLatentAudio', 'inputs': {'seconds': int(duration), 'batch_size': 1}},
                '5': {'class_type': 'KSampler', 'inputs': {'seed': 42, 'steps': 8, 'cfg': 1.0, 'sampler_name': 'lcm', 'scheduler': 'simple', 'denoise': 1.0, 'model': ['1', 0], 'positive': ['3', 0], 'negative': ['3', 0], 'latent_image': ['4', 0]}},
                '6': {'class_type': 'VAEDecodeAudio', 'inputs': {'samples': ['5', 0], 'vae': ['1', 2]}},
                '7': {'class_type': 'SaveAudio', 'inputs': {'audio': ['6', 0], 'filename_prefix': 'sfx_ai'}},
            }

            # 提交任务
            data = json.dumps({'prompt': workflow}).encode()
            req = urllib.request.Request(f'{self.comfyui_url}/prompt', data=data, headers={'Content-Type': 'application/json'})
            resp = json.loads(urllib.request.urlopen(req, timeout=10).read())
            pid = resp.get('prompt_id')
            if not pid:
                logger.info(f"  ⚠️ ComfyUI未返回任务ID")
                return None

            # 等待完成（最多120秒）
            output_file = None
            for i in range(60):
                import time
                time.sleep(2)
                try:
                    hist = json.loads(urllib.request.urlopen(f'{self.comfyui_url}/history/{pid}', timeout=5).read())
                    if pid in hist:
                        outputs = hist[pid].get('outputs', {})
                        for nid, out in outputs.items():
                            if 'audio' in out:
                                for a in out['audio']:
                                    output_file = a['filename']
                        break
                except Exception:
                    pass

            if not output_file:
                logger.info(f"  ⚠️ Stable Audio 3生成超时")
                return None

            # 从ComfyUI output目录复制到工作目录
            comfy_output = r"D:\Ai\ComfyUI-aki-v3.2\ComfyUI\output"
            src_path = os.path.join(comfy_output, output_file)
            if os.path.exists(src_path):
                import shutil
                shutil.copy2(src_path, output_path)
                try:
                    os.remove(src_path)
                except Exception:
                    pass
            else:
                logger.info(f"  ⚠️ 输出文件不存在: {src_path}")
                return None

            if os.path.exists(output_path):
                # 转码为mp3（更小）
                mp3_path = output_path.replace(".flac", ".mp3")
                transcode_cmd = f'"{self.ffmpeg}" -y -i "{output_path}" -acodec libmp3lame -q:a 4 "{mp3_path}"'
                subprocess.run(transcode_cmd, shell=True, capture_output=True, timeout=15)
                if os.path.exists(mp3_path):
                    final_path = mp3_path
                    try:
                        os.remove(output_path)
                    except Exception:
                        pass
                else:
                    final_path = output_path

                # 入库（A级）
                name = f"{sfx_type}_ai_{uuid.uuid4().hex[:6]}"
                sound_id = self.library.add_sound(
                    name=name, path=final_path, tags=tags + ["ai", "stable_audio_3"],
                    source="ai", rating="A",
                    duration=self._get_audio_duration(final_path),
                    description=f"Stable Audio 3生成: {ai_prompt}",
                    quality_score=0.85,
                )
                return {
                    "path": final_path, "name": name, "source": "ai",
                    "rating": "A", "duration": self._get_audio_duration(final_path),
                    "from_cache": False, "sound_id": sound_id,
                }
        except urllib.error.URLError as e:
            logger.info(f"  ⚠️ ComfyUI连接失败: {e}")
        except Exception as e:
            logger.info(f"  ⚠️ Stable Audio 3生成失败: {e}")
        return None

    def _get_audio_duration(self, path: str) -> float:
        """获取音频时长（秒）"""
        try:
            ffprobe = self.ffmpeg.replace("ffmpeg.exe", "ffprobe.exe")
            result = subprocess.run(
                f'"{ffprobe}" -v quiet -print_format json -show_format "{path}"',
                shell=True, capture_output=True, text=True, timeout=10
            )
            info = json.loads(result.stdout)
            return float(info.get("format", {}).get("duration", 0))
        except Exception:
            return 1.0

    def batch_generate(self, sfx_list: List[Dict]) -> List[Dict]:
        """
        批量生成音效

        Args:
            sfx_list: [{type, emotion, duration, start_time}, ...]

        Returns:
            生成结果列表
        """
        results = []
        for sfx in sfx_list:
            sfx_type = sfx.get("type", "ding")
            emotion = sfx.get("emotion", "normal")
            duration = sfx.get("duration", 1.0)
            result = self.generate(sfx_type, emotion, duration)
            if result:
                result["start_time"] = sfx.get("start_time", 0)
                results.append(result)
                logger.info(f"  ✅ 音效: {sfx_type} → {result['rating']}级 ({'缓存' if result['from_cache'] else '新生成'})")
            else:
                logger.info(f"  ❌ 音效生成失败: {sfx_type}")
        return results

    def get_library_stats(self) -> Dict:
        """获取音效库统计"""
        return self.library.get_stats()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info("=" * 60)
    logger.info("音效执行器测试")
    logger.info("=" * 60)

    executor = SFXExecutor()

    # 测试生成几种音效
    test_sfx = [
        {"type": "拍桌", "emotion": "愤怒", "duration": 0.5},
        {"type": "门铃", "emotion": "normal", "duration": 1.0},
        {"type": "惊讶", "emotion": "惊讶", "duration": 0.5},
        {"type": "嗖", "emotion": "normal", "duration": 0.5},
    ]

    logger.info("\n生成测试音效:")
    results = executor.batch_generate(test_sfx)

    logger.info(f"\n生成 {len(results)}/{len(test_sfx)} 个音效")
    for r in results:
        logger.info(f"  [{r['rating']}] {r['name']} ({r['source']}) - {r['duration']:.1f}s - {'缓存' if r['from_cache'] else '新生成'}")

    logger.info(f"\n音效库统计: {json.dumps(executor.get_library_stats(), ensure_ascii=False, indent=2)}")
