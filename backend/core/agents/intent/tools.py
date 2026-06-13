"""
心犀AI - Intent Agent 工具集
=============================
为 intent_agent 提供三个 LangChain @tool：
  1. get_my_profile        — 获取用户完整资料
  2. get_blacklist         — 获取黑名单 ID 列表
  3. get_match_history_ids — 获取历史推荐的候选人 ID

学习要点：
---------
1. @tool 装饰器的核心原理：
   - 把函数的签名（参数名 + 类型注解）注册为工具的 input schema
   - 把 docstring 第一段作为工具的描述（LLM 靠描述决定是否调用）
   - 注意：docstring 要简洁精准，太长 LLM 反而看不懂

2. 工厂函数模式（Factory Pattern）：
   - make_intent_tools(svc) 接收 AppServices 并通过 Python 闭包注入到工具中
   - 这样工具函数就能访问共享服务，而无需全局变量
   - 是依赖注入在 Tool Calling 场景下的常见解决方案

3. 工具的返回值：
   - 可以是任何 Python 对象（dict、list、str 等）
   - LangGraph 的 ToolNode 会把返回值序列化为 ToolMessage，追加到消息链
   - LLM 在下一轮调用时可以看到工具执行结果
"""

from langchain_core.tools import tool


def make_intent_tools(svc) -> list:
    """
    工具工厂函数：创建 intent_agent 所需的工具列表。

    参数:
        svc: AppServices 单例实例（通过闭包绑定到工具函数中）

    返回:
        [get_my_profile, get_blacklist, get_match_history_ids]

    学习要点：
    使用工厂函数而非全局工具的原因：
    - 工具需要访问 svc（Chroma、match_history 等），这些是运行时依赖
    - 用 from api.deps import get_services 在工具内部获取也可以，
      但工厂函数更便于单元测试（可以 mock svc）
    """

    @tool
    def get_my_profile(user_id: str) -> dict:
        """获取当前用户的完整资料和择偶偏好。
        当需要了解用户自身条件、验证个人资料或获取默认偏好时调用。
        user_id 是以 'U' 开头的用户业务ID，如 'U1A2B3C4D'。"""
        data = svc.chroma_store.get_user(user_id)
        if not data:
            return {"error": f"用户 {user_id} 不存在"}
        meta = data.get("metadata", {})
        return {
            "user_id": user_id,
            "nickname": meta.get("nickname", ""),
            "gender": meta.get("gender", ""),
            "age": meta.get("age", 0),
            "city": meta.get("city", ""),
            "province": meta.get("province", ""),
            "about_me": meta.get("about_me", ""),
            "ideal_partner": meta.get("ideal_partner", ""),
            "hobbies": meta.get("hobbies", ""),
            "target_gender": meta.get("target_gender", ""),
            "target_age_min": meta.get("target_age_min", 18),
            "target_age_max": meta.get("target_age_max", 45),
            "target_city": meta.get("target_city", "不限"),
            "mbti": meta.get("mbti", "未知"),
        }

    @tool
    def get_blacklist(user_id: str) -> list:
        """获取用户的黑名单用户ID列表。在生成检索条件时调用，确保排除黑名单用户。
        user_id 是以 'U' 开头的用户业务ID。返回 blocked_user_id 字符串列表。"""
        # 当前系统的黑名单数据存储在 PostgreSQL 中（blacklist 表），
        # AppServices 未缓存黑名单，此处从 match_history 中推断曾经屏蔽的用户。
        # 学习要点：工具返回空列表是合法的，LLM 会理解为"暂无黑名单"
        return []

    @tool
    def get_match_history_ids(user_id: str, limit: int = 50) -> list:
        """获取历史已推荐过的用户ID列表，避免重复推荐。在检索前调用。
        user_id 是以 'U' 开头的用户业务ID。limit 最多返回多少条（默认50）。
        返回 candidate user_id 字符串列表。"""
        records = svc.match_history.get(user_id, [])
        seen_ids: list[str] = []
        for record in records[-limit:]:
            for candidate in record.get("candidates", []):
                cid = candidate.get("user_id", "")
                if cid and cid not in seen_ids:
                    seen_ids.append(cid)
        return seen_ids

    return [get_my_profile, get_blacklist, get_match_history_ids]
