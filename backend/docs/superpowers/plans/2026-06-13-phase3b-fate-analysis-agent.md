# Phase 3b — 心动 TA 们 · 缘分分析 Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现「心动 TA 们」收藏功能、两层缘分分析（群体洞察 + 升级分析三路径）、FateAnalysisAgent（星座/属相/MBTI/爱情语言 Tool Calling + Streaming），以及通知系统。

**Architecture:** 后端新增 `/api/fate` 路由模块，FateAnalysisAgent 基于 LangGraph 状态机实现两层分析流，工具调用获取星座/属相/MBTI 兼容性数据，SSE 流式推送进度；前端新建「心动清单」页面和「缘分分析」页（Bento Grid 布局），通知中心接收实时更新。

**Tech Stack:** Python/LangGraph/LangChain/FastAPI SSE · React/TypeScript/framer-motion

**前置条件：** Phase 3a 已完成（数据库表已创建，20位种子用户已入库）

---

## 文件清单

### 后端（新建）
- `backend/core/agents/fate/__init__.py`
- `backend/core/agents/fate/tools.py` — 星座/属相/MBTI 工具函数
- `backend/core/agents/fate/agent.py` — FateAnalysisAgent（LangGraph）
- `backend/api/routers/fate.py` — 心动候选 + 缘分分析 API 路由
- `backend/api/routers/notifications.py` — 通知 API 路由

### 后端（修改）
- `backend/api/app.py` — 注册新路由
- `backend/api/deps.py` — 确保 get_db 和 get_current_user 导出正确

### 前端（新建）
- `frontend/src/pages/FateList.tsx` — 心动清单页
- `frontend/src/pages/FateAnalysis.tsx` — 缘分分析页（Bento Grid）
- `frontend/src/components/FateParamsDrawer.tsx` — 参数临时调整抽屉
- `frontend/src/components/AnalysisCard.tsx` — 分析结果卡片组件

### 前端（修改）
- `frontend/src/api/client.ts` — 添加心动/分析 API 函数
- `frontend/src/App.tsx` — 注册新路由
- `frontend/src/components/Navbar.tsx` — 通知角标接通实际数据
- `frontend/src/components/UserCard.tsx` — 心动按钮接通实际 API

---

## Task 1：星座/属相/MBTI 工具函数

**Files:**
- Create: `backend/core/agents/fate/__init__.py`
- Create: `backend/core/agents/fate/tools.py`

- [ ] **Step 1: 创建 __init__.py**

```python
# backend/core/agents/fate/__init__.py
```

- [ ] **Step 2: 创建 tools.py**

```python
"""
缘分分析 Agent 工具集。

工具设计原则：
- 每个工具职责单一（一个工具只做一件事）
- 工具输入输出均为 JSON 可序列化类型
- 兼容性规则内置在代码中（无需外部 API）
- Tool Calling 学习要点：每个函数加 @tool 装饰器即成为 LLM 可调用的工具

属相/星座兼容性来源：传统民间合婚规则（趣味性为主，不作严肃建议）
MBTI 兼容性来源：Myers-Briggs 研究的常见"黄金搭档"组合
"""
from langchain_core.tools import tool


# ── 属相兼容表 ────────────────────────────────────────────────
# 三合：最佳组合；六合：次佳；相冲：不合
_ZODIAC_SANHÉ = {
    "鼠": ["龙", "猴"], "牛": ["蛇", "鸡"], "虎": ["马", "狗"],
    "兔": ["羊", "猪"], "龙": ["鼠", "猴"], "蛇": ["牛", "鸡"],
    "马": ["虎", "狗"], "羊": ["兔", "猪"], "猴": ["鼠", "龙"],
    "鸡": ["牛", "蛇"], "狗": ["虎", "马"], "猪": ["兔", "羊"],
}
_ZODIAC_LIUHÉ = {
    "鼠": "牛", "牛": "鼠", "虎": "猪", "兔": "狗",
    "龙": "鸡", "蛇": "猴", "马": "羊", "羊": "马",
    "猴": "蛇", "鸡": "龙", "狗": "兔", "猪": "虎",
}
_ZODIAC_CHONG = {
    "鼠": "马", "牛": "羊", "虎": "猴", "兔": "鸡",
    "龙": "狗", "蛇": "猪", "马": "鼠", "羊": "牛",
    "猴": "虎", "鸡": "兔", "狗": "龙", "猪": "蛇",
}

# ── 星座兼容表（西方传统元素分组）────────────────────────────
_ZODIAC_ELEMENTS = {
    "火象": ["白羊座", "狮子座", "射手座"],
    "土象": ["金牛座", "处女座", "摩羯座"],
    "风象": ["双子座", "天秤座", "水瓶座"],
    "水象": ["巨蟹座", "天蝎座", "双鱼座"],
}
_ELEMENT_COMPAT = {
    ("火象", "火象"): (85, "激情四射，能量同频，容易相互激励"),
    ("火象", "风象"): (90, "风助火势，相性极佳，彼此点燃"),
    ("土象", "土象"): (80, "稳定踏实，共同价值观，长久伴侣"),
    ("土象", "水象"): (88, "水润土地，互相滋养，深度羁绊"),
    ("风象", "风象"): (75, "思维碰撞，话题不断，偶尔需要落地"),
    ("水象", "水象"): (82, "情感共鸣，默契感强，需保持独立空间"),
    ("火象", "土象"): (60, "各有节奏，需要耐心磨合"),
    ("火象", "水象"): (65, "反差吸引，但情绪管理是关键"),
    ("土象", "风象"): (55, "踏实与飘逸的碰撞，需要理解与尊重"),
    ("水象", "风象"): (70, "感性与理性，互补但需沟通"),
}

# ── MBTI 兼容配对 ─────────────────────────────────────────────
_MBTI_GOLDEN_PAIRS = {
    frozenset(["INFJ", "ENFP"]): (95, "灵魂共鸣，直觉相通，理想型搭档"),
    frozenset(["INFP", "ENFJ"]): (92, "理想主义双星，彼此成就"),
    frozenset(["INTJ", "ENTP"]): (90, "智识对等，观点碰撞，精神伴侣"),
    frozenset(["INTP", "ENTJ"]): (88, "理性互补，一个思考一个执行"),
    frozenset(["ISFJ", "ESFP"]): (85, "稳定与活力，平衡感极好"),
    frozenset(["ISTJ", "ESTP"]): (80, "踏实与行动力，现实中的好搭档"),
    frozenset(["ISTP", "ESTJ"]): (78, "实干派组合，互相尊重"),
    frozenset(["ISFP", "ESFJ"]): (82, "温柔与细心，家庭氛围一流"),
}


def _get_element(zodiac: str) -> str:
    for element, signs in _ZODIAC_ELEMENTS.items():
        if zodiac in signs:
            return element
    return "未知"


@tool
def calc_zodiac_compatibility(zodiac_a: str, zodiac_b: str) -> dict:
    """
    计算西方星座配对兼容性。

    参数:
        zodiac_a: 用户A的星座（如"双鱼座"）
        zodiac_b: 用户B的星座（如"天蝎座"）

    返回:
        {
            "score": int (0-100),
            "element_a": str,
            "element_b": str,
            "description": str
        }
    """
    elem_a = _get_element(zodiac_a)
    elem_b = _get_element(zodiac_b)
    key = (elem_a, elem_b) if (elem_a, elem_b) in _ELEMENT_COMPAT else (elem_b, elem_a)
    score, desc = _ELEMENT_COMPAT.get(key, (70, "各有特点，缘分需要用心经营"))
    return {"score": score, "element_a": elem_a, "element_b": elem_b, "description": desc}


@tool
def calc_chinese_zodiac_compatibility(zodiac_a: str, zodiac_b: str) -> dict:
    """
    计算属相合婚兼容性（中国传统）。

    参数:
        zodiac_a: 用户A的属相（如"猪"）
        zodiac_b: 用户B的属相（如"兔"）

    返回:
        {
            "score": int (0-100),
            "relation": str ("三合" | "六合" | "相冲" | "普通"),
            "description": str
        }
    """
    if zodiac_b in _ZODIAC_SANHÉ.get(zodiac_a, []):
        return {"score": 92, "relation": "三合", "description": f"{zodiac_a}与{zodiac_b}三合，天生一对，感情顺遂"}
    if _ZODIAC_LIUHÉ.get(zodiac_a) == zodiac_b:
        return {"score": 85, "relation": "六合", "description": f"{zodiac_a}与{zodiac_b}六合，相互吸引，婚姻美满"}
    if _ZODIAC_CHONG.get(zodiac_a) == zodiac_b:
        return {"score": 40, "relation": "相冲", "description": f"{zodiac_a}与{zodiac_b}相冲，性格强强碰撞，需要更多包容"}
    return {"score": 70, "relation": "普通", "description": f"{zodiac_a}与{zodiac_b}无特殊冲合，缘分全凭两人经营"}


@tool
def calc_mbti_compatibility(mbti_a: str, mbti_b: str) -> dict:
    """
    计算 MBTI 人格类型兼容性。

    参数:
        mbti_a: 用户A的MBTI（如"INFJ"）
        mbti_b: 用户B的MBTI（如"ENFP"）

    返回:
        {
            "score": int (0-100),
            "is_golden_pair": bool,
            "description": str,
            "shared_traits": list[str]
        }
    """
    pair = frozenset([mbti_a.upper(), mbti_b.upper()])
    if pair in _MBTI_GOLDEN_PAIRS:
        score, desc = _MBTI_GOLDEN_PAIRS[pair]
        return {"score": score, "is_golden_pair": True, "description": desc, "shared_traits": []}

    # 计算共同维度数量（N/S/T/F/J/P/I/E 各1分）
    shared = sum(1 for a, b in zip(mbti_a.upper(), mbti_b.upper()) if a == b)
    score = 50 + shared * 10
    desc = ["截然不同，挑战与魅力并存", "有些共鸣，需要沟通磨合",
            "相互理解，有一定默契", "思维相近，沟通顺畅"][min(shared, 3)]
    return {"score": score, "is_golden_pair": False, "description": desc, "shared_traits": []}


@tool
def get_tarot_for_fate(initiator_zodiac: str, candidate_zodiac: str) -> dict:
    """
    根据两人星座抽取一张缘分塔罗牌（趣味装饰功能）。

    参数:
        initiator_zodiac: 发起者星座
        candidate_zodiac: 候选者星座

    返回:
        {
            "card_name": str,
            "card_emoji": str,
            "fate_reading": str
        }
    """
    import hashlib
    seed = initiator_zodiac + candidate_zodiac
    idx = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(_TAROT_CARDS)
    card = _TAROT_CARDS[idx]
    return card


_TAROT_CARDS = [
    {"card_name": "恋人", "card_emoji": "👫", "fate_reading": "两颗心的连接，爱意流动，彼此选择的缘分。"},
    {"card_name": "星星", "card_emoji": "⭐", "fate_reading": "充满希望的相遇，对方带来光和指引。"},
    {"card_name": "月亮", "card_emoji": "🌙", "fate_reading": "深沉而神秘的缘分，需要时间慢慢了解。"},
    {"card_name": "太阳", "card_emoji": "☀️", "fate_reading": "温暖明亮的缘分，相处愉快，充满活力。"},
    {"card_name": "世界", "card_emoji": "🌍", "fate_reading": "圆满的缘分，这段关系有走向完整的潜力。"},
    {"card_name": "命运之轮", "card_emoji": "🎡", "fate_reading": "命中注定的相遇，把握这次缘分的契机。"},
    {"card_name": "力量", "card_emoji": "🦁", "fate_reading": "两人都有内在力量，能给彼此支撑。"},
    {"card_name": "节制", "card_emoji": "⚖️", "fate_reading": "平衡与和谐，这段缘分需要双方配合节奏。"},
]
```

