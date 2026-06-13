"""
属相（Chinese Zodiac）和星座（Western Zodiac）计算工具。
根据生日自动计算，无需外部 API。
"""
from datetime import date


CHINESE_ZODIAC = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]

WESTERN_ZODIAC = [
    (1, 20, "摩羯座"),
    (2, 19, "水瓶座"),
    (3, 21, "双鱼座"),
    (4, 20, "白羊座"),
    (5, 21, "金牛座"),
    (6, 21, "双子座"),
    (7, 23, "巨蟹座"),
    (8, 23, "狮子座"),
    (9, 23, "处女座"),
    (10, 23, "天秤座"),
    (11, 22, "天蝎座"),
    (12, 22, "射手座"),
    (12, 31, "摩羯座"),
]


def get_chinese_zodiac(birth_date: date) -> str:
    """计算属相（以1900年为庚子鼠年基准）"""
    base_year = 1900  # 庚子鼠年
    offset = (birth_date.year - base_year) % 12
    return CHINESE_ZODIAC[offset]


def get_zodiac_sign(birth_date: date) -> str:
    """计算西方星座"""
    month = birth_date.month
    day = birth_date.day
    for end_month, end_day, sign in WESTERN_ZODIAC:
        if month < end_month or (month == end_month and day <= end_day):
            return sign
    return "摩羯座"


def update_zodiac_fields(user, birth_date: date) -> None:
    """在更新 birth_date 时同步写入 zodiac_sign 和 chinese_zodiac"""
    user.birth_date = birth_date
    user.zodiac_sign = get_zodiac_sign(birth_date)
    user.chinese_zodiac = get_chinese_zodiac(birth_date)
    today = date.today()
    user.age = (
        today.year - birth_date.year
        - ((today.month, today.day) < (birth_date.month, birth_date.day))
    )
