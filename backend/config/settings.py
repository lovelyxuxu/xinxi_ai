"""
心犀AI - 配置管理模块
=====================
集中管理所有配置项，从 .env 文件和环境变量中读取配置。

架构说明：
  - LLM（对话/推理）: 使用 DeepSeek V4 Flash API
  - Embedding（文本向量化）: 使用硅基流动的免费 bge-m3 模型
  - 两者都兼容 OpenAI API 协议，所以代码中可以统一用 langchain_openai 调用
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载项目根目录下的 .env 文件
# Path(__file__) 是当前文件(config/settings.py)，往上两级就是项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class LLMConfig:
    """DeepSeek LLM 配置"""
    api_key: str = os.getenv("DEEPSEEK_API_KEY", "sk-placeholder")
    base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    model: str = os.getenv("LLM_MODEL", "deepseek-v4-flash")
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))


class EmbeddingConfig:
    """硅基流动 Embedding 配置（bge-m3 模型，免费且中文效果好）"""
    api_key: str = os.getenv("SILICONFLOW_API_KEY", "sk-placeholder")
    base_url: str = os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
    model: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "1024"))


class ChromaConfig:
    """Chroma 向量数据库配置"""
    persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", str(PROJECT_ROOT / "chroma_db"))
    collection_name: str = os.getenv("CHROMA_COLLECTION_NAME", "xinxi_users")


class MatchConfig:
    """匹配系统参数"""
    max_candidates: int = int(os.getenv("MAX_RETRIEVAL_CANDIDATES", "10"))
    max_top_matches: int = int(os.getenv("MAX_TOP_MATCHES", "3"))
    match_threshold: float = float(os.getenv("MATCH_THRESHOLD_SCORE", "0.6"))
    max_agent_loops: int = int(os.getenv("MAX_AGENT_LOOPS", "3"))


class SupervisorConfig:
    """
    Supervisor 多 Agent 架构配置

    学习要点：
    - USE_SUPERVISOR: True 使用新的 Supervisor 多 Agent 图，False 使用旧版单 Agent 图
    - ROUTER_MODE: "rule" 使用规则版路由（稳定），"llm" 使用 LLM 版路由（灵活）
    - 通过环境变量可以热切换，方便对比学习两种架构的差异
    """
    use_supervisor: bool = os.environ.get("USE_SUPERVISOR", "true").lower() == "true"
    router_mode: str = os.environ.get("SUPERVISOR_ROUTER", "rule")


class LangFuseConfig:
    """
    LangFuse 可观测性配置（Phase 3 使用）

    学习要点：
    - LangFuse 是开源的 LLM 可观测性平台，可以追踪每次 LLM 调用
    - 通过 LangChain 的 Callback 机制集成，无需修改业务代码
    - enabled 设为 True 后，所有 LLM 调用会自动上报到 LangFuse Dashboard
    """
    enabled: bool = os.environ.get("LANGFUSE_ENABLED", "false").lower() == "true"
    public_key: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    secret_key: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    host: str = os.getenv("LANGFUSE_HOST", "http://localhost:3000")


# 统一导出所有配置，方便其他模块引用
llm_config = LLMConfig()
embedding_config = EmbeddingConfig()
chroma_config = ChromaConfig()
match_config = MatchConfig()
supervisor_config = SupervisorConfig()
langfuse_config = LangFuseConfig()