- [ ] **Step 3: Commit**

```bash
git add backend/core/agents/fate/
git commit -m "feat: add fate analysis tools (zodiac/mbti/tarot compatibility)"
```

---

## Task 2：FateAnalysisAgent（LangGraph 状态机）

**Files:**
- Create: `backend/core/agents/fate/agent.py`

- [ ] **Step 1: 创建 agent.py**

```python
"""
FateAnalysisAgent - 缘分分析 Agent。

架构说明（LangGraph 学习要点）：
=================================
本 Agent 使用 LangGraph 实现两层分析流程：

第一层（group_overview）：
  START → analyze_profiles → generate_overview → END

第二层（deep/comm/comparison）：
  START → load_first_layer → [路径选择] → deep_analysis / comm_advice / comparison → END

技术要点：
- StateGraph：定义 Agent 的状态机，每个节点是一个函数
- ToolNode：将工具调用封装为 LangGraph 节点
- Streaming：每个节点通过 `yield` 流式输出中间状态
- Tool Calling：LLM 通过 bind_tools 绑定工具，自主决定何时调用

Agent 状态设计：
- 使用 TypedDict 定义状态（messages + 业务字段）
- 每个节点读取状态、处理后返回更新
"""
from __future__ import annotations

import json
import uuid
from typing import TypedDict, Annotated, Optional

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from core.agents.fate.tools import (
    calc_zodiac_compatibility,
    calc_chinese_zodiac_compatibility,
    calc_mbti_compatibility,
    get_tarot_for_fate,
)


# ── Agent 状态定义 ────────────────────────────────────────────
class FateAnalysisState(TypedDict):
    """Agent 执行过程中的完整状态。"""
    # 基础信息
    analysis_id: str
    analysis_type: str          # group_overview / deep_compatibility / comm_advice / comparison
    initiator: dict             # 发起者用户数据
    candidates: list[dict]      # 候选者用户数据列表
    match_params: dict          # 偏好参数

    # 工具调用结果
    compat_results: list[dict]  # 每位候选者的兼容性计算结果

    # 输出
    overview_result: Optional[dict]   # 第一层：全量洞察
    deep_result: Optional[dict]       # 第二层：深度分析
    final_report: Optional[dict]      # 最终输出
    error: Optional[str]


# ── 工具列表 ─────────────────────────────────────────────────
FATE_TOOLS = [
    calc_zodiac_compatibility,
    calc_chinese_zodiac_compatibility,
    calc_mbti_compatibility,
    get_tarot_for_fate,
]

# ── LLM 初始化 ────────────────────────────────────────────────
def _get_llm():
    """获取绑定了工具的 LLM 实例。"""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, streaming=True)
    return llm.bind_tools(FATE_TOOLS)


# ── 节点：计算兼容性数据 ──────────────────────────────────────
def compute_compatibility(state: FateAnalysisState) -> FateAnalysisState:
    """
    节点1：为每位候选者调用工具计算星座/属相/MBTI 兼容性。

    学习要点：
    - 这里直接调用工具函数（非通过 LLM），效率更高
    - LLM 在后续节点中利用这些结果生成叙事报告
    """
    initiator = state["initiator"]
    results = []

    for candidate in state["candidates"]:
        compat = {"candidate_id": candidate["user_id"], "candidate_name": candidate["nickname"]}

        # 西方星座
        if initiator.get("zodiac_sign") and candidate.get("zodiac_sign"):
            z_result = calc_zodiac_compatibility.invoke({
                "zodiac_a": initiator["zodiac_sign"],
                "zodiac_b": candidate["zodiac_sign"],
            })
            compat["zodiac"] = z_result

        # 属相
        if initiator.get("chinese_zodiac") and candidate.get("chinese_zodiac"):
            cz_result = calc_chinese_zodiac_compatibility.invoke({
                "zodiac_a": initiator["chinese_zodiac"],
                "zodiac_b": candidate["chinese_zodiac"],
            })
            compat["chinese_zodiac"] = cz_result

        # MBTI
        if initiator.get("mbti") and candidate.get("mbti"):
            m_result = calc_mbti_compatibility.invoke({
                "mbti_a": initiator["mbti"],
                "mbti_b": candidate["mbti"],
            })
            compat["mbti"] = m_result

        # 塔罗牌（仅在 group_overview 和 deep_compatibility 时生成）
        if state["analysis_type"] in ("group_overview", "deep_compatibility"):
            if initiator.get("zodiac_sign") and candidate.get("zodiac_sign"):
                tarot = get_tarot_for_fate.invoke({
                    "initiator_zodiac": initiator["zodiac_sign"],
                    "candidate_zodiac": candidate["zodiac_sign"],
                })
                compat["tarot"] = tarot

        # 综合评分（加权平均）
        scores = []
        if "zodiac" in compat:
            scores.append(compat["zodiac"]["score"] * 0.15)
        if "chinese_zodiac" in compat:
            scores.append(compat["chinese_zodiac"]["score"] * 0.10)
        if "mbti" in compat:
            scores.append(compat["mbti"]["score"] * 0.20)
        # 基础条件分（年龄/城市/学历，简单规则）
        basic_score = _calc_basic_score(initiator, candidate)
        scores.append(basic_score * 0.05)
        # 剩余 50% 由 LLM 语义分析（在报告中体现）
        weighted = sum(scores) / (sum([0.15, 0.10, 0.20, 0.05][:len(scores)]) or 1)
        compat["partial_score"] = round(weighted)
        results.append(compat)

    # 按 partial_score 降序排序
    results.sort(key=lambda x: x.get("partial_score", 0), reverse=True)
    return {**state, "compat_results": results}


def _calc_basic_score(initiator: dict, candidate: dict) -> int:
    """基础条件匹配评分（年龄/城市/学历）。"""
    score = 70
    age = candidate.get("age", 0)
    if age and initiator.get("target_age_min") and initiator.get("target_age_max"):
        if initiator["target_age_min"] <= age <= initiator["target_age_max"]:
            score += 20
        else:
            score -= 15
    if initiator.get("target_city", "不限") != "不限":
        if candidate.get("city") == initiator["target_city"]:
            score += 10
    return min(100, max(0, score))


# ── 节点：生成群体洞察报告 ────────────────────────────────────
async def generate_overview(state: FateAnalysisState) -> FateAnalysisState:
    """
    节点2（group_overview）：LLM 生成全量洞察报告。

    学习要点：
    - SystemMessage 设定 AI 角色和输出格式
    - HumanMessage 传入结构化数据（兼容性计算结果 + 用户资料）
    - 返回 JSON 格式报告，前端解析后渲染
    """
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.8)

    initiator = state["initiator"]
    compat_data = state["compat_results"]

    system_prompt = """你是「心犀」AI 红娘，专业分析两人的缘分契合度。
分析风格：温暖有趣，融合现代玄学感（星座、属相、MBTI），给出真诚而有洞见的建议。
输出要求：返回 JSON，结构如下：
{
  "initiator_insight": "对用户本人的择偶偏好洞察（100字内）",
  "candidates": [
    {
      "candidate_id": "...",
      "candidate_name": "...",
      "overall_score": 0-100,
      "headline": "一句话概括缘分（15字内，有趣）",
      "zodiac_note": "星座分析（30字内）",
      "chinese_zodiac_note": "属相分析（30字内）",
      "mbti_note": "MBTI 分析（30字内）",
      "energy_color": "一个CSS颜色值（十六进制，代表这对缘分的能量色调）",
      "tarot_card": "塔罗牌名",
      "tarot_emoji": "对应emoji",
      "tarot_reading": "缘分塔罗解读（30字内）",
      "pros": ["优势1", "优势2"],
      "summary": "综合缘分小结（60字内）"
    }
  ],
  "top_recommendation": "候选者user_id",
  "recommendation_reason": "推荐理由（50字内）"
}"""

    user_data = json.dumps({
        "initiator": {
            "nickname": initiator["nickname"],
            "age": initiator.get("age"),
            "zodiac_sign": initiator.get("zodiac_sign"),
            "chinese_zodiac": initiator.get("chinese_zodiac"),
            "mbti": initiator.get("mbti"),
            "about_me": initiator.get("about_me", ""),
            "ideal_partner": initiator.get("ideal_partner", ""),
        },
        "compatibility_data": compat_data,
    }, ensure_ascii=False)

    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"请分析以下缘分数据：\n{user_data}"),
    ])

    try:
        report = json.loads(response.content)
    except json.JSONDecodeError:
        # 若 LLM 输出非纯 JSON，提取 JSON 部分
        content = response.content
        start = content.find("{")
        end = content.rfind("}") + 1
        report = json.loads(content[start:end]) if start >= 0 else {"raw": content}

    return {**state, "overview_result": report, "final_report": report}


# ── 节点：深度相性分析 ────────────────────────────────────────
async def generate_deep_compatibility(state: FateAnalysisState) -> FateAnalysisState:
    """节点：深度相性分析（星座/属相/MBTI/爱情语言/潜在摩擦点）。"""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.8)

    initiator = state["initiator"]
    candidates = state["candidates"]
    compat_data = state["compat_results"]

    system_prompt = """你是专业的爱情分析师，深度分析两人的相性。
输出 JSON：
{
  "analyses": [
    {
      "candidate_id": "...",
      "candidate_name": "...",
      "love_language": {
        "initiator": "肯定言辞|精心时刻|服务行为|肢体接触|收受礼物",
        "candidate": "..."
      },
      "compatibility_matrix": {
        "personality": {"score": 0-100, "note": "30字"},
        "values": {"score": 0-100, "note": "30字"},
        "lifestyle": {"score": 0-100, "note": "30字"},
        "communication": {"score": 0-100, "note": "30字"}
      },
      "friction_points": ["潜在摩擦点1", "潜在摩擦点2"],
      "growth_potential": "这段关系能带给彼此的成长（40字）",
      "final_verdict": "深度总结（80字，真诚不浮夸）"
    }
  ]
}"""

    user_data = json.dumps({
        "initiator": initiator,
        "candidates": candidates,
        "compat_data": compat_data,
    }, ensure_ascii=False, default=str)

    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"请进行深度相性分析：\n{user_data}"),
    ])

    try:
        report = json.loads(response.content)
    except json.JSONDecodeError:
        content = response.content
        start = content.find("{")
        end = content.rfind("}") + 1
        report = json.loads(content[start:end]) if start >= 0 else {"raw": content}

    return {**state, "deep_result": report, "final_report": report}


# ── 节点：沟通建议 ────────────────────────────────────────────
async def generate_comm_advice(state: FateAnalysisState) -> FateAnalysisState:
    """节点：生成具体的沟通开场和约会建议。"""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.9)

    initiator = state["initiator"]
    candidates = state["candidates"]

    system_prompt = """你是机智幽默的约会顾问，给出实用又有趣的破冰建议。
输出 JSON：
{
  "advices": [
    {
      "candidate_id": "...",
      "candidate_name": "...",
      "opening_lines": ["破冰第一句1", "破冰第一句2", "破冰第一句3"],
      "date_ideas": ["约会场景1（结合对方兴趣）", "约会场景2"],
      "topics_to_avoid": ["避免聊的话题"],
      "topics_to_explore": ["推荐深聊的话题"],
      "timing_tip": "最佳联系时机建议（20字）"
    }
  ]
}"""

    user_data = json.dumps({
        "initiator": {"nickname": initiator["nickname"], "mbti": initiator.get("mbti"), "hobbies": initiator.get("hobbies")},
        "candidates": [{"user_id": c["user_id"], "nickname": c["nickname"], "mbti": c.get("mbti"), "hobbies": c.get("hobbies"), "about_me": c.get("about_me")} for c in candidates],
    }, ensure_ascii=False)

    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"请给出沟通建议：\n{user_data}"),
    ])

    try:
        report = json.loads(response.content)
    except json.JSONDecodeError:
        content = response.content
        start = content.find("{")
        end = content.rfind("}") + 1
        report = json.loads(content[start:end]) if start >= 0 else {"raw": content}

    return {**state, "final_report": report}


# ── 节点：横向对比 ────────────────────────────────────────────
async def generate_comparison(state: FateAnalysisState) -> FateAnalysisState:
    """节点：生成多候选者横向对比报告（Bento Grid 数据）。"""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

    initiator = state["initiator"]
    candidates = state["candidates"]
    compat_data = state["compat_results"]

    system_prompt = """你是数据分析师，用对比表格形式呈现候选者分析。
输出 JSON：
{
  "dimensions": ["外貌条件", "学历背景", "共同兴趣", "价值观", "地理距离", "星座相性", "MBTI相性"],
  "candidates": [
    {
      "candidate_id": "...",
      "candidate_name": "...",
      "scores": {
        "外貌条件": {"score": 0-100, "note": "10字"},
        "学历背景": {"score": 0-100, "note": "10字"},
        "共同兴趣": {"score": 0-100, "note": "10字"},
        "价值观": {"score": 0-100, "note": "10字"},
        "地理距离": {"score": 0-100, "note": "10字"},
        "星座相性": {"score": 0-100, "note": "10字"},
        "MBTI相性": {"score": 0-100, "note": "10字"}
      },
      "total_score": 0-100,
      "unique_advantage": "这个人最突出的优势（20字）"
    }
  ],
  "winner": "综合最佳候选者user_id",
  "winner_reason": "推荐理由（30字）"
}"""

    user_data = json.dumps({
        "initiator": initiator,
        "candidates": candidates,
        "compat_data": compat_data,
    }, ensure_ascii=False, default=str)

    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"请生成对比分析：\n{user_data}"),
    ])

    try:
        report = json.loads(response.content)
    except json.JSONDecodeError:
        content = response.content
        start = content.find("{")
        end = content.rfind("}") + 1
        report = json.loads(content[start:end]) if start >= 0 else {"raw": content}

    return {**state, "final_report": report}


# ── 路由函数 ──────────────────────────────────────────────────
def route_analysis_type(state: FateAnalysisState) -> str:
    """根据 analysis_type 路由到对应节点。"""
    return {
        "group_overview": "generate_overview",
        "deep_compatibility": "generate_deep_compatibility",
        "comm_advice": "generate_comm_advice",
        "comparison": "generate_comparison",
    }.get(state["analysis_type"], "generate_overview")


# ── 构建 LangGraph ────────────────────────────────────────────
def build_fate_graph():
    """
    构建缘分分析状态机。

    LangGraph 学习要点：
    - StateGraph(FateAnalysisState)：创建以 FateAnalysisState 为状态的图
    - add_node：添加节点（每个节点是一个函数）
    - add_conditional_edges：根据函数返回值决定下一个节点
    - compile()：编译图，生成可执行的 runnable
    """
    graph = StateGraph(FateAnalysisState)

    # 添加节点
    graph.add_node("compute_compatibility", compute_compatibility)
    graph.add_node("generate_overview", generate_overview)
    graph.add_node("generate_deep_compatibility", generate_deep_compatibility)
    graph.add_node("generate_comm_advice", generate_comm_advice)
    graph.add_node("generate_comparison", generate_comparison)

    # 边：入口 → 计算兼容性
    graph.set_entry_point("compute_compatibility")

    # 条件边：计算完成后根据 analysis_type 路由
    graph.add_conditional_edges(
        "compute_compatibility",
        route_analysis_type,
        {
            "generate_overview": "generate_overview",
            "generate_deep_compatibility": "generate_deep_compatibility",
            "generate_comm_advice": "generate_comm_advice",
            "generate_comparison": "generate_comparison",
        },
    )

    # 所有分析节点 → END
    for node in ["generate_overview", "generate_deep_compatibility", "generate_comm_advice", "generate_comparison"]:
        graph.add_edge(node, END)

    return graph.compile()


# 全局图实例（单例，避免重复编译）
fate_graph = build_fate_graph()


# ── 对外接口 ──────────────────────────────────────────────────
async def run_fate_analysis(
    analysis_id: str,
    analysis_type: str,
    initiator: dict,
    candidates: list[dict],
    match_params: dict | None = None,
) -> dict:
    """
    运行缘分分析，返回完整报告。

    参数:
        analysis_id: 分析记录 ID
        analysis_type: 分析类型
        initiator: 发起者用户数据（to_dict() 输出）
        candidates: 候选者用户数据列表
        match_params: 偏好参数（可空）

    返回:
        final_report: dict（缘分分析报告）
    """
    initial_state: FateAnalysisState = {
        "analysis_id": analysis_id,
        "analysis_type": analysis_type,
        "initiator": initiator,
        "candidates": candidates,
        "match_params": match_params or {},
        "compat_results": [],
        "overview_result": None,
        "deep_result": None,
        "final_report": None,
        "error": None,
    }

    final_state = await fate_graph.ainvoke(initial_state)
    return final_state.get("final_report") or {}
```

