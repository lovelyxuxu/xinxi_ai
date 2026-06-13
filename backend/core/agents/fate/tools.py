"""
缘分分析 Agent 工具集。

工具设计原则：
- 每个工具职责单一（一个工具只做一件事）
- 工具输入输出均为 JSON 可序列化类型
- 兼容性规则内置在代码中（无需外部 API）
- Tool Calling 学习要点：
    每个函数加 @tool 装饰器即成为 LLM 可调用的工具。
    LangChain 会自动解析函数签名和 docstring，
    生成 OpenAI Function Calling 格式的 schema，
    让 LLM 知道何时以及如何调用这些工具。

属相/星座兼容性来源：传统民间合婚规则（趣味性为主，不作严肃建议）
MBTI 兼容性来源：Myers-Briggs 研究的常见"黄金搭档"组合
"""
import random
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
_ZODIAC_ELEMENTS: dict[str, list[str]] = {
    "火象": ["白羊座", "狮子座", "射手座"],
    "土象": ["金牛座", "处女座", "摩羯座"],
    "风象": ["双子座", "天秤座", "水瓶座"],
    "水象": ["巨蟹座", "天蝎座", "双鱼座"],
}
_ELEMENT_COMPAT: dict[tuple[str, str], tuple[int, str]] = {
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
_MBTI_GOLDEN_PAIRS: dict[frozenset, tuple[int, str]] = {
    frozenset(["INFJ", "ENFP"]): (95, "灵魂共鸣，直觉相通，理想型搭档"),
    frozenset(["INFP", "ENFJ"]): (92, "理想主义双星，彼此成就"),
    frozenset(["INTJ", "ENTP"]): (90, "智识对等，观点碰撞，精神伴侣"),
    frozenset(["INTP", "ENTJ"]): (88, "理性互补，一个思考一个执行"),
    frozenset(["ISFJ", "ESFP"]): (85, "稳定与活力，平衡感极好"),
    frozenset(["ISTJ", "ESTP"]): (80, "踏实与行动力，现实中的好搭档"),
    frozenset(["ISTP", "ESTJ"]): (78, "实干派组合，互相尊重"),
    frozenset(["ISFP", "ESFJ"]): (82, "温柔与细心，家庭氛围一流"),
    frozenset(["INFJ", "INTJ"]): (85, "深度思考者，共同探索人生意义"),
    frozenset(["ENFP", "ENTP"]): (83, "创意爆发，对话永远不会无聊"),
}

# ── 塔罗牌库 ──────────────────────────────────────────────────
_TAROT_CARDS = [
    {"name": "恋人", "emoji": "💑", "meaning": "命中注定的相遇，两颗心的共鸣", "upright": True},
    {"name": "星星", "emoji": "⭐", "meaning": "希望与灵感，美好的预兆", "upright": True},
    {"name": "太阳", "emoji": "☀️", "meaning": "喜悦与成功，充满活力的缘分", "upright": True},
    {"name": "月亮", "emoji": "🌙", "meaning": "神秘与直觉，深层次的情感连接", "upright": True},
    {"name": "世界", "emoji": "🌍", "meaning": "圆满与完整，两个人共同创造完整", "upright": True},
    {"name": "魔术师", "emoji": "🎩", "meaning": "意志与技能，善用各自优势", "upright": True},
    {"name": "命运之轮", "emoji": "☯️", "meaning": "命运交汇，此刻相遇皆有意义", "upright": True},
    {"name": "力量", "emoji": "🦁", "meaning": "温柔的力量，彼此给予勇气", "upright": True},
    {"name": "节制", "emoji": "⚖️", "meaning": "平衡与耐心，两人节奏需要调和", "upright": False},
    {"name": "正义", "emoji": "⚔️", "meaning": "公平与真实，需要坦诚相待", "upright": False},
]


def _get_element(zodiac: str) -> str | None:
    """根据星座名获取所属元素组。"""
    for element, signs in _ZODIAC_ELEMENTS.items():
        if zodiac in signs:
            return element
    return None


@tool
def calc_zodiac_compatibility(zodiac_a: str, zodiac_b: str) -> dict:
    """
    计算两人西方星座兼容性。

    Tool Calling 学习要点：
    - @tool 装饰器将普通函数转为 LangChain Tool
    - 函数名成为工具名（LLM 通过名称选择工具）
    - docstring 成为工具描述（告诉 LLM 何时使用此工具）
    - 参数类型注解成为 JSON Schema（LLM 知道传什么类型）

    Args:
        zodiac_a: 第一人的星座（如 "双鱼座"）
        zodiac_b: 第二人的星座（如 "天蝎座"）

    Returns:
        包含 score（兼容分数 0-100）、description（说明）的字典
    """
    elem_a = _get_element(zodiac_a)
    elem_b = _get_element(zodiac_b)

    if not elem_a or not elem_b:
        return {
            "score": 70,
            "description": "星座数据不完整，按中等缘分计算",
            "element_a": elem_a,
            "element_b": elem_b,
        }

    key = (elem_a, elem_b) if (elem_a, elem_b) in _ELEMENT_COMPAT else (elem_b, elem_a)
    score, desc = _ELEMENT_COMPAT.get(key, (68, "两人相性中等，后天努力更重要"))

    return {
        "score": score,
        "description": desc,
        "zodiac_a": zodiac_a,
        "zodiac_b": zodiac_b,
        "element_a": elem_a,
        "element_b": elem_b,
    }


@tool
def calc_chinese_zodiac_compatibility(zodiac_a: str, zodiac_b: str) -> dict:
    """
    计算两人属相（中国传统生肖）兼容性。

    按三合（最佳）> 六合（良好）> 普通 > 相冲（挑战）分级。

    Args:
        zodiac_a: 第一人的属相（如 "龙"）
        zodiac_b: 第二人的属相（如 "猴"）

    Returns:
        包含 score、level（三合/六合/普通/相冲）、description 的字典
    """
    # 三合：分数 90-95
    if zodiac_b in _ZODIAC_SANHÉ.get(zodiac_a, []):
        score = random.randint(90, 95)
        level = "三合"
        desc = f"{zodiac_a}与{zodiac_b}天作之合，传统婚配中的最佳搭档！"
    # 六合：分数 82-88
    elif _ZODIAC_LIUHÉ.get(zodiac_a) == zodiac_b:
        score = random.randint(82, 88)
        level = "六合"
        desc = f"{zodiac_a}与{zodiac_b}六合吉缘，相性和谐，互补性强"
    # 相冲：分数 45-55
    elif _ZODIAC_CHONG.get(zodiac_a) == zodiac_b:
        score = random.randint(45, 55)
        level = "相冲"
        desc = f"{zodiac_a}与{zodiac_b}相冲，存在一些性格摩擦，但后天努力同样可以相处融洽"
    # 普通：分数 65-78
    else:
        score = random.randint(65, 78)
        level = "普通"
        desc = f"{zodiac_a}与{zodiac_b}缘分平和，相处得当可发展出深厚感情"

    return {
        "score": score,
        "level": level,
        "description": desc,
        "zodiac_a": zodiac_a,
        "zodiac_b": zodiac_b,
    }


@tool
def calc_mbti_compatibility(mbti_a: str, mbti_b: str) -> dict:
    """
    计算两人 MBTI 性格类型兼容性。

    依据 Myers-Briggs 研究中的黄金配对组合进行评分。
    若不在已知配对中，按 NT/NF/ST/SF 功能组相似度评估。

    Args:
        mbti_a: 第一人的 MBTI（如 "INFJ"）
        mbti_b: 第二人的 MBTI（如 "ENFP"）

    Returns:
        包含 score、is_golden_pair、description 的字典
    """
    pair = frozenset([mbti_a.upper(), mbti_b.upper()])

    if pair in _MBTI_GOLDEN_PAIRS:
        score, desc = _MBTI_GOLDEN_PAIRS[pair]
        return {
            "score": score,
            "is_golden_pair": True,
            "description": desc,
            "mbti_a": mbti_a,
            "mbti_b": mbti_b,
        }

    # 按功能组（NT/NF/ST/SF）评估相似度
    def _group(m: str) -> str:
        m = m.upper()
        n_s = "N" if "N" in m else "S"
        t_f = "T" if "T" in m else "F"
        return n_s + t_f

    g_a, g_b = _group(mbti_a), _group(mbti_b)
    if g_a == g_b:
        score, desc = 78, "同功能组，思维方式相近，话题丰富"
    elif set(g_a) & set(g_b):  # 共享一个维度
        score, desc = 68, "部分共鸣，各有所长，互补潜力大"
    else:
        score, desc = 58, "差异明显，需要更多理解与包容，但反差也是魅力所在"

    return {
        "score": score,
        "is_golden_pair": False,
        "description": desc,
        "mbti_a": mbti_a,
        "mbti_b": mbti_b,
    }


@tool
def get_tarot_for_fate(initiator_zodiac: str, candidate_zodiac: str) -> dict:
    """
    为两个人抽取缘分塔罗牌（趣味性功能）。

    根据双方星座元素和随机种子选牌，增加神秘感与趣味性。
    这是 Agent 的"潮流元素"特性——将命理/占卜融入 AI 分析。

    Args:
        initiator_zodiac: 发起人星座
        candidate_zodiac: 候选人星座

    Returns:
        包含 card（牌名）、meaning（含义）、is_positive（是否正位）的字典
    """
    # 用星座名的哈希值作为种子，让同一对组合每次抽到相同的牌（稳定性）
    seed = hash(f"{initiator_zodiac}{candidate_zodiac}") % len(_TAROT_CARDS)
    card = _TAROT_CARDS[seed]

    return {
        "card": card["name"],
        "emoji": card["emoji"],
        "meaning": card["meaning"],
        "is_positive": card["upright"],
        "reading": (
            f"✦ 为{initiator_zodiac}({initiator_zodiac})与{candidate_zodiac}({candidate_zodiac})抽到「{card['name']}」{card['emoji']}\n"
            f"  {'正位' if card['upright'] else '逆位'}：{card['meaning']}"
        ),
    }


@tool
def calc_composite_fate_score(
    zodiac_score: int,
    chinese_zodiac_score: int,
    mbti_score: int,
    age_diff: int,
    height_diff: int,
) -> dict:
    """
    综合缘分指数计算（加权平均）。

    权重设计：
    - MBTI（35%）：性格匹配是感情长久的核心
    - 西方星座（25%）：趣味性强，用户感兴趣
    - 属相（25%）：传统文化，有文化认同感
    - 年龄差（10%）：适度年龄差有加分
    - 身高差（5%）：审美偏好

    Args:
        zodiac_score: 西方星座兼容分（0-100）
        chinese_zodiac_score: 属相兼容分（0-100）
        mbti_score: MBTI 兼容分（0-100）
        age_diff: 年龄差（绝对值，岁）
        height_diff: 身高差（绝对值，厘米）

    Returns:
        包含 total_score（综合缘分指数）、breakdown（各项分解）、label（等级标签）的字典
    """
    # 年龄差分数：差值越小越高分，5岁以内满分，超过15岁较低
    age_score = max(0, 100 - max(0, age_diff - 5) * 6)

    # 身高差分数：男女推荐10-20cm差，太小或太大都略低分
    if 8 <= height_diff <= 25:
        height_score = 90
    elif height_diff < 8:
        height_score = 70
    else:
        height_score = max(50, 90 - (height_diff - 25) * 2)

    total = int(
        zodiac_score * 0.25
        + chinese_zodiac_score * 0.25
        + mbti_score * 0.35
        + age_score * 0.10
        + height_score * 0.05
    )

    # 等级标签
    if total >= 88:
        label = "天作之合 ✨"
    elif total >= 78:
        label = "缘分深厚 💕"
    elif total >= 65:
        label = "相性不错 💫"
    elif total >= 50:
        label = "缘分普通 🌱"
    else:
        label = "需要磨合 🤝"

    return {
        "total_score": total,
        "label": label,
        "breakdown": {
            "zodiac": zodiac_score,
            "chinese_zodiac": chinese_zodiac_score,
            "mbti": mbti_score,
            "age": age_score,
            "height": height_score,
        },
    }


# 导出所有工具列表，供 Agent 初始化使用
FATE_TOOLS = [
    calc_zodiac_compatibility,
    calc_chinese_zodiac_compatibility,
    calc_mbti_compatibility,
    get_tarot_for_fate,
    calc_composite_fate_score,
]
