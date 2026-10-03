"""
P25: 中央调度器（Central Orchestrator）
导演引擎的第三模块：按依赖关系执行指令序列，调度各工具协同工作

核心能力：
1. 任务依赖图（DAG）：先生成素材→再做动画→最后合成
2. 执行队列：并行/串行调度
3. 失败重试：工具失败自动降级或重试
4. 音画同步：对白对齐口型，音效对齐动作
5. 资源管理：显存清理、临时文件管理

输入：P24输出的指令序列JSON
输出：执行结果报告（成功/失败/耗时/产物路径）
"""

import json
import os
import time
import uuid
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskType(Enum):
    TTS = "tts"                    # 语音合成
    KEYFRAME = "keyframe"          # 剪映关键帧
    EFFECT = "effect"              # 特效/转场
    AUDIO = "audio"                # 音轨处理
    TEXT = "text"                  # 文字排版
    COMFYUI = "comfyui"            # ComfyUI视频生成
    BLENDER = "blender"            # Blender动画
    MEDIA = "media"                # 素材准备
    COMPOSE = "compose"            # 最终合成


@dataclass
class Task:
    """调度任务单元"""
    id: str
    type: TaskType
    name: str
    params: Dict = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str = ""
    start_time: float = 0
    end_time: float = 0
    retry_count: int = 0
    max_retries: int = 2


@dataclass
class ExecutionReport:
    """执行结果报告"""
    total_tasks: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    total_duration: float = 0
    tasks: List[Dict] = field(default_factory=list)
    output_path: str = ""