- [ ] **Step 2: Commit**

```bash
git add backend/core/agents/fate/agent.py
git commit -m "feat: implement FateAnalysisAgent with LangGraph state machine and zodiac/MBTI tools"
```

---

## Task 3：心动候选 + 缘分分析 API 路由

**Files:**
- Create: `backend/api/routers/fate.py`
- Modify: `backend/api/app.py`

- [ ] **Step 1: 创建 fate.py 路由**

```python
"""
/api/fate 路由 - 心动 TA 们清单 + 缘分分析。
"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from api.deps import get_db, get_current_user
from api.schemas import (
    FateCandidateListResponse, FateCandidateResponse,
    FateAnalysisCreate, FateAnalysisResponse,
    UserPublicResponse,
)
from core.database.models import User, FateCandidate, FateAnalysis, Notification
from core.agents.fate.agent import run_fate_analysis

router = APIRouter(prefix="/api/fate", tags=["fate"])


# ── 心动候选接口 ──────────────────────────────────────────────

@router.post("/candidates/{candidate_id}", status_code=201)
async def add_fate_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """加入心动 TA 们清单。"""
    if candidate_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="不能把自己加入心动清单")

    # 检查候选者是否存在
    candidate = await db.scalar(select(User).where(User.user_id == candidate_id))
    if not candidate:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 检查是否已存在
    existing = await db.scalar(
        select(FateCandidate).where(
            FateCandidate.user_id == current_user.user_id,
            FateCandidate.candidate_id == candidate_id,
        )
    )
    if existing:
        return {"message": "已在心动清单中"}

    fc = FateCandidate(
        user_id=current_user.user_id,
        candidate_id=candidate_id,
    )
    db.add(fc)

    # 发送通知给被加入的用户
    notif = Notification(
        notif_id=str(uuid.uuid4()),
        recipient_id=candidate_id,
        type="fate_added",
        actor_id=current_user.user_id,
        payload={"actor_name": current_user.nickname},
    )
    db.add(notif)

    await db.commit()

    # 检查是否双向心动
    reverse = await db.scalar(
        select(FateCandidate).where(
            FateCandidate.user_id == candidate_id,
            FateCandidate.candidate_id == current_user.user_id,
        )
    )
    if reverse:
        # 双向心动！通知双方
        for recipient_id, actor_id in [
            (current_user.user_id, candidate_id),
            (candidate_id, current_user.user_id),
        ]:
            mutual_notif = Notification(
                notif_id=str(uuid.uuid4()),
                recipient_id=recipient_id,
                type="mutual_fate",
                actor_id=actor_id,
                payload={"message": "你们互相心动了！"},
            )
            db.add(mutual_notif)
        await db.commit()
        return {"message": "加入成功", "mutual_fate": True}

    return {"message": "加入成功", "mutual_fate": False}


@router.delete("/candidates/{candidate_id}", status_code=204)
async def remove_fate_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """从心动清单移除。"""
    await db.execute(
        delete(FateCandidate).where(
            FateCandidate.user_id == current_user.user_id,
            FateCandidate.candidate_id == candidate_id,
        )
    )
    await db.commit()


@router.get("/candidates", response_model=FateCandidateListResponse)
async def get_fate_candidates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取我的心动 TA 们清单（含候选者详情）。"""
    result = await db.execute(
        select(FateCandidate).where(FateCandidate.user_id == current_user.user_id)
        .order_by(FateCandidate.added_at.desc())
    )
    fcs = result.scalars().all()

    items = []
    for fc in fcs:
        candidate = await db.scalar(select(User).where(User.user_id == fc.candidate_id))
        if candidate:
            items.append(FateCandidateResponse(
                candidate_id=fc.candidate_id,
                note=fc.note,
                added_at=fc.added_at.isoformat(),
                candidate=UserPublicResponse(**_to_public(candidate)),
            ))

    return FateCandidateListResponse(items=items, total=len(items))


def _to_public(user: User) -> dict:
    """转换为公开资料（不含敏感字段）。"""
    return {
        "user_id": user.user_id,
        "nickname": user.nickname,
        "gender": user.gender,
        "age": user.age,
        "city": user.city,
        "education": user.education,
        "mbti": user.mbti,
        "zodiac_sign": user.zodiac_sign,
        "chinese_zodiac": user.chinese_zodiac,
        "height_cm": user.height_cm,
        "about_me": user.about_me,
        "hobbies": user.hobbies,
        "avatar_url": user.avatar_url,
        "photos": user.photos or [],
        "profile_complete": user.profile_complete,
    }


# ── 缘分分析接口 ──────────────────────────────────────────────

@router.post("/analyses", response_model=FateAnalysisResponse, status_code=201)
async def create_fate_analysis(
    data: FateAnalysisCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    发起缘分分析。

    权限检查：必须 profile_complete=True 才能发起分析。
    异步执行：Agent 在后台运行，前端通过 /stream 端点获取实时进度。
    """
    if not current_user.profile_complete:
        raise HTTPException(status_code=403, detail="请先完善个人资料后再发起缘分分析")

    # 获取候选者数据
    candidates_data = []
    for cid in data.candidate_ids:
        candidate = await db.scalar(select(User).where(User.user_id == cid))
        if candidate:
            candidates_data.append(candidate.to_dict())

    if not candidates_data:
        raise HTTPException(status_code=400, detail="候选者列表为空")

    analysis_id = str(uuid.uuid4())
    analysis = FateAnalysis(
        analysis_id=analysis_id,
        initiator_id=current_user.user_id,
        analysis_type=data.analysis_type,
        candidate_ids=data.candidate_ids,
        match_params_snapshot=data.match_params_override,
        parent_analysis_id=data.parent_analysis_id,
        status="pending",
    )
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    # 后台执行 Agent
    background_tasks.add_task(
        _run_analysis_background,
        analysis_id=analysis_id,
        analysis_type=data.analysis_type,
        initiator=current_user.to_dict(),
        candidates=candidates_data,
        match_params=data.match_params_override or {},
    )

    return FateAnalysisResponse(
        analysis_id=analysis_id,
        analysis_type=data.analysis_type,
        candidate_ids=data.candidate_ids,
        result=None,
        status="pending",
        created_at=analysis.created_at.isoformat(),
    )


async def _run_analysis_background(
    analysis_id: str,
    analysis_type: str,
    initiator: dict,
    candidates: list[dict],
    match_params: dict,
):
    """后台任务：运行 Agent 并更新数据库。"""
    from core.database.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        try:
            report = await run_fate_analysis(
                analysis_id=analysis_id,
                analysis_type=analysis_type,
                initiator=initiator,
                candidates=candidates,
                match_params=match_params,
            )
            analysis = await db.scalar(
                select(FateAnalysis).where(FateAnalysis.analysis_id == analysis_id)
            )
            if analysis:
                analysis.result = report
                analysis.status = "done"
                await db.commit()

            # 发送分析完成通知
            notif = Notification(
                notif_id=str(uuid.uuid4()),
                recipient_id=initiator["user_id"],
                type="analysis_done",
                payload={"analysis_id": analysis_id, "type": analysis_type},
            )
            db.add(notif)
            await db.commit()

        except Exception as e:
            analysis = await db.scalar(
                select(FateAnalysis).where(FateAnalysis.analysis_id == analysis_id)
            )
            if analysis:
                analysis.status = "failed"
                analysis.result = {"error": str(e)}
                await db.commit()


@router.get("/analyses/{analysis_id}", response_model=FateAnalysisResponse)
async def get_fate_analysis(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取分析结果（前端轮询直到 status=done）。"""
    analysis = await db.scalar(
        select(FateAnalysis).where(
            FateAnalysis.analysis_id == analysis_id,
            FateAnalysis.initiator_id == current_user.user_id,
        )
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="分析记录不存在")

    return FateAnalysisResponse(
        analysis_id=analysis.analysis_id,
        analysis_type=analysis.analysis_type,
        candidate_ids=analysis.candidate_ids,
        result=analysis.result,
        status=analysis.status,
        created_at=analysis.created_at.isoformat(),
    )


@router.get("/analyses", response_model=list[FateAnalysisResponse])
async def list_fate_analyses(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取我的历史缘分分析列表。"""
    result = await db.execute(
        select(FateAnalysis)
        .where(FateAnalysis.initiator_id == current_user.user_id)
        .order_by(FateAnalysis.created_at.desc())
        .limit(20)
    )
    analyses = result.scalars().all()
    return [
        FateAnalysisResponse(
            analysis_id=a.analysis_id,
            analysis_type=a.analysis_type,
            candidate_ids=a.candidate_ids,
            result=a.result,
            status=a.status,
            created_at=a.created_at.isoformat(),
        )
        for a in analyses
    ]
```

