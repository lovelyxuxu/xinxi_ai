"""
心犀AI - 主入口
================
这是整个项目的启动入口，负责：
1. 初始化所有组件（Embedding、Chroma、检索器）
2. 加载模拟数据到向量数据库
3. 构建 LangGraph 工作流
4. 以指定用户身份触发一次完整的匹配流程
5. 展示匹配结果

使用方式：
    python main.py                    # 默认以 F001（小晴）的身份运行
    python main.py --user M001        # 指定用户ID
    python main.py --init-only        # 仅初始化数据，不执行匹配
"""

import sys
import os
import io

# ============================================================
# Windows 终端编码修复
# ============================================================
# Windows CMD/PowerShell 默认使用 GBK 编码，无法显示 emoji。
# 这里强制将 stdout/stderr 切换为 UTF-8，让 Rich 正常渲染。
if sys.platform == "win32":
    # 尝试使用 Windows 的 UTF-8 控制台模式
    try:
        os.system("chcp 65001 >nul 2>&1")
    except Exception:
        pass
    # 将 stdout 包装为 UTF-8 输出
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 确保项目根目录在 Python 路径中（这样 import core.xxx 才能正常工作）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

from core.embedding.embedding_service import EmbeddingService
from core.database.chroma_store import ChromaStore
from core.retrieval.hybrid_retriever import HybridRetriever
from core.agent.graph import build_matching_graph
from core.agent.state import AgentState
from core.models.user_profile import UserProfile
from data.mock_data import get_mock_users, get_mock_user_by_id


console = Console(force_terminal=True)


def init_database(force_reload: bool = False) -> tuple[EmbeddingService, ChromaStore]:
    """
    初始化 Embedding 服务和 Chroma 数据库。
    如果数据库中已有数据，默认跳过导入（使用 force_reload=True 强制重载）。
    """
    console.print(Panel("⚙️  正在初始化组件...", style="blue"))

    # 1. 创建 Embedding 服务
    embedding_service = EmbeddingService()
    console.print("  ✅ Embedding 服务就绪")

    # 2. 创建 Chroma 存储
    chroma_store = ChromaStore(embedding_service)
    user_count = chroma_store.get_user_count()
    console.print(f"  ✅ Chroma 数据库就绪（当前 {user_count} 条记录）")

    # 3. 导入模拟数据
    if user_count == 0 or force_reload:
        console.print("  📦 正在导入模拟用户数据...")
        mock_users = get_mock_users()
        chroma_store.upsert_users(mock_users)
        console.print(f"  ✅ 已导入 {len(mock_users)} 位用户")
    else:
        console.print("  ⏭️  数据库已有数据，跳过导入（使用 --reload 强制重载）")

    return embedding_service, chroma_store


def run_matching(user_id: str, chroma_store: ChromaStore):
    """
    以指定用户身份执行一次完整的婚恋匹配流程。
    """
    # 1. 获取用户资料
    user = get_mock_user_by_id(user_id)
    if not user:
        console.print(f"[red]❌ 未找到用户: {user_id}[/red]")
        console.print("可用用户ID: F001~F006 (女), M001~M006 (男)")
        return

    # 2. 展示当前用户信息
    user_panel = f"""**{user.nickname}** ({user.user_id})
{user.gender} · {user.age}岁 · {user.city} · {user.education}
MBTI: {user.mbti}

**关于我**: {user.about_me}

**理想的Ta**: {user.ideal_partner}

**兴趣爱好**: {user.hobbies}"""
    console.print(Panel(Markdown(user_panel), title="👤 当前用户", border_style="cyan"))

    # 3. 构建检索器和工作流
    retriever = HybridRetriever(chroma_store)
    app = build_matching_graph(retriever)

    # 4. 初始化 Agent 状态
    initial_state: AgentState = {
        "user_profile": user,
        "loop_count": 0,
        "messages": [f"🚀 开始为 {user.nickname} 寻找缘分..."],
    }

    # 5. 执行工作流
    console.print(Panel("🤖 Agent 工作流启动", style="green"))

    # LangGraph 的 invoke 方法会按照图的拓扑结构自动执行各节点
    # 条件边会决定走哪条路径
    final_state = app.invoke(initial_state)

    # 6. 展示执行日志
    console.print("\n")
    console.print(Panel("📜 Agent 执行日志", style="yellow"))
    for msg in final_state.get("messages", []):
        console.print(f"  {msg}")

    # 7. 展示匹配结果
    top_matches = final_state.get("top_matches", [])
    match_letters = final_state.get("match_letters", [])

    if not top_matches:
        console.print("\n[red]😔 未找到匹配的候选人[/red]")
        return

    console.print("\n")
    console.print(Panel("💕 匹配结果", style="magenta"))

    for i, (match, letter) in enumerate(zip(top_matches, match_letters), 1):
        # 匹配评分卡
        score = match.get("score", 0)
        score_color = "green" if score >= 80 else "yellow" if score >= 60 else "red"

        result_table = Table(show_header=False, box=None)
        result_table.add_column("字段", style="dim")
        result_table.add_column("值")
        result_table.add_row("昵称", match.get("nickname", "未知"))
        result_table.add_row("契合指数", f"[{score_color}]{score}分[/{score_color}]")
        result_table.add_row("匹配理由", match.get("reason", ""))

        console.print(Panel(result_table, title=f"💘 推荐 #{i}", border_style="magenta"))

        # 推荐信
        console.print(Panel(letter, title=f"✉️ 缘分推荐信 - {match.get('nickname', '')}", border_style="bright_magenta"))

    console.print("\n[dim]匹配流程完成！可更换用户ID再次尝试。[/dim]")


def main():
    """主函数：解析命令行参数并执行"""
    import argparse

    parser = argparse.ArgumentParser(description="心犀AI - 智能婚恋匹配系统")
    parser.add_argument("--user", type=str, default="F001",
                        help="用户ID，默认 F001（小晴）")
    parser.add_argument("--reload", action="store_true",
                        help="强制重载模拟数据")
    parser.add_argument("--init-only", action="store_true",
                        help="仅初始化数据库，不执行匹配")
    args = parser.parse_args()

    # 打印欢迎信息
    welcome = """
    ╔══════════════════════════════════════════╗
    ║         心犀AI · 智能婚恋匹配            ║
    ║   Agent + Hybrid RAG · LangGraph 驱动    ║
    ╚══════════════════════════════════════════╝
    """
    console.print(welcome, style="bold cyan")

    # 初始化
    _, chroma_store = init_database(force_reload=args.reload)

    if args.init_only:
        console.print("[green]✅ 数据库初始化完成！[/green]")
        return

    # 执行匹配
    run_matching(args.user, chroma_store)


if __name__ == "__main__":
    main()
