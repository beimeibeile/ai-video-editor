# 踩坑自学习日志 (Pitfalls Log)

> 记录开发过程中遇到的所有"被同一块石头绊倒"的问题，确保不再重复犯错。

## PIT-001: 剪映坐标系统
- **问题**: 剪映坐标x范围-1~1（左负右正），y正=上（与像素坐标相反）
- **根因**: 直接使用像素坐标导致元素位置错误
- **解决**: `x = pixel_x / canvas_w * 2 - 1`，`y = -(pixel_y / canvas_h * 2 - 1)`
- **状态**: 已解决，已建立coord_calibrator.py工具和verified_params.json参数库

## PIT-002: 蒙版size单位
- **问题**: 蒙版size是相对画布高度的比例，不是像素
- **根因**: 直接传入像素值导致蒙版过大
- **解决**: `mask_size = diameter_pixels / canvas_h`
- **状态**: 已解决

## PIT-003: scale单位
- **问题**: scale是相对素材原始像素的比例，不是相对画布
- **根因**: 用画布尺寸计算scale导致缩放错误
- **解决**: `scale = target_display_pixels / material_native_pixels`
- **状态**: 已解决

## PIT-004: 静态图片duration检测
- **问题**: add_media_safe对静态图片duration检测有bug
- **根因**: pymediainfo无法解析图片时长，返回None
- **解决**: 直接创建VideoSegment并显式设置duration
- **状态**: 已解决

## PIT-005: 片段不能时间重叠
- **问题**: 同一轨道的图片片段不能时间重叠（SegmentOverlap）
- **根因**: 剪映不支持同一轨道片段重叠
- **解决**: 首尾相接，或使用不同轨道
- **状态**: 已解决

## PIT-006: 单个圆形蒙版无法解决豆包掉出头像框
- **问题**: 豆包动画移动时会掉出圆形头像框
- **根因**: 蒙版跟随素材移动，不跟随头像框
- **解决**: 采用透明背景动画上层遮挡方案，或头像框蒙版固定在背景层
- **状态**: 已验证，采用透明背景动画方案

## PIT-007: 剪映转场对前后素材时长有最低限制
- **问题**: 短素材添加转场导致工程无法渲染
- **根因**: 剪映内置转场要求前后素材时长足够
- **解决**: 改用透明度关键帧实现转场效果
- **状态**: 已解决

## PIT-008: ffmpeg滤镜标签名不能以a/v/s/d/t开头
- **问题**: `[a0]`、`[t0]`等标签名被ffmpeg解析为流选择器而非滤镜输出标签
- **根因**: ffmpeg中a=音频流, v=视频流, s=字幕流, d=数据流, t=附件流，`[a0]`被解析为"所有音频流第0个"
- **错误信息**: `Invalid stream specifier: a0` / `matches no streams`
- **解决**: 使用不以a/v/s/d/t开头的标签名，如`[p0]`（processed）、`[dk1]`（ducked）、`[mixed]`、`[out]`
- **状态**: 已解决，multi_track_mixer.py已全部改用[p{i}]标签

## PIT-009: ffmpeg滤镜输出标签只能被消费一次
- **问题**: sidechaincompress用了人声标签做侧链后，amix不能再引用同一个标签
- **根因**: ffmpeg滤镜图中一个输出标签只能被消费一次
- **错误信息**: `matches no streams`
- **解决**: 用asplit滤镜先分流：`[p0]asplit=2[vsc0][vmix0]`，侧链用[vsc0]，混合用[vmix0]
- **状态**: 已解决

## PIT-010: ffmpeg afade不能同时做淡入淡出
- **问题**: `afade=t=in:st=0:d=0.1:t=out:st=4.8:d=0.2`语法错误
- **根因**: afade一次只能做一个方向（t=in或t=out）
- **解决**: 串联两个afade：`afade=t=in:st=0:d=0.1,afade=t=out:st=4.8:d=0.2`
- **状态**: 已解决