- [ ] **Step 2: 注册路由到 app.py**

在 `backend/api/app.py` 中添加：

```python
from api.routers.fate import router as fate_router
from api.routers.notifications import router as notifications_router

app.include_router(fate_router)
app.include_router(notifications_router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/api/routers/fate.py backend/api/app.py
git commit -m "feat: add fate candidates and fate analysis API routes"
```

---

## Task 4：通知 API 路由

**Files:**
- Create: `backend/api/routers/notifications.py`

- [ ] **Step 1: 创建 notifications.py**

```python
"""
/api/notifications 路由 - 系统通知。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from api.deps import get_db, get_current_user
from api.schemas import NotificationListResponse, NotificationResponse
from core.database.models import User, Notification

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取我的通知列表（最近50条）。"""
    result = await db.execute(
        select(Notification)
        .where(Notification.recipient_id == current_user.user_id)
        .order_by(Notification.created_at.desc())
        .limit(50)
    )
    notifs = result.scalars().all()
    unread = sum(1 for n in notifs if not n.is_read)

    return NotificationListResponse(
        items=[
            NotificationResponse(
                notif_id=n.notif_id,
                type=n.type,
                actor_id=n.actor_id,
                payload=n.payload or {},
                is_read=n.is_read,
                created_at=n.created_at.isoformat(),
            )
            for n in notifs
        ],
        unread_count=unread,
    )


@router.put("/{notif_id}/read", status_code=204)
async def mark_read(
    notif_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """标记单条通知为已读。"""
    await db.execute(
        update(Notification)
        .where(
            Notification.notif_id == notif_id,
            Notification.recipient_id == current_user.user_id,
        )
        .values(is_read=True)
    )
    await db.commit()


@router.put("/read-all", status_code=204)
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """全部标记为已读。"""
    await db.execute(
        update(Notification)
        .where(
            Notification.recipient_id == current_user.user_id,
            Notification.is_read == False,
        )
        .values(is_read=True)
    )
    await db.commit()
```

