"""
种子数据脚本 - 创建20位完整资料的测试用户。
运行: python scripts/seed_users.py（在 backend/ 目录下执行）

统一密码: Test@123456
"""
import asyncio
import sys
import os
import secrets
import string

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
import bcrypt as _bcrypt
from sqlalchemy import select
from core.database.session import AsyncSessionLocal
from core.database.models import User
from core.utils.zodiac import get_zodiac_sign, get_chinese_zodiac

DEFAULT_PASSWORD = "Test@123456"


def _hash_password(plain: str) -> str:
    """直接用 bcrypt 加密，绕过 passlib 版本兼容问题。"""
    return _bcrypt.hashpw(plain.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")

# (nickname, gender, phone, age, birth_date, city, province, education,
#  annual_income, mbti, height_cm, about_me, ideal_partner, hobbies,
#  target_gender, target_age_min, target_age_max)
USERS_DATA = [
    ("林晓雨", "女", "13800000001", 26, date(1998, 3, 15), "上海", "上海",
     "本科", "15-25万", "INFJ", 163,
     "喜欢读书和爬山，在互联网公司做产品经理。性格温柔但有自己的坚持。",
     "希望他有上进心，爱生活，最好能一起旅行。",
     "阅读 爬山 摄影 美食探店", "男", 26, 35),

    ("陈浩然", "男", "13800000002", 29, date(1995, 7, 22), "上海", "上海",
     "硕士", "25-40万", "ENTJ", 178,
     "金融行业，喜欢健身和投资。周末会去骑行，追求高效的生活方式。",
     "独立自主，有自己的事业和想法，不依赖男方。",
     "健身 骑行 投资 看纪录片", "女", 24, 32),

    ("张美琳", "女", "13800000003", 24, date(2000, 11, 5), "北京", "北京",
     "本科", "8-15万", "ENFP", 158,
     "刚参加工作的设计师，充满活力，喜欢画画和看展。生活里充满色彩。",
     "温柔体贴，有安全感，包容我的小情绪。",
     "绘画 看展 街拍 咖啡 音乐", "男", 24, 32),

    ("王子豪", "男", "13800000004", 31, date(1993, 1, 18), "北京", "北京",
     "本科", "15-25万", "ISTJ", 175,
     "程序员，喜欢打篮球和玩游戏。性格稳重，对感情认真专一。",
     "善良真诚，不在乎外表，在乎内心。",
     "篮球 编程 游戏 做饭", "女", 23, 30),

    ("刘思远", "女", "13800000005", 27, date(1997, 5, 30), "广州", "广东",
     "本科", "15-25万", "ISFJ", 160,
     "小学教师，喜欢种植和烘焙。生活平静温暖，享受当下。",
     "顾家，有责任心，最好爱孩子。",
     "烘焙 种植 瑜伽 读书", "男", 27, 36),

    ("赵明宇", "男", "13800000006", 33, date(1991, 9, 12), "广州", "广东",
     "硕士", "40万以上", "INTJ", 182,
     "创业公司CEO，工作忙但重视感情。喜欢马拉松和冥想。",
     "有自己想法，不随波逐流，能接受我经常出差。",
     "马拉松 冥想 商业读物 旅行", "女", 25, 35),

    ("孙雨桐", "女", "13800000007", 25, date(1999, 2, 14), "成都", "四川",
     "本科", "8-15万", "ESFP", 162,
     "市场运营，四川人超爱吃辣！喜欢逛街和追剧。活泼开朗。",
     "幽默风趣，不沉闷，最好也爱吃。",
     "美食 逛街 追剧 打卡新店", "男", 25, 33),

    ("李建国", "男", "13800000008", 28, date(1996, 4, 8), "成都", "四川",
     "大专", "8-15万", "ESFJ", 173,
     "厨师，做得一手好川菜。性格豪爽，朋友多。",
     "真实不做作，能接受我不规律的工作时间。",
     "做饭 打牌 钓鱼 看球", "女", 22, 30),

    ("吴静怡", "女", "13800000009", 30, date(1994, 8, 19), "杭州", "浙江",
     "硕士", "15-25万", "INTP", 165,
     "数据分析师，理性逻辑强，但内心温柔。喜欢一个人旅行。",
     "尊重个人空间，有共同话题，不无聊。",
     "一人旅行 冥想 科幻小说 养猫", "男", 28, 38),

    ("周大伟", "男", "13800000010", 35, date(1989, 12, 25), "杭州", "浙江",
     "本科", "25-40万", "ENTP", 180,
     "律师，能说会道，喜欢辩论和下棋。希望找到灵魂伴侣。",
     "聪明有趣，有自己的见解，不依附于人。",
     "辩论 下棋 红酒 历史", "女", 26, 36),

    ("郑小燕", "女", "13800000011", 22, date(2002, 6, 20), "上海", "上海",
     "本科", "8万以下", "ENFJ", 156,
     "大学应届生，主修心理学，喜欢倾听和帮助他人。",
     "成熟稳重，给我引导和安全感。",
     "心理学 公益 瑜伽 写日记", "男", 24, 32),

    ("黄志强", "男", "13800000012", 27, date(1997, 10, 3), "北京", "北京",
     "硕士", "15-25万", "INFP", 176,
     "公务员，稳定有保障。平时喜欢写作和看电影。",
     "善解人意，不爱争吵，一起安安静静过日子。",
     "写作 电影 慢跑 烹饪", "女", 23, 30),

    ("徐梦洁", "女", "13800000013", 29, date(1995, 3, 28), "广州", "广东",
     "本科", "15-25万", "ESTP", 168,
     "销售总监，雷厉风行，有激情。喜欢极限运动和派对。",
     "有担当，不软弱，敢于拼搏的男生。",
     "极限运动 派对 买买买 网球", "男", 28, 38),

    ("马天宇", "男", "13800000014", 32, date(1992, 7, 15), "成都", "四川",
     "本科", "15-25万", "ISFP", 174,
     "自由摄影师，走遍中国。安静内敛，镜头后面是另一个世界。",
     "欣赏艺术，包容我的漂泊，有自己的生活。",
     "摄影 旅行 咖啡 人文纪录片", "女", 24, 34),

    ("高丽娜", "女", "13800000015", 26, date(1998, 1, 7), "杭州", "浙江",
     "硕士", "15-25万", "ESTJ", 161,
     "医生，工作认真负责。下班爱看综艺减压，人很接地气。",
     "理解医生工作的辛苦，有耐心，爱家庭。",
     "综艺 美食 健身 睡觉", "男", 27, 36),

    ("蒋俊凯", "男", "13800000016", 24, date(2000, 9, 9), "上海", "上海",
     "本科", "8-15万", "ENFP", 179,
     "短视频博主，有几十万粉。热爱生活，每天都很充实。",
     "支持我的工作，活泼有趣，不无聊。",
     "短视频 街舞 旅行 剧本杀", "女", 22, 28),

    ("韩冰清", "女", "13800000017", 31, date(1993, 5, 16), "北京", "北京",
     "硕士", "25-40万", "INTJ", 167,
     "大学讲师，研究方向AI。理性冷静，有点高冷，熟了很暖。",
     "智识对等，能聊学术也能聊生活，尊重边界。",
     "AI研究 古典音乐 阅读 茶道", "男", 30, 40),

    ("曹宇轩", "男", "13800000018", 26, date(1998, 2, 22), "广州", "广东",
     "本科", "8-15万", "ESFP", 177,
     "健身教练，体型好看，阳光开朗。喜欢带人运动。",
     "阳光健康，积极向上，最好也喜欢运动。",
     "健身 篮球 冲浪 烤肉", "女", 22, 30),

    ("宋欣然", "女", "13800000019", 28, date(1996, 11, 11), "成都", "四川",
     "本科", "15-25万", "INFP", 159,
     "插画师，工作在家，自由度高。喜欢猫和一切毛茸茸的东西。",
     "温柔体贴，能接受猫，不排斥宅。",
     "画画 养猫 刷剧 逛花市", "男", 26, 35),

    ("冯天浩", "男", "13800000020", 36, date(1988, 4, 4), "杭州", "浙江",
     "本科", "25-40万", "ISTP", 181,
     "建筑设计师，有自己的工作室。沉默寡言，但设计作品很有温度。",
     "独立自主，不黏人，欣赏美的事物。",
     "建筑设计 木工 登山 清酒", "女", 26, 36),
]


def _gen_uid() -> str:
    uid_chars = string.ascii_uppercase + string.digits
    return "U" + "".join(secrets.choice(uid_chars) for _ in range(8))


async def seed():
    async with AsyncSessionLocal() as session:
        created = 0
        for row in USERS_DATA:
            (nickname, gender, phone, age, birth_date, city, province,
             education, annual_income, mbti, height_cm, about_me,
             ideal_partner, hobbies, target_gender,
             target_age_min, target_age_max) = row

            existing = await session.execute(select(User).where(User.phone == phone))
            if existing.scalar_one_or_none():
                print(f"  跳过已存在: {nickname} ({phone})")
                continue

            zodiac = get_zodiac_sign(birth_date)
            chinese_z = get_chinese_zodiac(birth_date)

            user = User(
                user_id=_gen_uid(),
                nickname=nickname,
                gender=gender,
                phone=phone,
                password_hash=_hash_password(DEFAULT_PASSWORD),
                age=age,
                birth_date=birth_date,
                zodiac_sign=zodiac,
                chinese_zodiac=chinese_z,
                city=city,
                province=province,
                education=education,
                annual_income=annual_income,
                marital_status="未婚",
                mbti=mbti,
                height_cm=height_cm,
                about_me=about_me,
                ideal_partner=ideal_partner,
                hobbies=hobbies,
                target_gender=target_gender,
                target_age_min=target_age_min,
                target_age_max=target_age_max,
                target_city="不限",
                profile_complete=True,
                photos=[],
            )
            session.add(user)
            created += 1
            print(f"  [+] {nickname} | {zodiac} {chinese_z} | {gender} {age}岁 | {city}")

        await session.commit()
        print(f"\n完成！新增 {created} 位用户，统一密码: {DEFAULT_PASSWORD}")


if __name__ == "__main__":
    import selectors
    # Windows 默认使用 ProactorEventLoop，不兼容 psycopg async，强制换为 SelectorEventLoop
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(seed())
    finally:
        loop.close()
