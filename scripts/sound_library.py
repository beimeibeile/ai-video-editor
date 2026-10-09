"""
音效库管理模块
SQLite存储音效元数据，支持标签检索、评级管理、复用缓存

评级体系：
- A级：AI生成（AudioLDM2）或人工精选，质量高，优先使用
- B级：TTS拟声词，快速可用，质量中等
- C级：ffmpeg合成，简单音效，质量一般
- 调用时按评级降序返回，同级按使用次数降序
"""

import logging
logger = logging.getLogger(__name__)


import os
import sqlite3
import json
from typing import List, Dict, Optional
from datetime import datetime


class SoundLibrary:
    """音效库管理器"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                r"D:\DobaoWork_Project\Ai_Video_Editor", "ai-video-editor-runtime", "data", "sound_library.db"
            )
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS sounds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                tags TEXT,
                duration REAL,
                path TEXT NOT NULL UNIQUE,
                source TEXT DEFAULT 'synth',  -- tts/synth/ai/manual
                rating TEXT DEFAULT 'C',       -- A/B/C
                quality_score REAL DEFAULT 0.5,
                usage_count INTEGER DEFAULT 0,
                created_at TEXT,
                last_used TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS sound_tags (
                sound_id INTEGER,
                tag_id INTEGER,
                FOREIGN KEY (sound_id) REFERENCES sounds(id),
                FOREIGN KEY (tag_id) REFERENCES tags(id),
                PRIMARY KEY (sound_id, tag_id)
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_sounds_rating ON sounds(rating)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sounds_source ON sounds(source)")
        conn.commit()
        conn.close()

    def add_sound(self, name: str, path: str, tags: List[str] = None,
                  source: str = "synth", rating: str = "C",
                  duration: float = 0, description: str = "",
                  quality_score: float = 0.5) -> int:
        """
        添加音效到库

        Args:
            name: 音效名称
            path: 音频文件路径
            tags: 标签列表
            source: 来源（tts/synth/ai/manual）
            rating: 评级（A/B/C）
            duration: 时长（秒）
            description: 描述
            quality_score: 质量分（0-1）

        Returns:
            音效ID
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # 检查是否已存在
        c.execute("SELECT id FROM sounds WHERE path = ?", (path,))
        existing = c.fetchone()
        if existing:
            sound_id = existing[0]
            # 更新使用次数
            c.execute("UPDATE sounds SET usage_count = usage_count + 1, last_used = ? WHERE id = ?",
                      (datetime.now().isoformat(), sound_id))
            conn.commit()
            conn.close()
            return sound_id

        now = datetime.now().isoformat()
        tags_str = ",".join(tags) if tags else ""
        c.execute("""
            INSERT INTO sounds (name, description, tags, duration, path, source, rating,
                                quality_score, usage_count, created_at, last_used)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
        """, (name, description, tags_str, duration, path, source, rating,
              quality_score, now, now))
        sound_id = c.lastrowid

        # 添加标签
        if tags:
            for tag in tags:
                c.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
                c.execute("SELECT id FROM tags WHERE name = ?", (tag,))
                tag_id = c.fetchone()[0]
                c.execute("INSERT OR IGNORE INTO sound_tags (sound_id, tag_id) VALUES (?, ?)",
                          (sound_id, tag_id))

        conn.commit()
        conn.close()
        return sound_id

    def search(self, query: str = None, tags: List[str] = None,
               source: str = None, min_rating: str = None,
               limit: int = 10) -> List[Dict]:
        """
        搜索音效

        Args:
            query: 关键词搜索（名称/描述）
            tags: 标签过滤
            source: 来源过滤
            min_rating: 最低评级（A/B/C，返回该级别及更高级别）
            limit: 返回数量

        Returns:
            音效列表，按评级降序、使用次数降序排列
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        sql = "SELECT * FROM sounds WHERE 1=1"
        params = []

        if query:
            sql += " AND (name LIKE ? OR description LIKE ? OR tags LIKE ?)"
            like = f"%{query}%"
            params.extend([like, like, like])

        if source:
            sql += " AND source = ?"
            params.append(source)

        if min_rating:
            # 评级排序：A=3, B=2, C=1
            rating_order = {"A": 3, "B": 2, "C": 1}
            min_val = rating_order.get(min_rating, 1)
            sql += f" AND CASE rating WHEN 'A' THEN 3 WHEN 'B' THEN 2 WHEN 'C' THEN 1 ELSE 0 END >= {min_val}"

        # 按评级降序、使用次数降序
        sql += " ORDER BY CASE rating WHEN 'A' THEN 3 WHEN 'B' THEN 2 WHEN 'C' THEN 1 ELSE 0 END DESC, usage_count DESC"
        sql += f" LIMIT {limit}"

        c.execute(sql, params)
        rows = c.fetchall()
        results = [dict(row) for row in rows]

        # 更新使用次数
        for r in results:
            c.execute("UPDATE sounds SET usage_count = usage_count + 1, last_used = ? WHERE id = ?",
                      (datetime.now().isoformat(), r["id"]))
        conn.commit()
        conn.close()

        return results

    def get_best(self, query: str, tags: List[str] = None) -> Optional[Dict]:
        """获取最佳匹配音效（评级最高+使用次数最多）"""
        results = self.search(query=query, tags=tags, limit=1)
        return results[0] if results else None

    def update_rating(self, sound_id: int, rating: str):
        """更新音效评级"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE sounds SET rating = ? WHERE id = ?", (rating, sound_id))
        conn.commit()
        conn.close()

    def get_stats(self) -> Dict:
        """获取库统计信息"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM sounds")
        total = c.fetchone()[0]
        c.execute("SELECT source, COUNT(*) FROM sounds GROUP BY source")
        by_source = dict(c.fetchall())
        c.execute("SELECT rating, COUNT(*) FROM sounds GROUP BY rating")
        by_rating = dict(c.fetchall())
        conn.close()
        return {
            "total": total,
            "by_source": by_source,
            "by_rating": by_rating,
        }

    def list_all(self, limit: int = 50) -> List[Dict]:
        """列出所有音效"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM sounds ORDER BY rating DESC, usage_count DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]


if __name__ == "__main__":
    lib = SoundLibrary()
    logger.info("音效库统计:", json.dumps(lib.get_stats(), ensure_ascii=False, indent=2))
    logger.info("\n所有音效:")
    for s in lib.list_all():
        logger.info(f"  [{s['rating']}] {s['name']} ({s['source']}) - {s['duration']:.1f}s - 使用{s['usage_count']}次")
