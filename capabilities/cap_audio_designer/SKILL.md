# cap_audio_designer — 音频设计模块

## 概述

BGM智能匹配、TTS旁白生成、音效推荐、多音轨管理，解决"音频搭配不合理"问题。

## 依赖

- jianying-editor（pyJianYingDraft）

## API

```python
from capabilities.cap_audio_designer import (
    match_bgm, add_bgm, add_tts_narration, add_sfx, auto_audio_design
)

# 1. BGM匹配
keywords = match_bgm("国风", mood="欢快")
# ['欢快', '明亮', '愉悦', '国风', '古风']

# 2. 添加BGM
add_bgm(project, "国风", start_time="0s", duration="30s")

# 3. TTS旁白
add_tts_narration(project, "这是一段旁白", start_time="1s", voice="女声_温柔")

# 4. 音效
add_sfx(project, "转场", start_time="3s", duration="0.5s")

# 5. 一键音频设计
auto_audio_design(project, "国风", duration=30,
                  narration_text="旁白文案。第二句。",
                  hook_text="钩子标题")
```

## BGM主题

| 主题 | 关键词 |
|------|--------|
| 国风 | 国风/古风/古筝/二胡/笛子 |
| 治愈 | 治愈/温暖/钢琴/吉他/民谣 |
| 卡点 | 电子/EDM/鼓点/动感/beat |
| 电影 | 电影/史诗/交响乐/大气/cinematic |
| 赛博 | 赛博朋克/合成器/科技感/synthwave |
| 极简 | 极简/氛围/环境音/ambient |
| 复古 | 复古/怀旧/爵士/lofi/80年代 |

## TTS音色

- 女声_温柔 / 女声_活泼 / 女声_知性
- 男声_磁性 / 男声_沉稳 / 男声_活力
- 童声 / 旁白_纪录片 / 旁白_情感

## 音效场景

转场 / 强调 / 氛围 / 搞笑 / 科技 / 自然
