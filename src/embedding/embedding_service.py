"""
心犀AI - Embedding 服务
========================
将文本转换为高维向量，是语义检索的核心组件。

学习要点：
---------
- Embedding 本质上是一个"文本→数字向量"的映射
- 语义相近的文本，其向量在空间中的距离更近
- 常用距离度量：余弦相似度（Cosine Similarity）

本项目使用硅基流动的 BAAI/bge-m3 模型：
  - 免费调用，无需本地部署
  - 中文语义理解能力强，非常适合婚恋场景
  - 输出 1024 维向量
  - 兼容 OpenAI API 协议，用 langchain_openai 即可调用
"""

from typing import Optional
from langchain_openai import OpenAIEmbeddings
from config.settings import embedding_config


class EmbeddingService:
    """
    Embedding 服务封装类
    --------------------
    统一使用 OpenAI 兼容协议调用远程 Embedding API。
    """

    def __init__(self):
        """
        初始化 Embedding 模型。
        使用硅基流动的 bge-m3，通过 OpenAI 兼容接口调用。
        """
        self._model: Optional[OpenAIEmbeddings] = None
        self._init_model()

    def _init_model(self):
        """
        初始化 OpenAI 兼容的 Embedding 客户端。
        硅基流动的 API 兼容 OpenAI 协议，只需替换 base_url 和 api_key。

        注意：不传 dimensions 参数，因为硅基流动不支持这个 OpenAI 专有参数。
        bge-m3 模型固定输出 1024 维向量，无需手动指定。
        """
        self._model = OpenAIEmbeddings(
            model=embedding_config.model,
            openai_api_key=embedding_config.api_key,
            openai_api_base=embedding_config.base_url,
            # 不传 dimensions —— 硅基流动不支持，bge-m3 固定 1024 维
        )

    def embed_text(self, text: str) -> list[float]:
        """
        将单段文本转换为向量。

        参数:
            text: 要转换的文本
        返回:
            一个浮点数列表，即文本的向量表示（1024 维）

        示例:
            >>> service = EmbeddingService()
            >>> vector = service.embed_text("喜欢安静的周末")
            >>> len(vector)
            1024
        """
        return self._model.embed_query(text)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        批量将多段文本转换为向量。
        批量处理比逐条调用更高效（减少了网络请求次数）。

        参数:
            texts: 文本列表
        返回:
            向量列表，每个向量对应一段输入文本
        """
        return self._model.embed_documents(texts)

    def get_langchain_embeddings(self):
        """
        返回 LangChain 兼容的 Embeddings 对象。
        Chroma 等向量数据库需要直接接收这个对象来自动处理向量化。
        """
        return self._model