- [ ] **Step 2: Commit**

```bash
git add backend/api/routers/notifications.py
git commit -m "feat: add notifications API (list, mark read)"
```

---

## Task 5：前端 API Client 更新

**Files:**
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: 添加心动和分析 API 函数**

在 `frontend/src/api/client.ts` 末尾追加：

```typescript
// ── 心动 TA 们 ────────────────────────────────────────────────

export const addFateCandidate = (candidateId: string) =>
  api.post(`/fate/candidates/${candidateId}`);

export const removeFateCandidate = (candidateId: string) =>
  api.delete(`/fate/candidates/${candidateId}`);

export const getFateCandidates = () =>
  api.get<FateCandidateListResponse>("/fate/candidates").then(r => r.data);

// ── 缘分分析 ──────────────────────────────────────────────────

export interface FateAnalysisCreateRequest {
  analysis_type: "group_overview" | "deep_compatibility" | "comm_advice" | "comparison";
  candidate_ids: string[];
  match_params_override?: Record<string, unknown>;
  parent_analysis_id?: string;
}

export const createFateAnalysis = (data: FateAnalysisCreateRequest) =>
  api.post<{ analysis_id: string; status: string }>("/fate/analyses", data).then(r => r.data);

export const getFateAnalysis = (analysisId: string) =>
  api.get<FateAnalysisResponse>(`/fate/analyses/${analysisId}`).then(r => r.data);

export const listFateAnalyses = () =>
  api.get<FateAnalysisResponse[]>("/fate/analyses").then(r => r.data);

// ── 通知 ──────────────────────────────────────────────────────

export const getNotifications = () =>
  api.get<NotificationListResponse>("/notifications").then(r => r.data);

export const markNotificationRead = (notifId: string) =>
  api.put(`/notifications/${notifId}/read`);

export const markAllNotificationsRead = () =>
  api.put("/notifications/read-all");
```