## PIT-011: ffmpeg sidechaincompress输出时长=侧链信号时长
- **问题**: 闪避后BGM时长被截断为人声时长（9秒而非25秒）
- **根因**: sidechaincompress输出时长等于侧链信号（人声）时长，而非被压缩信号（BGM）时长
- **解决**: 侧链信号先apad延长：`[vsc0]apad[vscp0]`，再用[vscp0]做sidechaincompress
- **状态**: 已解决

## PIT-012: JyProjectBase没有save方法
- **问题**: project.save()报错AttributeError
- **根因**: JyProjectBase没有save方法，只有script属性有save方法
- **解决**: 使用project.script.save()，保存路径从project.draft_dir获取
- **状态**: 已解决

## PIT-013: JyProjectBase没有_stage_local_asset方法
- **问题**: 调用project._stage_local_asset()报错
- **根因**: 该方法在media_ops.py的MediaOpsMixin中，JyProjectBase未继承
- **解决**: 手动复制素材到草稿目录的materials/子目录
- **状态**: 已解决

## PIT-014: AudioSegment.add_keyframe只接受2个参数
- **问题**: add_keyframe(time_offset, volume, property)报错
- **根因**: 音频关键帧只支持volume属性，方法签名是(time_offset, volume)
- **解决**: 直接调用add_keyframe(time_offset, volume)
- **状态**: 已解决

## PIT-015: ComfyUI dit.py合并冲突导致启动失败
- **问题**: ComfyUI启动报SyntaxError: invalid syntax
- **根因**: comfy/ldm/audio/dit.py文件中有<<<<<<< HEAD合并冲突标记
- **解决**: 手动解决合并冲突或恢复文件
- **状态**: 已解决（用户已修复）

## PIT-016: JyProjectBase没有add_media_safe方法
- **问题**: 调用project.add_media_safe()报错AttributeError
- **根因**: add_media_safe在MediaOpsMixin中，只有JyProject（继承了MediaOpsMixin）才有，JyProjectBase没有
- **解决**: 使用JyProject而非JyProjectBase创建工程
- **状态**: 已解决

## PIT-017: KeyframeProperty透明度是alpha不是opacity
- **问题**: KeyframeProperty.opacity不存在
- **根因**: 剪映关键帧属性枚举中透明度叫alpha（KFTypeAlpha），不叫opacity
- **解决**: 使用KeyframeProperty.alpha，值范围0~1（1=完全不透明）
- **状态**: 已解决

## PIT-018: TextSegment参数名是timerange/style/border/shadow
- **问题**: TextSegment(text, target_timerange=..., text_style=...)报错
- **根因**: TextSegment构造函数参数名是timerange（非target_timerange）、style（非text_style）、border（非在style里设置stroke）、shadow直接传参
- **解决**: `TextSegment(text, timerange=Timerange(...), style=TextStyle(...), border=TextBorder(...), shadow=TextShadow(...))`
- **状态**: 已解决

## PIT-019: add_track参数名是track_name不是name
- **问题**: script.add_track(TrackType.text, name="字幕")报错
- **根因**: add_track方法的轨道名称参数叫track_name，不叫name
- **解决**: `script.add_track(TrackType.text, track_name="字幕")`
- **状态**: 已解决

## PIT-020: 同轨道片段不能时间重叠（文字/视频都一样）
- **问题**: 同一轨道添加时间重叠的片段报SegmentOverlap
- **根因**: 剪映不支持同一轨道片段时间重叠（包括文字轨道和视频轨道）
- **解决**: 错开时间，或使用不同轨道（如"字幕"和"特效字幕"两个轨道）
- **状态**: 已解决

## PIT-021: script.materials没有add方法
- **问题**: script.materials.add(material)报错
- **根因**: materials是MaterialsManager对象，没有add方法，素材登记由add_media_safe自动处理
- **解决**: 使用project.add_media_safe()自动处理素材登记，不要手动操作script.materials
- **状态**: 已解决

