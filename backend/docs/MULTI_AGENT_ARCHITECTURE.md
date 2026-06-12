# Multi-Agent 架构学习文档

## 概述

本文档介绍心犀AI从单 Agent 流水线升级到 Supervisor 多 Agent 架构的全过程。
两种架构的代码都保留在项目中，可以通过配置切换，方便对比学习。

## 架构对比

### 旧版：单 Agent 链式流水线

```
parse_intent → hybrid_search → post_analysis → [条件判断]
                                                    │
              ┌─── 满意 ──→ generate_match → END
              └─── 不满意 → reflection → [循环判断]
                                            │
                      ┌─── 未超限 ──→ hybrid_search（重试）
                      └─── 已超限 ──→ generate_match → END
```

代码位置：`core/agent/nodes.py` + `core/agent/graph.py`

特点：
- 所有节点函数在同一个文件中
- 节点之间用固定的边连接（链式流水线）
- 条件判断逻辑分散在各个路由函数中

### 新版：Supervisor 多 Agent 架构

```
                    ┌─────────────┐
                    │  SUPERVISOR │  ← 调度中心（路由器）
                    │  (Router)   │
                    └──────┬──────┘
                           │
           ┌───────┬───────┼───────┬───────┬───────┐
           ▼       ▼       ▼       ▼       ▼       ▼
        Intent  Retrieval Analysis Letter  Judge  Reflection
        Agent    Agent    Agent   Agent   Agent    Agent
           │       │       │       │       │        │
           └───────┴───────┴───────┴───────┴────────┘
                           │
                    回到 Supervisor
```

代码位置：`core/agents/` 目录

特点：
- 每个 Agent 是独立的模块，有自己的文件
- 所有 Agent 通过 Supervisor 统一调度（星型拓扑）
- 增删 Agent 不影响其他模块
- 新增 Judge Agent 自动评估匹配质量

## 目录结构

```
backend/core/agents/
  __init__.py
  supervisor/
    __init__.py
    state.py        # SupervisorState（共享状态定义）
    router.py       # 路由器（规则版 + LLM 版）
    graph.py        # 图构建器（StateGraph 编排）
  intent/
    agent.py        # 意图解析 Agent
  retrieval/
    agent.py        # 混合检索 Agent（无 LLM 调用）
  analysis/
    agent.py        # 深度分析 Agent
  reflection/
    agent.py        # 策略反思 Agent
  letter/
    agent.py        # 推荐信生成 Agent
  judge/
    agent.py        # 质量评估 Agent（LLM-as-Judge）
```

## 核心概念详解

### 1. 共享状态（Shared State / Blackboard Pattern）

所有 Agent 共享同一个 `SupervisorState`，类似"黑板模式"：
- 每个 Agent 从"黑板"上读取自己需要的信息
- 处理完后把结果写回"黑板"
- 不需要知道其他 Agent 的存在

```python
class SupervisorState(TypedDict, total=False):
    user_profile: UserProfile       # 输入
    hard_filters: dict              # Intent Agent 的输出
    rewritten_query: str            # Intent Agent 的输出
    candidates: list[dict]          # Retrieval Agent 的输出
    analysis_results: list[dict]    # Analysis Agent 的输出
    best_score: float               # Analysis Agent 的输出
    top_matches: list[dict]         # Letter Agent 的输出
    match_letters: list[str]        # Letter Agent 的输出
    evaluation: dict                # Judge Agent 的输出（新增！）
    next_agent: str                 # Supervisor 调度字段（新增！）
    agent_history: list[str]        # 执行记录（新增！）
```

### 2. Supervisor 路由器

路由器是 Supervisor 的"大脑"，决定下一步执行哪个 Agent。

**规则版（默认）**：用 if/elif 硬编码决策逻辑

```python
def rule_based_router(state: SupervisorState) -> str:
    last_agent = state.get("agent_history", [])[-1]
    if last_agent == "analysis":
        best_score = state.get("best_score", 0)
        if best_score >= threshold:
            return "letter"
        else:
            return "reflection"
    # ...
```

优点：确定性强、易调试、速度快
缺点：新增 Agent 时需手动修改路由代码

**LLM 版（进阶）**：用 LLM 理解各 Agent 的能力描述，动态决策

```python
def llm_based_router(state: SupervisorState) -> str:
    prompt = f"当前状态: ..., 可用Agent: ..."
    response = llm.invoke(prompt)
    return parse(response)["next_agent"]
```

