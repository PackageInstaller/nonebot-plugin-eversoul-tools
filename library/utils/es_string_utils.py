import os
import re
import ast
import asyncio
from nonebot.log import logger
from difflib import get_close_matches


async def select_text_by_priority(
    zh_tw: str,
    zh_cn: str,
    kr: str,
    ja: str = "",
    server: str = "global",
    data_type: str = "live",
) -> str:
    """
    根据服务器和数据类型选择文本

    选择逻辑：
    - cn (国服) -> zh_cn (简体中文)
    - jp (日服) -> ja (日文)
    - global + review -> kr (韩文)
    - global + live -> zh_tw (繁体中文)

    Args:
        zh_tw: 繁体中文文本
        zh_cn: 简体中文文本
        kr: 韩文文本
        ja: 日文文本
        server: 服务器类型 (global/cn/jp)
        data_type: 数据类型 (live/review)

    Returns:
        str: 选择的文本
    """
    if server == "cn":
        # 国服使用简体中文
        return zh_cn
    elif server == "jp":
        # 日服使用日文
        return ja
    elif server == "global":
        # 国际服根据数据类型选择
        if data_type == "review":
            return kr
        else:  # live
            return zh_tw
    else:
        # 默认返回繁体中文
        return zh_tw


async def clean_rich_text(text: str) -> str:
    """
    清理富文本标签
    Args:
        text: 包含富文本标签的输入字符串
    Returns:
        清理后的字符串
    """
    pattern = r'</?color\s*(?:=\s*"?#?[A-Fa-f0-9]+"?\s*)?>|<effect:none>'

    return re.sub(pattern, "", text, flags=re.IGNORECASE)


async def concat_color_text(
    buff_type: int,
    value: float,
    type: str,
    integer: bool = True,
    use_color_text: bool = False,
) -> str:  # pyright: ignore[reportReturnType]
    """
    拼接颜色文本
    Args:
        buff_type: buff effect 类型
        value: 数值
        type: 类型，buff或者code
        integer: 是否为整数
        use_color_text: 是否使用颜色文本
    Returns:
        str: 拼接后的字符串
    """
    if type == "buff":
        if use_color_text:
            color_code = await get_buff_value_color_text(buff_type, value)
            if color_code:
                return (
                    f"<color={color_code}>{await format_value(value, integer)}</color>"
                )
            else:
                return await format_value(value, integer)
        else:
            return await format_value(value, integer)
    elif type == "code":
        if use_color_text:
            color_code = await get_code_value_color_text(buff_type)
            if color_code:
                return (
                    f"<color={color_code}>{await format_value(value, integer)}</color>"
                )
            else:
                return await format_value(value, integer)
        else:
            return await format_value(value, integer)


async def format_value(
    value: float,
    integer: bool,
    no_percent_sign: bool = False,
    percent_multiplier: float = 100.0,
) -> str:
    """
    格式化数值
    Args:
        value: 数值
        integer: 是否为整数
        no_percent_sign: 是否不添加%符号（默认为False，即添加%符号）
        percent_multiplier: 百分比乘数（默认为100.0）
    Returns:
        str: 格式化后的字符串
    """
    abs_value = abs(value)
    if integer:
        formatted_str = f"{abs_value:.2f}".rstrip("0").rstrip(".")
        return formatted_str
    else:
        percent_value = abs_value * percent_multiplier
        formatted_str = f"{percent_value:.2f}".rstrip("0").rstrip(".")
        if no_percent_sign:
            return formatted_str
        else:
            return f"{formatted_str}%"


async def get_character_skill_description(
    data, no: int, type: str, use_color_text: bool = False
) -> str:
    """
    获取角色技能值
    Args:
        data: json 数据
        value_id: 技能值编号
        value_type: 技能值类型

    Returns:
        str: 格式化后的技能描述
    """

    skill_code = next(
        (code for code in data["skill_code"]["json"] if code["no"] == no), None
    )
    if skill_code is None:
        return ""

    function_key = skill_code.get("function_key", 0)

    if function_key > 29:
        if function_key in (30, 300):
            buff_id = skill_code.get("value", 0)
            buff_code = next(
                (b for b in data["skill_buff"]["json"] if b["no"] == buff_id)
            )

            if type == "VALUE":
                return await get_buff_value_text(
                    buff_code.get("buff_effect", 0),
                    buff_code.get("value", 0),
                    use_color_text,
                )
            elif type == "DURATION":
                return await get_duration_text(
                    buff_code.get("duration", 0), use_color_text
                )
    elif ((function_key - 28) & 0xFFFFFFFF) < 2 or function_key == 25:
        if type == "DURATION":
            return await get_duration_text(
                skill_code.get("duration", 0), use_color_text
            )

        referenced_code = next(
            (
                code
                for code in data["skill_code"]["json"]
                if code["no"] == skill_code.get("value", 0)
            )
        )
        ref_function_key = referenced_code.get("function_key", 0)

        if ref_function_key in (30, 300):
            buff_id = referenced_code.get("value", 0)
            buff_code = next(
                (b for b in data["skill_buff"]["json"] if b["no"] == buff_id)
            )
            return await get_buff_value_text(
                buff_code.get("buff_effect", 0),
                buff_code.get("value", 0),
                use_color_text,
            )
        else:
            return await get_code_value_text(
                ref_function_key, referenced_code.get("value", 0), use_color_text
            )
    if type == "VALUE":
        return await get_code_value_text(
            function_key, skill_code.get("value", 0), use_color_text
        )
    elif type == "DURATION":
        return await get_duration_text(skill_code.get("duration", 0), use_color_text)
    return ""


async def get_code_value_text(
    function_key: int, value: float, use_color_text: bool
) -> str:
    """
    获取code类型数值文本
    SkillTextUtil::GetCodeValueText
    Args:
        function_key: function key
        value: 数值
        use_color_text: 是否使用颜色文本
    Returns:
        str: 格式化后的字符串
    """
    return await concat_color_text(
        function_key,
        value,
        "code",
        (
            function_key <= 0x1B
            and ((1 << function_key) & 0xC000010) != 0
            or ((function_key - 1026) & 0xFFFFFFFF) < 2
        ),
        use_color_text,
    )


async def get_code_value_color_text(function_key: int) -> str:
    """
    获取code类型数值颜色文本
    SkillTextUtil::GetCodeValueColorText
    Args:
        function_key: function key
    Returns:
        str: 颜色代码
    """
    if function_key in [1, 2, 9, 10, 11, 14, 15, 16, 17, 19, 21, 24, 32, 47, 1002]:
        return "#E67373"  # 红色
    elif function_key in [3, 12, 13, 18, 20, 22]:
        return "#00CC27"  # 绿色
    elif function_key in [4, 5, 6]:
        return "#4ABFD3"  # 蓝色
    elif function_key in [26, 27] or (function_key & 0xFFFFFFFE) == 0x402:
        return "#FFFFFF"  # 白色
    else:
        return ""


async def get_duration_text(duration: float, use_color_text: bool) -> str:
    """
    获取持续时间文本
    SkillTextUtil::GetDuraionText
    Args:
        duration: 持续时间
        use_color_text: 是否使用颜色文本
    Returns:
        str: 格式化后的字符串
    """
    text = f"{int(duration)}" if duration.is_integer() else f"{duration}"
    return f"<color=#FFFFFF>{text}</color>" if use_color_text else text


async def get_buff_value_text(
    buff_type: int, value: float, use_color_text: bool
) -> str:
    """
    获取buff类型数值文本
    SkillTextUtil::GetBuffValueText
    Args:
        buff_type: buff effect 类型
        value: 数值
        use_color_text: 是否使用颜色文本
    Returns:
        str: 格式化后的字符串
    """
    if buff_type <= 10102:
        if ((buff_type - 10101) & 0xFFFFFFFF) >= 2 and buff_type != 420:
            return await concat_color_text(
                buff_type, value, "buff", False, use_color_text
            )
        else:
            return await concat_color_text(
                buff_type, value, "buff", True, use_color_text
            )

    if ((buff_type - 10106) & 0xFFFFFFFF) <= 4 and (
        (1 << (buff_type - 122) % 32) & 0x13
    ) != 0:
        return await concat_color_text(buff_type, value, "buff", True, use_color_text)
    else:
        return await concat_color_text(buff_type, value, "buff", False, use_color_text)


async def get_buff_value_color_text(buff_type: int, value: float) -> str:
    """
    获取buff类型数值颜色文本
    SkillTextUtil::GetBuffValueColorText
    Args:
        buff_type: buff effect 类型
        value: 数值
    Returns:
        str: 颜色代码
    """
    if buff_type > 1402:
        if buff_type > 2304:
            if buff_type <= 3002:
                if (
                    ((buff_type - 2901) & 0xFFFFFFFF) > 0xF
                    or (((1 << (buff_type - 85)) % 32) & 0xFC3F == 0)
                    and (buff_type - 3001) & 0xFFFFFFFF >= 2
                ):
                    return ""
            elif buff_type <= 10111:
                if buff_type != 3401 and (buff_type - 10101) & 0xFFFFFFFF > 0xA:
                    return ""
            elif (buff_type - 10301) & 0xFFFFFFFF >= 2 and (
                buff_type - 10201
            ) & 0xFFFFFFFF > 1:
                return ""
            if value < 0.0:
                return "#B778FF"
            return "#EDA900"
        if buff_type > 1702:
            if buff_type > 1906:
                if (buff_type - 2301) & 0xFFFFFFFF > 3 or buff_type == 2303:
                    return ""
                if value < 0.0:
                    return "#B778FF"
                return "#EDA900"
            if buff_type != 1703:
                if (buff_type - 1901) & 0xFFFFFFFF <= 5:
                    if value < 0.0:
                        return "#B778FF"
                    return "#EDA900"
                return ""
            return "#00CC27"
        if buff_type == 1501:
            return "#EDA900"
        if buff_type == 1502:
            return "#B778FF"
        if buff_type != 1702:
            return ""
        return "#E67373"

    if buff_type <= 503:
        if buff_type <= 313:
            if (buff_type - 101) & 0xFFFFFFFF < 0xB:
                if value < 0.0:
                    return "#B778FF"
                return "#EDA900"
            if (buff_type - 301) & 0xFFFFFFFF >= 0xD or (
                (0x1E3F >> (buff_type - 45) % 32) & 1
            ) == 0:
                return ""
            return "#E67373"

        if buff_type <= 411:
            if (buff_type - 401) & 0xFFFFFFFF > 0xA or (
                ((1 << (buff_type + 111)) % 32) & 0x601
            ) == 0:
                return ""
            return "#00CC27"
        if buff_type == 420:
            return "#4ABFD3"
        if (buff_type - 501) & 0xFFFFFFFF > 2:
            return ""
        return "#368AFF"

    if buff_type > 802:
        if buff_type <= 1101:
            if (buff_type - 1001) & 0xFFFFFFFF >= 2 and buff_type != 1101:
                return ""
        elif (buff_type - 1401) & 0xFFFFFFFF >= 2 and buff_type != 1202:
            return ""
        if value < 0.0:
            return "#B778FF"
        return "#EDA900"

    if (buff_type - 511) & 0xFFFFFFFF < 2:
        return "#368AFF"
    if buff_type != 801 and buff_type != 802:
        return ""
    if value >= 0.0:
        return "#B778FF"
    return "#FFDF24"


async def get_stat_string_in_hero_option(value: float, buff_type: str) -> str:
    """
    获取潜能属性字符串
    UtilManager::GetStatStringInHeroOption
    Args:
        value: 需要格式化的原始数值。
        buff_type: 效果的类型
    Returns:
        格式化后的字符串。
    """
    INTEGER_TYPE = {
        "attack",
        "defence",
        "hp",
        "dodge",
        "mana_crystal",
        "mana_dust",
        "gold",
        "hit",
        "attack_per_level",
        "defence_per_level",
        "hp_per_level",
    }

    PERCENTAGE_TYPE = {
        "attack_rate",
        "defence_rate",
        "hp_rate",
        "critical_rate",
        "critical_power",
        "physical_resist",
        "magic_resist",
        "life_leech",
        "critical_resist",
        "life_leech_buff",
        "human_type_damage",
        "furry_type_damage",
        "undead_type_damage",
        "elf_type_damage",
        "angel_type_damage",
        "demon_type_damage",
        "chaos_type_damage",
    }

    if buff_type in PERCENTAGE_TYPE:
        return await format_value(value, False)
    elif buff_type in INTEGER_TYPE:
        return await format_value(value, True)
    else:
        return ""


