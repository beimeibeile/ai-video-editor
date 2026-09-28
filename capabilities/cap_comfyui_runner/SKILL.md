# cap_comfyui_runner — ComfyUI 本地算力集成模块

## 概述

通过 ComfyUI REST API（默认 `http://127.0.0.1:8188`）操作本地 ComfyUI 实例，执行批量、耗时、耗算力的图像处理任务。

## 已验证能力（最佳方案）

### 1. 图片超分 (upscale_image / upscale_batch)
- **模型**：9种 ESRGAN 系列（RealESRGAN_x4plus, 4x-UltraSharp, SwinIR_4x 等）
- **验证**：256×256 → 1024×1024 测试通过
- **用途**：低分辨率素材放大、老照片修复

### 2. 批量抠图 (matting_image / matting_batch)
- **模型**：BiRefNet（12种）+ RMBG（4种）
- **输出**：RGBA 模式，背景完全透明
- **验证**：测试图抠图通过，Alpha 通道范围 0-255
- **用途**：人物/物体抠图、贴纸制作、背景替换

### 3. 人脸统一 (face_unify_image / face_unify_batch)
- **方案**：ReActor 人脸交换（inswapper_128.onnx）
- **原理**：将源脸的人脸特征精确交换到目标图，保留目标图的服装/背景/构图
- **参数**：swap_model, facedetection(retinaface_resnet50), face_restore_model(none/GFPGAN/codeformer)
- **验证**：单张 + 批量（3张）测试通过，输出 1080×1920，人脸融合自然
- **用途**：统一系列图片的人物五官、角色一致性
- **注意**：face_restore_model=GFPGAN/codeformer 会触发下载retinaface检测模型（网络不通时失败），默认用none

### 4. ControlNet生成 (controlnet_generate)
- **模型**：8种（openpose/canny/depth/lineart/softedge/seg/inpaint/tile）
- **原理**：用控制图（姿态骨架/边缘/深度）引导文生图，精确控制构图和姿态
- **参数**：control_image, controlnet_model, strength(0-1), positive_prompt, negative_prompt
- **验证**：openpose姿态控制测试通过，strength=0.85效果最佳
- **用途**：姿态控制、构图控制、风格迁移、线稿上色

### 5. 角色三视图 — Qwen方案（最佳方案）(generate_character_views_qwen)
- **方案**：千问Qwen-Image-Edit图像编辑模型 + Lightning 4steps LoRA
- **原理**：图像编辑模型直接从原图生成不同角度视图，天然保持人物特征和服装一致，无需额外人脸统一
- **模型**：qwen_image_edit_2511_fp8 + Qwen-Image-Edit-2511-Lightning-4steps + qwen_image_vae + qwen_2.5_vl_7b_fp8
- **所需插件**：ComfyUI-Custom-Scripts、ComfyUI-KJNodes、ComfyUI-Easy-Use、ComfyUI_LayerStyle（目录名可能带-main后缀）
- **视角**：front(正面)/side(侧面)/back(背面)/half(上半身)，支持任意组合
- **输出**：单视图PNG + 横向拼接图（three_views_concat.png）
- **尺寸限制**：16GB显存以上用2048，不足用1024或1536（longer_edge参数）
- **留白控制**：crop_top（裁剪上方）、crop_sides（裁剪两侧），数值越大留白越少
- **自定义提示词**：custom_prompt追加到所有视图（如"黑色鞋子，蓝色裤子"），custom_prompts覆盖特定视图
- **验证**：老年女性三视图测试通过，服装100%一致、人物特征还原、纯白背景
- **关键**：negative必须是ConditioningZeroOut(positive)，不能直接用positive当negative
- **用途**：角色设计参考图、游戏角色设定、虚拟人素材、电商模特多视角

### 6. 角色三视图 — ControlNet方案（备选）(generate_character_views)
- **方案**：PIL生成标准姿态骨架 + ControlNet openpose + 文生图 + ReActor人脸统一
- **视角**：front(正面)/side(侧面90度)/back(背面)
- **输出**：768×1024竖版全身
- **局限**：服装一致性不如Qwen方案，需要额外人脸统一步骤
- **用途**：当Qwen模型不可用时的备选方案

### 7. 极速文生图 — Z-Image-Turbo（默认生图方案）(txt2img_zimage)
- **方案**：阿里通义千问Z-Image模型 + Turbo加速，MMDiT架构
- **模型**：z_image_turbo_bf16（推荐，8秒/张）或 z-image-turbo-fp8-e4m3fn（显存小）
- **文本编码**：qwen_3_4b.safetensors (CLIPLoader type=lumina2)
- **VAE**：ae.safetensors（Z-Image专用）
- **采样**：res_multistep采样器，4步极速，cfg=1.0，ModelSamplingAuraFlow(shift=3)
- **空潜空间**：EmptySD3LatentImage（不是普通EmptyLatentImage）
- **negative**：空字符串 + ConditioningZeroOut
- **速度**：bf16 4步=8秒，8步=16秒（1024×1024，RTX 3080）
- **验证**：海边日落、猫咪等测试通过，画质高清细节丰富
- **用途**：默认文生图方案、素材生成、背景图、概念图、占位图
- **质量/速度平衡策略**：批量草图用低分辨率+少步数快速出图，需要高清时再用upscale_image超分，避免过度追求高清浪费算力
  - 极速草图：512×512 + 4步 + fp8 ≈ 3-5秒/张（批量素材、概念验证）
  - 标准质量：768×768 + 4步 + bf16 ≈ 5-8秒/张（日常素材、背景图）
  - 高质量：1024×1024 + 8步 + bf16 ≈ 16秒/张（最终成品、关键帧）
  - 超分放大：低分辨率出图后用upscale_image(4x)放大，比直接高分辨率生图更快