class CentralOrchestrator:
    """中央调度器"""

    def __init__(self, work_dir: str = None):
        self.work_dir = work_dir or os.path.join(
            os.path.expanduser("~"), "Videos", "剪映导出", "Doubao_Jianying-editor",
            "director_engine_output"
        )
        os.makedirs(self.work_dir, exist_ok=True)

        self.tasks: List[Task] = []
        self.task_map: Dict[str, Task] = {}
        self.report = ExecutionReport()

        # 工具执行器注册
        self.executors: Dict[TaskType, Callable] = {}
        self._register_default_executors()

    def _register_default_executors(self):
        """注册默认执行器（占位，实际执行由外部注入）"""
        self.executors[TaskType.TTS] = self._execute_tts
        self.executors[TaskType.KEYFRAME] = self._execute_keyframe
        self.executors[TaskType.EFFECT] = self._execute_effect
        self.executors[TaskType.AUDIO] = self._execute_audio
        self.executors[TaskType.TEXT] = self._execute_text
        self.executors[TaskType.COMFYUI] = self._execute_comfyui
        self.executors[TaskType.BLENDER] = self._execute_blender
        self.executors[TaskType.MEDIA] = self._execute_media
        self.executors[TaskType.COMPOSE] = self._execute_compose

    def build_tasks_from_instructions(self, instruction_sequence: Dict[str, Any]) -> List[Task]:
        """
        从P24指令序列构建任务DAG

        依赖关系：
        - MEDIA（素材准备）→ 所有其他任务
        - COMFYUI/BLENDER（素材生成）→ COMPOSE
        - TTS → COMPOSE
        - AUDIO → COMPOSE
        - KEYFRAME/EFFECT/TEXT → COMPOSE
        - COMPOSE 最后执行
        """
        self.tasks = []
        self.task_map = {}

        project = instruction_sequence.get("project", {})
        project_name = project.get("title", "未命名项目")

        # 1. 素材准备任务（最先执行）
        media_task = Task(
            id=f"media_{uuid.uuid4().hex[:8]}",
            type=TaskType.MEDIA,
            name=f"素材准备: {project_name}",
            params={"project": project},
        )
        self._add_task(media_task)

        # 2. TTS任务
        for i, tts in enumerate(instruction_sequence.get("tts_instructions", [])):
            task = Task(
                id=f"tts_{i:03d}",
                type=TaskType.TTS,
                name=f"TTS: {tts.get('character', '')} - {tts.get('text', '')[:20]}",
                params=tts,
                dependencies=[media_task.id],
            )
            self._add_task(task)

        # 3. 音轨任务
        for i, audio in enumerate(instruction_sequence.get("audio_instructions", [])):
            task = Task(
                id=f"audio_{i:03d}",
                type=TaskType.AUDIO,
                name=f"音轨: {audio.get('name', '')}",
                params=audio,
                dependencies=[media_task.id],
            )
            self._add_task(task)

        # 4. 剪映工程构建任务（合并关键帧+特效+文字）
        keyframes = instruction_sequence.get("keyframe_instructions", [])
        effects = instruction_sequence.get("effect_instructions", [])
        texts = instruction_sequence.get("text_instructions", [])

        if keyframes or effects or texts:
            # 把完整指令序列传给剪映执行器
            jianying_task = Task(
                id="jianying_build",
                type=TaskType.KEYFRAME,
                name=f"剪映工程: {len(keyframes)}关键帧+{len(effects)}特效+{len(texts)}文字",
                params={
                    "instruction_sequence": instruction_sequence,
                    "project": project,
                },
                dependencies=[media_task.id],
            )
            self._add_task(jianying_task)

        # 5. 最终合成任务（最后执行）
        compose_deps = [t.id for t in self.tasks if t.type != TaskType.COMPOSE]
        compose_task = Task(
            id=f"compose_{uuid.uuid4().hex[:8]}",
            type=TaskType.COMPOSE,
            name=f"最终合成: {project_name}",
            params={"project": project, "output_dir": self.work_dir},
            dependencies=compose_deps,
        )
        self._add_task(compose_task)

        return self.tasks

    def _add_task(self, task: Task):
        """添加任务到调度器"""
        self.tasks.append(task)
        self.task_map[task.id] = task

    def execute(self, dry_run: bool = False) -> ExecutionReport:
        """
        执行任务DAG

        Args:
            dry_run: 只打印执行计划，不实际执行

        Returns:
            ExecutionReport 执行报告
        """
        print(f"\n{'='*60}")
        print(f"中央调度器启动")
        print(f"{'='*60}")
        print(f"任务总数: {len(self.tasks)}")
        print(f"工作目录: {self.work_dir}")
        print(f"模式: {'模拟执行' if dry_run else '实际执行'}")

        start_time = time.time()
        self.report = ExecutionReport(total_tasks=len(self.tasks))

        # 拓扑排序执行
        executed = set()
        while len(executed) < len(self.tasks):
            # 找到所有依赖已满足的待执行任务
            ready = [
                t for t in self.tasks
                if t.status == TaskStatus.PENDING
                and all(d in executed for d in t.dependencies)
            ]

            if not ready:
                # 检查是否有死锁
                pending = [t for t in self.tasks if t.status == TaskStatus.PENDING]
                if pending:
                    print(f"⚠️ 检测到死锁，{len(pending)}个任务无法执行")
                    for t in pending:
                        t.status = TaskStatus.FAILED
                        t.error = "依赖死锁"
                        self.report.failed_count += 1
                        self.report.tasks.append(self._task_to_report(t))
                break

            # 执行就绪任务（可并行，这里串行执行）
            for task in ready:
                self._execute_task(task, dry_run)
                executed.add(task.id)

        self.report.total_duration = time.time() - start_time

        # 打印报告
        self._print_report()

        return self.report

    def _execute_task(self, task: Task, dry_run: bool = False):
        """执行单个任务"""
        task.status = TaskStatus.RUNNING
        task.start_time = time.time()

        print(f"\n▶ [{task.type.value}] {task.name}")
        if task.dependencies:
            print(f"  依赖: {len(task.dependencies)}个任务")

        if dry_run:
            # 模拟执行
            time.sleep(0.1)
            task.status = TaskStatus.SUCCESS
            task.result = {"dry_run": True, "output": f"模拟输出_{task.id}"}
            print(f"  ✅ 模拟完成")
        else:
            # 实际执行
            executor = self.executors.get(task.type)
            if executor:
                try:
                    result = executor(task)
                    task.status = TaskStatus.SUCCESS
                    task.result = result
                    print(f"  ✅ 完成")
                except Exception as e:
                    if task.retry_count < task.max_retries:
                        task.retry_count += 1
                        print(f"  ⚠️ 失败，重试 {task.retry_count}/{task.max_retries}: {e}")
                        task.status = TaskStatus.PENDING  # 重新排队
                        return
                    else:
                        task.status = TaskStatus.FAILED
                        task.error = str(e)
                        print(f"  ❌ 失败（已重试{task.max_retries}次）: {e}")
            else:
                task.status = TaskStatus.SKIPPED
                task.error = "无执行器"
                print(f"  ⏭️ 跳过（无执行器）")

        task.end_time = time.time()

        # 记录报告
        if task.status == TaskStatus.SUCCESS:
            self.report.success_count += 1
        elif task.status == TaskStatus.FAILED:
            self.report.failed_count += 1
        elif task.status == TaskStatus.SKIPPED:
            self.report.skipped_count += 1

        self.report.tasks.append(self._task_to_report(task))

    def _task_to_report(self, task: Task) -> Dict:
        """任务转报告格式"""
        return {
            "id": task.id,
            "type": task.type.value,
            "name": task.name,
            "status": task.status.value,
            "duration": round(task.end_time - task.start_time, 2) if task.end_time else 0,
            "error": task.error,
            "retry_count": task.retry_count,
        }

    def _print_report(self):
        """打印执行报告"""
        print(f"\n{'='*60}")
        print(f"执行报告")
        print(f"{'='*60}")
        print(f"总任务: {self.report.total_tasks}")
        print(f"✅ 成功: {self.report.success_count}")
        print(f"❌ 失败: {self.report.failed_count}")
        print(f"⏭️ 跳过: {self.report.skipped_count}")
        print(f"总耗时: {self.report.total_duration:.2f}秒")
        print(f"{'='*60}\n")

    def save_report(self, output_path: str = None):
        """保存执行报告"""
        if not output_path:
            output_path = os.path.join(self.work_dir, "execution_report.json")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(asdict(self.report), f, ensure_ascii=False, indent=2)
        print(f"✅ 执行报告已保存: {output_path}")
        return output_path

    # ============ 默认执行器（占位实现） ============

    def _execute_tts(self, task: Task) -> Dict:
        """TTS执行器（占位）"""
        # 实际实现：调用TTS API生成音频
        return {"output_path": f"{self.work_dir}/tts/{task.id}.wav"}

    def _execute_keyframe(self, task: Task) -> Dict:
        """剪映工程构建执行器（调用实际的jianying_executor）"""
        try:
            from jianying_executor import JianyingExecutor
        except ImportError:
            # 占位实现
            return {"draft_path": f"{self.work_dir}/drafts/{task.id}", "placeholder": True}

        instructions = task.params.get("instruction_sequence", {})
        project = task.params.get("project", {})
        project_name = project.get("title", task.id)
        duration = project.get("duration", 20)

        executor = JianyingExecutor(work_dir=self.work_dir)
        result = executor.execute(
            instructions,
            project_name=project_name,
            duration=duration,
        )
        return result

    def _execute_effect(self, task: Task) -> Dict:
        """特效执行器（占位）"""
        return {"applied": len(task.params.get("effects", []))}

    def _execute_audio(self, task: Task) -> Dict:
        """音轨执行器（占位）"""
        return {"audio_path": f"{self.work_dir}/audio/{task.id}.wav"}

    def _execute_text(self, task: Task) -> Dict:
        """文字排版执行器（占位）"""
        return {"text_count": len(task.params.get("texts", []))}

    def _execute_comfyui(self, task: Task) -> Dict:
        """ComfyUI执行器（占位）"""
        return {"video_path": f"{self.work_dir}/videos/{task.id}.mp4"}

    def _execute_blender(self, task: Task) -> Dict:
        """Blender执行器（占位）"""
        return {"animation_path": f"{self.work_dir}/animations/{task.id}.mp4"}

    def _execute_media(self, task: Task) -> Dict:
        """素材准备执行器（占位）"""
        return {"media_ready": True}

    def _execute_compose(self, task: Task) -> Dict:
        """最终合成执行器（占位）"""
        output = f"{self.work_dir}/output/{task.params.get('project', {}).get('title', 'output')}.mp4"
        return {"output_path": output}


if __name__ == "__main__":
    # 测试：用P24输出的指令序列做调度
    instr_path = r"C:\Users\Administrator\Videos\剪映导出\Doubao_Jianying-editor\director_engine_test\instruction_sequence.json"

    if os.path.exists(instr_path):
        with open(instr_path, "r", encoding="utf-8") as f:
            instructions = json.load(f)

        orchestrator = CentralOrchestrator()
        tasks = orchestrator.build_tasks_from_instructions(instructions)

        print(f"\n构建任务DAG: {len(tasks)}个任务")
        for t in tasks:
            deps = f" (依赖:{len(t.dependencies)})" if t.dependencies else ""
            print(f"  [{t.type.value}] {t.name}{deps}")

        # 模拟执行
        report = orchestrator.execute(dry_run=True)
        orchestrator.save_report()
    else:
        print(f"❌ 指令序列文件不存在: {instr_path}")
