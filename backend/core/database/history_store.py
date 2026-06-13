"""
心犀AI - 匹配历史持久化存储
============================
使用 SQLite 持久化匹配历史记录，解决服务重启后历史丢失的问题。

学习要点：
---------
- 之前 match_history 是内存 dict，服务一重启就清空了
- 这里用独立的 SQLite 文件（history.db）持久化，和 checkpoint.db 分开
- 使用同步 sqlite3（非 aiosqlite），因为匹配历史的读写都很轻量
- JSON 序列化：candidates 和 match_letters 等复杂字段存为 JSON 文本

设计思路：
  每条匹配记录存为一行，user_id 建索引方便按用户查询。
  加载时按 created_at 倒序，最新的在前面。
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional


class HistoryStore:
    """
    匹配历史的 SQLite 持久化存储。

    职责：
    - save: 保存一次匹配结果
    - get_by_user: 获取某用户的所有历史（按时间倒序）
    - get_by_match_id: 根据 match_id 查找单条记录
    - get_all_index: 获取全量索引（用于 get_match_result 遍历）
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """
        获取数据库连接（延迟创建）。

        学习要点：
        - check_same_thread=False: 允许跨线程使用连接
        - FastAPI 的 sync 端点会在 anyio 线程池中运行，
          如果连接在主线程创建、在工作线程使用，会报 ProgrammingError
        - 对于读多写少的场景，这是安全的（SQLite 本身有内部锁）
        """
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self):
        """初始化表结构"""
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS match_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                candidates TEXT DEFAULT '[]',
                match_letters TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                agent_log TEXT DEFAULT '[]'
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_match_history_user_id
            ON match_history(user_id)
        """)
        conn.commit()

    def save(self, record: dict):
        """
        保存一条匹配记录。

        参数 record 的格式与 _build_final_result() 返回值一致：
        {
            "match_id": "M...",
            "user_id": "F002",
            "candidates": [...],
            "match_letters": [...],
            "created_at": "2026-06-13T10:52:00",
            "agent_log": [...]  # 可能是 str 列表或 LangChain Message 对象
        }
        """
        conn = self._get_conn()

        # 安全序列化 agent_log（可能是 Message 对象，需要转成字符串）
        raw_log = record.get("agent_log", [])
        safe_log = []
        for item in raw_log:
            if isinstance(item, str):
                safe_log.append(item)
            elif hasattr(item, "content"):
                # LangChain Message 对象 → 取 content 字段
                safe_log.append(str(item.content))
            else:
                safe_log.append(str(item))

        try:
            conn.execute(
                """INSERT OR REPLACE INTO match_history
                   (match_id, user_id, candidates, match_letters, created_at, agent_log)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    record["match_id"],
                    record["user_id"],
                    json.dumps(record.get("candidates", []), ensure_ascii=False),
                    json.dumps(record.get("match_letters", []), ensure_ascii=False),
                    record["created_at"],
                    json.dumps(safe_log, ensure_ascii=False),
                ),
            )
            conn.commit()
        except Exception as e:
            print(f"  [HistoryStore] 保存失败: {e}")

    def get_by_user(self, user_id: str) -> list[dict]:
        """
        获取某用户的所有匹配历史，按时间倒序。
        """
        conn = self._get_conn()
        cursor = conn.execute(
            """SELECT match_id, user_id, candidates, match_letters, created_at, agent_log
               FROM match_history
               WHERE user_id = ?
               ORDER BY created_at DESC""",
            (user_id,),
        )
        return [self._row_to_dict(row) for row in cursor.fetchall()]

    def get_by_match_id(self, match_id: str) -> Optional[dict]:
        """根据 match_id 查找单条记录"""
        conn = self._get_conn()
        cursor = conn.execute(
            """SELECT match_id, user_id, candidates, match_letters, created_at, agent_log
               FROM match_history
               WHERE match_id = ?""",
            (match_id,),
        )
        row = cursor.fetchone()
        return self._row_to_dict(row) if row else None

    def get_all_index(self) -> dict[str, list[dict]]:
        """
        加载全量数据，按 user_id 分组。
        用于服务启动时恢复到内存，以及 get_match_result 遍历查找。
        """
        conn = self._get_conn()
        cursor = conn.execute(
            """SELECT match_id, user_id, candidates, match_letters, created_at, agent_log
               FROM match_history
               ORDER BY created_at DESC"""
        )
        result: dict[str, list[dict]] = {}
        for row in cursor.fetchall():
            record = self._row_to_dict(row)
            uid = record["user_id"]
            if uid not in result:
                result[uid] = []
            result[uid].append(record)
        return result

    def get_user_ids_with_recent_match(self, hours: int = 24) -> list[dict]:
        """
        查询近期有过匹配记录的用户（用于提示功能）。
        返回 [{user_id, match_id, created_at}, ...]
        """
        conn = self._get_conn()
        cursor = conn.execute(
            """SELECT user_id, match_id, created_at
               FROM match_history
               WHERE created_at >= datetime('now', ?)
               ORDER BY created_at DESC""",
            (f"-{hours} hours",),
        )
        return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def _row_to_dict(row) -> dict:
        """将 sqlite3.Row 转换为前端兼容的 dict"""
        if row is None:
            return {}
        return {
            "match_id": row["match_id"],
            "user_id": row["user_id"],
            "candidates": json.loads(row["candidates"]),
            "match_letters": json.loads(row["match_letters"]),
            "created_at": row["created_at"],
            "agent_log": json.loads(row["agent_log"]),
        }