async def process_skill_description(data, description, use_color_text: bool):
    """
    处理技能描述
    Args:
        data: json 数据
        description: 技能描述
        use_color_text: 是否使用颜色文本
    Returns:
        str: 处理后的技能描述
    """

    if use_color_text:
        processed_text = description
    else:
        processed_text = await clean_rich_text(description)
    placeholder_pattern = r"<\s*(\d+)\.(VALUE|DURATION)\s*>"
    matches = list(re.finditer(placeholder_pattern, processed_text))

    async def get_value_for_match(match):
        no = int(match.group(1))
        type_str = match.group(2)
        return await get_character_skill_description(data, no, type_str, use_color_text)

    for match, replacement in zip(
        reversed(matches),
        reversed(await asyncio.gather(*[get_value_for_match(m) for m in matches])),
    ):
        start, end = match.span()
        processed_text = processed_text[:start] + replacement + processed_text[end:]

    return processed_text


async def get_formation_type(formation_no):
    """
    获取阵型类型
    Args:
        formation_no: 阵型编号
    Returns:
        str: 阵型类型
    """
    from ...config import FORMATION_TYPE_MAPPING

    return FORMATION_TYPE_MAPPING.get(formation_no, "")


async def get_string_by_type(data, string_type, no):
    """
    获取字符串
    Args:
        data: JSON 数据字典
        string_type: string 类型的都行，例如 ui, character, item, system, etc.
        no: 编号
    Returns:
        dict: 包含不同语言的文本, 键为 'zh_tw', 'zh_cn', 'kr', 'en'
    Note: 切换到国服数据源时也使用 zh_tw 即可
    """

    for string in data[f"string_{string_type}"]["json"]:
        if string["no"] == no:
            return {
                # 这里是为了直接适配国服。。
                "zh_tw": (
                    string.get("zh_tw")
                    if string.get("zh_tw") != ""
                    else string.get("zh_cn")
                ),
                "zh_cn": string.get("zh_cn", ""),
                "kr": string.get("kr", ""),
                "en": string.get("en", ""),
            }

    return {"zh_tw": "", "zh_cn": "", "kr": "", "en": ""}


async def get_character_birthday(data, birthday: int) -> str:
    """
    获取格式化后的生日字符串
    Args:
        data: JSON 数据字典
        birthday: 生日
    Returns:
        str: 格式化的生日字符串
    """

    template = (await get_string_by_type(data, "ui", 10625)).get("zh_tw", "{0}月{1}日")
    month = ((0x51EB851F * birthday) >> 37) % 32 + (
        (0x51EB851F * birthday >> 63) & 0xFFFFFFFFFFFFFFFF
    ) % 64
    day = birthday % 0x64
    return template.format(str(month), str(day))


async def get_string_character(data, hero_no, special=False):
    """
    获取角色名称
    Args:
        data: JSON 数据字典
        hero_no: 角色编号
        special: 当文本无法直接从 string_character 中获取时使用
    Returns:
        dict: 包含不同语言的文本, 键为 'zh_tw', 'zh_cn', 'kr', 'en'
    """
    name_sno = hero_no

    if special:
        for hero in data["hero"]["json"]:
            if hero["no"] == hero_no:
                name_sno = hero.get("name_sno")
                break

    for char in data["string_character"]["json"]:
        if char["no"] == name_sno:
            return {
                # 这里是为了直接适配国服。。
                "zh_tw": (
                    char.get("zh_tw") if char.get("zh_tw") != "" else char.get("zh_cn")
                ),
                "zh_cn": char.get("zh_cn", ""),
                "kr": char.get("kr", ""),
                "en": char.get("en", ""),
            }

    return {"zh_tw": "", "zh_cn": "", "kr": "", "en": ""}


async def get_drop_item_rate(data, group_no):
    """
    获取掉落物品信息，保留概率最高的物品
    Args:
        data: JSON 数据字典
        group_no: 掉落组编号

    Returns:
        list: [(物品名称, 数量, 掉落率)]
    """
    drop_items = []

    if group_no is None:
        return []

    for drop_group in data["item_drop_group"]["json"]:
        if drop_group["no"] == group_no:
            item_no = drop_group.get("item_no")
            value = drop_group.get("value", 0)
            drop_rate = drop_group.get("drop_rate", 0)

            if item_no:
                item_name = await get_string_item(data, item_no)
                # 转换掉落率 (1 = 0.001%)
                rate_percent = drop_rate * 0.001
                drop_items.append((item_name, value, rate_percent))

    name_to_best_item = {}

    for item in drop_items:
        item_name = item[0]["zh_tw"]
        item_rate = item[2]

        if (
            item_name not in name_to_best_item
            or item_rate > name_to_best_item[item_name][2]
        ):
            name_to_best_item[item_name] = item

    unique_items = list(name_to_best_item.values())
    return sorted(unique_items, key=lambda x: -x[2])


async def get_string_item(data, item_no):
    """
    获取物品名称
    Args:
        data: JSON 数据字典
        item_no: 物品编号

    Returns:
        dict: 包含不同语言的文本, 键为 'zh_tw', 'zh_cn', 'kr', 'en'
    """
    # 在Item.json中查找物品
    for item in data["item"]["json"]:
        if item["no"] == int(item_no):
            name_sno = item.get("name_sno")
            if name_sno:
                # 在StringItem.json中查找物品名称
                for string in data["string_item"]["json"]:
                    if string.get("no") == name_sno:
                        return {
                            # 这里是为了直接适配国服。。
                            "zh_tw": (
                                string.get("zh_tw")
                                if string.get("zh_tw") != ""
                                else string.get("zh_cn")
                            ),
                            "zh_cn": string.get("zh_cn", ""),
                            "kr": string.get("kr", ""),
                            "en": string.get("en", ""),
                        }
    return {"zh_tw": "", "zh_cn": "", "kr": "", "en": ""}


async def get_character_cv(data, hero_desc) -> str:
    """
    获取角色配音
    Args:
        data: JSON 数据字典
        hero_desc: 角色描述

    Returns:
        dict: 包含韩语和日语配音, 键为 'kr', 'ja'
    """
    cv_kr = (
        (await get_string_character(data, hero_desc.get("cv_sno", 0))).get("zh_tw")
        if hero_desc
        else ""
    )
    cv_ja = (
        (await get_string_character(data, hero_desc.get("cv_jp_sno", 0))).get("zh_tw")
        if hero_desc
        else ""
    )
    cv_ja = cv_ja if (cv_ja != cv_kr and cv_ja != "") else ""

    return {"kr": cv_kr, "ja": cv_ja}  # pyright: ignore[reportReturnType]


async def get_character_release_date(data, hero_id):
    """
    获取角色发布日期
    Args:
        data: JSON 数据字典
        hero_id: 角色编号

    Returns:
        str: 格式化的发布日期, 如果未找到, 返回默认日期 (2023-01-05)
    """
    release_date = None
    for movie in data["promotion_movie"]["json"]:
        if movie.get("hero_check") == hero_id:
            # 只取日期部分，不要时间
            start_date = movie.get("start_date", "").split()[0]
            if start_date and start_date != "2999-12-31":  # 排除默认日期
                release_date = start_date
                break
    return f"{release_date}" if release_date else "2023-01-05"


async def get_character_arbeit(data, hero_id):
    """
    获取角色属性
    Args:
        data: JSON 数据字典
        hero_id: 角色编号
    Returns:
        dict: 包含初始和满级属性, 键为 'initial', 'max'

    """
    from ...config import TRAIT_NAME_MAPPING

    # 收集所有相关等级的数据
    level_data = []
    for level in data["arbeit_fairy_level"]["json"]:
        if level.get("hero_no") == hero_id:
            level_data.append(level)

    if not level_data:
        return {"initial": "", "max": ""}

    # 按等级排序
    level_data.sort(key=lambda x: x.get("level", 0))

    # 获取初始等级和满级数据
    initial_level = level_data[0]
    max_level = level_data[-1]

    # 获取初始属性
    initial_traits = []
    for trait, value in initial_level.items():
        if trait in TRAIT_NAME_MAPPING and value > 0:
            initial_traits.append(f"{TRAIT_NAME_MAPPING[trait]}{value}⭐")

    # 获取满级属性
    max_traits = []
    for trait, value in max_level.items():
        if trait in TRAIT_NAME_MAPPING and value > 0:
            max_traits.append(f"{TRAIT_NAME_MAPPING[trait]}{value}⭐")

    # 格式化文本
    initial_text = "、".join(initial_traits)
    max_text = "、".join(max_traits)

    return {"initial": initial_text, "max": max_text}


async def get_character_prefer_gift(data, hero_id):
    """
    获取角色喜好礼物
    Args:
        data: JSON 数据字典
        hero_id: 角色编号

    Returns:
        str: 喜好礼物, 用逗号分隔
    """
    gift_items = []
    for gift in data["hero_gift"]["json"]:
        if gift.get("hero_no") == hero_id:
            prefer_items = gift.get("prefer_gift_items", "").split(",")
            prefer_items = [item.strip() for item in prefer_items if item.strip()]
            for item_no in prefer_items:
                gift_items.append(
                    (await get_string_item(data, item_no)).get("zh_tw", "")
                )
    return "、".join(gift_items) if gift_items else ""


async def get_character_similar_name(query, alias_map):
    """
    获取角色相似名称
    Args:
        query: 查询名称
        alias_map: 别名映射
    Returns:
        list: 角色相似名称列表 [(名称, 别名), ...]
    """
    hero_map = {}
    for name, hero_id in alias_map.items():
        if hero_id not in hero_map:
            hero_map[hero_id] = [name, []]
        else:
            if len(hero_map[hero_id][1]) == 0:
                hero_map[hero_id][1].append(name)
            else:
                hero_map[hero_id][1].append(name)

    all_names = []
    for name, hero_id in alias_map.items():
        all_names.append(name)

    similar_names = get_close_matches(query, all_names, n=3, cutoff=0.3)

    results = []
    for similar_name in similar_names:
        hero_id = alias_map[similar_name]
        main_name = hero_map[hero_id][0]
        aliases = [alias for alias in hero_map[hero_id][1] if alias != main_name]
        if (main_name, aliases) not in results:
            results.append((main_name, aliases))

    return results


