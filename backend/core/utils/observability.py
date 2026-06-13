"""
心犀AI - LangFuse 可观测性集成
=================================

【学习要点】
可观测性（Observability）是 LLM 应用从"Demo"走向"生产"的关键一步。

为什么需要可观测性？
-------------------
LLM 应用有几个传统应用不存在的挑战：
1. **不确定性**：同样的输入，LLM 可能给出不同的输出
2. **黑箱问题**：LLM 为什么给出这个结果？中间推理过程是什么？
3. **成本监控**：每次 LLM 调用花了多少钱？用了多少 token？
4. **延迟分析**：哪个 Agent 最慢？哪个 Prompt 导致了超时？
5. **质量追踪**：匹配质量是在提升还是下降？

没有可观测性，这些问题只能靠"猜"和"手动查日志"。
有了可观测性，所有答案都在 Dashboard 上一目了然。

LangFuse 是什么？
-----------------
LangFuse 是一个开源的 LLM 可观测性平台（可以理解为"LLM 版的 DataDog"）。
核心概念：

  Trace（追踪）
    一次完整的用户请求链路。比如"为用户 Alice 做一次匹配"就是一个 Trace。
    一个 Trace 包含多个 Observation。

  Observation（观测点）
    Trace 中的每个步骤。分为三种：
    - Span：一个普通操作（如 Agent 执行、数据库查询）
    - Generation：一次 LLM 调用（自动记录 prompt、completion、token 数）
    - Event：一个离散事件（如"评估完成"）

  Score（评分）
    给 Trace 打分数。我们用 Judge Agent 的评估结果作为 Score。
    这样就能在 Dashboard 上看到"匹配质量的趋势图"。

集成方式：LangChain Callback
----------------------------
LangChain 有一个强大的 Callback 机制：
  - 你只需要在"图执行"的时候传入一个 CallbackHandler
  - LangChain 会自动把所有 LLM 调用、Chain 执行的事件都通知给这个 Handler
  - Handler 负责把事件上报到 LangFuse 服务器

这意味着：**不需要修改任何 Agent 代码**，就能获得完整的追踪数据。
这就是"关注点分离"的好处——业务逻辑（Agent）和可观测性（LangFuse）完全解耦。

架构图：
  ┌─────────────────────────────────────────┐
  │          WebSocket 请求                   │
  │  config = { callbacks: [langfuse_cb] }   │
  └─────────────┬───────────────────────────┘
                │
                ▼
  ┌─────────────────────────────────────────┐
  │        LangGraph 图执行                  │
  │   Callback 自动传播到每个节点              │
  │                                          │
  │  ┌──────────┐  ┌──────────┐             │
  │  │Intent Agent│→│Retrieval │→ ...        │
  │  │(LLM调用)  │  │Agent     │             │
  │  └────┬─────┘  └────┬─────┘             │
  │       │              │                   │
  │       ▼              ▼                   │
  │  ┌─────────────────────────────┐         │
  │  │  LangFuse Callback Handler  │         │
  │  │  自动记录所有事件             │         │
  │  └─────────────┬───────────────┘         │
  └────────────────┼────────────────────────┘
                   │
                   ▼
  ┌─────────────────────────────────────────┐
  │     LangFuse Server (localhost:3000)     │
  │     Dashboard 可视化查看 Trace            │
  └─────────────────────────────────────────┘
"""

from typing import Optional

from config.settings import langfuse_config