## 关键避坑记录

### 已验证死路（不要再尝试）
1. **IP-Adapter 在 ComfyUI v3.2 全黑**：ComfyUI_IPAdapter_plus（2025年4月版）与 ComfyUI v3.2内核（2026年8月）不兼容，标准模型和FaceID模型均输出全黑。已改用ReActor方案。
2. **insightface 全版本不兼容**：0.2.1不支持providers参数；2.0仍全黑；0.7.3编译失败（Python太新）。ReActor用insightface 2.0可正常工作。
3. **图生图人脸统一是折中方案**：denoise=0.5会改变服装和背景，不如ReActor精确。已弃用。
4. **v3.2 不能加载 v1.1 的 custom_nodes**：Python版本不兼容，触发datetime错误。

### 必须遵守的规则
1. **BiRefNet/RMBG节点必须传全部optional参数**：sensitivity, mask_blur, mask_offset, invert_output, refine_foreground, background, background_color，否则报KeyError。
2. **ComfyUI API模型路径用Windows反斜杠`\`**：正斜杠报"value not in list"。
3. **工作流JSON必须无BOM**：PowerShell WriteAllText默认带BOM，需用UTF8Encoding($false)。
4. **load_workflow_template对字符串值做json.dumps转义**。
5. **ReActor的install.py有bug**：`torch.torch_version.__version__`应为`torch.__version__`，torch 2.13+会触发崩溃。已修复。
6. **ReActor的requirements.txt不能固定旧版本**：insightface==0.7.3和numpy==1.26.4在新Python下编译失败。已改为>=版本。
7. **Z-Image必须用EmptySD3LatentImage**：普通EmptyLatentImage维度不匹配。
8. **Z-Image的CLIP type必须是lumina2**：用stable_diffusion会报维度错误(2560 vs 768)。
9. **Z-Image的negative必须ConditioningZeroOut**：直接用空字符串当negative可能生成噪点。

## 环境要求

- ComfyUI 运行中，API 端口 8188
- ComfyUI Python：`D:\Ai\ComfyUI-aki-v3.2\python\python.exe`（torch 2.13.0+cu130）
- GPU：NVIDIA（测试用 RTX 3080 12GB）
- 自定义节点：ComfyUI_IPAdapter_plus、comfyui-reactor-node
- 模型目录：`D:\Ai\ComfyUI-aki-v3.2\ComfyUI\models\`

## 快速使用

```python
from capabilities.cap_comfyui_runner import (
    check_comfyui_ready, upscale_image, matting_image, face_unify_image
)

# 检查状态
status = check_comfyui_ready()

# 超分
upscale_image("input.png", "output.png", model_name="RealESRGAN_x4plus.pth")

# 抠图
matting_image("input.png", "output.png", model_name="BiRefNet-general.pth")

# 人脸统一（ReActor最佳方案）
face_unify_image(
    source_image="reference_face.png",   # 源脸
    target_image="target.png",           # 目标图（保留服装/背景）
    output_path="result.png",
    face_restore_model="none",           # 可选GFPGANv1.4.pth/codeformer.pth
)

# ControlNet生成（用姿态骨架控制）
controlnet_generate(
    control_image="pose.png",
    positive_prompt="full body woman, standing, white background",
    output_path="output.png",
    controlnet_model="control_v11p_sd15_openpose.pth",
    strength=0.85,
)

# 极速文生图（Z-Image-Turbo默认方案，4步8秒出图）
txt2img_zimage(
    prompt="a beautiful sunset over the ocean, golden hour, photorealistic",
    output_path="output.png",
    width=1024, height=1024,
    steps=4, model="bf16",  # bf16推荐，fp8显存小
)
# 角色三视图（Qwen最佳方案，一键生成正面/侧面/背面+拼接图）
result = generate_character_views_qwen(
    input_image="人物照片.jpg",
    output_dir="character_views/",
    views=["front", "side", "back"],  # 可选"half"上半身
    longer_edge=2048,                  # 16GB显存以上用2048
    custom_prompt="黑色鞋子",          # 自定义补充提示词
    crop_top=100, crop_sides=50,       # 留白裁剪
)
# result = {"front": "...", "side": "...", "back": "...", "concat": "..."}

# 角色三视图（ControlNet备选方案）
generate_character_views(
    reference_image="reference.jpg",
    output_dir="character_views/",
    character_prompt="elderly woman, gray hair, blue floral shirt",
)
```

## 待扩展能力（模型已就绪）
- 图生视频：混元视频1.5 720P i2v
- 批量文生图
- ControlNet canny/depth/lineart 高级应用
