"""
心犀AI - LLM 工厂模块
========================

【学习要点】
这个模块是整个 Agent 系统的"LLM 制造工厂"。

为什么需要工厂模式？
--------------------
在没有这个模块之前，_create_ll() 函数在三个文件中各写了一遍：
- core/agent/nodes.py
- core/agent/interview/nodes.py
- core/evaluation/judge.py

三个版本几乎一模一样，只是名字不同（_create_ll vs _create_judge_llm）。
这就是经典的"代码重复"问题——如果要换模型或改配置，得改三个地方。

工厂模式（Factory Pattern）的好处：
1. **单一职责**：只负责创建 LLM 实例，不管 LLM 怎么用
2. **配置集中**：所有 LLM 配置都在一个地方管理
3. **扩展方便**：以后如果要支持多模型（GPT-4、Claude 等），
   只需在这里添加参数，调用方不需要改

【设计模式笔记】
这其实是"简单工厂"（Simple Factory），不是 GoF 的"抽象工厂"。
简单工厂 = 一个函数，根据参数返回不同的对象。
抽象工厂 = 一个类层级，每个子类创建一族相关产品。
对于我们的场景，简单工厂就够了。
"""

from langchain_openai import ChatOpenAI
from config.settings import llm_config


def create_ll(
    temperature: float | None = None,
    model: str | None = None,
    callbacks: list | None = None,
) -> ChatOpenAI:
    """
    创建 ChatOpenAI 实例（统一入口）。

    参数说明
    --------
    temperature : float | None
        控制输出随机性。
        - 0.0~0.3：确定性输出，适合意图解析、评分
        - 0.5~0.7：平衡创造性和一致性，适合反思、对话
        - 0.8~1.0：高创造性，适合文案生成（推荐信）
        - None：使用配置文件中的默认值

    model : str | None
        模型名称。None 使用配置文件中的默认模型。
        例如："deepseek-v4-flash", "deepseek-chat"

    callbacks : list | None
        LangChain 回调处理器列表。
        用于 LangFuse 可观测性追踪（Phase 3 会用到）。
        传入后，LLM 的每次调用都会自动记录 trace。

    返回值
    ------
    ChatOpenAI 实例，已配置好 API 密钥、URL、模型等。

    【学习要点】
    ChatOpenAI 是 LangChain 对 OpenAI 兼容 API 的封装。
    虽然名字叫"OpenAI"，但通过设置 base_url 和 api_key，
    可以连接任何 OpenAI 兼容的 API（如 DeepSeek、智谱等）。
    这就是"接口兼容"的威力——同一套代码适配多个模型供应商。
    """
    return ChatOpenAI(
        model=model or llm_config.model,
        api_key=llm_config.api_key,
        base_url=llm_config.base_url,
        temperature=temperature if temperature is not None else llm_config.temperature,
        # 禁用流式输出，我们需要完整的响应来解析 JSON
        streaming=False,
        # 传入回调处理器（用于 LangFuse 追踪等）
        callbacks=callbacks,
    )