def create_langfuse_callback(
    user_id: str,
    session_id: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> Optional[object]:
    """
    创建 LangFuse CallbackHandler（用于 LangChain 集成）。

    【学习要点】
    这个函数返回一个 LangFuse 的 CallbackHandler 对象。
    把它放进 RunnableConfig 的 callbacks 列表中，
    LangChain 就会自动把所有执行事件上报到 LangFuse。

    参数
    ----
    user_id : str
        当前用户 ID，用作 trace 的标识。
        同一个用户的多次匹配可以在 LangFuse 中按 user_id 过滤。
    session_id : str | None
        会话 ID，用于关联同一会话的多个 trace。
        比如同一次 WebSocket 连接中的所有 LLM 调用。
    tags : list[str] | None
        标签列表，用于在 LangFuse 中分类和过滤。
        例如 ["match", "supervisor"] 表示这是一次 Supervisor 模式的匹配。

    返回值
    ------
    LangFuse CallbackHandler 实例，或者 None（如果 LangFuse 未启用）。
    返回 None 时，调用方应跳过所有 LangFuse 相关操作。

    【学习要点 — 优雅降级】
    当 LangFuse 未启用时（比如开发环境、或 Docker 没启动），
    这个函数返回 None 而不是报错。
    调用方只需要检查返回值是否为 None，就能决定是否启用可观测性。
    这叫做"优雅降级"（Graceful Degradation）——
    附加功能不可用时，核心功能仍然正常工作。
    """
    # 如果 LangFuse 未启用，直接返回 None
    if not langfuse_config.enabled:
        return None

    try:
        from langfuse import Langfuse, get_client
        from langfuse.langchain import CallbackHandler

        # 【学习要点 — trace_id 格式要求】
        # Langfuse v4 基于 OpenTelemetry，要求 trace_id 必须是
        # 32 位小写十六进制字符（W3C Trace Context 标准）。
        # 例如: "a1b2c3d4e5f6789012345678abcdef01"
        #
        # 如果用自定义格式（如 "match_M002_20260613"），Langfuse 会报错：
        # "Passed trace ID is not a valid 32 lowercase hex char Langfuse trace id"
        # 导致 CallbackHandler 的每个事件都抛出 ValueError。
        #
        # 解决方案：用 uuid4().hex 生成标准格式的 trace_id。
        import uuid
        trace_id = uuid.uuid4().hex  # 32 位小写 hex，如 "a1b2c3d4..."

        # 【学习要点 — 全局客户端初始化】
        # Langfuse v4 使用"全局客户端"模式：
        # 先创建一个 Langfuse 客户端（配置连接信息），它会自动注册为全局默认。
        # 之后 CallbackHandler 通过 get_client() 获取这个全局客户端。
        # 这和 v2 不同——v2 是在 CallbackHandler 构造函数里直接传所有参数。
        Langfuse(
            public_key=langfuse_config.public_key,
            secret_key=langfuse_config.secret_key,
            host=langfuse_config.host,
        )

        # 创建 CallbackHandler，关联到指定的 trace
        # trace_context 告诉 LangFuse "这个 Handler 产生的所有事件都归属于这个 trace"
        handler = CallbackHandler(
            trace_context={"trace_id": trace_id},
        )

        # 将 trace_id 保存到 handler 对象上，方便调用方读取
        # （用于存入 State，供 Judge Agent 上报评分时使用）
        handler._xinxi_trace_id = trace_id

        # 设置 trace 级别的属性（user_id、session_id、tags）
        # 【学习要点 — propagate_attributes】
        # Langfuse v4 使用 OpenTelemetry 上下文传播属性。
        # propagate_attributes() 返回一个上下文管理器，
        # 在 with 块内的所有 LangChain 调用都会自动携带这些属性。
        # 对于异步代码，我们改用 set_environment 的方式（见下方）。
        import os
        os.environ["LANGFUSE_USER_ID"] = user_id
        if session_id:
            os.environ["LANGFUSE_SESSION_ID"] = session_id

        print(f"  [LangFuse] 追踪已启动: trace_id={trace_id}")
        return handler

    except ImportError:
        # langfuse 包未安装（可能在某些环境中不需要安装）
        print("  [LangFuse] 警告: langfuse 包未安装，跳过可观测性")
        return None
    except Exception as e:
        # 连接失败等异常——不影响核心功能
        print(f"  [LangFuse] 警告: 初始化失败 ({e})，跳过可观测性")
        return None


def flush_langfuse(handler: Optional[object] = None) -> None:
    """
    将待上报的 LangFuse 数据立即发送到服务器。

    【学习要点】
    LangFuse 内部使用"批量上报"策略：
    事件不会立即发送到服务器，而是先攒在内存队列中，
    定期批量发送（以减少网络请求次数，提高性能）。

    如果不手动 flush，当程序退出时，队列中可能还有未发送的事件，
    导致 Dashboard 上看到的 trace 不完整（缺少最后几个节点的数据）。

    所以在每次匹配完成后调用 flush，确保数据完整。

    【学习要点 — v4 API 变化】
    Langfuse v4 的 CallbackHandler 没有直接的 flush() 方法。
    需要通过 get_client() 获取全局客户端来 flush。
    这是 v4 "全局客户端"架构的体现。

    参数
    ----
    handler : CallbackHandler | None
        占位参数（保持接口兼容）。v4 中实际通过全局客户端 flush。
    """
    if handler is None:
        return
    try:
        from langfuse import get_client
        client = get_client()
        client.flush()
    except Exception as e:
        # flush 失败不应影响主流程
        print(f"  [LangFuse] flush 失败: {e}")


def langfuse_report_scores(
    trace_id: str,
    user_id: str,
    evaluation: dict,
    match_id: str = "",
) -> None:
    """
    将 Judge Agent 的评估分数上报到 LangFuse。

    【学习要点】
    这是可观测性闭环的最后一环：
      匹配 → 评估（Judge Agent 打分）→ 上报分数 → Dashboard 趋势图

    有了分数数据，LangFuse Dashboard 可以展示：
    - 匹配质量的趋势变化（随着 Prompt 优化，分数是上升还是下降？）
    - 各维度的分数分布（哪个维度最容易得低分？）
    - 按用户分组的分数对比

    这对"持续优化"非常有价值——你可以快速发现：
    "上次改了 Prompt 后，温度感分数下降了 2 分"，然后针对性优化。

    参数
    ----
    trace_id : str
        LangFuse trace ID（要关联到哪个追踪记录）。
    user_id : str
        用户 ID。
    evaluation : dict
        Judge Agent 的评估结果（包含 overall_score、各维度分数等）。
    match_id : str
        匹配记录 ID（可选，作为元数据附加）。

    【学习要点 — try/except 包裹外部调用】
    网络请求、外部服务调用都可能失败（网络超时、服务器宕机等）。
    评分上报是"锦上添花"的功能，不应该因为上报失败就中断整个匹配流程。
    所以用 try/except 捕获所有异常，打印警告后继续执行。
    """
    if not langfuse_config.enabled:
        return

    try:
        from langfuse import Langfuse

        # 创建 Langfuse 客户端（如果全局客户端已初始化，这里会复用配置）
        client = Langfuse(
            public_key=langfuse_config.public_key,
            secret_key=langfuse_config.secret_key,
            host=langfuse_config.host,
        )

        # 1. 上报整体评分
        #    这是最重要的指标——一次匹配的总体质量
        #    【学习要点 — v4 create_score】
        #    Langfuse v4 使用 create_score() 替代了 v2 的 score()。
        #    参数基本一致：name（指标名）、value（分数值）、trace_id（关联的追踪）。
        overall = evaluation.get("overall_score", 0)
        if overall:
            client.create_score(
                trace_id=trace_id,
                name="overall_match_quality",     # 指标名称（Dashboard 上显示）
                value=overall,                     # 分数值（1-10）
                comment=f"Match quality for user {user_id}",
            )

        # 2. 上报各维度评分
        #    多维度分析帮助定位具体问题：
        #    比如"整体分高但温度感低"→ 需要优化推荐信的文案风格
        dimension_names = {
            "relevance": "相关性",       # 候选人是否符合择偶要求
            "compatibility": "契合度",    # 性格、兴趣匹配程度
            "explanation": "解释力",      # 匹配理由是否具体有说服力
            "consistency": "一致性",      # 评分与理由是否自洽
            "warmth": "温度感",           # 推荐信是否真诚温暖
        }

        for key, cn_name in dimension_names.items():
            score_value = evaluation.get(key)
            if score_value is not None:
                client.create_score(
                    trace_id=trace_id,
                    name=f"dim_{key}",            # 用英文 key 作为指标名（便于程序处理）
                    value=score_value,
                    comment=f"{cn_name}评分",       # 中文描述（便于人工查看）
                )

        # 确保数据立即发送（不等待批量上报）
        client.flush()

        print(f"  [LangFuse] 评分已上报: 整体 {overall}/10, trace_id={trace_id}")

    except ImportError:
        print("  [LangFuse] 警告: langfuse 包未安装，跳过评分上报")
    except Exception as e:
        # 上报失败不影响主流程
        print(f"  [LangFuse] 评分上报失败（不影响主流程）: {e}")