async def get_character_skill(
    data,
    skill_no,
    support=False,
    generate_image=False,
    server="global",
    data_type="live",
):
    """
    获取角色技能
    Args:
        data: JSON 数据字典
        skill_no: 技能编号
        support: 是否为支援技能
        generate_image: 是否生成图片
        review: 是否为review模式（影响语言选择）
    Returns:
        dict: 包含技能信息，如果generate_image=True，还包含image_bytes字段
    """
    skill_data_list = []
    skill_name_zh_tw = ""
    skill_name_zh_cn = ""
    skill_name_kr = ""
    skill_name_en = ""
    skill_name_ja = ""
    skill_descriptions = []
    skill_icon_info = None

    for skill in data["skill"]["json"]:
        if skill["no"] == skill_no:
            skill_data_list.append(skill)
            if not skill_icon_info:
                icon_prefab = skill.get("icon_prefab")
                # 这里是适配数据表里面没有的转变形态技能的着色(光凯)
                for icon_data in data["skill_icon"]["json"]:
                    if icon_data["no"] == icon_prefab:
                        skill_icon_info = {
                            "icon": icon_data["icon"],
                            "color": f"#{icon_data['color']}",
                        }
                    elif icon_prefab == 14:
                        skill_icon_info = {
                            "icon": "Icon_Sub_Change",
                            "color": "#e168eb",
                        }
                        break

    if skill_data_list:
        skill_name_data = await get_string_by_type(
            data, "skill", skill_data_list[0]["name_sno"]
        )
        skill_name_zh_tw = skill_name_data.get("zh_tw", "")
        skill_name_zh_cn = skill_name_data.get("zh_cn", "")
        skill_name_kr = skill_name_data.get("kr", "")
        skill_name_ja = skill_name_data.get("ja", "")
        skill_name_en = (
            await get_string_by_type(data, "skill", skill_data_list[0]["name_sno"])
        ).get("en", "")

        if support:
            # 支援技能，获取最高等级的技能描述
            max_level_skill = max(skill_data_list, key=lambda x: x.get("level", 1))
            desc_tw = await process_skill_description(
                data,
                (
                    await get_string_by_type(
                        data, "skill", max_level_skill["tooltip_sno"]
                    )
                ).get("zh_tw", ""),
                True,
            )
            desc_cn = await process_skill_description(
                data,
                (
                    await get_string_by_type(
                        data, "skill", max_level_skill["tooltip_sno"]
                    )
                ).get("zh_cn", ""),
                True,
            )
            desc_kr = await process_skill_description(
                data,
                (
                    await get_string_by_type(
                        data, "skill", max_level_skill["tooltip_sno"]
                    )
                ).get("kr", ""),
                True,
            )
            desc_en = await process_skill_description(
                data,
                (
                    await get_string_by_type(
                        data, "skill", max_level_skill["tooltip_sno"]
                    )
                ).get("en", ""),
                True,
            )
            skill_descriptions.append(
                {
                    "desc_zh_tw": desc_tw,
                    "desc_zh_cn": desc_cn,
                    "desc_kr": desc_kr,
                    "desc_en": desc_en,
                    "type": "support",
                }
            )
        else:
            # 非支援技能，获取所有等级的技能描述
            for skill_data in skill_data_list:
                desc_tw = await process_skill_description(
                    data,
                    (
                        await get_string_by_type(
                            data, "skill", skill_data["tooltip_sno"]
                        )
                    ).get("zh_tw", ""),
                    True,
                )
                desc_cn = await process_skill_description(
                    data,
                    (
                        await get_string_by_type(
                            data, "skill", skill_data["tooltip_sno"]
                        )
                    ).get("zh_cn", ""),
                    True,
                )
                desc_kr = await process_skill_description(
                    data,
                    (
                        await get_string_by_type(
                            data, "skill", skill_data["tooltip_sno"]
                        )
                    ).get("kr", ""),
                    True,
                )
                desc_en = await process_skill_description(
                    data,
                    (
                        await get_string_by_type(
                            data, "skill", skill_data["tooltip_sno"]
                        )
                    ).get("en", ""),
                    True,
                )
                skill_descriptions.append(
                    {
                        "desc_zh_tw": desc_tw,
                        "desc_zh_cn": desc_cn,
                        "desc_kr": desc_kr,
                        "desc_en": desc_en,
                        "hero_level": skill_data.get("hero_level", 1),
                    }
                )

    result = {
        "name": {
            "zh_tw": skill_name_zh_tw,
            "zh_cn": skill_name_zh_cn,
            "kr": skill_name_kr,
            "en": skill_name_en,
            "ja": skill_name_ja,
        },
        "descriptions": skill_descriptions,
        "icon_info": skill_icon_info,
        "support": support,
    }

    # 生成图片（如果需要）
    if generate_image and skill_descriptions:
        try:
            # 获取技能类型（从第一个技能数据中）
            skill_type = ""
            if skill_data_list:
                skill_type_sno = skill_data_list[0].get("type")
                if skill_type_sno:
                    skill_type_data = await get_string_by_type(
                        data, "system", skill_type_sno
                    )
                    # 根据review模式选择语言
                    skill_type = await select_text_by_priority(
                        skill_type_data.get("zh_tw", ""),
                        skill_type_data.get("zh_cn", ""),
                        skill_type_data.get("kr", ""),
                        skill_type_data.get("ja", ""),
                        server,
                        data_type,
                    )

            # 根据服务器选择技能名称
            skill_name_display = await select_text_by_priority(
                skill_name_zh_tw,
                skill_name_zh_cn,
                skill_name_kr,
                skill_name_ja,
                server,
                data_type,
            )

            # 准备技能图标
            if skill_icon_info:
                try:
                    from ...config import ICON_DIR

                    icon_path = str(ICON_DIR / f"{skill_icon_info['icon']}.png")
                    cache_filename = f"{skill_icon_info['icon']}_{skill_icon_info['color'].replace('#', '')}.png"
                    cache_path = str(ICON_DIR / cache_filename)

                    # 检查缓存
                    if os.path.exists(cache_path):
                        with open(cache_path, "rb") as f:
                            icon_bytes_data = f.read()
                    elif os.path.exists(icon_path):
                        # 需要着色
                        from .es_image_utils import apply_color_to_icon

                        icon_bytes_data = await apply_color_to_icon(
                            icon_path, skill_icon_info["color"]
                        )
                        # 保存缓存
                        with open(cache_path, "wb") as f:
                            f.write(icon_bytes_data)
                except Exception as e:
                    logger.error(f"加载技能图标失败: {e}")

            from .es_image_utils import generate_skill_description_image

            image_bytes = await generate_skill_description_image(
                skill_descriptions,
                skill_name_display,
                skill_type,
                support,
                icon_bytes_data,
                server=server,
                data_type=data_type,
            )
            result["image_bytes"] = image_bytes
        except Exception as e:
            logger.error(f"生成技能图片失败: {e}")
            result["image_bytes"] = None

    return result


async def get_character_keyword_point(data: dict, keyword_type: str) -> list:
    """
    获取角色关键字点数
    Args:
        data: JSON 数据字典
        keyword_type: 关键字类型
    """
    key_name = {
        "normal": "TRIP_KEYWORD_GRADE_POINT",
        "bad": "TRIP_KEYWORD_GRADE_POINT_BAD",
        "good": "TRIP_KEYWORD_GRADE_POINT_GOOD",
    }[keyword_type]

    points = next(
        (
            kv.get("values_data")
            for kv in data["key_values"]["json"]
            if kv.get("key_name") == key_name
        )
    )
    return ast.literal_eval(points)


async def get_story_chapter_name(
    data: dict, story: dict, server: str = "global", data_type: str = "live"
) -> str:
    """
    获取故事章节名称
    Args:
        data: JSON 数据字典
        story: 故事信息字典
        review: 是否为测试
    Returns:
        格式化的章节名称
    """
    chapter = story.get("chapter", 0)
    if chapter:
        chapter_format_data = await get_string_by_type(data, "ui", 652001)
        chapter_format = await select_text_by_priority(
            chapter_format_data["zh_tw"],
            chapter_format_data["zh_cn"],
            chapter_format_data["kr"],
            chapter_format_data.get("ja", ""),
            server,
            data_type,
        )
        return chapter_format.format(chapter)
    else:
        default_data = await get_string_by_type(data, "ui", 652000)
        return await select_text_by_priority(
            default_data["zh_tw"],
            default_data["zh_cn"],
            default_data["kr"],
            default_data.get("ja", ""),
            server,
            data_type,
        )


async def get_character_keyword_source(
    data: dict,
    source_sno: int,
    details: int,
    keyword_type: int,
    server: str = "global",
    data_type: str = "live",
) -> tuple[str, str]:
    """
    获取角色关键字来源和地点信息
    Info::TripKeyworInfoExtension::GetKeywordSource
    Args:
        data: JSON 数据字典
        source_sno: 来源描述的字符串编号
        details: 详情ID
        keyword_type: 关键字类型
        review: 是否为测试
    Returns:
        tuple: (source, location) - 来源信息和地点信息
    """
    source = ""
    location = ""
    # 剧情来源
    if keyword_type == 3:
        story = next(
            (s for s in data["story_info"]["json"] if s["no"] == details), None
        )
        if story:
            desc_data = await get_string_by_type(data, "ui", source_sno)
            desc = await select_text_by_priority(
                desc_data.get("zh_tw", ""),
                desc_data.get("zh_cn", ""),
                desc_data.get("kr", ""),
                desc_data.get("ja", ""),
                server,
                data_type,
            )
            if desc:
                source = desc.format(
                    await get_story_chapter_name(data, story, server, data_type),
                    story.get("episode", 0),
                )
    # 地点来源
    elif keyword_type == 7:
        town_location = next(
            (loc for loc in data["town_location"]["json"] if loc["no"] == details), None
        )
        if town_location:
            location_data = await get_string_by_type(
                data, "town", town_location.get("location_name_sno")
            )
            location = await select_text_by_priority(
                location_data.get("zh_tw", ""),
                location_data.get("zh_cn", ""),
                location_data.get("kr", ""),
                location_data.get("ja", ""),
                server,
                data_type,
            )
            desc_data = await get_string_by_type(data, "ui", source_sno)
            desc = await select_text_by_priority(
                desc_data.get("zh_tw", ""),
                desc_data.get("zh_cn", ""),
                desc_data.get("kr", ""),
                desc_data.get("ja", ""),
                server,
                data_type,
            )
            if desc:
                source = desc.format(location)
    # 通用数值来源
    elif ((1 << keyword_type) & 0xFFFFFFFF) & 0x370 != 0:
        desc_data = await get_string_by_type(data, "ui", source_sno)
        desc = await select_text_by_priority(
            desc_data.get("zh_tw", ""),
            desc_data.get("zh_cn", ""),
            desc_data.get("kr", ""),
            desc_data.get("ja", ""),
            server,
            data_type,
        )
        if desc:
            source = desc.format(details)
    # 固定文本来源
    elif keyword_type in {101, 102, 103}:
        string_data = await get_string_by_type(data, "ui", 619000 + keyword_type)
        source = await select_text_by_priority(
            string_data.get("zh_tw", ""),
            string_data.get("zh_cn", ""),
            string_data.get("kr", ""),
            string_data.get("ja", ""),
            server,
            data_type,
        )
    # 获取地点信息
    location = "通用"
    town_location = next(
        (loc for loc in data["town_location"]["json"] if loc["no"] == details), None
    )
    if town_location:
        location_data = await get_string_by_type(
            data, "town", town_location.get("location_name_sno")
        )
        location = await select_text_by_priority(
            location_data.get("zh_tw", ""),
            location_data.get("zh_cn", ""),
            location_data.get("kr", ""),
            location_data.get("ja", ""),
            server,
            data_type,
        )
    return source, location


async def get_character_keyword_info(
    data: dict,
    keyword_info: dict,
    trip_info: dict,
    server: str = "global",
    data_type: str = "live",
) -> dict:
    """
    获取完整的角色关键字信息
    Args:
        data: JSON 数据字典
        keyword_info: 关键字基础信息
        trip_info: 旅行关键字信息
        review: 是否为测试
    Returns:
        dict: 完整的关键字信息
    """
    # 关键字类型
    keyword_type = "normal"  # 粉心
    if not trip_info.get("favor_point"):  # 黄心
        keyword_type = "bad"
    elif trip_info.get("favor_point") == 2:  # 红心
        keyword_type = "good"

    # 好感度加成
    points = await get_character_keyword_point(data, keyword_type)
    grade_sno = keyword_info.get("keyword_grade")
    grade_index = 0  # 一般
    if grade_sno == 110012:  # 稀有
        grade_index = 1
    elif grade_sno == 110014:  # 史诗
        grade_index = 2
    favor_point = points[grade_index]

    # 关键字名称
    name_data = await get_string_by_type(data, "ui", keyword_info.get("keyword_string"))
    name = name_data.get(
        await select_text_by_priority("zh_tw", "zh_cn", "kr", "", server, data_type), ""
    )

    # 关键字等级
    grade_data = await get_string_by_type(data, "system", grade_sno)
    grade = grade_data.get("zh_tw", "")

    # 关键字来源和地点信息
    source, location = await get_character_keyword_source(
        data,
        keyword_info.get("keyword_source", 0),
        keyword_info.get("keyword_get_details", 0),
        keyword_info.get("keyword_type", 0),
        server,
        data_type,
    )

    return {
        "name": name,
        "type": keyword_type,
        "favor_point": favor_point,
        "grade": grade,
        "source": source,
        "location": location,
        "keyword_get_details": keyword_info.get("keyword_get_details"),
    }


async def get_character_keyword(
    data: dict, hero_id: int, server: str = "global", data_type: str = "live"
) -> str:
    """
    获取角色关键字
    Args:
        data: JSON 数据字典
        hero_id: 角色编号
        server: 服务器类型 (global/cn/jp)
        data_type: 数据类型 (live/review)
    """
    trip_keywords = []
    keyword_msgs = []

    for trip in data["trip_hero"]["json"]:
        if trip.get("hero_no") == hero_id:
            keyword_info = next(
                (
                    k
                    for k in data["trip_keyword"]["json"]
                    if k["no"] == trip.get("keyword_no")
                ),
                None,
            )
            if keyword_info:
                keyword = await get_character_keyword_info(
                    data, keyword_info, trip, server, data_type
                )
                trip_keywords.append(keyword)

    bad_keywords = [k for k in trip_keywords if k["type"] == "bad"]
    good_keywords = [k for k in trip_keywords if k["type"] == "good"]

    if not (bad_keywords or good_keywords):
        return ""

    keyword_msgs.append("【角色关键字】")
    if bad_keywords:
        keyword_msgs.append("▼ 讨厌的话题")
        for keyword in bad_keywords:
            msg = f"・{keyword['name']}（{keyword['grade']}）"
            if keyword.get("location"):
                msg += f"\n  地点：{keyword['location']}"
            keyword_msgs.append(msg)

    if good_keywords:
        if bad_keywords:
            keyword_msgs.append("")
        keyword_msgs.append("▼ 喜欢的话题")
        normal_keywords = [k for k in good_keywords if not k["source"]]
        for keyword in normal_keywords:
            msg = f"・{keyword['name']}（{keyword['grade']}）"
            if keyword.get("location"):
                msg += f"\n  地点：{keyword['location']}"
            keyword_msgs.append(msg)

        if normal_keywords and any(k["source"] for k in good_keywords):
            if good_keywords:
                keyword_msgs.append("")
            keyword_msgs.append("▼ 以下为需要解锁的关键字")

        for keyword in (k for k in good_keywords if k["source"]):
            msg = f"・{keyword['name']}（{keyword['grade']}）"
            if keyword.get("location"):
                msg += f"\n  地点：{keyword['location']}"
            if keyword["source"]:
                msg += f"\n  条件：{keyword['source']}"
            keyword_msgs.append(msg)

    return "\n".join(keyword_msgs)