同时在文件顶部的 types 区域添加接口定义：

```typescript
export interface FateCandidateListResponse {
  items: FateCandidateItem[];
  total: number;
}

export interface FateCandidateItem {
  candidate_id: string;
  note?: string;
  added_at: string;
  candidate: UserPublic;
}

export interface FateAnalysisResponse {
  analysis_id: string;
  analysis_type: string;
  candidate_ids: string[];
  result: Record<string, unknown> | null;
  status: "pending" | "done" | "failed";
  created_at: string;
}

export interface NotificationListResponse {
  items: NotificationItem[];
  unread_count: number;
}

export interface NotificationItem {
  notif_id: string;
  type: string;
  actor_id?: string;
  payload: Record<string, unknown>;
  is_read: boolean;
  created_at: string;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/client.ts
git commit -m "feat: add fate candidates, analysis, and notification API client functions"
```

---

## Task 6：心动清单页面

**Files:**
- Create: `frontend/src/pages/FateList.tsx`

- [ ] **Step 1: 创建 FateList.tsx**

```tsx
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Heart, Sparkles, Trash2, MessageCircle } from "lucide-react";
import { getFateCandidates, removeFateCandidate, createFateAnalysis } from "../api/client";
import type { FateCandidateItem } from "../api/client";
import { useNavigate } from "react-router-dom";

export default function FateList() {
  const [candidates, setCandidates] = useState<FateCandidateItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [analyzing, setAnalyzing] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    getFateCandidates().then(data => {
      setCandidates(data.items);
      setLoading(false);
    });
  }, []);

  const handleRemove = async (candidateId: string) => {
    await removeFateCandidate(candidateId);
    setCandidates(prev => prev.filter(c => c.candidate_id !== candidateId));
    setSelected(prev => { const s = new Set(prev); s.delete(candidateId); return s; });
  };

  const handleAnalyzeOne = async (candidateId: string) => {
    setAnalyzing(true);
    const result = await createFateAnalysis({
      analysis_type: "group_overview",
      candidate_ids: [candidateId],
    });
    navigate(`/fate/analysis/${result.analysis_id}`);
  };

  const handleAnalyzeAll = async () => {
    const ids = candidates.map(c => c.candidate_id);
    setAnalyzing(true);
    const result = await createFateAnalysis({
      analysis_type: "group_overview",
      candidate_ids: ids,
    });
    navigate(`/fate/analysis/${result.analysis_id}`);
  };

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-8 h-8 rounded-full border-2 border-purple-400 border-t-transparent animate-spin" />
    </div>
  );

  return (
    <div className="min-h-screen pb-24 px-4 pt-6 max-w-2xl mx-auto">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-2xl flex items-center justify-center"
            style={{ background: "var(--gradient-heart)" }}>
            <Heart size={20} color="white" fill="white" />
          </div>
          <div>
            <h1 className="text-xl font-bold">心动 TA 们</h1>
            <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
              {candidates.length} 位等待缘分分析
            </p>
          </div>
        </div>

        {candidates.length === 0 ? (
          <div className="glass-card p-12 text-center">
            <Heart size={48} className="mx-auto mb-4" style={{ color: "var(--color-text-muted)" }} />
            <p className="font-medium mb-2">还没有心动的人</p>
            <p className="text-sm mb-6" style={{ color: "var(--color-text-secondary)" }}>
              在首页点击用户卡片上的 ❤️ 加入清单
            </p>
            <button className="btn-primary" onClick={() => navigate("/")}>
              去发现缘分
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {candidates.map((item, idx) => (
              <motion.div
                key={item.candidate_id}
                className="glass-card p-4 flex items-center gap-4"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.05 }}
              >
                {/* 头像 */}
                <div className="w-14 h-14 rounded-2xl flex-shrink-0 overflow-hidden"
                  style={{ background: "var(--gradient-primary)" }}>
                  {item.candidate.avatar_url ? (
                    <img src={item.candidate.avatar_url} className="w-full h-full object-cover" alt="" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-white text-xl font-bold">
                      {item.candidate.nickname[0]}
                    </div>
                  )}
                </div>

                {/* 信息 */}
                <div className="flex-1 min-w-0">
                  <p className="font-semibold">{item.candidate.nickname}</p>
                  <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
                    {item.candidate.age}岁 · {item.candidate.city} · {item.candidate.zodiac_sign || item.candidate.mbti}
                  </p>
                </div>

                {/* 操作按钮 */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  <button
                    className="btn-primary text-sm px-3 py-2"
                    onClick={() => handleAnalyzeOne(item.candidate_id)}
                    disabled={analyzing}
                  >
                    <Sparkles size={14} className="inline mr-1" />
                    分析
                  </button>
                  <button
                    className="btn-ghost p-2"
                    onClick={() => handleRemove(item.candidate_id)}
                  >
                    <Trash2 size={16} style={{ color: "var(--color-danger)" }} />
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>

      {/* 底部统一分析按钮 */}
      {candidates.length >= 2 && (
        <div className="fixed bottom-20 left-0 right-0 px-4">
          <button
            className="btn-primary w-full py-4 text-base font-semibold rounded-2xl"
            style={{ background: "var(--gradient-heart)" }}
            onClick={handleAnalyzeAll}
            disabled={analyzing}
          >
            <Sparkles size={18} className="inline mr-2" />
            统一缘分分析（{candidates.length} 人）
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/FateList.tsx
git commit -m "feat: add FateList page with heart candidate management"
```

