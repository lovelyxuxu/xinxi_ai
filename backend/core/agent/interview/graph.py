"""
心犀AI - 用户访谈 Subgraph 工作流编排
=======================================
使用 LangGraph 将访谈节点串联成状态机。
"""

from langgraph.graph import StateGraph, START, END
from core.agent.interview.state import InterviewState
from core.agent.interview.nodes import generate_question, parse_answer


def build_interview_graph(checkpointer=None):
    """
    构建用户访谈子图。
    
    设计模式：
    - 入口 -> parse_answer (解析用户最新回复)
    - parse_answer -> generate_question (生成下一个问题)
    - generate_question -> END (返回给用户，等待下一次回复)
    """
    
    graph = StateGraph(InterviewState)
    
    # 添加节点
    graph.add_node("parse_answer", parse_answer)
    graph.add_node("generate_question", generate_question)
    
    # 定义边
    graph.add_edge(START, "parse_answer")
    graph.add_edge("parse_answer", "generate_question")
    
    # 如果访谈已完成，可以在这里加条件边，或者在业务层判断
    # 为了简单，我们让 generate_question 总是在最后执行，
    # 如果 is_complete 为 True，generate_question 可以输出结束语。
    graph.add_edge("generate_question", END)
    
    # 编译图（必须带 checkpointer 才能多轮对话）
    app = graph.compile(checkpointer=checkpointer)
    
    return app
