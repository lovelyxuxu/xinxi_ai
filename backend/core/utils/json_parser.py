"""
心犀AI - JSON 解析工具模块
============================

【学习要点】
这个模块解决了 LLM 应用中的一个常见问题：
LLM 返回的不是"纯净的 JSON"，而是在 JSON 前后加了说明文字。

例如 DeepSeek 的"深度思考"模式，输出可能是：

    让我来分析一下这个用户...
    ```json
    {"name": "Alice", "age": 25}
    ```
    以上就是我的分析结果。

我们需要从这段文本中精准提取出 JSON 对象。

三种提取策略（按优先级）
-------------------------
1. **代码块提取**：找 ```json ... ``` 包裹的内容（最可靠）
2. **花括号提取**：找最外层 { ... } 匹配（处理无代码块的情况）
3. **方括号提取**：找最外层 [ ... ] 匹配（处理返回数组的情况）

为什么不用 LLM 的 function calling / tool_use？
-------------------------------------------------
因为 DeepSeek V4 Flash 的"深度思考"模式不支持 function calling。
所以我们只能让 LLM 输出文本，然后自己解析 JSON。
这就是 _parse_json_response() 存在的原因。

如果以后换成支持 function calling 的模型，
可以用 `llm.with_structured_output(PydanticModel)` 替代手动解析。
"""

import json
import re
from typing import TypeVar, Type
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI


# TypeVar 是 TypeScript 泛型的 Python 等价物
# T 绑定到 BaseModel 的子类，确保 invoke_structured 返回正确的 Pydantic 模型类型
T = TypeVar('T', bound=BaseModel)


def parse_json_response(text: str) -> dict | list:
    """
    从 LLM 文本响应中提取 JSON。

    参数
    ----
    text : str
        LLM 返回的完整文本（可能包含非 JSON 内容）

    返回值
    ------
    解析后的 Python dict 或 list

    异常
    ----
    ValueError : 如果三种策略都无法提取有效 JSON

    【学习要点 — 多策略解析】
    这是一个"防御性编程"的例子：
    不信任 LLM 的输出格式，而是准备多种解析策略。
    在生产环境中，LLM 的输出格式经常会变化，
    多策略解析可以大大提高系统的鲁棒性。
    """

    # 策略 1：提取 ```json ... ``` 代码块中的内容
    # 这是最可靠的方式，因为 LLM 通常会把 JSON 放在代码块中
    code_block = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if code_block:
        try:
            return json.loads(code_block.group(1).strip())
        except json.JSONDecodeError:
            pass  # 代码块内容不是有效 JSON，尝试下一个策略

    # 策略 2：找最外层 { ... } 匹配
    # 适用于 LLM 直接输出 JSON 但没有代码块的情况
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # 策略 3：找最外层 [ ... ] 匹配
    # 适用于 LLM 返回 JSON 数组的情况
    # 注意：之前的 interview/nodes.py 缺少这个策略，现在统一补齐
    array_match = re.search(r'\[[\s\S]*\]', text)
    if array_match:
        try:
            return json.loads(array_match.group(0))
        except json.JSONDecodeError:
            pass

    # 三种策略都失败了
    raise ValueError(
        f"无法从 LLM 响应中提取有效 JSON。\n"
        f"原始文本前200字符: {text[:200]}"
    )


# 追加到 LLM prompt 末尾的 JSON 格式指令
# 告诉 LLM 必须返回 JSON，并给出期望的 schema
JSON_SUFFIX = """

请严格按照以下 JSON Schema 返回结果，不要添加任何额外说明文字：
{json_schema}

将 JSON 放在 ```json ``` 代码块中返回。"""


def invoke_structured(
    llm: ChatOpenAI,
    prompt_messages,
    model_class: Type[T],
) -> T:
    """
    调用 LLM 并将响应解析为 Pydantic 模型。

    这是一个"高级封装"函数，组合了：
    1. 调用 LLM（传入已构建好的 prompt_messages）
    2. 解析 JSON（使用多策略解析）
    3. Pydantic 验证（确保数据结构正确）

    参数
    ----
    llm : ChatOpenAI
        LLM 实例（由 create_ll() 创建）
    prompt_messages : list
        已构建好的 LangChain 消息列表。
        通常由 ChatPromptTemplate.invoke() 返回。
        调用方负责在 prompt 中包含 JSON 格式要求。
    model_class : Type[T]
        Pydantic 模型类，用于验证 LLM 的输出

    返回值
    ------
    经过 Pydantic 验证的模型实例

    【学习要点 — 为什么要用 Pydantic 验证？】
    LLM 的输出可能不符合预期（漏字段、类型错误等）。
    Pydantic 验证可以在运行时捕获这些问题：
    - 缺少必填字段 → ValidationError
    - 类型不匹配（如字符串而非数字）→ ValidationError
    - 值超出范围 → ValidationError

    这比手动检查 dict 的 key 和 value 类型安全得多。
    """
    # 调用 LLM 获取自由文本回复
    response = llm.invoke(prompt_messages)

    # 从回复中提取 JSON（兼容 DeepSeek thinking 模式）
    parsed = parse_json_response(response.content)

    # 用 Pydantic 验证并构造模型实例
    return model_class.model_validate(parsed)
