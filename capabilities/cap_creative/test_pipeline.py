import sys
sys.path.insert(0, '.')
from comfyui_image_pipeline import ComfyUIImagePipeline

pipeline = ComfyUIImagePipeline()
print(f'ComfyUI在线: {pipeline.is_online()}')

# 测试工作流构建
workflow = pipeline._build_workflow(
    prompt='test prompt',
    checkpoint='基础模型\\sd_xl_turbo_1.0_fp16.safetensors',
    width=512, height=512,
    steps=6, cfg=2.0,
    reference_images=[],
)
print(f'工作流节点数: {len(workflow)}')
node_types = [v["class_type"] for v in workflow.values()]
print(f'节点类型: {node_types}')

# 测试提交（不等待）
prompt_id = pipeline._queue_prompt(workflow)
print(f'提交成功: prompt_id={prompt_id}')
print('✅ 基础功能测试通过')