async def get_character_town_object(
    data: dict, hero_id: int, server: str = "global", data_type: str = "live"
) -> dict:  # pyright: ignore[reportReturnType]
    """
    获取角色专属领地物品
    Args:
        data: JSON 数据字典
        hero_id: 角色编号
        server: 服务器类型 (global/cn/jp)
        data_type: 数据类型 (live/review)
    public enum BuildingBuff
    {
        None = 0,
        LootGoldBonus = 1,
        LootManaDustBonus = 3,
        LootManaCrystalBonus = 4,
        TownBuildingLevelLimit = 10,
        HeroRestSlotCount = 11,
        TownShopType = 12,
        SilverCoinAmount = 16,
        HeroAttackkUp = 50,
        HeroDefendUp = 51,
        HeroHealthPointUp = 52,
        HeroCriticalPowerUp = 53,
        HeroAccuracyUp = 54,
        HeroEvasionUp = 55,
        HeroMagicRegistUp = 56,
        HeroPhysicalResistUp = 57,
        HeroLifeLeechUp = 58,
        LootGoldBonusPlus = 101,
        LootManaDustBonusPlus = 103,
        LootManaCrystalBonusPlus = 104
    }
    Args:
        data: JSON 数据字典
        hero_id: 角色编号

    Returns:
        list: 物品信息列表 [(物品编号, 物品名称, 物品品质, 物品类型, 物品描述, 图片路径), ...]
    """
    from ...config import TOWN_DIR

    for obj in data["town_object"]["json"]:
        if obj.get("hero") == hero_id:
            obj_no = obj.get("no")
            buff1_sno = obj.get("buff1")
            buff2_sno = obj.get("buff2")
            if not obj_no:
                continue

            # 获取prefab作为图片名称
            tooltip = (await get_string_by_type(data, "ui", buff1_sno)).get("zh_tw", "")
            prefab = obj.get("prefab", "").lower()

            for buff in data["town_buff"]["json"]:
                if buff.get("no") == buff2_sno:
                    contents_buff_no = buff.get("contents_buff_no")
                    break

            if contents_buff_no:
                for buff in data["contents_buff"]["json"]:
                    if buff.get("no") == contents_buff_no:
                        battle_power_per = buff.get("battle_power_per")
                        break

            # 在Item.json中查找对应物品信息
            for item in data["item"]["json"]:
                if item.get("no") == obj_no:
                    name = await select_text_by_priority(
                        (await get_string_item(data, obj_no)).get("zh_tw", ""),
                        (await get_string_item(data, obj_no)).get("zh_cn", ""),
                        (await get_string_item(data, obj_no)).get("kr", ""),
                        (await get_string_item(data, obj_no)).get("ja", ""),
                        server,
                        data_type,
                    )

                    # 获取物品品质
                    grade = ""
                    grade_sno = item.get("grade_sno")
                    if grade_sno:
                        grade = await select_text_by_priority(
                            (await get_string_by_type(data, "system", grade_sno)).get(
                                "zh_tw", ""
                            ),
                            (await get_string_by_type(data, "system", grade_sno)).get(
                                "zh_cn", ""
                            ),
                            (await get_string_by_type(data, "system", grade_sno)).get(
                                "kr", ""
                            ),
                            (await get_string_by_type(data, "system", grade_sno)).get(
                                "ja", ""
                            ),
                            server,
                            data_type,
                        )

                    # 获取物品类型
                    slot_type = ""
                    slot_limit_sno = item.get("slot_limit_sno")
                    if slot_limit_sno:
                        slot_type = await select_text_by_priority(
                            (await get_string_by_type(data, "ui", slot_limit_sno)).get(
                                "zh_tw", ""
                            ),
                            (await get_string_by_type(data, "ui", slot_limit_sno)).get(
                                "zh_cn", ""
                            ),
                            (await get_string_by_type(data, "ui", slot_limit_sno)).get(
                                "kr", ""
                            ),
                            (await get_string_by_type(data, "ui", slot_limit_sno)).get(
                                "ja", ""
                            ),
                            server,
                            data_type,
                        )

                    # 获取物品描述
                    desc_sno = item.get("desc_sno")
                    if desc_sno:
                        for string in data["string_item"]["json"]:
                            if string.get("no") == desc_sno:
                                zh_tw = string.get("zh_tw", "")
                                zh_cn = string.get("zh_cn", "")
                                kr = string.get("kr", "")
                                ja = string.get("ja", "")
                                desc_text = await select_text_by_priority(
                                    zh_tw, zh_cn, kr, ja, server, data_type
                                )
                                desc = await clean_rich_text(desc_text)
                                break

                    if name:
                        if prefab:
                            img_path = ""
                            for file in os.listdir(TOWN_DIR):
                                if file.lower() == f"{prefab}.png":
                                    img_path = TOWN_DIR / file
                                    break
                        return {
                            "obj_no": obj_no,
                            "name": name,
                            "grade": grade,
                            "slot_type": slot_type,
                            "desc": desc,
                            "img_path": img_path,
                            "battle_power_per": battle_power_per,
                            "tooltip": tooltip,
                        }


async def get_character_town_object_task(
    data: dict, obj_no: int, server: str = "global", data_type: str = "live"
) -> list:
    """
    获取角色专属领地物品任务
    Args:
        data: JSON 数据字典
        obj_no: 物品编号

    Returns:
        list: 任务信息列表
    """
    from ...config import TRAIT_NAME_MAPPING

    try:
        tasks_info = []

        # 在ArbeitChoice中查找对应物品的任务
        for choice in data["arbeit_choice"]["json"]:
            if choice.get("objet_no") == obj_no:
                arbeit_no = choice.get("arbeit_no")
                if not arbeit_no:
                    continue

                # 在ArbeitList中查找任务详情
                for arbeit in data["arbeit_list"]["json"]:
                    if arbeit.get("no") == arbeit_no:
                        # 获取任务品质
                        rarity = ""
                        rarity_sno = arbeit.get("rarity")
                        if rarity_sno:
                            for string in data["string_system"]["json"]:
                                if string.get("no") == rarity_sno:
                                    rarity_zh_tw = string.get("zh_tw", "")
                                    rarity_zh_cn = string.get("zh_cn", "")
                                    rarity_kr = string.get("kr", "")
                                    rarity_ja = string.get("ja", "")
                                    rarity = await select_text_by_priority(
                                        rarity_zh_tw,
                                        rarity_zh_cn,
                                        rarity_kr,
                                        rarity_ja,
                                        server,
                                        data_type,
                                    )
                                    break

                        # 获取任务名称
                        name = ""
                        name_sno = arbeit.get("name_sno")
                        if name_sno:
                            for string in data["string_town"]["json"]:
                                if string.get("no") == name_sno:
                                    name_zh_tw = string.get("zh_tw", "")
                                    name_zh_cn = string.get("zh_cn", "")
                                    name_kr = string.get("kr", "")
                                    name_ja = string.get("ja", "")
                                    name = await select_text_by_priority(
                                        name_zh_tw,
                                        name_zh_cn,
                                        name_kr,
                                        name_ja,
                                        server,
                                        data_type,
                                    )
                                    break

                        # 获取所需时间
                        time_hours = arbeit.get("time", 0) / 3600

                        # 获取要求特性
                        traits = []
                        for trait, zh_name in TRAIT_NAME_MAPPING.items():
                            if stars := arbeit.get(trait):
                                traits.append(f"{zh_name}{stars}★")

                        # 获取奖励物品
                        rewards = []
                        for i in range(1, 3):  # 检查item1和item2
                            item_no = arbeit.get(f"item{i}_no")
                            item_amount = arbeit.get(f"item{i}_amount")
                            if item_no and item_amount:
                                # 查找物品名称
                                for item in data["item"]["json"]:
                                    if item.get("no") == item_no:
                                        name_sno = item.get("name_sno")
                                        if name_sno:
                                            item_name = await get_string_by_type(
                                                data, "item", name_sno
                                            )
                                            item_name = await select_text_by_priority(
                                                item_name["zh_tw"],
                                                item_name["zh_cn"],
                                                item_name["kr"],
                                                item_name.get("ja", ""),
                                                server,
                                                data_type,
                                            )
                                            rewards.append(f"{item_name}x{item_amount}")

                        # 添加任务信息
                        tasks_info.append(
                            {
                                "name": name,
                                "rarity": rarity,
                                "time": time_hours,
                                "traits": traits,
                                "stress": arbeit.get("stress", 0),
                                "exp": arbeit.get("arbeit_exp", 0),
                                "rewards": rewards,
                            }
                        )

        return tasks_info

    except Exception as e:
        logger.error(f"获取专属物品任务信息时发生错误: {e}, obj_no={obj_no}")
        return []


async def get_cash_pack(data: dict, item_type: str, gate_info: dict) -> list:
    """
    获取礼包信息
    Args:
        data: JSON 数据字典
        item_type: 礼包类型 ('barrier'/'stage'/'tower'/'grade_eternal')
        gate_info: 门/角色信息字典

    Returns:
        list: 礼包信息列表
    """
    from ...config import PACKAGE_TYPE_MAPPING

    messages = []
    shop_items = []

    # 获取礼包类型显示名称
    package_type_name = PACKAGE_TYPE_MAPPING.get(item_type, "特殊礼包")

    # 获取符合条件的商店物品
    for shop_item in data["cash_shop_item"]["json"]:
        if shop_item.get("type") == item_type and shop_item.get("type_value") == str(
            gate_info["no"]
        ):
            shop_items.append(shop_item)

    if shop_items:
        for shop_item in shop_items:
            package_info = []
            package_info.append(f"▼【{package_type_name}】")

            # 获取礼包名称和描述
            name_sno = shop_item.get("name_sno")
            package_name = (await get_string_by_type(data, "cashshop", name_sno)).get(
                "zh_tw", ""
            )

            info_sno = shop_item.get("item_info_sno")
            package_desc = (await get_string_by_type(data, "cashshop", info_sno)).get(
                "zh_tw", ""
            )

            desc_sno = shop_item.get("desc_sno")
            limit_desc = (
                (await get_string_by_type(data, "ui", desc_sno))
                .get("zh_tw", "")
                .format(shop_item.get("limit_buy", 0))
            )

            # 基本信息部分
            basic_info = [f"礼包名称：{package_name}"]
            if package_desc:
                basic_info.append(f"礼包描述：{package_desc}")
            basic_info.extend(
                [f"{limit_desc}", f"剩余时间：{shop_item.get('limit_hour', 0)}小时"]
            )
            package_info.append("\n".join(basic_info))

            # 礼包内容部分
            content_info = []
            if item_infos := shop_item.get("item_infos"):
                try:
                    items = ast.literal_eval(item_infos)
                    content_info.append("\n礼包内容：")
                    for item_no, value in items:
                        item_name = await get_string_item(data, item_no)
                        content_info.append(f"・{item_name["zh_tw"]}x{value}")
                except Exception as e:
                    logger.error(f"解析礼包内容时发生错误：{e}")
            if content_info:
                package_info.append("\n".join(content_info))

            # 价格信息部分
            price_info = ["\n价格信息："]
            if price_krw := shop_item.get("price_krw"):
                price_info.append(f"・ {price_krw}韩元")
            if price_other := shop_item.get("price_other"):
                price_info.append(f"・ {price_other}日元")
            package_info.append("\n".join(price_info))

            package_info.append("-" * 25)

            messages.append("\n".join(package_info))

    return messages


