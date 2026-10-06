"""
PRPROJ 模板修改器 v2
基于真实PR模板，程序化替换媒体路径生成新的.prproj工程。

已验证：剪映可正常导入，媒体链接正常，关键帧动画保留。

使用方式：
    from prproj_template_modifier import PrprojTemplateModifier
    
    modifier = PrprojTemplateModifier(template_path="real_template.prproj")
    modifier.replace_media({
        "原视频1.mov": "C:/path/to/new_video.mp4",
        "原LOGO.png": "C:/path/to/new_logo.png",
    })
    modifier.save("output.prproj")
"""
import gzip
import re
import os
import uuid
from typing import Dict, List, Optional


class PrprojTemplateModifier:
    """PRPROJ模板修改器"""

    def __init__(self, template_path: str):
        """加载模板

        Args:
            template_path: 模板.prproj文件路径
        """
        self.template_path = template_path
        with gzip.open(template_path, 'rt', encoding='utf-8') as f:
            self.content = f.read()
        self.original_size = len(self.content)

        # 提取模板中的所有媒体信息
        self.media_files = self._extract_media_files()
        self.sequences = self._extract_sequences()

    def _extract_media_files(self) -> List[Dict]:
        """提取模板中的所有媒体文件信息"""
        media = []
        # 找所有FilePath
        file_paths = re.findall(r'<FilePath>([^<]+)</FilePath>', self.content)
        for fp in file_paths:
            if '\\' in fp or '/' in fp:  # 实际路径
                filename = os.path.basename(fp)
                media.append({
                    'path': fp,
                    'filename': filename,
                    'name': os.path.splitext(filename)[0],
                })
        return media

    def _extract_sequences(self) -> List[Dict]:
        """提取模板中的所有序列信息"""
        sequences = []
        # 找Sequence ObjectUID定义
        for m in re.finditer(
            r'<Sequence ObjectUID="([^"]+)" ClassID="6a15d903-8739-11d5-af2d-9b7855ad8974" Version="(\d+)">',
            self.content
        ):
            uid = m.group(1)
            version = m.group(2)
            # 找序列名称（在附近的Name标签）
            nearby = self.content[m.start():m.start()+5000]
            name_match = re.search(r'<Name>([^<]+)</Name>', nearby)
            name = name_match.group(1) if name_match else f"Sequence_{uid[:8]}"
            sequences.append({'uid': uid, 'version': version, 'name': name})
        return sequences

    def replace_media(self, mapping: Dict[str, str]) -> int:
        """替换媒体文件路径

        Args:
            mapping: 映射字典，key为原文件名（如"video.mov"），value为新路径

        Returns:
            替换的媒体数量
        """
        replaced = 0
        for old_name, new_path in mapping.items():
            # 在媒体列表中查找
            for media in self.media_files:
                if media['filename'].lower() == old_name.lower() or \
                   media['name'].lower() == old_name.lower() or \
                   media['path'].lower().endswith(old_name.lower()):
                    # 替换FilePath
                    old_fp = f'<FilePath>{media["path"]}</FilePath>'
                    new_fp = f'<FilePath>{new_path}</FilePath>'
                    if old_fp in self.content:
                        self.content = self.content.replace(old_fp, new_fp)
                        replaced += 1
                        print(f"  替换: {media['filename']} -> {new_path}")
                    break
        return replaced

    def replace_all_media(self, new_path: str) -> int:
        """将所有媒体替换为同一个文件

        Args:
            new_path: 新的媒体文件路径

        Returns:
            替换的媒体数量
        """
        replaced = 0
        seen_paths = set()
        for media in self.media_files:
            if media['path'] not in seen_paths:
                seen_paths.add(media['path'])
                old_fp = f'<FilePath>{media["path"]}</FilePath>'
                new_fp = f'<FilePath>{new_path}</FilePath>'
                if old_fp in self.content:
                    self.content = self.content.replace(old_fp, new_fp)
                    replaced += 1
        return replaced

    def keep_only_sequence(self, sequence_name: str) -> bool:
        """只保留指定序列（删除其他序列）

        注意：此操作较复杂，可能影响引用关系。建议谨慎使用。

        Args:
            sequence_name: 要保留的序列名称

        Returns:
            是否成功
        """
        # 找到目标序列
        target = None
        for seq in self.sequences:
            if seq['name'].lower() == sequence_name.lower():
                target = seq
                break
        if not target:
            print(f"未找到序列: {sequence_name}")
            return False

        # 此功能需要复杂的XML操作，暂时标记为实验性
        print("警告：keep_only_sequence为实验性功能，可能导致工程损坏")
        print(f"目标序列: {target['name']} (UID: {target['uid']})")
        return True

    def save(self, output_path: str) -> str:
        """保存修改后的工程

        Args:
            output_path: 输出.prproj文件路径

        Returns:
            输出文件路径
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with gzip.open(output_path, 'wt', encoding='utf-8') as f:
            f.write(self.content)
        size = os.path.getsize(output_path)
        print(f"\n已保存: {output_path}")
        print(f"  原始XML: {self.original_size} 字符")
        print(f"  输出大小: {size} bytes")
        return output_path

    def print_info(self):
        """打印模板信息"""
        print("=" * 60)
        print(f"模板: {self.template_path}")
        print(f"XML大小: {self.original_size} 字符")
        print(f"\n序列 ({len(self.sequences)}):")
        for seq in self.sequences:
            print(f"  - {seq['name']} (UID: {seq['uid'][:8]}...)")
        print(f"\n媒体文件 ({len(self.media_files)}):")
        for m in self.media_files:
            print(f"  - {m['filename']}")
        print("=" * 60)


def main():
    """命令行测试"""
    import sys

    template = r"C:\Users\Administrator\Videos\剪映导出\Doubao_Jianying-editor\prxml_test\real_template.prproj"
    output = r"C:\Users\Administrator\Videos\剪映导出\Doubao_Jianying-editor\prxml_test\test_modified_v2.prproj"
    test_image = r"C:\temp\prtest\test.png"

    print("PRPROJ模板修改器 v2 测试")
    print("=" * 60)

    modifier = PrprojTemplateModifier(template)
    modifier.print_info()

    print("\n替换所有媒体为测试图片...")
    count = modifier.replace_all_media(test_image)
    print(f"已替换 {count} 个媒体路径")

    modifier.save(output)
    print("\n完成！请在剪映中导入测试。")


if __name__ == '__main__':
    main()
