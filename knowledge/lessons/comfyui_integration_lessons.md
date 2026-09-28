# ComfyUI 集成经验沉淀

## 已验证能力（最佳方案）
- ✅ 图片超分：9种ESRGAN模型，256→1024
- ✅ 批量抠图：BiRefNet(12种)+RMBG(4种)，RGBA透明
- ✅ 人脸统一：ReActor人脸交换（inswapper_128.onnx），单张+批量，保留目标图服装/背景/构图

## 关键避坑

### 死路（不要再尝试）
1. **IP-Adapter 在 ComfyUI v3.2 全黑**：ComfyUI_IPAdapter_plus（2025-04版）与ComfyUI v3.2内核（2026-08）不兼容，标准模型和FaceID模型均全黑。改用ReActor。
2. **insightface 全版本不兼容IP-Adapter**：0.2.1缺providers参数；2.0仍全黑；0.7.3编译失败。但ReActor用insightface 2.0可正常工作。
3. **图生图人脸统一是折中方案**：denoise=0.5会改变服装和背景，不如ReActor精确。已弃用。
4. **v3.2 加载 v1.1 custom_nodes**：Python版本不兼容，datetime错误。

### 必须遵守
1. BiRefNet/RMBG节点必须传全部optional参数
2. ComfyUI API模型路径用Windows反斜杠`\`
3. 工作流JSON必须无BOM（用UTF8Encoding($false)）
4. load_workflow_template对字符串值做json.dumps转义
5. ReActor install.py bug：`torch.torch_version.__version__`→`torch.__version__`（torch 2.13+会崩溃）
6. ReActor requirements.txt不能固定旧版本（insightface==0.7.3, numpy==1.26.4编译失败），改为>=

### ReActor安装要点
- 节点源码：hf-mirror.com/woods55/comfyui-ReActor（GitHub不通时用此镜像）
- 模型：inswapper_128.onnx（528.6MB），放models/insightface/
- 依赖：insightface 2.0, onnxruntime-gpu, opencv-contrib-python-headless, numpy 2.3.5
- 节点名：ReActorFaceSwap（API中），类名reactor（代码中）
- 输入：input_image(目标图, required), source_image(源脸, optional)
- 输出：SWAPPED_IMAGE, FACE_MODEL, ORIGINAL_IMAGE

## 环境信息
- ComfyUI v3.2根目录：D:\Ai\ComfyUI-aki-v3.2\ComfyUI
- API：http://127.0.0.1:8188
- Python：D:\Ai\ComfyUI-aki-v3.2\python\python.exe（torch 2.13.0+cu130）
- GPU：RTX 3080 12GB
- v1.1目录：D:\StableDiffusion\ComfyUI\ComfyUI-aki-v1.1（用户计划删除）

## 待扩展
- 图生视频：混元视频1.5 720P i2v（模型已就绪）
- 风格迁移：ControlNet canny/depth/openpose（模型已就绪）
- 批量文生图
## ControlNet 三视图生成经验

### 技术路线
1. PIL绘制标准OpenPose骨架图（正面/侧面/背面站立）
2. ControlNet openpose模型控制姿态（strength=0.85）
3. 文生图生成（768×1024竖版全身）
4. ReActor统一人脸

### 关键发现
- 纯文生图无法保证标准姿态（经常生成弯腰/扶物/回头），必须用ControlNet
- "character reference sheet"提示词会导致生成多人物排列，需移除并加"single person, solo"
- 图生图（img2img）受原图构图限制，无法从半身照生成全身照
- 侧面姿态骨架：左右关键点x坐标接近（重叠），面部关键点部分不可见（设为None）
- 背面姿态骨架：面部关键点不可见（None），保留耳朵关键点
- ControlNet strength=0.85效果最佳（0.7以下姿态控制弱，0.9以上过于僵硬）

### 避坑
- ReActor face_restore_model=GFPGAN/codeformer 会触发下载retinaface检测模型，网络不通时失败，用none
- BiRefNet模型名不带.pth后缀（"BiRefNet-general"而非"BiRefNet-general.pth"）
- 姿态骨架图必须是黑色背景+彩色线条，与OpenPose输出格式一致
## Qwen 图像编辑三视图经验（最佳方案）

### 技术路线
- 模型：千问Qwen-Image-Edit 2511 (fp8) + Lightning 4steps LoRA + qwen_image_vae + qwen_2.5_vl_7b_fp8
- 采样：euler_ancestral, 5步, cfg=1.0, scheduler=simple
- 输入：ResizeImagesByLongerEdge(2048) → VAEEncode
- 文本编码：TextEncodeQwenImageEditPlus（prompt + clip + vae + image1）
- 关键：negative = ConditioningZeroOut(positive)，不能直接用positive当negative

### 提示词模板
- 正面："获取人物全景像白底图，人物站立，双臂自然下垂，不需要摆出姿势，看向前方"
- 侧面："获取人物左侧面白底图，人物全身站立，双臂自然下垂，面朝左方，纯白背景"
- 背面："获取人物背面白底图，人物全身站立，双臂自然下垂，纯白背景"
- 上半身："获取人物上半身白底图，面向观众，身体正直"

### 关键避坑
1. **negative必须是ConditioningZeroOut(positive)**：直接用positive当negative会生成噪点/故障图
2. **TextEncodeQwenImageEditPlus参数名是prompt不是text**，图片输入是image1不是image
3. **蓝图节点不能直接API调用**：class_type是UUID会报missing_node_type，必须展开为普通节点
4. **Qwen模型cfg=1.0**：不是常规的7.5，Lightning LoRA专用低cfg
5. **侧面提示词必须强调"白底"和"全身站立"**：否则可能生成半身+公园背景

### 与ControlNet方案对比
| 维度 | Qwen方案 | ControlNet方案 |
|------|----------|----------------|
| 服装一致性 | ✅ 100%一致 | ⚠️ 有差异 |
| 人脸统一 | ✅ 天然一致 | ❌ 需ReActor额外步骤 |
| 背景 | ✅ 纯白 | ⚠️ 浅灰渐变 |
| 生成速度 | ✅ 5步/张 | ❌ 35步/张+人脸统一 |
| 分辨率 | ✅ 2048 | ❌ 768×1024 |
| 模型依赖 | ❌ 需Qwen全套模型 | ✅ SD1.5通用 |

### v1.1 custom_nodes 复制例外
- ComfyUI_LayerStyle 从v1.1复制到v3.2可正常工作（目录名带-main后缀）
- 并非所有v1.1插件都不兼容，纯Python节点通常可以，涉及C扩展或旧API的可能失败
- 复制后需重启ComfyUI，观察控制台是否有导入错误