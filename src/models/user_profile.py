"""
心犀AI - 用户画像数据模型
==========================
使用 Pydantic 定义用户的数据结构。
每个用户包含两类数据：
  1. 元数据（Metadata）：用于硬性过滤的结构化字段（性别、年龄、城市等）
  2. 文本描述（Profile Text）：用于生成向量、做语义匹配的软性字段
"""

from pydantic import BaseModel, Field
from typing import Optional


class UserProfile(BaseModel):
    """
    用户画像模型
    -------------
    这是系统中最核心的数据结构，每个用户在数据库中存储一条记录。
    """
    # === 基础标识 ===
    user_id: str = Field(description="用户唯一标识")
    nickname: str = Field(description="用户昵称")

    # === 元数据字段（用于 SQL/硬性过滤）===
    gender: str = Field(description="性别: male / female")
    age: int = Field(description="年龄")
    city: str = Field(description="所在城市")
    province: str = Field(description="所在省份")
    education: str = Field(description="学历: 高中/大专/本科/硕士/博士")
    annual_income: str = Field(default="未填写", description="年收入范围，如 '10-20万'")
    marital_status: str = Field(default="未婚", description="婚姻状况: 未婚/离异")

    # === 择偶硬性要求（元数据过滤用）===
    target_gender: str = Field(description="期望对方性别: male / female")
    target_age_min: int = Field(default=18, description="期望对方最小年龄")
    target_age_max: int = Field(default=45, description="期望对方最大年龄")
    target_city: str = Field(default="不限", description="期望对方城市，'不限'表示无要求")

    # === 文本描述字段（用于生成 Embedding 向量，做软性语义匹配）===
    about_me: str = Field(description="关于我：性格、兴趣、生活方式的自由描述")
    ideal_partner: str = Field(description="理想的Ta：对另一半的期望描述")

    # === 可选字段 ===
    hobbies: str = Field(default="", description="兴趣爱好，逗号分隔")
    mbti: str = Field(default="未知", description="MBTI 性格类型")

    def get_profile_text(self) -> str:
        """
        将所有软性文本拼接为一段完整的描述，用于生成 Embedding 向量。
        这是向量检索的核心输入——把用户的性格、兴趣、择偶期望
        融合成一段文字，Embedding 后会捕捉其中的语义信息。
        """
        parts = [
            f"关于我：{self.about_me}",
            f"理想的另一半：{self.ideal_partner}",
        ]
        if self.hobbies:
            parts.append(f"兴趣爱好：{self.hobbies}")
        if self.mbti and self.mbti != "未知":
            parts.append(f"性格类型：{self.mbti}")
        return "。".join(parts)

    def get_metadata(self) -> dict:
        """
        提取元数据字段，返回一个字典。
        这些字段会存入 Chroma 的 metadata 中，用于硬性条件过滤。
        """
        return {
            "user_id": self.user_id,
            "nickname": self.nickname,
            "gender": self.gender,
            "age": self.age,
            "city": self.city,
            "province": self.province,
            "education": self.education,
            "annual_income": self.annual_income,
            "marital_status": self.marital_status,
            "target_gender": self.target_gender,
            "target_age_min": self.target_age_min,
            "target_age_max": self.target_age_max,
            "target_city": self.target_city,
            "hobbies": self.hobbies,
            "mbti": self.mbti,
        }