---

## Task 7：缘分分析结果页（Bento Grid）

**Files:**
- Create: `frontend/src/pages/FateAnalysis.tsx`
- Create: `frontend/src/components/FateParamsDrawer.tsx`

- [ ] **Step 1: 创建 FateParamsDrawer.tsx（参数临时调整）**

```tsx
import { useState } from "react";
import { X, SlidersHorizontal } from "lucide-react";

interface MatchParams {
  age_min: number;
  age_max: number;
  height_min: number;
  height_max: number;
  city: string;
  education: string;
}

interface Props {
  defaultParams: MatchParams;
  onConfirm: (params: MatchParams) => void;
  onClose: () => void;
}

export default function FateParamsDrawer({ defaultParams, onConfirm, onClose }: Props) {
  const [params, setParams] = useState<MatchParams>(defaultParams);

  return (
    <div className="fixed inset-0 z-50 flex items-end">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative w-full glass-card rounded-t-3xl p-6 animate-slide-up"
        style={{ background: "rgba(26,16,64,0.95)" }}>
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <SlidersHorizontal size={20} style={{ color: "#667eea" }} />
            <h3 className="font-bold text-lg">这次寻找的另一半条件</h3>
          </div>
          <button onClick={onClose}><X size={20} /></button>
        </div>

        <div className="space-y-5">
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span>年龄范围</span>
              <span style={{ color: "#667eea" }}>{params.age_min} — {params.age_max} 岁</span>
            </div>
            <div className="flex gap-3">
              <input type="range" min={18} max={params.age_max - 1} value={params.age_min}
                onChange={e => setParams(p => ({...p, age_min: +e.target.value}))}
                className="flex-1 accent-purple-500" />
              <input type="range" min={params.age_min + 1} max={60} value={params.age_max}
                onChange={e => setParams(p => ({...p, age_max: +e.target.value}))}
                className="flex-1 accent-purple-500" />
            </div>
          </div>

          <div>
            <div className="flex justify-between text-sm mb-2">
              <span>城市</span>
            </div>
            <select value={params.city}
              onChange={e => setParams(p => ({...p, city: e.target.value}))}
              className="input-dark">
              <option value="不限">不限</option>
              <option value="同城">同城优先</option>
              <option value="上海">上海</option>
              <option value="北京">北京</option>
              <option value="广州">广州</option>
              <option value="成都">成都</option>
              <option value="杭州">杭州</option>
            </select>
          </div>

          <div>
            <div className="text-sm mb-2">学历要求</div>
            <div className="flex gap-2 flex-wrap">
              {["不限", "大专及以上", "本科及以上", "硕士及以上"].map(edu => (
                <button key={edu}
                  className={`px-3 py-1.5 rounded-xl text-sm border transition-all ${params.education === edu ? "border-purple-500 bg-purple-500/20" : "border-white/20"}`}
                  onClick={() => setParams(p => ({...p, education: edu}))}>
                  {edu}
                </button>
              ))}
            </div>
          </div>
        </div>

        <p className="text-xs mt-4 text-center" style={{ color: "var(--color-text-muted)" }}>
          仅本次有效，不改变你的默认设置
        </p>

        <div className="flex gap-3 mt-5">
          <button className="btn-ghost flex-1" onClick={() => onConfirm(defaultParams)}>
            用默认条件
          </button>
          <button className="btn-primary flex-1" onClick={() => onConfirm(params)}>
            开始缘分分析
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 创建 FateAnalysis.tsx（Bento Grid 结果页）**

```tsx
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Sparkles, Heart, Star, RefreshCw, ArrowLeft } from "lucide-react";
import { getFateAnalysis, createFateAnalysis } from "../api/client";
import type { FateAnalysisResponse } from "../api/client";

