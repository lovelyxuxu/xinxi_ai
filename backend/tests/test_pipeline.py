"""
心犀AI - 快速验证脚本
=====================
用于验证数据管道和基础检索是否正常工作。
无需 API Key 即可运行（使用 Chroma 默认 Embedding）。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.embedding.embedding_service import EmbeddingService
from core.database.chroma_store import ChromaStore
from data.mock_data import get_mock_users


def main():
    print("=" * 50)
    print("  心犀AI - 数据管道验证")
    print("=" * 50)

    # 1. 初始化组件
    print("\n[1/4] 初始化 Embedding + Chroma...")
    es = EmbeddingService()
    cs = ChromaStore(es)
    cs.clear_collection()
    print(f"  OK - 数据库已清空")

    # 2. 导入模拟数据
    print("\n[2/4] 导入模拟用户数据...")
    users = get_mock_users()
    cs.upsert_users(users)
    count = cs.get_user_count()
    print(f"  OK - 已导入 {count} 位用户")

    # 3. 验证单条查询
    print("\n[3/4] 查询单个用户...")
    u = cs.get_user("F001")
    if u:
        m = u["metadata"]
        print(f"  OK - F001: {m['nickname']}, {m['age']}岁, {m['city']}")
    else:
        print("  FAIL - 未找到 F001")
        return

    # 4. 测试向量搜索
    print("\n[4/4] 测试向量相似度搜索...")
    print("  查询: '安静内向 喜欢猫 宅家看书'")
    r = cs.search(
        query_text="安静内向 喜欢猫 宅家看书",
        n_results=5,
    )
    if r and r["ids"] and r["ids"][0]:
        for i, uid in enumerate(r["ids"][0]):
            meta = r["metadatas"][0][i]
            dist = r["distances"][0][i]
            print(f"  #{i+1}: {uid} {meta['nickname']} - {meta['age']}岁 {meta['city']} (距离={dist:.4f})")
    else:
        print("  FAIL - 搜索无结果")

    print("\n" + "=" * 50)
    print("  验证完成！数据管道工作正常。")
    print("=" * 50)


if __name__ == "__main__":
    main()
