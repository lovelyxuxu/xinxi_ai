"""
心犀AI - 模拟数据集
====================
为了让项目能快速跑起来，这里预置了一批虚拟用户数据。
每个用户都有丰富的文本描述，方便测试语义匹配的效果。

使用方式：
    python -m data.mock_data    # 直接运行，将数据写入 Chroma
"""

from core.models.user_profile import UserProfile

# ============================================================
# 模拟用户数据 - 12 位虚拟用户（6男6女）
# 覆盖不同年龄、城市、性格和兴趣爱好，方便测试匹配效果
# ============================================================

MOCK_USERS: list[UserProfile] = [
    # -------- 女性用户 --------
    UserProfile(
        user_id="F001",
        nickname="小晴",
        gender="female",
        age=26,
        city="杭州",
        province="浙江",
        education="本科",
        annual_income="15-25万",
        marital_status="未婚",
        target_gender="male",
        target_age_min=25,
        target_age_max=35,
        target_city="杭州",
        about_me="性格温柔偏内向，周末喜欢在家看书、烘焙，偶尔和朋友去咖啡馆坐坐。喜欢小动物，养了一只英短猫。不太喜欢太喧闹的场所，更享受安静的二人世界",
        ideal_partner="希望对方性格温和有耐心，不抽烟，喜欢小动物，有稳定的工作和收入。最好也喜欢阅读，周末能一起窝在家看电影",
        hobbies="阅读,烘焙,猫咪,咖啡,电影",
        mbti="INFP",
    ),
    UserProfile(
        user_id="F002",
        nickname="雨桐",
        gender="female",
        age=28,
        city="上海",
        province="上海",
        education="硕士",
        annual_income="25-40万",
        marital_status="未婚",
        target_gender="male",
        target_age_min=27,
        target_age_max=38,
        target_city="上海",
        about_me="互联网产品经理，工作中理性果断，生活中感性浪漫。热爱旅行，去过十几个国家。平时坚持健身和瑜伽，注重生活品质。也喜欢看展、听音乐会",
        ideal_partner="希望对方有见识有格局，事业上有追求但不workaholic。热爱旅行或至少愿意一起去探索世界，有幽默感，能聊得来最重要",
        hobbies="旅行,健身,瑜伽,看展,音乐会",
        mbti="ENTJ",
    ),
    UserProfile(
        user_id="F003",
        nickname="阿月",
        gender="female",
        age=24,
        city="成都",
        province="四川",
        education="大专",
        annual_income="8-15万",
        marital_status="未婚",
        target_gender="male",
        target_age_min=23,
        target_age_max=32,
        target_city="成都",
        about_me="幼儿园老师，超级喜欢小朋友。性格开朗活泼，朋友很多。周末爱出去吃吃喝喝、逛公园、拍照片。做饭手艺一般但很爱折腾，喜欢看美食博主的视频",
        ideal_partner="希望对方阳光开朗，爱笑爱闹，不要太闷。能接受我偶尔的小任性，周末能陪我到处逛吃逛吃。对小动物有爱心就更好了",
        hobbies="美食,拍照,逛公园,烹饪,手工",
        mbti="ESFP",
    ),
    UserProfile(
        user_id="F004",
        nickname="思远",
        gender="female",
        age=30,
        city="北京",
        province="北京",
        education="硕士",
        annual_income="30-50万",
        marital_status="未婚",
        target_gender="male",
        target_age_min=28,
        target_age_max=40,
        target_city="不限",
        about_me="金融行业分析师，逻辑思维强，但对生活充满热情。喜欢跑步和游泳，每年参加一次马拉松。喜欢纪录片和历史类书籍，偶尔也追剧放松。性格独立但不冷漠，相信好的关系是彼此成就",
        ideal_partner="希望对方成熟稳重，有自己的事业追求和兴趣爱好。三观正，尊重女性，沟通时能理性表达而不是冷暴力。年龄和地域不是绝对限制，聊得来最重要",
        hobbies="跑步,马拉松,游泳,纪录片,历史",
        mbti="INTJ",
    ),
    UserProfile(
        user_id="F005",
        nickname="小薇",
        gender="female",
        age=27,
        city="深圳",
        province="广东",
        education="本科",
        annual_income="20-30万",
        marital_status="未婚",
        target_gender="male",
        target_age_min=26,
        target_age_max=35,
        target_city="深圳",
        about_me="UI设计师，审美在线，家里布置得很ins风。周末喜欢画画、逛美术馆、学新技能。喜欢日料和东南亚菜，每年会去日本或泰国旅行。性格慢热但熟了之后很话痨",
        ideal_partner="希望对方有审美品味，穿着干净整洁。有创意或艺术类相关工作背景更好。性格温柔细腻，能理解我偶尔的完美主义。最好也喜欢旅行和美食",
        hobbies="绘画,美术馆,日料,旅行,摄影",
        mbti="ISFP",
    ),
    UserProfile(
        user_id="F006",
        nickname="晓晓",
        gender="female",
        age=29,
        city="杭州",
        province="浙江",
        education="本科",
        annual_income="15-25万",
        marital_status="离异",
        target_gender="male",
        target_age_min=28,
        target_age_max=40,
        target_city="杭州",
        about_me="电商运营，性格直爽不做作。经历过一段婚姻后更清楚自己想要什么。喜欢户外运动、露营、徒步。也享受宅家时煲汤做饭的烟火气。养了一只金毛犬，每天遛狗是我的日常",
        ideal_partner="希望对方真诚坦率，有责任感。不介意我的过去，看重的是未来能一起走下去。喜欢户外或者至少不排斥周末去郊外走走。有爱心、喜欢狗狗加分",
        hobbies="露营,徒步,遛狗,煲汤,户外",
        mbti="ESTP",
    ),

    # -------- 男性用户 --------
    UserProfile(
        user_id="M001",
        nickname="阿杰",
        gender="male",
        age=28,
        city="杭州",
        province="浙江",
        education="本科",
        annual_income="20-30万",
        marital_status="未婚",
        target_gender="female",
        target_age_min=23,
        target_age_max=30,
        target_city="杭州",
        about_me="软件工程师，性格偏内向但熟了很健谈。平时喜欢看书（科幻和推理小说居多）、打游戏、偶尔写写博客。养了一只布偶猫，周末喜欢在家撸猫编程。不抽烟不喝酒，生活简单规律",
        ideal_partner="希望对方温柔善良，性格安静一些，喜欢小动物。不需要太外向，能享受安静的二人世界就好。如果在杭州就更好了，同城方便见面",
        hobbies="编程,阅读,游戏,猫咪,博客",
        mbti="INTP",
    ),
    UserProfile(
        user_id="M002",
        nickname="浩然",
        gender="male",
        age=32,
        city="上海",
        province="上海",
        education="硕士",
        annual_income="40-60万",
        marital_status="未婚",
        target_gender="female",
        target_age_min=25,
        target_age_max=33,
        target_city="上海",
        about_me="金融投行从业者，工作节奏快但懂得享受生活。热爱旅行和摄影，去过欧洲、东南亚、南美。坚持健身，喜欢打网球。平时也爱看经济学和哲学方面的书，喜欢有深度的对话",
        ideal_partner="希望对方聪明独立，有自己的事业和追求。热爱旅行或愿意一起探索世界。有内涵、能聊深度话题的女生最吸引我。外在干净大方就好",
        hobbies="旅行,摄影,健身,网球,阅读",
        mbti="ENTP",
    ),
    UserProfile(
        user_id="M003",
        nickname="小宇",
        gender="male",
        age=25,
        city="成都",
        province="四川",
        education="本科",
        annual_income="10-20万",
        marital_status="未婚",
        target_gender="female",
        target_age_min=22,
        target_age_max=28,
        target_city="成都",
        about_me="自由摄影师，时间自由但不太稳定。性格很阳光，朋友评价我是'气氛担当'。喜欢美食（尤其是川菜和火锅）、旅行拍照、弹吉他。生活态度比较随性，享受当下",
        ideal_partner="希望对方活泼开朗，爱笑，不要太拘束。能接受我不太规律的工作时间，愿意和我一起到处走走拍拍。如果在成都就太棒了，一起吃遍成都",
        hobbies="摄影,美食,旅行,吉他,火锅",
        mbti="ENFP",
    ),
    UserProfile(
        user_id="M004",
        nickname="文博",
        gender="male",
        age=30,
        city="北京",
        province="北京",
        education="博士",
        annual_income="25-40万",
        marital_status="未婚",
        target_gender="female",
        target_age_min=26,
        target_age_max=35,
        target_city="不限",
        about_me="高校讲师，教计算机科学。性格沉稳内敛，但不无聊——朋友说我冷幽默很强。喜欢看纪录片、下围棋、爬山。做饭水平不错，拿手菜是红烧肉和糖醋排骨。追求精神层面的契合",
        ideal_partner="希望对方有独立思考能力，对世界有好奇心。学历不限但希望爱学习、爱思考。性格温和，能接受偶尔的学术宅生活。会做饭或愿意一起做饭就完美了",
        hobbies="围棋,爬山,纪录片,烹饪,编程",
        mbti="INFJ",
    ),
    UserProfile(
        user_id="M005",
        nickname="子轩",
        gender="male",
        age=27,
        city="深圳",
        province="广东",
        education="本科",
        annual_income="25-35万",
        marital_status="未婚",
        target_gender="female",
        target_age_min=24,
        target_age_max=30,
        target_city="深圳",
        about_me="游戏公司原画师，审美和创意在线。喜欢画画、逛展、收集手办。性格偏宅但不闷，朋友聚会也玩得很嗨。养了一只柯基犬，经常带狗去公园。喜欢日料和粤菜，偶尔自己做寿司",
        ideal_partner="希望对方有艺术气质或审美品味，穿着打扮有自己的风格。性格温柔细腻，能理解宅文化。喜欢小动物（特别是狗）加分，能一起遛狗就更好了",
        hobbies="绘画,手办,看展,遛狗,日料",
        mbti="INFP",
    ),
    UserProfile(
        user_id="M006",
        nickname="大伟",
        gender="male",
        age=33,
        city="杭州",
        province="浙江",
        education="本科",
        annual_income="30-50万",
        marital_status="离异",
        target_gender="female",
        target_age_min=25,
        target_age_max=38,
        target_city="杭州",
        about_me="创业公司CEO，经历过一次婚姻失败后更加成熟。热爱户外运动，每周骑行或跑步。喜欢做饭和品酒，周末偶尔去周边短途旅行。性格直率坦诚，重视真诚的关系",
        ideal_partner="希望对方成熟理性，有自己的生活重心。不介意离异，重要的是两个人三观合、能坦诚沟通。喜欢运动或户外的女生很加分，能一起跑步骑行就太棒了",
        hobbies="骑行,跑步,烹饪,品酒,旅行",
        mbti="ESTJ",
    ),
]


def get_mock_users() -> list[UserProfile]:
    """获取所有模拟用户数据"""
    return MOCK_USERS


def get_mock_user_by_id(user_id: str) -> UserProfile | None:
    """根据 user_id 获取指定用户"""
    for user in MOCK_USERS:
        if user.user_id == user_id:
            return user
    return None


# 直接运行此文件时，打印所有用户信息（方便调试）
if __name__ == "__main__":
    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(title="心犀AI - 模拟用户数据", show_lines=True)

    table.add_column("ID", style="cyan", width=6)
    table.add_column("昵称", style="magenta", width=8)
    table.add_column("性别", width=6)
    table.add_column("年龄", width=6)
    table.add_column("城市", width=8)
    table.add_column("MBTI", width=6)
    table.add_column("关于我", width=40)

    for user in MOCK_USERS:
        table.add_row(
            user.user_id,
            user.nickname,
            user.gender,
            str(user.age),
            user.city,
            user.mbti,
            user.about_me[:40] + "...",
        )

    console.print(table)