## PIT-022: 剪映草稿缺少主轨道（is_main=False）导致播放无反应、打开关闭卡顿
- **问题**: 所有通过pyJianYingDraft创建的剪映草稿，video轨道的is_main字段都是False，剪映打开后播放无反应，打开/关闭耗时很长
- **根因**: pyJianYingDraft的Track类不支持is_main属性，export_json()不输出该字段；add_track()也不自动设置第一个video轨道为is_main=True
- **影响范围**: 全部141个草稿（已批量修复），17个因JSON损坏无法修复
- **解决**: 
  1. 修改`track.py`的Track类：添加`is_main`属性（默认False），`__init__`接受`is_main`参数，`export_json()`输出`is_main`字段
  2. 修改`script_file.py`的`add_track()`：添加第一个video轨道时自动设置`is_main=True`
  3. 批量修复脚本：`debug/fix_main_track.py`，扫描所有草稿将第一个video轨道设为is_main=True
- **验证**: ScriptFile测试通过，第一个video轨道自动is_main=True，JSON输出正确
- **状态**: 已根本修复（vendor库已修改），现有草稿已批量修复

## PIT-023: Remotion 透明背景视频渲染 — CLI直接编码丢失Alpha通道

- **问题**: Remotion CLI 使用 --transparent 标志渲染 WebM/MOV 视频时，输出文件不包含 Alpha 通道（pix_fmt=yuv420p），透明背景变成黑色
- **根因**: Remotion 的视频编码阶段（ffmpeg）默认不保留 Alpha 通道，即使 --transparent 标志在帧渲染阶段正确输出了 RGBA
- **验证过程**:
  1. WebM VP8（默认）: pix_fmt=yuv420p，无Alpha ❌
  2. WebM VP9（--codec vp9）: pix_fmt=yuv420p，无Alpha ❌
  3. MOV ProRes 4444（--codec prores --prores-profile 4444）: pix_fmt=yuv422p12le，无Alpha ❌
  4. 单帧PNG（--transparent）: pix_fmt=rgba，有Alpha ✅
  5. PNG序列（--transparent --sequence）: 每帧rgba，有Alpha ✅
  6. ffmpeg合成VP9（-pix_fmt yuva420p）: 编码后仍yuv420p，Alpha丢失 ❌
  7. ffmpeg合成ProRes 4444（-c:v prores_ks -profile:v 4 -pix_fmt yuva444p12le）: pix_fmt=yuva444p12le，有Alpha ✅
  8. ffmpeg合成APNG（-plays 0 -f apng）: pix_fmt=rgba，有Alpha ✅（但剪映可能不支持）
- **解决方案**: 两步法 — Remotion渲染PNG序列 → ffmpeg合成ProRes 4444
  1. 
px remotion render src/index.ts Comp out/seq --transparent --sequence
  2. fmpeg -framerate 30 -i out/seq/element-%03d.png -c:v prores_ks -profile:v 4 -pix_fmt yuva444p12le out/output.mov
- **已封装**: emotion_controls.py render-transparent 命令自动完成两步流程+临时文件清理
- **验证结果**: 5秒1080x1920，4.59MB，yuva444p12le，Alpha=True，剪映兼容 ✅
- **状态**: 已根本解决（Remotion-controls-skill已封装）
## PIT-024: add_media_safe导入视频时自动转码导致Alpha通道丢失