async def get_character_soullink(
    data: dict, hero_id: int, server: str = "global", data_type: str = "live"
) -> list:
    """
    获取角色灵魂链接
    Args:
        data: JSON 数据字典
        hero_id: 角色编号
        server: 服务器类型 (global/cn/jp)
        data_type: 数据类型 (live/review)
    """
    from ...config import STAT_NAME_MAPPING, SOULLINK_INTEGER_STAT_MAPPING

    soullink_info = []

    # 查找所有包含该角色的灵魂链接
    for link in data["soullink"]["json"]:
        # 动态查找所有hero槽位键
        hero_keys = [
            key
            for key in link.keys()
            if key.startswith("Group_Hero") and link[key] == hero_id
        ]

        if not hero_keys:
            continue  # 如果没有找到包含目标角色的槽位，跳过此链接

        # 收集所有角色ID
        hero_ids = []
        for key in link.keys():
            if key.startswith("Group_Hero") and link[key] > 0:
                hero_ids.append(link[key])

        if not hero_ids:
            continue

        # 获取灵魂链接标题和故事
        title = await get_string_by_type(data, "character", link.get("Group_Title"))
        title = await select_text_by_priority(
            title["zh_tw"],
            title["zh_cn"],
            title["kr"],
            title.get("ja", ""),
            server,
            data_type,
        )

        story = await get_string_by_type(data, "character", link.get("Group_Story"))
        story = await select_text_by_priority(
            story["zh_tw"],
            story["zh_cn"],
            story["kr"],
            story.get("ja", ""),
            server,
            data_type,
        )

        # 获取所有角色名称
        hero_names = []
        for hid in hero_ids:
            name_data = await get_string_character(data, hid, special=True)
            name_zh_tw = name_data["zh_tw"]
            name_zh_cn = name_data["zh_cn"]
            name_kr = name_data["kr"]
            name_ja = name_data.get("ja", "")
            name = await select_text_by_priority(
                name_zh_tw, name_zh_cn, name_kr, name_ja, server, data_type
            )
            if name:
                hero_names.append(name)

        # 获取收集效果
        collection_effects = []

        if collection_id := link.get("collection"):
            # 按condition_list排序
            collection_items = sorted(
                [
                    item
                    for item in data["soullink_collection"]["json"]
                    if item.get("collection_group") == collection_id
                ],
                key=lambda x: x.get("condition_list", 0),
            )

            for item in collection_items:
                # 获取条件文本
                condition_string_no = item.get("condition_string")
                condition_data = await get_string_by_type(
                    data, "ui", condition_string_no
                )
                condition_text = await select_text_by_priority(
                    condition_data["zh_tw"],
                    condition_data["zh_cn"],
                    condition_data["kr"],
                    condition_data.get("ja", ""),
                    server,
                    data_type,
                )
                # 格式化条件文本
                condition_text = condition_text.format(
                    item.get("condition_count", 0), item.get("condition_count", 0)
                )

                # 获取buff效果
                buff_effects = []
                if buff_no := item.get("contents_buff_no"):
                    buff = next(
                        (
                            b
                            for b in data["contents_buff"]["json"]
                            if b.get("no") == buff_no
                        ),
                        None,
                    )
                    if buff:
                        # 处理所有属性，包括战力加成
                        for key, value in buff.items():
                            if key in STAT_NAME_MAPPING:
                                stat_name = STAT_NAME_MAPPING[key]
                                if key in SOULLINK_INTEGER_STAT_MAPPING:
                                    buff_effects.append(
                                        f"{stat_name}：{await format_value(value, True)}%"
                                    )
                                else:
                                    buff_effects.append(
                                        f"{stat_name}：{await format_value(value, False)}"
                                    )

                        # 战力百分比加成
                        battle_power_per = buff.get("battle_power_per", 0)
                        if battle_power_per != 0:
                            buff_effects.append(f"战力百分比：{battle_power_per}")

                        # 固定值战力加成
                        battle_power = buff.get("battle_power", 0)
                        if battle_power != 0:
                            buff_effects.append(f"战力：{int(battle_power)}")

                if condition_text and buff_effects:
                    collection_effects.append(
                        {"condition": condition_text, "effects": buff_effects}
                    )

        # 添加到结果列表
        soullink_info.append(
            {
                "title": title,
                "heroes": hero_names,
                "story": story,
                "effects": collection_effects,
                "open_date": link.get("Open_date", ""),
            }
        )

    return soullink_info


async def get_character_signature_value(data, level_group):
    """获取角色遗物值

    Args:
        data: JSON 数据字典
        level_group: 遗物等级组编号

    Returns:
        dict: 包含遗物属性统计信息
    """
    from ...config import STAT_NAME_MAPPING

    max_level_data = None
    max_level = 0

    # 这个遗物的最大等级（45）
    for level_data in data["signature_level"]["json"]:
        if level_data["group"] == level_group:
            if level_data["signature_level"] > max_level:
                max_level = level_data["signature_level"]

    # 再找到最大等级的数据
    for level_data in data["signature_level"]["json"]:
        if (
            level_data["group"] == level_group
            and level_data["signature_level"] == max_level
        ):
            max_level_data = level_data
            break

    if not max_level_data:
        return []

    formatted_stats = []
    for stat_key, stat_name in STAT_NAME_MAPPING.items():
        if stat_key in max_level_data and max_level_data[stat_key] != 0:
            value = max_level_data[stat_key]
            formatted_stats.append(f"{stat_name}：{await format_value(value, False)}")

    return formatted_stats, max_level, max_level_data["battle_power_per"]


async def get_character_signature(
    data, hero_id, generate_image=False, server="global", data_type="live"
):
    """获取角色遗物

    Args:
        data: JSON 数据字典
        hero_id: 角色编号
        generate_image: 是否生成图片
        review: 是否为review模式（影响语言选择）

    Returns:
        dict: 包含遗物信息，如果generate_image=True，还包含image_bytes字段
    """

    skill_descriptions = []
    signature_bg_path = ""
    signature_data = None

    # 在Signature中查找对应角色的遗物
    for signature in data["signature"]["json"]:
        if signature["hero_sno"] == hero_id:
            signature_data = signature
            if signature_bg_path := signature.get("signature_bg_path"):
                signature_bg_path = f"Img_Signature_{signature_bg_path}.png"
            break

    if signature_data:
        # 获取遗物名称
        signature_name_data = await get_string_by_type(
            data, "skill", signature_data["signature_name_sno"]
        )
        signature_name_zh_tw = signature_name_data.get("zh_tw", "")
        signature_name_zh_cn = signature_name_data.get("zh_cn", "")
        signature_name_kr = signature_name_data.get("kr", "")
        signature_name_en = signature_name_data.get("en", "")
        signature_name_ja = signature_name_data.get("ja", "")

        # 获取遗物技能名称
        signature_title_data = await get_string_by_type(
            data, "skill", signature_data["skill_name_sno"]
        )
        signature_title_zh_tw = signature_title_data.get("zh_tw", "")
        signature_title_zh_cn = signature_title_data.get("zh_cn", "")
        signature_title_kr = signature_title_data.get("kr", "")
        signature_title_en = signature_title_data.get("en", "")
        signature_title_ja = signature_title_data.get("ja", "")

        # 获取遗物描述
        signature_desc_data = await get_string_by_type(
            data, "skill", signature_data["tooltip_explain_sno"]
        )
        signature_desc_zh_tw = signature_desc_data.get("zh_tw", "")
        signature_desc_zh_cn = signature_desc_data.get("zh_cn", "")
        signature_desc_kr = signature_desc_data.get("kr", "")
        signature_desc_en = signature_desc_data.get("en", "")
        signature_desc_ja = signature_desc_data.get("ja", "")
        # 查找解锁品质
        grade_group = signature_data.get("grade_group")
        skill_level_to_grade_name = {}
        if grade_group and "signature_grade" in data:
            for grade_data in data["signature_grade"]["json"]:
                if grade_data.get("group") == grade_group:
                    skill_level = grade_data.get("skill_level", 0)
                    signature_grade = grade_data.get("signature_grade", 0)
                    
                    # 获取品质名称
                    if signature_grade > 0:
                        grade_name_data = await get_string_by_type(data, "system", signature_grade)
                        grade_name = await select_text_by_priority(
                            grade_name_data.get("zh_tw", ""),
                            grade_name_data.get("zh_cn", ""),
                            grade_name_data.get("kr", ""),
                            grade_name_data.get("ja", ""),
                            server,
                            data_type,
                        )
                        if skill_level > 0 and grade_name:
                            skill_level_to_grade_name[skill_level] = grade_name
        
        # 获取所有等级的技能描述
        for i in range(1, 8):
            sno_key = f"skill_tooltip_sno{i}"
            if sno_key in signature_data:
                tooltip_sno = signature_data[sno_key]
                # 处理数值标签
                desc_tw = await process_skill_description(
                    data,
                    (await get_string_by_type(data, "skill", tooltip_sno)).get(
                        "zh_tw", ""
                    ),
                    True,
                )
                desc_cn = await process_skill_description(
                    data,
                    (await get_string_by_type(data, "skill", tooltip_sno)).get(
                        "zh_cn", ""
                    ),
                    True,
                )
                desc_kr = await process_skill_description(
                    data,
                    (await get_string_by_type(data, "skill", tooltip_sno)).get(
                        "kr", ""
                    ),
                    True,
                )
                desc_en = await process_skill_description(
                    data,
                    (await get_string_by_type(data, "skill", tooltip_sno)).get(
                        "en", ""
                    ),
                    True,
                )

                # 获取该技能等级对应的遗物解锁品质
                unlock_grade = skill_level_to_grade_name.get(i, "")
                
                skill_descriptions.append(
                    {
                        "desc_zh_tw": desc_tw,
                        "desc_zh_cn": desc_cn,
                        "desc_kr": desc_kr,
                        "desc_en": desc_en,
                        "level": i,
                        "unlock_grade": unlock_grade,  # 添加解锁品质
                    }
                )
    # 添加图标路径
    if signature_data:
        level_group = signature_data.get("level_group")
        signature_stats = (
            await get_character_signature_value(data, level_group)
            if level_group
            else []
        )

        result = {
            "name": {
                "zh_tw": signature_name_zh_tw,
                "zh_cn": signature_name_zh_cn,
                "kr": signature_name_kr,
                "en": signature_name_en,
            },
            "title": {
                "zh_tw": signature_title_zh_tw,
                "zh_cn": signature_title_zh_cn,
                "kr": signature_title_kr,
                "en": signature_title_en,
            },
            "description": {
                "zh_tw": signature_desc_zh_tw,
                "zh_cn": signature_desc_zh_cn,
                "kr": signature_desc_kr,
                "en": signature_desc_en,
            },
            "skills": skill_descriptions,
            "stats": signature_stats[0] if signature_stats else [],
            "max_level": signature_stats[1] if len(signature_stats) > 1 else 0,
            "max_level_battle_power_per": (
                signature_stats[2] if len(signature_stats) > 2 else 0
            ),
            "bg_path": signature_bg_path,
        }

        # 生成图片（如果需要）
        if generate_image and skill_descriptions:
            try:
                # 准备遗物图标（使用遗物背景图片）
                if signature_bg_path:
                    try:
                        from ...config import SOUL_DIR

                        signature_img_path = str(SOUL_DIR / signature_bg_path)
                        if os.path.exists(signature_img_path):
                            with open(signature_img_path, "rb") as f:
                                icon_bytes_data = f.read()
                    except Exception as e:
                        logger.error(f"加载遗物图标失败: {e}")
                from .es_image_utils import generate_skill_description_image

                # 根据服务器选择显示语言
                signature_name_display = await select_text_by_priority(
                    signature_name_zh_tw,
                    signature_name_zh_cn,
                    signature_name_kr,
                    signature_name_ja,
                    server,
                    data_type,
                )
                signature_title_display = await select_text_by_priority(
                    signature_title_zh_tw,
                    signature_title_zh_cn,
                    signature_title_kr,
                    signature_title_ja,
                    server,
                    data_type,
                )
                signature_desc_display = await select_text_by_priority(
                    signature_desc_zh_tw,
                    signature_desc_zh_cn,
                    signature_desc_kr,
                    signature_desc_ja,
                    server,
                    data_type,
                )

                # 准备额外信息（遗物属性）
                extra_info = {
                    "description": signature_desc_display,
                    "stats": signature_stats[0] if signature_stats else [],
                    "battle_power_per": (
                        signature_stats[2] if len(signature_stats) > 2 else 0
                    ),
                    "max_level": signature_stats[1] if len(signature_stats) > 1 else 0,
                }

                image_bytes = await generate_skill_description_image(
                    skill_descriptions,
                    f"{signature_title_display}",
                    signature_name_display,
                    support=False,
                    icon_bytes=icon_bytes_data,
                    extra_info=extra_info,
                    server=server,
                    data_type=data_type,
                )
                result["image_bytes"] = image_bytes
            except Exception as e:
                logger.error(f"生成遗物技能图片失败: {e}")
                result["image_bytes"] = None

        return result

    return {
        "name": {"zh_tw": "", "zh_cn": "", "kr": "", "en": ""},
        "title": {"zh_tw": "", "zh_cn": "", "kr": "", "en": ""},
        "description": {"zh_tw": "", "zh_cn": "", "kr": "", "en": ""},
        "skills": [],
        "stats": [],
        "max_level": 0,
        "max_level_battle_power_per": 0,
        "bg_path": "",
    }


