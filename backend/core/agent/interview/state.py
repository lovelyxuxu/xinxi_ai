"""
心犀AI - 用户访谈 Subgraph 状态定义
===================================
定义访谈 Agent 在多轮对话中维护的状态。
"""

from typing import TypedDict, Annotated, List, Optional
from operator import add
from langchain_core.messages import BaseMessage
from core.models.user_profile import UserProfile


class InterviewState(TypedDict):
    """
    用户访谈状态
    ------------
    """
    # 消息列表（Annotated[..., add] 表示新消息会追加到列表中，而不是替换）
    messages: Annotated[List[BaseMessage], add]
    
    # 当前正在完善的用户画像草稿
    draft_profile: UserProfile
    
    # 还需要补充的字段列表
    missing_fields: List[str]
    
    # 是否完成访谈
    is_complete: bool
    
    # 用户ID
    user_id: str