- **问题**: 通过project.add_media_safe()导入ProRes 4444 mov（带Alpha通道）时，剪映工程中生成的是0.07MB的mp4文件，透明背景变成黑色
- **根因**: dd_media_safe在导入视频时会触发剪映的媒体规范化/转码流程，将ProRes 4444转码为H.264 mp4，而H.264不支持Alpha通道
- **验证**: 18.22MB mov → 0.07MB mp4（转码后），pix_fmt从yuva444p12le变为yuv420p（无Alpha）
- **解决方案**: 直接复制mov文件到草稿materials目录，手动创建VideoMaterial和VideoSegment，不通过add_media_safe导入
  1. shutil.copy2(mov_path, os.path.join(draft_dir, 'materials', 'anim.mov'))
  2. material = LocalVideoMaterial(mov_dst, duration=20000000)
  3. project.script.materials.videos.append(material)
  4. segment = VideoSegment(material=material, target_timerange=Timerange(0, 20000000))
  5. project.script.add_segment(segment, track_name='动画层')
- **状态**: 已根本解决（v6修复版验证通过）

## PIT-025: 用jianying-editor创建的工程剪映草稿列表不显示

- **问题**: 用build脚本创建的v8/v9/v10-v14工程，文件目录存在但剪映草稿列表看不到，只有在剪映里手动打开过的工程（如v7_简化版）才能显示
- **根因**: 三重缺失导致剪映无法识别新工程：
  1. **双草稿目录**: jianying-editor的`get_default_drafts_root()`返回`D:\JianyingProDrafts\JianyingPro Drafts\`，而剪映实际管理目录在`C:\Users\...\com.lveditor.draft\`，索引文件root_meta_info.json在C盘
  2. **缺少辅助文件**: skill创建的工程只有draft_info.json+draft_meta_info.json+draft_settings+key_value.json+materials，缺少剪映必需的draft_cover.jpg封面图、Timelines目录、draft_content.json、attachment_pc_common.json、timeline_layout.json等20+文件
  3. **索引未注册/时间戳过期**: 剪映通过`root_meta_info.json`的`all_draft_store`数组管理草稿列表，不是直接扫描目录；新工程的tm_draft_modified时间戳太旧排在列表底部，或tm_duration=0被误认为空工程
- **验证**: v9工程目录完整但tm_duration=0、size=4MB（实际34MB）、无封面图 → 剪映不显示
- **解决方案**: 新建工程后必须执行三步修复：
  1. 从已显示的工程（如v7_简化版）复制所有辅助文件到新工程目录（不覆盖draft_info.json和materials）
  2. 确保materials目录包含完整素材（动画mov等），计算实际大小
  3. 更新root_meta_info.json中对应条目的tm_duration=20000000、draft_timeline_materials_size=实际大小、tm_draft_modified=当前时间戳
- **根本修复方向**: 在build脚本中集成上述三步，创建工程后自动补全辅助文件+更新索引
- **状态**: 已解决（v8/v9/v10-v14手动修复验证通过），待集成到build脚本

## PIT-026: 动画素材质量验证 — 首帧/末帧全黑检查对透明背景动画不适用

- **问题**: 验证脚本用"首帧非全黑/末帧非全黑"检查动画素材，但透明背景动画的首帧/末帧通常是全透明的（角色还没出现/已经消失），提取为JPG后变成全黑，导致误报失败
- **根因**: 透明背景动画的Alpha=0区域在提取为JPG时变成黑色，"全黑"实际上是"全透明"，这是正常的
- **验证**: v9动画首帧亮度=0.5（全透明），但中段有内容，动画本身是合格的
- **解决方案**: 
  1. 用PNG格式提取帧（保留Alpha通道），检查"非透明像素比例"而非"亮度"
  2. 首帧/末帧内容只记录不报错（INFO级别），因为透明背景动画首尾全透明是正常的
  3. 用"内容覆盖率"替代"中段单点检查"：10个时间点采样，覆盖率≥30%（短动画）或≥50%（长动画）即通过
- **已封装**: `remotion-controls-skill/verify_animation.py` 自动化验证工具，11项检查
- **质量标准**: `remotion-controls-skill/QUALITY_STANDARD.md` 定义A/B/C三级标准
- **基础组件库**: `remotion-project/src/components/`（CharacterSprite/MotionPath/Effects），已验证可正常渲染
- **状态**: 已根本解决（验证脚本v1.1，组件库v1.0）