async def group_choices_by_talk_index(episode_choices):
    """
    按 talk_index 分组选择

    Args:
        episode_choices: 剧集选择列表

    Returns:
        dict: 按 talk_index 分组的选择
    """
    choices_by_index = {}
    for choice in episode_choices:
        talk_index = choice["talk_index"]
        if talk_index not in choices_by_index:
            choices_by_index[talk_index] = []
        choices_by_index[talk_index].append(choice)
    return choices_by_index


async def find_best_and_worst_choices(choices):
    """
    在选择组中找到最好和最坏的选择

    Args:
        choices: 选择列表

    Returns:
        tuple: (最好选择, 最坏选择)
    """
    if not choices:
        return None, None

    max_affinity = max(c["affinity"] for c in choices)
    min_affinity = min(c["affinity"] for c in choices)

    best_choice = next(c for c in choices if c["affinity"] == max_affinity)
    worst_choice = next(c for c in choices if c["affinity"] == min_affinity)

    return best_choice, worst_choice


async def calculate_choice_differences(good_choices, bad_choices):
    """
    计算选择差异并排序

    Args:
        good_choices: 好选择列表
        bad_choices: 坏选择列表

    Returns:
        list: 排序后的差异列表
    """
    choice_diffs = []
    for i, (good_choice, bad_choice) in enumerate(zip(good_choices, bad_choices)):
        diff = good_choice["affinity"] - bad_choice["affinity"]
        if diff > 0:
            choice_diffs.append(
                {
                    "index": i,
                    "diff": diff,
                    "good_choice": good_choice,
                    "bad_choice": bad_choice,
                }
            )

    return sorted(choice_diffs, key=lambda x: x["diff"], reverse=True)


async def optimize_choices_for_normal_ending(
    good_choices, bad_choices, bad_threshold, normal_threshold
):
    """
    为一般结局优化选择

    Args:
        good_choices: 好选择列表
        bad_choices: 坏选择列表
        bad_threshold: 坏结局阈值
        normal_threshold: 正常结局阈值

    Returns:
        list: 优化后的选择列表
    """
    choice_diffs = await calculate_choice_differences(good_choices, bad_choices)

    normal_choices = good_choices.copy()
    current_affinity = sum(choice["affinity"] for choice in good_choices)

    for diff_info in choice_diffs:
        if current_affinity <= normal_threshold:
            break

        diff = diff_info["diff"]
        if current_affinity - diff > bad_threshold:
            current_affinity -= diff
            normal_choices[diff_info["index"]] = diff_info["bad_choice"]

        if bad_threshold < current_affinity <= normal_threshold:
            break

    return normal_choices


async def extract_best_choices_from_groups(grouped_choices):
    """
    从分组的选择中提取最佳选择

    Args:
        grouped_choices: 按 talk_index 分组的选择

    Returns:
        list: 最佳选择文本列表
    """
    best_choices = []
    for talk_index in sorted(grouped_choices.keys()):
        choices = grouped_choices[talk_index]
        max_affinity = max(c["affinity"] for c in choices)
        best_choice_texts = [
            c["text"] for c in choices if c["affinity"] == max_affinity
        ]
        best_choices.extend(best_choice_texts)
    return best_choices


async def extract_worst_choices_from_groups(grouped_choices):
    """
    从分组的选择中提取最坏选择

    Args:
        grouped_choices: 按 talk_index 分组的选择

    Returns:
        list: 最坏选择文本列表
    """
    worst_choices = []
    for talk_index in sorted(grouped_choices.keys()):
        choices = grouped_choices[talk_index]
        min_affinity = min(c["affinity"] for c in choices)

        if min_affinity < 0:
            # 优先选择负好感度选择
            worst_choice_texts = [
                c["text"] for c in choices if c["affinity"] == min_affinity
            ]
        else:
            # 如果没有负好感度，选择好感度为0的选择
            zero_choices = [c["text"] for c in choices if c["affinity"] == 0]
            if zero_choices:
                worst_choice_texts = zero_choices
            else:
                # 如果没有0好感度，选择最小正好感度
                worst_choice_texts = [
                    c["text"] for c in choices if c["affinity"] == min_affinity
                ]

        if len(worst_choice_texts) > 1:
            worst_choices.append("或者".join(worst_choice_texts))
        else:
            worst_choices.extend(worst_choice_texts)

    return worst_choices


async def format_choice_info(choice, server: str = "global", data_type: str = "live"):
    """
    格式化单个选择信息

    Args:
        choice: 选择数据
        review: 是否为测试模式

    Returns:
        dict: 格式化后的选择信息
    """
    talk_index = choice.get("talk_index", 0)
    affinity = choice.get("affinity", 0)
    affinity_str = (
        str(affinity) if affinity < 0 else f"+{affinity}" if affinity > 0 else "0"
    )

    return {
        "talk_index": talk_index,
        "choice_group": choice["choice_group"],
        "text": f"（{choice['choice_group']}）{await clean_rich_text(await select_text_by_priority(choice['zh_tw_text'], choice['zh_cn_text'], choice['kr_text'], choice.get('ja_text', ''), server, data_type))}({affinity_str})",
        "affinity": affinity,
        "position_type": choice.get("position_type"),
        "group_no": choice.get("group_no"),
    }


async def process_episode_choices(ep, server: str = "global", data_type: str = "live"):
    """
    处理单个剧集的选择

    Args:
        ep: 剧集信息
        review: 是否为测试模式

    Returns:
        tuple: (所有选择列表, 剧集标题)
    """
    all_choices = []
    for position_type, choices in ep["choices"].items():
        for choice in choices:
            choice_info = await format_choice_info(choice, server, data_type)
            choice_info["episode"] = ep["episode"]
            all_choices.append(choice_info)

    title = await select_text_by_priority(
        ep["zh_tw_title"],
        ep["zh_cn_title"],
        ep["kr_title"],
        ep.get("ja_title", ""),
        server,
        data_type,
    )
    return all_choices, title


async def calculate_normal_ending_choice(
    all_episodes_choices, bad_threshold, normal_threshold
):
    """
    计算正常结局选择

    Args:
        all_episodes_choices: 所有结局选择
        bad_threshold: 坏结局阈值
        normal_threshold: 正常结局阈值

    Returns:
        list: 按剧集组织的正常结局选择
    """
    good_ending_choices = []
    bad_ending_choices = []

    for episode_data in all_episodes_choices:
        episode_choices = episode_data["choices"]
        episode_num = episode_data["episode"]

        choices_by_index = await group_choices_by_talk_index(episode_choices)

        for talk_index, choices in choices_by_index.items():
            best_choice, worst_choice = await find_best_and_worst_choices(choices)

            if best_choice and worst_choice:
                good_ending_choices.append(
                    {
                        "episode": episode_num,
                        "talk_index": talk_index,
                        "choice": best_choice,
                        "affinity": best_choice["affinity"],
                    }
                )

                bad_ending_choices.append(
                    {
                        "episode": episode_num,
                        "talk_index": talk_index,
                        "choice": worst_choice,
                        "affinity": worst_choice["affinity"],
                    }
                )

    normal_choices = await optimize_choices_for_normal_ending(
        good_ending_choices, bad_ending_choices, bad_threshold, normal_threshold
    )

    normal_choices_by_episode = {}
    for choice in normal_choices:
        episode = choice["episode"]
        if episode not in normal_choices_by_episode:
            normal_choices_by_episode[episode] = []
        normal_choices_by_episode[episode].append(choice)

    result = []
    for episode, choices in normal_choices_by_episode.items():
        choices.sort(key=lambda x: x["talk_index"])
        choice_texts = [choice["choice"]["text"] for choice in choices]

        result.append({"episode": episode, "choices": choice_texts})

    return result


async def get_character_story(data, hero_id):
    """
    获取角色故事
    Args:
        data: JSON 数据字典
        hero_id: 角色编号
    """
    try:
        story_episodes = []
        ending_episodes = []

        for story in data["story_info"]["json"]:
            if "act" in story and story["act"] == hero_id:
                if story["episode"] in [8, 9, 10]:
                    ending_episodes.append(story)
                else:
                    story_episodes.append(story)

        if not ending_episodes:
            return False, [], {}

        endings = {}
        for episode in ending_episodes:
            if "ending_affinity" in episode:
                if episode["episode"] == 8:
                    endings["bad"] = episode["ending_affinity"]
                elif episode["episode"] == 9:
                    endings["normal"] = episode["ending_affinity"]
                elif episode["episode"] == 10:
                    endings["good"] = episode["ending_affinity"]

        if not endings:
            return False, [], {}

        episode_info = []
        for episode in story_episodes:
            choices = {}
            valid_talk_indexes = set()
            for talk in data["talk"]["json"]:
                if (
                    talk.get("group_no") == episode.get("talk_group")
                    and "affinity_point" in talk
                ):
                    valid_talk_indexes.add(talk.get("talk_index", 0))

            for talk in data["talk"]["json"]:
                if (
                    talk.get("group_no") == episode.get("talk_group")
                    and talk.get("talk_index", 0) in valid_talk_indexes
                ):
                    choice_text_zh_tw = ""
                    choice_text_zh_cn = ""
                    choice_text_kr = ""
                    choice_text_en = ""

                    talk_no = talk.get("no")
                    if talk_no is not None:
                        choice_text_zh_tw = (
                            await get_string_by_type(data, "talk", talk_no)
                        ).get("zh_tw", "")
                        choice_text_zh_cn = (
                            await get_string_by_type(data, "talk", talk_no)
                        ).get("zh_cn", "")
                        choice_text_kr = (
                            await get_string_by_type(data, "talk", talk_no)
                        ).get("kr", "")
                        choice_text_en = (
                            await get_string_by_type(data, "talk", talk_no)
                        ).get("en", "")

                    position_type = talk.get("position_type", 0)
                    if position_type not in choices:
                        choices[position_type] = []
                    choices[position_type].append(
                        {
                            "zh_tw_text": choice_text_zh_tw,
                            "zh_cn_text": choice_text_zh_cn,
                            "kr_text": choice_text_kr,
                            "en_text": choice_text_en,
                            "affinity": talk.get("affinity_point", 0),
                            "choice_group": talk.get("choice_group", 0),
                            "no": talk.get("no"),
                            "talk_index": talk.get("talk_index", 0),
                            "group_no": talk.get("group_no"),
                        }
                    )

            episode_title_zh_tw = ""
            episode_title_zh_cn = ""
            episode_title_kr = ""
            episode_title_en = ""
            episode_name_sno = episode.get("episode_name_sno")
            if episode_name_sno is not None:
                episode_title_zh_tw = (
                    await get_string_by_type(data, "talk", episode_name_sno)
                ).get("zh_tw", "")
                episode_title_zh_cn = (
                    await get_string_by_type(data, "talk", episode_name_sno)
                ).get("zh_cn", "")
                episode_title_kr = (
                    await get_string_by_type(data, "talk", episode_name_sno)
                ).get("kr", "")
                episode_title_en = (
                    await get_string_by_type(data, "talk", episode_name_sno)
                ).get("en", "")

            episode_info.append(
                {
                    "episode": episode.get("episode", 0),
                    "zh_tw_title": episode_title_zh_tw,
                    "zh_cn_title": episode_title_zh_cn,
                    "kr_title": episode_title_kr,
                    "en_title": episode_title_en,
                    "choices": choices,
                }
            )
        return True, episode_info, endings

    except Exception as e:
        logger.error(f"获取好感故事信息时发生错误: {e}, hero_id={hero_id}")
        return False, [], {}