优点：灵活、可扩展（只需描述新 Agent 的能力）
缺点：多一次 LLM 调用，有延迟和不确定性

### 3. 条件边（Conditional Edges）

LangGraph 的条件边让 Supervisor 可以动态路由：

```python
graph.add_conditional_edges(
    "supervisor",           # 从哪个节点出发
    _route_to_agent,        # 路由函数
    {                       # 映射表
        "intent": "intent_agent",
        "retrieval": "retrieval_agent",
        "FINISH": END,
    },
)
```

### 4. Agent 独立模块

每个 Agent 遵循统一的接口契约：
- 输入：从 `SupervisorState` 读取
- 输出：返回一个 `dict`，更新 `SupervisorState` 的特定字段
- 调度：设置 `next_agent` 告诉 Supervisor "我做完了"

```python
def intent_agent(state: SupervisorState) -> dict:
    user = state["user_profile"]          # 1. 从 state 读取输入
    result = llm.invoke(prompt)           # 2. 执行业务逻辑
    return {
        "hard_filters": result.hard_filters,
        "rewritten_query": result.query,
        "next_agent": "retrieval",         # 3. 告诉 Supervisor 下一步
        "agent_history": history + ["intent"],  # 4. 记录执行历史
    }
```

## 如何切换架构

在 `.env` 文件或环境变量中设置：

```bash
# 使用新版 Supervisor 多 Agent 架构（默认）
USE_SUPERVISOR=true

# 使用旧版单 Agent 流水线
USE_SUPERVISOR=false

# 路由方式：rule（规则版）或 llm（LLM 版）
SUPERVISOR_ROUTER=rule
```

## 多 Agent 模式变体对比

| 模式 | 特点 | 适用场景 |
|------|------|----------|
| **Supervisor**（本项目） | 一个调度者 + 多个执行者 | 流程相对固定，需要灵活调度 |
| **Swarm** | Agent 之间互相调用 | Agent 需要协作，无固定流程 |
| **Hierarchical** | 多层级的 Supervisor | 复杂任务需要分层管理 |
| **Sequential** | 链式流水线（就是旧版） | 简单固定的流程 |

## 共享工具模块

在重构过程中，提取了 3 处重复的工具代码：

### llm_factory.py — LLM 工厂

```python
def create_ll(temperature, model, callbacks) -> ChatOpenAI
```

统一 LLM 创建入口，支持 LangChain callbacks（为 LangFuse 集成做准备）。

### json_parser.py — JSON 解析器

```python
def parse_json_response(text) -> dict | list   # 3策略JSON解析
def invoke_structured(llm, prompt_messages, model_class) -> T  # LLM调用+解析+验证
```

兼容 DeepSeek thinking 模式的 JSON 提取逻辑只写一次。

### hard_filters 修复

旧版中 `parse_intent` 生成的 `hard_filters` 被存入 State 但从未被消费。
现在 `HybridRetriever.retrieve()` 接受 `hard_filters` 参数，
让 LLM 的智能分析真正影响检索过滤。

## WebSocket 兼容性

WebSocket 接口通过 `_NODE_LABELS` 映射表同时支持新旧节点名：

| 旧节点名 | 新节点名 | 中文描述 |
|----------|----------|----------|
| parse_intent | intent_agent | 意图解析 |
| hybrid_search | retrieval_agent | 混合检索 |
| post_analysis | analysis_agent | 深度分析 |
| reflection | reflection_agent | 策略反思 |
| generate_match | letter_agent | 推荐信生成 |
| — | supervisor | 调度中心 |
| — | judge_agent | 质量评估 |

前端的 `MatchProgressPanel` 组件也同步更新了两套节点名的映射。

## 学习路线建议

1. 先读 `supervisor/state.py` — 理解共享状态的结构
2. 再读 `intent/agent.py` — 最简单的 Agent 实现
3. 然后读 `supervisor/router.py` — 理解路由决策（对比规则版和 LLM 版）
4. 最后读 `supervisor/graph.py` — 理解图的编排

## 后续扩展方向

- **Phase 3: LangFuse 可观测性** — 追踪每个 Agent 的 LLM 调用
- **Human-in-the-loop** — 在 Supervisor 模式中集成 interrupt/resume
- **动态 Agent 注册** — 运行时添加新 Agent，无需重启
- **Agent 性能对比** — A/B 测试不同 Agent 的 prompt 策略