export default function FateAnalysis() {
  const { analysisId } = useParams<{ analysisId: string }>();
  const [analysis, setAnalysis] = useState<FateAnalysisResponse | null>(null);
  const [polling, setPolling] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    if (!analysisId) return;
    const poll = async () => {
      const data = await getFateAnalysis(analysisId);
      setAnalysis(data);
      if (data.status === "done" || data.status === "failed") {
        setPolling(false);
      }
    };
    poll();
    const interval = setInterval(() => {
      if (polling) poll();
    }, 2000);
    return () => clearInterval(interval);
  }, [analysisId, polling]);

  if (!analysis || analysis.status === "pending") {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-6 p-8">
        <div className="relative w-20 h-20">
          <div className="absolute inset-0 rounded-full animate-ping"
            style={{ background: "rgba(240,147,251,0.3)" }} />
          <div className="relative w-full h-full rounded-full flex items-center justify-center"
            style={{ background: "var(--gradient-heart)" }}>
            <Sparkles size={32} color="white" />
          </div>
        </div>
        <div className="text-center">
          <p className="text-lg font-semibold mb-2">AI 正在分析你们的缘分</p>
          <p className="text-sm" style={{ color: "var(--color-text-secondary)" }}>
            从星座、属相、MBTI 多维度深入分析中...
          </p>
        </div>
      </div>
    );
  }

  if (analysis.status === "failed") {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 p-8">
        <p className="text-lg font-semibold">分析遇到了问题</p>
        <button className="btn-primary" onClick={() => navigate(-1)}>返回重试</button>
      </div>
    );
  }

  const result = analysis.result as any;
  const candidates = result?.candidates || [];

  return (
    <div className="min-h-screen pb-20 px-4 pt-6 max-w-2xl mx-auto">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        {/* 顶部导航 */}
        <button className="flex items-center gap-2 mb-6 text-sm"
          style={{ color: "var(--color-text-secondary)" }}
          onClick={() => navigate(-1)}>
          <ArrowLeft size={16} /> 返回清单
        </button>

        {/* 洞察概要 */}
        {result?.initiator_insight && (
          <div className="glass-card p-5 mb-6 animate-fade-in-up"
            style={{ borderColor: "rgba(102,126,234,0.3)" }}>
            <div className="flex items-center gap-2 mb-3">
              <Star size={16} style={{ color: "#667eea" }} />
              <span className="text-sm font-semibold text-gradient-primary">你的择偶洞察</span>
            </div>
            <p className="text-sm leading-relaxed">{result.initiator_insight}</p>
          </div>
        )}

        {/* 候选者 Bento Grid */}
        <div className="grid grid-cols-1 gap-4">
          {candidates.map((c: any, idx: number) => (
            <motion.div
              key={c.candidate_id}
              className="glass-card overflow-hidden"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 }}
              style={idx === 0 ? { borderColor: "rgba(240,147,251,0.4)" } : {}}
            >
              {/* 顶部：基本信息 + 分数 */}
              <div className="p-5">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <p className="text-lg font-bold">{c.candidate_name}</p>
                    <p className="text-sm mt-1" style={{ color: "var(--color-text-secondary)" }}>
                      {c.headline}
                    </p>
                  </div>
                  <div className="text-right flex-shrink-0 ml-4">
                    <div className="text-3xl font-bold text-gradient-primary">{c.overall_score}</div>
                    <div className="text-xs" style={{ color: "var(--color-text-muted)" }}>缘分值</div>
                  </div>
                </div>

                {/* 三维度标签 Bento */}
                <div className="grid grid-cols-3 gap-2 mb-4">
                  {[
                    { label: "星座", value: c.zodiac_note, color: "#667eea" },
                    { label: "属相", value: c.chinese_zodiac_note, color: "#f093fb" },
                    { label: "MBTI", value: c.mbti_note, color: "#4facfe" },
                  ].map(item => (
                    <div key={item.label} className="rounded-xl p-3 text-center"
                      style={{ background: `${item.color}15`, border: `1px solid ${item.color}30` }}>
                      <p className="text-xs font-semibold mb-1" style={{ color: item.color }}>{item.label}</p>
                      <p className="text-xs leading-tight" style={{ color: "var(--color-text-secondary)" }}>
                        {item.value || "—"}
                      </p>
                    </div>
                  ))}
                </div>

                {/* 缘分塔罗 */}
                {c.tarot_card && (
                  <div className="rounded-xl p-3 mb-4 flex items-center gap-3"
                    style={{ background: "rgba(240,147,251,0.08)", border: "1px solid rgba(240,147,251,0.2)" }}>
                    <span className="text-2xl">{c.tarot_emoji}</span>
                    <div>
                      <p className="text-xs font-semibold" style={{ color: "#f5576c" }}>
                        缘分塔罗 · {c.tarot_card}
                      </p>
                      <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>
                        {c.tarot_reading}
                      </p>
                    </div>
                  </div>
                )}

                {/* 综合小结 */}
                <p className="text-sm leading-relaxed">{c.summary}</p>
              </div>

              {/* 底部操作区 */}
              <div className="px-5 pb-4 flex gap-2">
                <button
                  className="btn-primary flex-1 text-sm py-2"
                  onClick={async () => {
                    const r = await createFateAnalysis({
                      analysis_type: "deep_compatibility",
                      candidate_ids: [c.candidate_id],
                      parent_analysis_id: analysis.analysis_id,
                    });
                    navigate(`/fate/analysis/${r.analysis_id}`);
                  }}
                >
                  <Sparkles size={13} className="inline mr-1" />
                  深度分析
                </button>
                <button
                  className="btn-ghost flex-1 text-sm py-2"
                  onClick={async () => {
                    const r = await createFateAnalysis({
                      analysis_type: "comm_advice",
                      candidate_ids: [c.candidate_id],
                      parent_analysis_id: analysis.analysis_id,
                    });
                    navigate(`/fate/analysis/${r.analysis_id}`);
                  }}
                >
                  💬 沟通建议
                </button>
              </div>
            </motion.div>
          ))}
        </div>

        {/* 对比分析按钮（多人时显示）*/}
        {candidates.length >= 2 && (
          <button
            className="btn-ghost w-full mt-4 py-3"
            onClick={async () => {
              const r = await createFateAnalysis({
                analysis_type: "comparison",
                candidate_ids: analysis.candidate_ids,
                parent_analysis_id: analysis.analysis_id,
              });
              navigate(`/fate/analysis/${r.analysis_id}`);
            }}
          >
            📊 横向对比分析
          </button>
        )}
      </motion.div>
    </div>
  );
}
```

- [ ] **Step 3: 注册路由到 App.tsx**

```tsx
import FateList from "./pages/FateList";
import FateAnalysis from "./pages/FateAnalysis";

// 添加路由（需要登录 + 完善资料）：
<Route path="/fate/list" element={<ProtectedRoute requireProfileComplete><FateList /></ProtectedRoute>} />
<Route path="/fate/analysis/:analysisId" element={<ProtectedRoute><FateAnalysis /></ProtectedRoute>} />
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/FateAnalysis.tsx frontend/src/components/FateParamsDrawer.tsx frontend/src/App.tsx
git commit -m "feat: add FateAnalysis page with Bento grid and FateParamsDrawer"
```

---

## Task 8：接通 UserCard 心动按钮

**Files:**
- Modify: `frontend/src/components/UserCard.tsx`

- [ ] **Step 1: 接通心动按钮逻辑**

在 `UserCard.tsx` 中导入 API 函数，管理心动状态：

```tsx
import { addFateCandidate, removeFateCandidate } from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import { useNavigate } from "react-router-dom";
import { useState } from "react";

// 在组件内：
const { user } = useAuth();
const navigate = useNavigate();
const [isHearted, setIsHearted] = useState(false); // 可以从 props 传入初始状态

const handleHeartClick = async (e: React.MouseEvent) => {
  e.stopPropagation();
  if (!user) {
    navigate("/login");
    return;
  }
  try {
    if (isHearted) {
      await removeFateCandidate(userId);
      setIsHearted(false);
    } else {
      await addFateCandidate(userId);
      setIsHearted(true);
    }
  } catch (err) {
    console.error("心动操作失败", err);
  }
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/UserCard.tsx
git commit -m "feat: wire UserCard heart button to fate candidates API"
```

---

## Task 9：联调验证

- [ ] **Step 1: 确认 Phase 3a 已完成**（数据库表存在，20位种子用户已入库）

- [ ] **Step 2: 后端完整性检查**

```bash
cd backend
python -c "
import asyncio
from core.agents.fate.tools import calc_zodiac_compatibility, calc_mbti_compatibility
# 验证工具函数
print(calc_zodiac_compatibility.invoke({'zodiac_a': '双鱼座', 'zodiac_b': '天蝎座'}))
print(calc_mbti_compatibility.invoke({'mbti_a': 'INFJ', 'mbti_b': 'ENFP'}))
"
```

预期：两个工具均返回包含 `score` 和 `description` 的 dict

- [ ] **Step 3: 启动服务**

```bash
cd backend && python run.py
cd frontend && npm run dev
```

- [ ] **Step 4: 浏览器验证流程**

1. 登录（`13800000001 / Test@123456`）
2. 首页 → 点击某用户卡片心形按钮 → 变粉色，无报错
3. 导航栏「心动 TA 们」→ 进入列表页，看到刚才心动的用户
4. 点击「分析」→ 跳到分析页 → 出现 loading 动画
5. 等待约 10-15 秒 → 结果页显示 Bento 卡片
6. 点击「深度分析」→ 二层分析启动

- [ ] **Step 5: TypeScript 检查**

```bash
cd frontend && npm run typecheck
```

预期：0 errors

- [ ] **Step 6: 最终 Commit**

```bash
git add -A
git commit -m "feat: phase3b complete - fate candidates, analysis agent, Bento UI, notifications"
```

---

## 验收标准

- [ ] 用户卡片心形按钮点击后加入/取消心动清单，未登录跳转登录页
- [ ] 心动清单页展示所有候选者，支持单人分析和批量分析
- [ ] 缘分分析 pending 状态有 loading 动画，done 后展示 Bento 结果页
- [ ] 分析结果包含：星座/属相/MBTI 标签、缘分值（0-100）、塔罗牌
- [ ] 二层分析（深度/沟通/对比）可从第一层结果页发起
- [ ] 双向心动时双方均收到通知
- [ ] TypeScript 编译 0 错误