async def format_character_story(
    episode_info, endings, server: str = "global", data_type: str = "live"
):
    """
    格式化角色故事
    Args:
        episode_info: 剧情信息
        endings: 结局信息
        review: 是否为测试
    """
    good_end = ["😃好结局攻略："]
    normal_end = ["🙂一般结局攻略："]
    bad_end = ["🥲坏结局攻略："]

    bad_threshold = endings.get("bad", 0)
    normal_threshold = endings.get("normal", 0)

    if "bad" in endings:
        good_end.append(f"条件：好感度 > {normal_threshold}")
        normal_end.append(f"条件：{bad_threshold} < 好感度 < {normal_threshold}")
        bad_end.append(f"条件：好感度 < {bad_threshold}")

    all_episodes_choices = []

    for ep in episode_info:
        all_choices, title = await process_episode_choices(ep, server, data_type)

        if not all_choices:
            continue

        all_episodes_choices.append(
            {"episode": ep["episode"], "title": title, "choices": all_choices}
        )

        good_end.append(f"\nEP{ep['episode']}：{title}")
        normal_end.append(f"\nEP{ep['episode']}：{title}")
        bad_end.append(f"\nEP{ep['episode']}：{title}")

        all_choices.sort(key=lambda x: x["talk_index"])
        grouped_choices = {}
        for choice in all_choices:
            talk_index = choice["talk_index"]
            if talk_index not in grouped_choices:
                grouped_choices[talk_index] = []
            grouped_choices[talk_index].append(choice)

        good_choices = await extract_best_choices_from_groups(grouped_choices)
        bad_choices = await extract_worst_choices_from_groups(grouped_choices)

        good_end.extend(good_choices)
        bad_end.extend(bad_choices)

    normal_choices_by_episode = await calculate_normal_ending_choice(
        all_episodes_choices, bad_threshold, normal_threshold
    )

    for episode_data in normal_choices_by_episode:
        episode_num = episode_data["episode"]
        choices = episode_data["choices"]

        for i, line in enumerate(normal_end):
            if line.startswith(f"\nEP{episode_num}："):
                normal_end[i + 1 : i + 1] = choices
                break

    result = ["【好感故事攻略】"]
    result.extend(good_end)
    result.extend([""] + normal_end)
    result.extend([""] + bad_end)

    return "\n".join(result)


async def get_base_battle_power(data: dict, entity_type: int, level: int) -> int:
    """
    计算基础战力
    Args:
        data: JSON 数据字典
        entity_type: 实体类型 (1=角色, 2=怪物, 3=恶灵)
        level: 等级

    Returns:
        int: 计算后的基础战力
    """
    if entity_type == 1:
        type_prefix = "BP_hero"
    elif entity_type == 2:
        type_prefix = "BP_monster"
    elif entity_type == 3:
        type_prefix = "BP_raid"

    for kv in data["key_values"]["json"]:
        key_name = kv.get("key_name", "")

        if key_name == f"{type_prefix}_base":
            base_value = float(kv.get("values_data"))
        elif key_name == f"{type_prefix}_level":
            level_value = float(kv.get("values_data"))
        elif key_name == f"{type_prefix}_level_per":
            level_per_value = float(kv.get("values_data"))

    return int(base_value + (level_value + level_per_value * level) * (level - 1))


async def get_hero_grade_value(data: dict, grade: int) -> float:
    """
    获取角色品质加成值
    Args:
        data: JSON 数据字典
        grade: 品质

    Returns:
        float: 品质加成值
    """

    for grade_info in data["hero_grade"]["json"]:
        if grade_info.get("name_sno") == grade:
            return grade_info.get("hero_grade_value", 0.85)
    return 0.85


async def get_hero_level_grade_value(data: dict, level: int) -> float:
    """
    获取角色等级加成值

    Args:
        data: JSON 数据字典
        level: 等级

    Returns:
        float: 等级加成乘数
    """
    level_grades = data["hero_level_grade"]["json"]
    level_grades.sort(key=lambda x: x.get("level", 0))

    for i in range(len(level_grades) - 1, -1, -1):
        grade_data = level_grades[i]
        if grade_data.get("level", 0) <= level:
            return grade_data.get("value", 1.0)
    return 1.0


async def calculate_battle_power(
    data: dict,
    entity_type: int,
    level: int,
    grade: int,
    equipment_power: int = 0,
    equipment_power_per: float = 0.0,
    signature_power_per: float = 0.0,
    contents_buff_power: float = 0.0,
    contents_buff_power_per: float = 0.0,
) -> int:
    """
    计算总战力（完整公式）

    对应游戏函数: HeroStatus::CalculatePower

    战力公式:
        总战力 = 基础战力
               + (等级加成率 - 1) × 基础战力
               + (阶级系数 - 1) × 基础战力
               + 装备固定战力
               + 装备战力百分比 × 基础战力
               + 遗物战力百分比 × 基础战力
               + 内容增益固定战力
               + 内容增益战力百分比 × 基础战力

    Args:
        data: JSON 数据字典
        entity_type: 实体类型 (1=英雄, 2=怪物, 3=恶灵)
        level: 等级
        grade: 阶级品质

        equipment_power: 装备固定战力, 默认0
            计算方式: Σ(每件装备的battle_power)
            例如: 6件装备每件11948, 则 equipment_power = 11948 × 6 = 71688

        equipment_power_per: 装备战力百分比, 默认0.0
            计算方式: Σ(每件装备的battle_power_per)
            例如: 6件装备每件0.1, 则 equipment_power_per = 0.1 × 6 = 0.6
            战力贡献: 0.6 × 基础战力（注意是乘以基础战力，不是装备战力！）

        signature_power_per: 遗物战力百分比, 默认0.0
            计算方式: 遗物的battle_power（最高级生效）
            战力贡献: signature_power_per × 基础战力

        contents_buff_power: 内容增益固定战力, 默认0.0
            包含: 方舟强化战力、灵魂链接战力等
            计算方式: 直接累加到总战力

        contents_buff_power_per: 内容增益战力百分比, 默认0.0
            包含: 星座、建筑、潜能、好感等级等
            战力贡献: contents_buff_power_per × 基础战力

    Returns:
        int: 计算后的总战力(向下取整)
    """
    base_power = await get_base_battle_power(data, entity_type, level)
    grade_value = await get_hero_grade_value(data, grade)
    level_grade_value = await get_hero_level_grade_value(data, level)

    total_power = (
        base_power  # 基础战力
        + (level_grade_value - 1.0) * base_power  # 等级加成战力
        + (grade_value - 1.0) * base_power  # 阶级加成战力
        + equipment_power  # 装备固定战力（直接累加）
        + equipment_power_per * base_power  # 装备百分比战力（乘以基础战力）
        + signature_power_per * base_power  # 遗物百分比战力（乘以基础战力）
        + contents_buff_power  # 内容增益固定战力
        + contents_buff_power_per * base_power  # 内容增益百分比战力
    )

    return int(total_power)


async def get_character_skill_pattern(
    data: dict, hero_no: int, server: str = "global", data_type: str = "live"
) -> list:
    """
    获取角色技能释放顺序
    Args:
        data: JSON 数据字典
        hero_no: 角色编号

    Returns:
        list: 技能释放顺序列表, 每个元素是 (技能名称, 技能类型, 是否为普通攻击)
    """
    try:
        pattern_data = None
        for pattern in data["skill_pattern"]["json"]:
            if pattern.get("hero_no") == hero_no:
                pattern_data = pattern
                break
        if not pattern_data:
            return []

        for hero in data["hero"]["json"]:
            if hero.get("hero_id") == hero_no:
                hero_base_attack = hero.get("base_attack")
                break

        pattern_keys = [key for key in pattern_data.keys() if key.startswith("pattern")]
        pattern_keys.sort(key=lambda x: int(x.replace("pattern", "").replace("_", "")))
        skill_pattern = []
        for key in pattern_keys:
            skill_no = pattern_data.get(key)
            if skill_no == hero_base_attack:
                skill_pattern.append(("普通攻击", "无"))
            else:
                skill_name = ""
                for skill in data["skill"]["json"]:
                    if skill["no"] == skill_no:
                        if "name_sno" not in skill:
                            break
                        skill_name_data = await get_string_by_type(
                            data, "skill", skill["name_sno"]
                        )
                        skill_name_zh_tw = skill_name_data.get("zh_tw", "")
                        skill_name_zh_cn = skill_name_data.get("zh_cn", "")
                        skill_name_kr = skill_name_data.get("kr", "")
                        skill_name_ja = skill_name_data.get("ja", "")
                        skill_type = (
                            await get_string_by_type(data, "system", skill["type"])
                        ).get("zh_tw", "")

                        skill_name = await select_text_by_priority(
                            skill_name_zh_tw,
                            skill_name_zh_cn,
                            skill_name_kr,
                            skill_name_ja,
                            server,
                            data_type,
                        )
                        if skill_name:
                            skill_pattern.append((skill_name, skill_type))
                        break

        return skill_pattern

    except Exception as e:
        logger.error(f"获取角色技能释放顺序时发生错误: {e}")
        return []


async def get_character_attack_range(data: dict, hero_id: int) -> float:
    """获取角色攻击范围

    Args:
        data: JSON数据字典
        hero_id: 角色ID

    Returns:
        float: 攻击范围，如果没有找到则返回0.0

    游戏用的是三维欧几里得距离，公式：
    sqrtf((z - z')^2 + (x - x')^2 + (y - y')^2) <= attackRange

    """
    for skill in data["skill"]["json"]:
        if skill.get("no") == hero_id and skill.get("range"):
            return float(skill.get("range", 0.0))
    return 0.0


async def get_zodiac_name(data, zodiac_type_sno):
    """
    获取星座名称
    Args:
        data: 游戏数据
        zodiac_type_sno: 星座类型编号
    Returns:
        str: 星座名称
    """
    return (await get_string_by_type(data, "ui", zodiac_type_sno)).get("zh_tw", "")


async def get_zodiac_buff_description(data, tooltip_sno, value=None):
    """
    获取星座buff描述
    Args:
        data: 游戏数据
        tooltip_sno: 描述编号
        value: 需要填入的数值（如果有的话）
    Returns:
        str: buff描述
    """
    description = (await get_string_by_type(data, "ui", tooltip_sno)).get("zh_tw", "")

    if value is not None:
        description = description.replace("{0}", str(value))

    return description


async def format_zodiac_nodes(data, zodiac_type):
    """
    格式化指定星座类型的所有节点信息
    Args:
        data: 游戏数据
        zodiac_type: 星座类型
    Returns:
        dict: 包含节点信息和祝福信息的字典
    """
    nodes = []
    blessing = None

    zodiac_nodes = []
    for node in data["zodiac"]["json"]:
        if node.get("zodiac_type") == zodiac_type:
            zodiac_nodes.append(node)
    zodiac_nodes.sort(key=lambda x: x.get("no", 0))

    for node in zodiac_nodes:
        node_no = node.get("no", 0)
        zodiac_node_no = node.get("zodiac_node_no", 0)
        require_nodes = node.get("require_node_no", "0")
        need_point = node.get("need_point", 0)
        tooltip_sno = node.get("tooltip_sno")

        # 祝福节点（没有need_point键）
        is_blessing = "need_point" not in node

        if is_blessing:
            if tooltip_sno:
                blessing = await get_zodiac_buff_description(data, tooltip_sno)
                contents_buff_no = node.get("contents_buff_no")
                if contents_buff_no:
                    for buff in data["contents_buff"]["json"]:
                        if buff.get("no") == contents_buff_no:
                            battle_power_per = buff.get("battle_power_per")
                            if battle_power_per:
                                blessing += f"（战力百分比{battle_power_per}）"
                            break
        else:
            # 普通节点
            node_info = {
                "no": node_no,
                "node_no": zodiac_node_no,
                "require_nodes": require_nodes,
                "need_point": need_point,
                "description": "",
            }

            if "item_rate" in node and node["item_rate"] > 0:
                # 资源增加类型
                item_rate = node["item_rate"]
                formatted_rate = await format_value(item_rate, False, True)

                if tooltip_sno:
                    node_info["description"] = await get_zodiac_buff_description(
                        data, tooltip_sno, formatted_rate
                    )

            elif "contents_buff_no" in node:
                # 属性增加类型
                contents_buff_no = node["contents_buff_no"]

                # 从contents_buff中获取属性信息
                for buff in data["contents_buff"]["json"]:
                    if buff.get("no") == contents_buff_no:
                        for key, value in buff.items():
                            if key != "no" and value != 0:
                                formatted_value = await format_value(value, False, True)

                                if tooltip_sno:
                                    description = await get_zodiac_buff_description(
                                        data, tooltip_sno, formatted_value
                                    )
                                    buff_type_no = node.get("buff_type_no")
                                    buff_type_sno = node.get("buff_type_sno")
                                    prefix = ""

                                    if buff_type_no == 4 and buff_type_sno:
                                        buff_type_info = await get_string_by_type(
                                            data, "system", buff_type_sno
                                        )
                                        type_info = await get_string_by_type(
                                            data, "system", 110045
                                        )
                                        type_text = type_info.get("zh_tw", "")
                                        buff_type_text = buff_type_info.get("zh_tw", "")
                                        if buff_type_text and type_text:
                                            prefix = f"{buff_type_text} {type_text} - "
                                    elif buff_type_no == 1 and buff_type_sno:
                                        type_info = await get_string_by_type(
                                            data, "system", buff_type_sno
                                        )
                                        type_text = type_info.get("zh_tw", "")
                                        if type_text:
                                            prefix = f"{type_text} - "

                                    full_description = prefix + description
                                    battle_power_per = buff.get("battle_power_per")
                                    if battle_power_per:
                                        full_description += (
                                            f"（战力百分比{battle_power_per}）"
                                        )

                                    node_info["description"] = full_description
                                break
                        break

            nodes.append(node_info)

    return {"nodes": nodes, "blessing": blessing}


async def get_love_buff_type_name(buff_type):
    """
    获取好感buff类型名称
    public enum LoveBuffType
    {
        None = 0,
        DestinyStory = 1,
        Battle = 2,
        LoopLostItem = 3,
        TripGift = 4,
        Arbeit = 5,
        Rest = 6,
        BubbleTalk = 7,
        WelcomeRun = 8,
        SpecialTouch = 9,
        Sticker = 18
    }
    Args:
        buff_type: buff类型ID
    Returns:
        str: buff类型名称
    """
    buff_type_names = {
        1: "好感故事",
        2: "战斗属性",
        3: "循环遗失物品",
        4: "约会礼物",
        5: "打工",
        6: "休息",
        7: "领地内气泡对话",
        8: "领地内欢迎奔跑",
        9: "特殊触摸",
        18: "贴纸",
    }
    return buff_type_names.get(buff_type, "")


async def get_building_tooltip(data: dict, town_buff: dict, amount: float) -> str:
    """
    根据town_buff获取建筑buff描述
    Args:
        data: JSON数据字典
        town_buff: town_buff数据
        amount: 数值
    Returns:
        str: 描述文本
    """
    try:
        tooltip_sno = town_buff.get("tooltip_sno")
        amount_kind = town_buff.get("amount_kind", 0)

        if not tooltip_sno:
            return ""

        if amount_kind == 1:  # 整数
            display_value = str(int(amount))
        elif amount_kind == 2:  # 百分比
            display_value = await format_value(amount, False, True, 100.0)
        elif amount_kind == 3:  # 小数
            display_value = f"{amount:.2f}".rstrip("0").rstrip(".")
        else:
            string_info = await get_string_by_type(data, "ui", tooltip_sno)
            return string_info.get("zh_tw", "")

        string_info = await get_string_by_type(data, "ui", tooltip_sno)
        description = string_info.get("zh_tw", "")

        if "{0}" in description:
            description = description.replace("{0}", display_value)

        return description

    except Exception as e:
        logger.error(f"获取建筑buff描述时发生错误: {e}")
        return ""


async def format_building_data(data: dict) -> list:
    """
    格式化建筑数据
    Args:
        data: JSON数据字典
    Returns:
        list: 格式化后的建筑信息列表
    """
    try:
        buildings = []
        for town_obj in data["town_object"]["json"]:
            buff1 = town_obj.get("buff1")
            buff2 = town_obj.get("buff2")
            obj_no = town_obj.get("no")

            if not buff1 or buff2 or not obj_no:
                continue

            town_buff = None
            for buff in data["town_buff"]["json"]:
                if buff.get("no") == buff1:
                    town_buff = buff
                    break

            if not town_buff:
                continue

            buff_type = town_buff.get("buff_type")
            buff_type_no = town_buff.get("buff_type_no")

            if not buff_type or not (50 <= buff_type <= 58) or buff_type_no != 2:
                continue

            building_info = await get_building_basic_info(data, obj_no)
            if not building_info:
                continue

            amount = town_buff.get("amount", 0)
            buff_description = await get_building_tooltip(data, town_buff, amount)

            battle_power_per = ""
            contents_buff_no = town_buff.get("contents_buff_no")
            if contents_buff_no:
                for buff in data["contents_buff"]["json"]:
                    if buff.get("no") == contents_buff_no:
                        battle_power = buff.get("battle_power_per")
                        if battle_power:
                            battle_power_per = f"（战力百分比{battle_power}）"
                        break

            buildings.append(
                {
                    "no": obj_no,
                    "name": building_info["name"],
                    "grade": building_info["grade"],
                    "description": building_info["description"],
                    "img_path": building_info["img_path"],
                    "buff_description": buff_description,
                    "battle_power_per": battle_power_per,
                    "buff_type": buff_type,
                }
            )

        buildings.sort(key=lambda x: x["buff_type"])

        return buildings

    except Exception as e:
        logger.error(f"格式化建筑数据时发生错误: {e}")
        return []


async def get_building_basic_info(data: dict, obj_no: int) -> dict:
    """
    获取建筑基本信息
    Args:
        data: JSON数据字典
        obj_no: 建筑编号
    Returns:
        dict: 建筑基本信息
    """
    try:
        from ...config import TOWN_DIR

        for item in data["item"]["json"]:
            if item.get("no") == obj_no:
                name_sno = item.get("name_sno")
                name = ""
                if name_sno:
                    name_info = await get_string_by_type(data, "item", name_sno)
                    name = name_info.get("zh_tw", "")
                grade_sno = item.get("grade_sno")
                grade = ""
                if grade_sno:
                    grade_info = await get_string_by_type(data, "system", grade_sno)
                    grade = grade_info.get("zh_tw", "")
                desc_sno = item.get("desc_sno")
                description = ""
                if desc_sno:
                    desc_info = await get_string_by_type(data, "item", desc_sno)
                    desc_text = desc_info.get("zh_tw", "")
                    description = await clean_rich_text(desc_text)
                icon_path = item.get("icon_path", "")
                img_path = ""
                if icon_path:
                    img_filename = (
                        icon_path.split("/")[-1] if "/" in icon_path else icon_path
                    )
                    if img_filename:
                        import os

                        for file in os.listdir(TOWN_DIR):
                            if file.lower() == f"{img_filename.lower()}.png":
                                img_path = TOWN_DIR / file
                                break
                return {
                    "name": name,
                    "grade": grade,
                    "description": description,
                    "img_path": img_path,
                }

        return {}

    except Exception as e:
        logger.error(f"获取建筑基本信息时发生错误: {e}, obj_no={obj_no}")
        return {}


async def format_love_level_data(data):
    """
    格式化好感等级数据
    Args:
        data: 游戏数据
    Returns:
        list: 所有好感等级信息的统一列表
    """
    love_levels = []

    for level_data in data["love_level"]["json"]:
        level = level_data.get("level", 0)
        hero_type = level_data.get("hero_type", 0)

        if level <= 9:
            # 1-9级只收集hero_type为1的数据
            if hero_type != 1:
                continue
        else:
            # 10级及以上只收集hero_type为99的数据
            if hero_type != 99:
                continue
        level_info = {
            "no": level_data.get("no"),
            "level": level_data.get("level"),
            "hero_type": level_data.get("hero_type"),
            "lovepoint": level_data.get("lovepoint", 0),
            "total_lovepoint": level_data.get("total_lovepoint", 0),
            "buffs": [],
        }
        for i in range(1, 6):
            buff_type_key = f"buff{i}_type"
            buff_value_key = f"buff{i}_value"
            buff_sno_key = f"buff{i}_sno"

            buff_type = level_data.get(buff_type_key)
            buff_value = level_data.get(buff_value_key)
            buff_sno = level_data.get(buff_sno_key)

            if buff_type or buff_sno:
                buff_info = {
                    "type": buff_type,
                    "value": buff_value,
                    "sno": buff_sno,
                    "description": "",
                }

                if buff_sno:
                    string_info = await get_string_by_type(data, "ui", buff_sno)
                    description = string_info.get("zh_tw", "")
                    display_value = None
                    raw_value = 0.0

                    if buff_type == 1:  # DestinyStory
                        raw_value = float(buff_value) if buff_value else 0.0
                        display_value = str(int(raw_value))
                    elif buff_type == 2:  # Battle
                        # 战斗类型需要检查attack_rate, defence_rate, hp_rate
                        if "attack_rate" in level_data and level_data["attack_rate"]:
                            raw_value = level_data["attack_rate"]
                            display_value = await format_value(
                                raw_value, False, True, 0.001
                            )
                        elif (
                            "defence_rate" in level_data and level_data["defence_rate"]
                        ):
                            raw_value = level_data["defence_rate"]
                            display_value = await format_value(
                                raw_value, False, True, 0.001
                            )
                        elif "hp_rate" in level_data and level_data["hp_rate"]:
                            raw_value = level_data["hp_rate"]
                            display_value = await format_value(
                                raw_value, False, True, 0.001
                            )

                        # 战力加成
                        if buff_value and "contents_buff" in data:
                            for buff in data["contents_buff"]["json"]:
                                if buff.get("no") == buff_value:
                                    battle_power_per = buff.get("battle_power_per")
                                    if battle_power_per and display_value:
                                        description = description.replace(
                                            "{0}", display_value
                                        )
                                        description += (
                                            f"（战力百分比{battle_power_per}）"
                                        )
                                        display_value = None
                                    break
                    elif buff_type == 5:  # Arbeit
                        if "reduce_time" in level_data and level_data["reduce_time"]:
                            raw_value = level_data["reduce_time"]
                            display_value = await format_value(
                                raw_value, False, True, 0.001
                            )
                    elif buff_type == 6:  # Rest
                        if (
                            "increase_recovery" in level_data
                            and level_data["increase_recovery"]
                        ):
                            raw_value = level_data["increase_recovery"]
                            display_value = await format_value(
                                raw_value, False, True, 0.001
                            )
                    else:
                        raw_value = float(buff_value) if buff_value else 0.0
                        display_value = str(int(raw_value))

                    if "{0}" in description:
                        if display_value is None or (
                            raw_value == 0.0 and buff_value is None
                        ):
                            pass
                        else:
                            description = description.replace("{0}", display_value)
                    buff_info["description"] = description
                level_info["buffs"].append(buff_info)
        love_levels.append(level_info)
    love_levels.sort(key=lambda x: x["level"])

    return love_levels


async def get_character_stats_ranking(
    data: dict, hero_id: str, hero_data: dict
) -> dict:
    """
    计算角色1级基础属性在同职业中的排名

    Args:
        data: 游戏数据
        hero_id: 角色ID
        hero_data: 角色数据

    Returns:
        dict: 包含各属性排名信息的字典
    """
    try:
        # 获取当前角色的职业
        current_class = hero_data.get("class_sno")
        if not current_class:
            return {}
        class_heroes = []
        for hero in data["hero"]["json"]:
            if (
                hero.get("class_sno") == current_class
                and hero.get("battle_power_type") == 1
            ):
                class_heroes.append(
                    {
                        "hero_id": hero.get("hero_id"),
                        "attack": int(hero.get("attack", 0)),
                        "defence": int(hero.get("defence", 0)),
                        "max_hp": int(hero.get("max_hp", 0)),
                        "critical_rate": hero.get("critical_rate", 0),
                        "critical_power": hero.get("critical_power", 0),
                    }
                )

        total_count = len(class_heroes)
        if total_count == 0:
            return {}

        # 计算每个属性的排名
        rankings = {}
        stat_names = {
            "attack": "攻击力",
            "defence": "防御力",
            "max_hp": "生命值",
            "critical_rate": "暴击率",
            "critical_power": "暴击威力",
        }

        for stat_key, stat_name in stat_names.items():
            # 按属性值降序排序
            sorted_heroes = sorted(
                class_heroes, key=lambda x: x[stat_key], reverse=True
            )

            # 找到当前角色的排名
            rank = 1
            for i, hero in enumerate(sorted_heroes):
                if hero["hero_id"] == hero_id:
                    rank = i + 1
                    break

            rankings[stat_key] = {
                "name": stat_name,
                "rank": rank,
                "total": total_count,
            }

        return rankings

    except Exception as e:
        logger.error(f"计算属性排名时出错: {e}")
        return {}
