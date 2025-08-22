"""
字符串和多语言文本处理模块
"""
import itertools
import os
import re
import ast
import asyncio
from dataclasses import dataclass, field
from typing import Dict, Any, List
from nonebot.log import logger
from difflib import get_close_matches
from ...config import (
    TOWN_DIR, TRAIT_NAME_MAPPING, 
    PACKAGE_TYPE_MAPPING, STAT_NAME_MAPPING,
    FORMATION_TYPE_MAPPING, SOULLINK_INTEGER_STAT_MAPPING
)


async def select_text_by_priority(zh_tw: str, kr: str, review: bool = False) -> str:
    """
    根据优先级选择文本
    优先级：review ? kr : zh_tw
    Args:
        zh_tw: 繁体中文文本
        kr: 韩文文本
        review: 是否为测试模式
    
    Returns:
        str: 选择的文本
    """
    return kr if review else zh_tw
    # return zh_tw if zh_tw else (kr if review else zh_tw)


async def clean_rich_text(text: str) -> str:
    """
    清理富文本标签
    Args:
        text: 包含富文本标签的输入字符串
    Returns:
        清理后的字符串
    """
    pattern = r'</?color\s*(?:=\s*"?#?[A-Fa-f0-9]+"?\s*)?>|<effect:none>'
    
    return re.sub(pattern, '', text, flags=re.IGNORECASE)


async def concat_color_text(buff_type: int, value: float, type: str, integer: bool = True, use_color_text: bool = False) -> str:
    """
    拼接颜色文本
    Args:
        buff_type: buff effect 类型
        value: 数值
        type: 类型
        integer: 是否为整数
        use_color_text: 是否使用颜色文本
    Returns:
        str: 拼接后的字符串
    """
    if type == "buff":
        if use_color_text:
            color_code = await get_buff_value_color_text(buff_type, value)
            if color_code:
                return f"<color={color_code}>{await format_value(value, integer)}</color>"
            else:
                return await format_value(value, integer)
        else:
            return await format_value(value, integer)
    elif type == "code":
        if use_color_text:
            color_code = await get_code_value_color_text(buff_type)
            if color_code:
                return f"<color={color_code}>{await format_value(value, integer)}</color>"
            else:
                return await format_value(value, integer)
        else:
            return await format_value(value, integer)



async def format_value(value: float, integer: bool) -> str:
    """
    格式化数值
    Args:
        value: 数值
        integer: 是否为整数
    Returns:
        str: 格式化后的字符串
    """
    abs_value = abs(value)
    if integer:
        formatted_str = f"{abs_value:.2f}".rstrip('0').rstrip('.')
        return formatted_str
    else:
        percent_value = abs_value * 100
        formatted_str = f"{percent_value:.2f}".rstrip('0').rstrip('.')
        return f"{formatted_str}%"


async def format_duration(duration: float) -> str:
    """
    格式化持续时间
    Args:
        duration: 持续时间
    Returns:
        str: 格式化后的字符串
    """
    if duration.is_integer():
        return str(int(duration))
    else:
        return str(duration)


async def get_character_skill_description(data, no: int, type: str) -> str:
    """
    获取角色技能值
    Args:
        data: json 数据
        value_id: 技能值编号
        value_type: 技能值类型
    
    Returns:
        str: 格式化后的技能描述
    """

    skill_code = next((code for code in data["skill_code"]["json"] if code["no"] == no), None)
    if skill_code is None:
        return ""
    
    function_key = skill_code.get("function_key", 0)
    use_color_text = False

    if function_key > 29:
        if function_key in (30, 300):
            buff_id = skill_code.get("value", 0)
            buff_code = next((b for b in data["skill_buff"]["json"] if b["no"] == buff_id))
            
            if type == "VALUE":
                return await get_buff_value_text(buff_code.get("buff_effect", 0), buff_code.get("value", 0), use_color_text)
            elif type == "DURATION":
                return await format_duration(buff_code.get("duration", 0))
    elif ((function_key - 28) & 0xFFFFFFFF) < 2 or function_key == 25:
        if type == "DURATION":
            return await format_duration(skill_code.get("duration", 0))
        
        recursive_skill_id = skill_code.get("value", 0)
        referenced_code = next((code for code in data["skill_code"]["json"] if code["no"] == recursive_skill_id))
        ref_function_key = referenced_code.get("function_key", 0)
        
        if ref_function_key in (30, 300):
            buff_id = referenced_code.get("value", 0)
            buff_code = next((b for b in data["skill_buff"]["json"] if b["no"] == buff_id))
            return await get_buff_value_text(buff_code.get("buff_effect", 0), buff_code.get("value", 0), use_color_text)
        else:
            return await get_code_value_text(ref_function_key, referenced_code.get("value", 0), use_color_text)
    if type == "VALUE":
        return await get_code_value_text(function_key, skill_code.get("value", 0), use_color_text)
    elif type == "DURATION":
        return await format_duration(skill_code.get("duration", 0))
    return ""


async def get_code_value_text(function_key: int, value: float, use_color_text: bool) -> str:
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
    return await concat_color_text(function_key, value, "code", (function_key <= 0x1B and (((1 << function_key) % 32) & 0xC000010) != 0 or ((function_key - 1026) & 0xFFFFFFFF) < 2), use_color_text)


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
        return "#E67373" # 红色
    elif function_key in [3, 12, 13, 18, 20, 22]:
        return "#00CC27" # 绿色
    elif function_key in [4, 5, 6]:
        return "#4ABFD3" # 蓝色
    elif function_key in [26, 27] or (function_key & 0xFFFFFFFE) == 0x402:
        return "#FFFFFF" # 白色
    else:
        return ""


async def get_buff_value_text(buff_type: int, value: float, use_color_text: bool) -> str:
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
        if (((buff_type - 10101) & 0xFFFFFFFF) >= 2 and buff_type != 420):
            return await concat_color_text(buff_type, value, "buff", False, use_color_text)
        else:
            return await concat_color_text(buff_type, value, "buff", True, use_color_text)

    if (((buff_type - 10106) & 0xFFFFFFFF) <= 4 and ((1 << (buff_type - 122) % 32) & 0x13) != 0):
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
                if ((buff_type - 2901) & 0xFFFFFFFF) > 0xF or (((1 << (buff_type - 85)) % 32) & 0xFC3F == 0) and (buff_type - 3001) & 0xFFFFFFFF >= 2:
                    return ""
            elif buff_type <= 10111:
                if ( buff_type != 3401 and (buff_type - 10101) & 0xFFFFFFFF > 0xA):
                    return ""
            elif ((buff_type - 10301) & 0xFFFFFFFF >= 2 and (buff_type - 10201) & 0xFFFFFFFF > 1):
                return ""
            if value < 0.0:
                return "#B778FF" # 紫色
            return "#EDA900" # 黄色
        if buff_type > 1702:
            if buff_type > 1906:
                if ( (buff_type - 2301) & 0xFFFFFFFF > 3 or buff_type == 2303 ):
                    return ""
                if value < 0.0:
                    return "#B778FF" # 紫色
                return "#EDA900" # 黄色
            if buff_type != 1703:
                if ( (buff_type - 1901) & 0xFFFFFFFF <= 5 ):
                    if value < 0.0:
                        return "#B778FF" # 紫色
                    return "#EDA900" # 黄色
                return ""
            return "#00CC27" # 绿色
        if buff_type == 1501:
            return "#EDA900" # 黄色
        if buff_type == 1502:
            return "#B778FF" # 紫色
        if buff_type != 1702:
            return ""
        return "#E67373" # 红色
    
    if buff_type <= 503:
        if buff_type <= 313:
            if ((buff_type - 101) & 0xFFFFFFFF < 0xB ):
                if value < 0.0:
                    return "#B778FF" # 紫色
                return "#EDA900" # 黄色
            if ((buff_type - 301) & 0xFFFFFFFF >= 0xD or ((0x1E3F >> (buff_type - 45) % 32) & 1) == 0 ):
                return ""
            return "#E67373"
        
        if buff_type <= 411:
            if ((buff_type - 401) & 0xFFFFFFFF > 0xA or (((1 << (buff_type + 111)) % 32) & 0x601) == 0 ):
                return ""
            return "#00CC27" # 绿色
        if buff_type == 420:
            return "#4ABFD3" # 蓝色
        if ((buff_type - 501) & 0xFFFFFFFF > 2 ):
            return ""
        return "#368AFF" # 蓝色

    if buff_type > 802:
        if buff_type <= 1101:
            if ( (buff_type - 1001) & 0xFFFFFFFF >= 2  and buff_type != 1101 ):
                return ""
        elif ((buff_type - 1401) & 0xFFFFFFFF >= 2 and  buff_type != 1202 ):
            return ""
        if value < 0.0:
            return "#B778FF" # 紫色
        return "#EDA900" # 黄色
    
    if ((buff_type - 511) & 0xFFFFFFFF < 2):
        return "#368AFF" # 蓝色
    if (buff_type != 801 and buff_type != 802):
        return ""
    if value >= 0.0:
        return "#B778FF" # 紫色
    return "#FFDF24" # 黄色



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
        "attack", "defence", "hp", "dodge", "mana_crystal","mana_dust", "gold",
        "hit", "attack_per_level", "defence_per_level", "hp_per_level"
    }

    PERCENTAGE_TYPE = {
        "attack_rate", "defence_rate", "hp_rate", "critical_rate",
        "critical_power", "physical_resist", "magic_resist", "life_leech",
        "critical_resist", "life_leech_buff", "human_type_damage", "furry_type_damage",
        "undead_type_damage", "elf_type_damage", "angel_type_damage", "demon_type_damage", "chaos_type_damage"
    }

    if (buff_type in PERCENTAGE_TYPE):
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
        use_color_text: 是否使用颜色文本，True时保留富文本格式，False时清理富文本
    Returns:
        str: 处理后的技能描述
    """

    if use_color_text:
        processed_text = description
    else:
        processed_text = await clean_rich_text(description)
    placeholder_pattern = r'<\s*(\d+)\.(VALUE|DURATION)\s*>'
    matches = list(re.finditer(placeholder_pattern, processed_text))

    async def get_value_for_match(match):
        no = int(match.group(1))
        type_str = match.group(2)
        return await get_character_skill_description(data, no, type_str)

    for match, replacement in zip(reversed(matches), reversed(await asyncio.gather(*[get_value_for_match(m) for m in matches]))):
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
    return FORMATION_TYPE_MAPPING.get(formation_no, "")


async def get_string_by_type(data, string_type, no):
    """
    获取字符串
    Args:
        data: JSON 数据字典
        string_type: string 类型的都行，例如 ui, character, item, etc.
        no: 字符串编号
    Returns:
        dict: 包含不同语言的文本, 键为 'zh_tw', 'zh_cn', 'kr', 'en'
    """

    for string in data[f"string_{string_type}"]["json"]:
        if string["no"] == no:
            return {
                "zh_tw": string.get("zh_tw", ""),
                "zh_cn": string.get("zh_cn", ""),
                "kr": string.get("kr", ""),
                "en": string.get("en", "")
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
        # 0x51EB851F 是 2^37 / 100 的向上取整，用来模拟除 100，加快运算
        # (0x51EB851F * birthday >> 37) 等价于 birthday / 100
        # (0x51EB851F * birthday >> 63) 用来提取最高位
        month = ((0x51EB851F * birthday) >> 37) % 32 + ((0x51EB851F * birthday >> 63) & 0xFFFFFFFFFFFFFFFF) % 64
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
                "zh_tw": char.get("zh_tw", ""),
                "zh_cn": char.get("zh_cn", ""),
                "kr": char.get("kr", ""),
                "en": char.get("en", "")
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
    
    # 名称作为键，保存概率最高的物品
    name_to_best_item = {}
    
    for item in drop_items:
        item_name = item[0]['zh_tw']
        item_rate = item[2]
        
        # 如果名称还没有记录，或者当前概率更高，则更新
        if item_name not in name_to_best_item or item_rate > name_to_best_item[item_name][2]:
            name_to_best_item[item_name] = item
    
    # 将字典值转换为列表
    unique_items = list(name_to_best_item.values())
    
    # 按掉落率从高到低排序
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
                            "zh_tw": string.get("zh_tw", ""),
                            "zh_cn": string.get("zh_cn", ""),
                            "kr": string.get("kr", ""),
                            "en": string.get("en", "")
                        }
    return {"zh_tw": "", "zh_cn": "", "kr": "", "en": ""}


async def get_character_cv(data, hero_desc):
    """
    获取角色配音
    Args:
        data: JSON 数据字典
        hero_desc: 角色描述
    
    Returns:
        dict: 包含韩语和日语配音, 键为 'kr', 'ja'
    """
    cv_kr = (await get_string_character(data, hero_desc.get("cv_sno", 0))).get("zh_tw", "") if hero_desc else ""
    cv_ja = (await get_string_character(data, hero_desc.get("cv_jp_sno", 0))).get("zh_tw", "") if hero_desc else ""
    cv_ja = cv_ja if cv_ja != cv_kr and cv_ja != "" else ""

    return {"kr": cv_kr, "ja": cv_ja}


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
            # only get the date part, not the time
            start_date = movie.get("start_date", "").split()[0]
            if start_date and start_date != "2999-12-31":  # 排除默认日期. exclude default date
                release_date = start_date
                break
    
    
    # 如果找到日期返回该日期，否则返回默认日期
    # if found date, return the date, otherwise return default date
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
    # 收集所有相关等级的数据
    # collect all related level data
    level_data = []
    for level in data["arbeit_fairy_level"]["json"]:
        if level.get("hero_no") == hero_id:
            level_data.append(level)
    
    if not level_data:
        return {"initial": "", "max": ""}
    
    # 按等级排序
    # sort by level
    level_data.sort(key=lambda x: x.get("level", 0))
    
    # 获取初始等级和满级数据
    # get initial level and max level data
    initial_level = level_data[0]
    max_level = level_data[-1]
    
    # 获取初始属性
    # get initial traits
    initial_traits = []
    for trait, value in initial_level.items():
        if trait in TRAIT_NAME_MAPPING and value > 0:
            initial_traits.append(f"{TRAIT_NAME_MAPPING[trait]}{value}⭐")
    
    # 获取满级属性
    # get max traits
    max_traits = []
    for trait, value in max_level.items():
        if trait in TRAIT_NAME_MAPPING and value > 0:
            max_traits.append(f"{TRAIT_NAME_MAPPING[trait]}{value}⭐")
    
    # 格式化文本
    # format text
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
    # 在HeroGift.json中查找角色的喜好礼物
    gift_items = []
    for gift in data["hero_gift"]["json"]:
        if gift.get("hero_no") == hero_id:
            # 获取prefer_gift_items字符串并分割成列表
            prefer_items = gift.get("prefer_gift_items", "").split(",")
            prefer_items = [item.strip() for item in prefer_items if item.strip()]
            for item_no in prefer_items:
                gift_items.append((await get_string_item(data, item_no)).get("zh_tw", ""))
    
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


async def get_character_skill(data, skill_no, support=False):
    """
    获取角色技能
    Args:
        data: JSON 数据字典
        skill_no: 技能编号
        support: 是否为支援技能
    Returns:
        dict: 包含技能信息
    """
    skill_data_list = []
    skill_name_zh_tw = ""
    skill_name_zh_cn = ""
    skill_name_kr = ""
    skill_name_en = ""
    skill_descriptions = []
    skill_icon_info = None
    
    for skill in data["skill"]["json"]:
        if skill["no"] == skill_no:
            skill_data_list.append(skill)
            if not skill_icon_info:
                icon_prefab = skill.get("icon_prefab")
                # 这里是适配数据表里面没有的转变形态技能的着色(光凯)
                if icon_prefab == 14:
                    skill_icon_info = {
                        "icon": "Icon_Sub_Change",
                        "color": "#e168eb"
                    }
                elif icon_prefab:
                    for icon_data in data["skill_icon"]["json"]:
                        if icon_data["no"] == icon_prefab:
                            skill_icon_info = {
                                "icon": icon_data["icon"],
                                "color": f"#{icon_data['color']}"
                            }
                            break
    
    if skill_data_list:
        skill_name_zh_tw = (await get_string_by_type(data, "skill", skill_data_list[0]["name_sno"])).get("zh_tw", "")
        skill_name_zh_cn = (await get_string_by_type(data, "skill", skill_data_list[0]["name_sno"])).get("zh_cn", "")
        skill_name_kr = (await get_string_by_type(data, "skill", skill_data_list[0]["name_sno"])).get("kr", "")
        skill_name_en = (await get_string_by_type(data, "skill", skill_data_list[0]["name_sno"])).get("en", "")
        
        if support:
            # 支援技能，获取最高等级的技能描述
            max_level_skill = max(skill_data_list, key=lambda x: x.get("level", 1))
            desc_tw = await process_skill_description(data, (await get_string_by_type(data, "skill", max_level_skill["tooltip_sno"])).get("zh_tw", ""), False)
            desc_cn = await process_skill_description(data, (await get_string_by_type(data, "skill", max_level_skill["tooltip_sno"])).get("zh_cn", ""), False)
            desc_kr = await process_skill_description(data, (await get_string_by_type(data, "skill", max_level_skill["tooltip_sno"])).get("kr", ""), False)
            desc_en = await process_skill_description(data, (await get_string_by_type(data, "skill", max_level_skill["tooltip_sno"])).get("en", ""), False)
            skill_descriptions.append({
                "desc_zh_tw": desc_tw,
                "desc_zh_cn": desc_cn,
                "desc_kr": desc_kr,
                "desc_en": desc_en,
                "type": "support"
            })
        else:
            # 非支援技能，获取所有等级的技能描述
            for skill_data in skill_data_list:
                hero_level = skill_data.get("hero_level", 1)
                desc_tw = await process_skill_description(data, (await get_string_by_type(data, "skill", skill_data["tooltip_sno"])).get("zh_tw", ""), False)
                desc_cn = await process_skill_description(data, (await get_string_by_type(data, "skill", skill_data["tooltip_sno"])).get("zh_cn", ""), False)
                desc_kr = await process_skill_description(data, (await get_string_by_type(data, "skill", skill_data["tooltip_sno"])).get("kr", ""), False)
                desc_en = await process_skill_description(data, (await get_string_by_type(data, "skill", skill_data["tooltip_sno"])).get("en", ""), False)
                skill_descriptions.append({
                    "desc_zh_tw": desc_tw,
                    "desc_zh_cn": desc_cn,
                    "desc_kr": desc_kr,
                    "desc_en": desc_en,
                    "hero_level": hero_level
                })
    
    return {
        "name": {
            "zh_tw": skill_name_zh_tw,
            "zh_cn": skill_name_zh_cn,
            "kr": skill_name_kr,
            "en": skill_name_en
        },
        "descriptions": skill_descriptions,
        "icon_info": skill_icon_info,
        "support": support
    }



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
        "good": "TRIP_KEYWORD_GRADE_POINT_GOOD"
    }[keyword_type]
    
    points = next((kv.get("values_data") for kv in data["key_values"]["json"] 
                    if kv.get("key_name") == key_name))
    return ast.literal_eval(points)


async def get_story_chapter_name(data: dict, story: dict, review: bool = False) -> str:
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
        chapter_format = await select_text_by_priority(chapter_format_data["zh_tw"], chapter_format_data["kr"], review)
        return chapter_format.format(chapter)
    else:
        default_data = await get_string_by_type(data, "ui", 652000)
        return await select_text_by_priority(default_data["zh_tw"], default_data["kr"], review)



async def get_character_keyword_source(data: dict, source_sno: int, details: int, keyword_type: int, review: bool = False) -> tuple[str, str]:
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
        story = next((s for s in data["story_info"]["json"] if s["no"] == details), None)
        if story:
            desc_data = await get_string_by_type(data, "ui", source_sno)
            desc = await select_text_by_priority(desc_data.get("zh_tw", ""), desc_data.get("kr", ""), review)
            if desc:
                source = desc.format(await get_story_chapter_name(data, story, review), story.get("episode", 0))
    # 地点来源
    elif keyword_type == 7:
        town_location = next((loc for loc in data["town_location"]["json"] if loc["no"] == details), None)
        if town_location:
            location_data = await get_string_by_type(data, "town", town_location.get("location_name_sno"))
            location = await select_text_by_priority(location_data.get("zh_tw", ""), location_data.get("kr", ""), review)
            desc_data = await get_string_by_type(data, "ui", source_sno)
            desc = await select_text_by_priority(desc_data.get("zh_tw", ""), desc_data.get("kr", ""), review)
            if desc:
                source = desc.format(location)
    # 通用数值来源
    elif ((1 << keyword_type) & 0xFFFFFFFF) & 0x370 != 0:
        desc_data = await get_string_by_type(data, "ui", source_sno)
        desc = await select_text_by_priority(desc_data.get("zh_tw", ""), desc_data.get("kr", ""), review)
        if desc:
            source = desc.format(details)
    # 固定文本来源
    elif keyword_type in {101, 102, 103}:
        string_data = await get_string_by_type(data, "ui", 619000 + keyword_type)
        source = await select_text_by_priority(string_data.get("zh_tw", ""), string_data.get("kr", ""), review)
    # 获取地点信息
    location = "通用"
    town_location = next((loc for loc in data["town_location"]["json"] if loc["no"] == details), None)
    if town_location:
        location_data = await get_string_by_type(data, "town", town_location.get("location_name_sno"))
        location = await select_text_by_priority(location_data.get("zh_tw", ""), location_data.get("kr", ""), review)
    return source, location


async def get_character_keyword_info(data: dict, keyword_info: dict, trip_info: dict, review: bool = False) -> dict:
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
    name = name_data.get(await select_text_by_priority("zh_tw", "kr", review), "")
    
    # 关键字等级
    grade_data = await get_string_by_type(data, "system", grade_sno)
    grade = grade_data.get("zh_tw", "")
    
    # 关键字来源和地点信息
    source, location = await get_character_keyword_source(
        data,
        keyword_info.get("keyword_source", 0),
        keyword_info.get("keyword_get_details", 0),
        keyword_info.get("keyword_type"),
        review
    )
    
    return {
        "name": name,
        "type": keyword_type,
        "favor_point": favor_point,
        "grade": grade,
        "source": source,
        "location": location,
        "keyword_get_details": keyword_info.get("keyword_get_details")
    }



async def get_character_keyword(data: dict, hero_id: int, review: bool = False) -> str:
    """
    获取角色关键字
    Args:
        data: JSON 数据字典
        hero_id: 角色编号
        review: 是否为测试
    """
    trip_keywords = []
    keyword_msgs = []
    
    for trip in data["trip_hero"]["json"]:
        if trip.get("hero_no") == hero_id:
            keyword_info = next((k for k in data["trip_keyword"]["json"] 
                                if k["no"] == trip.get("keyword_no")), None)
            if keyword_info:
                keyword = await get_character_keyword_info(data, keyword_info, trip, review)
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


async def get_character_town_object(data: dict, hero_id: int, review=False) -> dict:
    """
    获取角色专属领地物品
    Args:
        data: JSON 数据字典
        hero_id: 角色编号
    
    Returns:
        list: 物品信息列表 [(物品编号, 物品名称, 物品品质, 物品类型, 物品描述, 图片路径), ...]
    """
    for obj in data["town_object"]["json"]:
        if obj.get("hero") == hero_id:
            obj_no = obj.get("no")
            buff2_sno = obj.get("buff2")
            if not obj_no:
                continue
            
            # 获取prefab作为图片名称
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
                    name = await select_text_by_priority((await get_string_item(data, obj_no)).get("zh_tw", ""), (await get_string_item(data, obj_no)).get("kr", ""), review)
                    
                    # 获取物品品质
                    grade = ""
                    grade_sno = item.get("grade_sno")
                    if grade_sno:
                        grade = await select_text_by_priority((await get_string_by_type(data, "system", grade_sno)).get("zh_tw", ""), (await get_string_by_type(data, "system", grade_sno)).get("kr", ""), review)
                    
                    # 获取物品类型
                    slot_type = ""
                    slot_limit_sno = item.get("slot_limit_sno")
                    if slot_limit_sno:
                        slot_type = await select_text_by_priority((await get_string_by_type(data, "ui", slot_limit_sno)).get("zh_tw", ""), (await get_string_by_type(data, "ui", slot_limit_sno)).get("kr", ""), review)
                    
                    # 获取物品描述

                    desc_sno = item.get("desc_sno")
                    if desc_sno:
                        for string in data["string_item"]["json"]:
                            if string.get("no") == desc_sno:
                                zh_tw = string.get("zh_tw", "")
                                kr = string.get("kr", "")
                                desc_text = await select_text_by_priority(zh_tw, kr, review)
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
                            "battle_power_per": battle_power_per
                        }



async def get_character_town_object_task(data: dict, obj_no: int, review=False) -> list:
    """
    获取角色专属领地物品任务
    Args:
        data: JSON 数据字典
        obj_no: 物品编号
    
    Returns:
        list: 任务信息列表
    """
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
                                    rarity_kr = string.get("kr", "")
                                    rarity = await select_text_by_priority(rarity_zh_tw, rarity_kr, review)
                                    break
                        
                        # 获取任务名称
                        name = ""
                        name_sno = arbeit.get("name_sno")
                        if name_sno:
                            for string in data["string_town"]["json"]:
                                if string.get("no") == name_sno:
                                    name_zh_tw = string.get("zh_tw", "")
                                    name_kr = string.get("kr", "")
                                    name = await select_text_by_priority(name_zh_tw, name_kr, review)
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
                            item_value = arbeit.get(f"item{i}_value")
                            if item_no and item_value:
                                # 查找物品名称
                                for item in data["item"]["json"]:
                                    if item.get("no") == item_no:
                                        name_sno = item.get("name_sno")
                                        if name_sno:
                                            item_name = await get_string_by_type(data, "item", name_sno)
                                            item_name = await select_text_by_priority(item_name["zh_tw"], item_name["kr"], review)
                                            rewards.append(f"{item_name}x{item_value}")
                        
                        # 添加任务信息
                        tasks_info.append({
                            "name": name,
                            "rarity": rarity,
                            "time": time_hours,
                            "traits": traits,
                            "stress": arbeit.get("stress", 0),
                            "exp": arbeit.get("arbeit_exp", 0),
                            "rewards": rewards
                        })
                        
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
    messages = []
    shop_items = []
    
    # 获取礼包类型显示名称
    package_type_name = PACKAGE_TYPE_MAPPING.get(item_type, '特殊礼包')
    
    # 获取符合条件的商店物品
    for shop_item in data["cash_shop_item"]["json"]:
        if shop_item.get("type") == item_type and shop_item.get("type_value") == str(gate_info["no"]):
            shop_items.append(shop_item)
    
    if shop_items:
        for shop_item in shop_items:
            package_info = []
            package_info.append(f"▼【{package_type_name}】")
            
            # 获取礼包名称和描述
            name_sno = shop_item.get("name_sno")
            package_name = (await get_string_by_type(data, "cashshop", name_sno)).get("zh_tw", "")
            
            info_sno = shop_item.get("item_info_sno")
            package_desc = (await get_string_by_type(data, "cashshop", info_sno)).get("zh_tw", "")
            
            desc_sno = shop_item.get("desc_sno")
            limit_desc = (await get_string_by_type(data, "ui", desc_sno)).get("zh_tw", "").format(shop_item.get("limit_buy", 0))
            
            # 基本信息部分
            basic_info = [
                f"礼包名称：{package_name}"
            ]
            if package_desc:
                basic_info.append(f"礼包描述：{package_desc}")
            basic_info.extend([
                f"{limit_desc}",
                f"剩余时间：{shop_item.get('limit_hour', 0)}小时"
            ])
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


async def get_character_soullink(data: dict, hero_id: int, review: bool = False) -> list:
    """
    获取角色灵魂链接
    Args:
        data: JSON 数据字典
        hero_id: 角色编号
        review: 是否为测试
    """
    soullink_info = []
    
    # 查找所有包含该角色的灵魂链接
    for link in data["soullink"]["json"]:
        # 动态查找所有hero槽位键
        hero_keys = [key for key in link.keys() if key.startswith("group_hero") and link[key] == hero_id]
        
        if not hero_keys:
            continue  # 如果没有找到包含目标角色的槽位，跳过此链接
        
        # 收集所有角色ID
        hero_ids = []
        for key in link.keys():
            if key.startswith("group_hero") and link[key] > 0:
                hero_ids.append(link[key])
        
        if not hero_ids:
            continue
        
        # 获取灵魂链接标题和故事
        title = await get_string_by_type(data, "character", link.get("group_title"))
        title = await select_text_by_priority(title["zh_tw"], title["kr"], review)
        
        story = await get_string_by_type(data, "character", link.get("group_story"))
        story = await select_text_by_priority(story["zh_tw"], story["kr"], review)
        
        # 获取所有角色名称
        hero_names = []
        for hid in hero_ids:
            name_data = await get_string_character(data, hid, special=True)
            name_zh_tw = name_data["zh_tw"]
            name_kr = name_data["kr"]
            name = await select_text_by_priority(name_zh_tw, name_kr, review)
            if name:
                hero_names.append(name)
                
        # 获取收集效果
        collection_effects = []
        
        if collection_id := link.get("collection"):
            # 按condition_list排序
            collection_items = sorted(
                [item for item in data["soullink_collection"]["json"] 
                    if item.get("collection_group") == collection_id],
                key=lambda x: x.get("condition_list", 0)
            )
            
            for item in collection_items:
                # 获取条件文本
                condition_string_no = item.get("condition_string")
                condition_data = await get_string_by_type(data, "ui", condition_string_no)
                condition_text = await select_text_by_priority(condition_data["zh_tw"], condition_data["kr"], review)
                # 格式化条件文本
                condition_text = condition_text.format(
                    item.get("condition_count", 0),
                    item.get("condition_count", 0)
                )
                
                # 获取buff效果
                buff_effects = []
                if buff_no := item.get("contents_buff_no"):
                    buff = next((b for b in data["contents_buff"]["json"] 
                                if b.get("no") == buff_no), None)
                    if buff:
                        # 处理所有属性，包括战力加成
                        for key, value in buff.items():
                            if key in STAT_NAME_MAPPING:
                                stat_name = STAT_NAME_MAPPING[key]
                                if key in SOULLINK_INTEGER_STAT_MAPPING:
                                    buff_effects.append(f"{stat_name}：{await format_value(value, True)}%")
                                else:
                                    buff_effects.append(f"{stat_name}：{await format_value(value, False)}")
                        
                        # 战力百分比加成
                        battle_power_per = buff.get("battle_power_per", 0)
                        if battle_power_per != 0:
                            buff_effects.append(f"战力百分比：{battle_power_per}")
                        
                        # 固定值战力加成
                        battle_power = buff.get("battle_power", 0)
                        if battle_power != 0:
                            buff_effects.append(f"战力加成：{int(battle_power)}")
                
                if condition_text and buff_effects:
                    collection_effects.append({
                        "condition": condition_text,
                        "effects": buff_effects
                    })
        
        # 添加到结果列表
        soullink_info.append({
            "title": title,
            "heroes": hero_names,
            "story": story,
            "effects": collection_effects,
            "open_date": link.get("open_date", "")
        })
    
    return soullink_info


async def get_character_signature_value(data, level_group):
    """获取角色遗物值
    
    Args:
        data: JSON 数据字典
        level_group: 遗物等级组编号
    
    Returns:
        dict: 包含遗物属性统计信息
    """
    max_level_data = None
    max_level = 0
    
    # 这个遗物的最大等级（45）
    for level_data in data["signature_level"]["json"]:
        if level_data["group"] == level_group:
            if level_data["signature_level"] > max_level:
                max_level = level_data["signature_level"]
    
    # 再找到最大等级的数据
    for level_data in data["signature_level"]["json"]:
        if level_data["group"] == level_group and level_data["signature_level"] == max_level:
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


async def get_character_signature(data, hero_id):
    """获取角色遗物
    
    Args:
        data: JSON 数据字典
        hero_id: 角色编号
    
    Returns:
        dict: 包含遗物信息
    """

    skill_descriptions = []
    signature_bg_path = ""
    
    # 在Signature中查找对应角色的遗物
    for signature in data["signature"]["json"]:
        if signature["hero_sno"] == hero_id:
            signature_data = signature
            if signature_bg_path := signature.get("signature_bg_path"):
                signature_bg_path = f"Img_Signature_{signature_bg_path}.png"
            break
    
    if signature_data:
        # 获取遗物名称
        signature_name_zh_tw = (await get_string_by_type(data, "skill", signature_data["signature_name_sno"])).get("zh_tw", "")
        signature_name_zh_cn = (await get_string_by_type(data, "skill", signature_data["signature_name_sno"])).get("zh_cn", "")
        signature_name_kr = (await get_string_by_type(data, "skill", signature_data["signature_name_sno"])).get("kr", "")
        signature_name_en = (await get_string_by_type(data, "skill", signature_data["signature_name_sno"])).get("en", "")
        # 获取遗物技能名称
        signature_title_zh_tw = (await get_string_by_type(data, "skill", signature_data["skill_name_sno"])).get("zh_tw", "")
        signature_title_zh_cn = (await get_string_by_type(data, "skill", signature_data["skill_name_sno"])).get("zh_cn", "")
        signature_title_kr = (await get_string_by_type(data, "skill", signature_data["skill_name_sno"])).get("kr", "")
        signature_title_en = (await get_string_by_type(data, "skill", signature_data["skill_name_sno"])).get("en", "")
        # 获取遗物描述
        signature_desc_zh_tw = (await get_string_by_type(data, "skill", signature_data["tooltip_explain_sno"])).get("zh_tw", "")
        signature_desc_zh_cn = (await get_string_by_type(data, "skill", signature_data["tooltip_explain_sno"])).get("zh_cn", "")
        signature_desc_kr = (await get_string_by_type(data, "skill", signature_data["tooltip_explain_sno"])).get("kr", "")
        signature_desc_en = (await get_string_by_type(data, "skill", signature_data["tooltip_explain_sno"])).get("en", "")
        # 获取所有等级的技能描述
        for i in range(1, 8):
            sno_key = f"skill_tooltip_sno{i}"
            if sno_key in signature_data:
                tooltip_sno = signature_data[sno_key]
                # 处理数值标签
                desc_tw = await process_skill_description(data, (await get_string_by_type(data, "skill", tooltip_sno)).get("zh_tw", ""), False)
                desc_cn = await process_skill_description(data, (await get_string_by_type(data, "skill", tooltip_sno)).get("zh_cn", ""), False)
                desc_kr = await process_skill_description(data, (await get_string_by_type(data, "skill", tooltip_sno)).get("kr", ""), False)
                desc_en = await process_skill_description(data, (await get_string_by_type(data, "skill", tooltip_sno)).get("en", ""), False)

                skill_descriptions.append({
                    "desc_zh_tw": desc_tw,
                    "desc_zh_cn": desc_cn,
                    "desc_kr": desc_kr,
                    "desc_en": desc_en,
                    "level": i
                })
    # 添加图标路径
    if signature_data:
        level_group = signature_data.get("level_group")
        signature_stats = await get_character_signature_value(data, level_group) if level_group else []
        
        return {
            "name": {
                "zh_tw": signature_name_zh_tw,
                "zh_cn": signature_name_zh_cn,
                "kr": signature_name_kr,
                "en": signature_name_en
            },
            "title": {
                "zh_tw": signature_title_zh_tw,
                "zh_cn": signature_title_zh_cn,
                "kr": signature_title_kr,
                "en": signature_title_en
            },
            "description": {
                "zh_tw": signature_desc_zh_tw,
                "zh_cn": signature_desc_zh_cn,
                "kr": signature_desc_kr,
                "en": signature_desc_en
            },
            "skills": skill_descriptions,
            "stats": signature_stats[0] if signature_stats else [],
            "max_level": signature_stats[1] if len(signature_stats) > 1 else 0,
            "max_level_battle_power_per": signature_stats[2] if len(signature_stats) > 2 else 0,
            "bg_path": signature_bg_path
        }
    
    return {
        "name": {"zh_tw": "", "zh_cn": "", "kr": "", "en": ""},
        "title": {"zh_tw": "", "zh_cn": "", "kr": "", "en": ""},
        "description": {"zh_tw": "", "zh_cn": "", "kr": "", "en": ""},
        "skills": [],
        "stats": [],
        "max_level": 0,
        "max_level_battle_power_per": 0,
        "bg_path": ""
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
            choice_diffs.append({
                "index": i,
                "diff": diff,
                "good_choice": good_choice,
                "bad_choice": bad_choice
            })
    
    return sorted(choice_diffs, key=lambda x: x["diff"], reverse=True)


async def optimize_choices_for_normal_ending(good_choices, bad_choices, bad_threshold, normal_threshold):
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
        best_choice_texts = [c["text"] for c in choices if c["affinity"] == max_affinity]
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
            worst_choice_texts = [c["text"] for c in choices if c["affinity"] == min_affinity]
        else:
            # 如果没有负好感度，选择好感度为0的选择
            zero_choices = [c["text"] for c in choices if c["affinity"] == 0]
            if zero_choices:
                worst_choice_texts = zero_choices
            else:
                # 如果没有0好感度，选择最小正好感度
                worst_choice_texts = [c["text"] for c in choices if c["affinity"] == min_affinity]
        
        if len(worst_choice_texts) > 1:
            worst_choices.append("或者".join(worst_choice_texts))
        else:
            worst_choices.extend(worst_choice_texts)
    
    return worst_choices


async def format_choice_info(choice, review=False):
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
    affinity_str = str(affinity) if affinity < 0 else f"+{affinity}" if affinity > 0 else "0"
    
    return {
        "talk_index": talk_index,
        "choice_group": choice["choice_group"],
        "text": f"（{choice['choice_group']}）{await clean_rich_text(await select_text_by_priority(choice['zh_tw_text'], choice['kr_text'], review))}({affinity_str})",
        "affinity": affinity,
        "position_type": choice.get("position_type"),
        "group_no": choice.get("group_no"),
    }


async def process_episode_choices(ep, review=False):
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
            choice_info = await format_choice_info(choice, review)
            choice_info["episode"] = ep['episode']
            all_choices.append(choice_info)
    
    title = await select_text_by_priority(ep['zh_tw_title'], ep['kr_title'], review)
    return all_choices, title


async def calculate_normal_ending_choice(all_episodes_choices, bad_threshold, normal_threshold):
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
                good_ending_choices.append({
                    "episode": episode_num,
                    "talk_index": talk_index,
                    "choice": best_choice,
                    "affinity": best_choice["affinity"]
                })
                
                bad_ending_choices.append({
                    "episode": episode_num,
                    "talk_index": talk_index,
                    "choice": worst_choice,
                    "affinity": worst_choice["affinity"]
                })
    
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
        
        result.append({
            "episode": episode,
            "choices": choice_texts
        })
    
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
            if ("act" in story and story["act"] == hero_id):
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
                if talk.get("group_no") == episode.get("talk_group") and "affinity_point" in talk:
                    valid_talk_indexes.add(talk.get("talk_index", 0))
            
            for talk in data["talk"]["json"]:
                if (talk.get("group_no") == episode.get("talk_group") and 
                    talk.get("talk_index", 0) in valid_talk_indexes):
                    choice_text_zh_tw = ""
                    choice_text_zh_cn = ""
                    choice_text_kr = ""
                    choice_text_en = ""
                    
                    talk_no = talk.get("no")
                    if talk_no is not None:
                        choice_text_zh_tw = (await get_string_by_type(data, "talk", talk_no)).get("zh_tw", "")
                        choice_text_zh_cn = (await get_string_by_type(data, "talk", talk_no)).get("zh_cn", "")
                        choice_text_kr = (await get_string_by_type(data, "talk", talk_no)).get("kr", "")
                        choice_text_en = (await get_string_by_type(data, "talk", talk_no)).get("en", "")
                    
                    position_type = talk.get("position_type", 0)
                    if position_type not in choices:
                        choices[position_type] = []
                    choices[position_type].append({
                        "zh_tw_text": choice_text_zh_tw,
                        "zh_cn_text": choice_text_zh_cn,
                        "kr_text": choice_text_kr,
                        "en_text": choice_text_en,
                        "affinity": talk.get("affinity_point", 0),
                        "choice_group": talk.get("choice_group", 0),
                        "no": talk.get("no"),
                        "talk_index": talk.get("talk_index", 0),
                        "group_no": talk.get("group_no")
                    })
            
            episode_title_zh_tw = ""
            episode_title_zh_cn = ""
            episode_title_kr = ""
            episode_title_en = ""
            episode_name_sno = episode.get("episode_name_sno")
            if episode_name_sno is not None:
                episode_title_zh_tw = (await get_string_by_type(data, "talk", episode_name_sno)).get("zh_tw", "")
                episode_title_zh_cn = (await get_string_by_type(data, "talk", episode_name_sno)).get("zh_cn", "")
                episode_title_kr = (await get_string_by_type(data, "talk", episode_name_sno)).get("kr", "")
                episode_title_en = (await get_string_by_type(data, "talk", episode_name_sno)).get("en", "")
            
            episode_info.append({
                "episode": episode.get("episode", 0),
                "zh_tw_title": episode_title_zh_tw,
                "zh_cn_title": episode_title_zh_cn,
                "kr_title": episode_title_kr,
                "en_title": episode_title_en,
                "choices": choices
            })
        return True, episode_info, endings
        
    except Exception as e:
        logger.error(f"获取好感故事信息时发生错误: {e}, hero_id={hero_id}")
        return False, [], {}


async def format_character_story(episode_info, endings, review=False):
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
    
    bad_threshold = endings.get('bad', 0)
    normal_threshold = endings.get('normal', 0)
    
    if "bad" in endings:
        good_end.append(f"条件：好感度 > {normal_threshold}")
        normal_end.append(f"条件：{bad_threshold} < 好感度 < {normal_threshold}")
        bad_end.append(f"条件：好感度 < {bad_threshold}")
    
    all_episodes_choices = []

    for ep in episode_info:
        all_choices, title = await process_episode_choices(ep, review)
        
        if not all_choices:
            continue
        
        all_episodes_choices.append({
            "episode": ep['episode'],
            "title": title,
            "choices": all_choices
        })
        
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

    normal_choices_by_episode = await calculate_normal_ending_choice(all_episodes_choices, bad_threshold, normal_threshold)
    
    for episode_data in normal_choices_by_episode:
        episode_num = episode_data["episode"]
        choices = episode_data["choices"]
        
        for i, line in enumerate(normal_end):
            if line.startswith(f"\nEP{episode_num}："):
                normal_end[i+1:i+1] = choices
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
        entity_type: 实体类型 (1=英雄, 2=怪物, 3=恶灵)
        level: 等级
    
    Returns:
        int: 计算后的基础战力
    """
    try:
        type_prefix = ""
        if entity_type == 1:
            type_prefix = "BP_hero"
        elif entity_type == 2:
            type_prefix = "BP_monster"
        elif entity_type == 3:
            type_prefix = "BP_raid"
        else:
            return 0
        
        base_value = 0.0
        level_value = 0.0
        level_per_value = 0.0
        
        for kv in data["key_values"]["json"]:
            key_name = kv.get("key_name", "")
            
            if key_name == f"{type_prefix}_base":
                try:
                    base_value = float(kv.get("values_data", "0"))
                except ValueError:
                    base_value = 0.0
            
            elif key_name == f"{type_prefix}_level":
                try:
                    level_value = float(kv.get("values_data", "0"))
                except ValueError:
                    level_value = 0.0
            
            elif key_name == f"{type_prefix}_level_per":
                try:
                    level_per_value = float(kv.get("values_data", "0"))
                except ValueError:
                    level_per_value = 0.0
        
        battle_power = int(base_value + (level_value + level_per_value * level) * (level - 1))
        return battle_power
    
    except Exception as e:
        logger.error(f"计算基础战力时发生错误: {e}")
        return 0


async def calculate_battle_power(data: dict, entity_type: int, level: int, grade: int, 
                            equipment_power: int = 0, equipment_power_per: float = 0.0, 
                            signature_power_per: float = 0.0, contents_buff_power: float = 0.0, 
                            contents_buff_power_per: float = 0.0) -> int:
    """
    计算总战力
    Args:
        data: JSON 数据字典
        entity_type: 实体类型 (1=英雄, 2=怪物, 3=恶灵)
        level: 等级
        grade: 品质
        level_grade: 等级品质, 默认1.0
        equipment_power: 装备战力, 默认0
        equipment_power_per: 装备战力百分比, 默认0.0
        signature_power_per: 遗物战力百分比, 默认0.0
        contents_buff_power: 内容增益战力, 默认0.0
        contents_buff_power_per: 内容增益战力百分比, 默认0.0
        
    Returns:
        int: 计算后的总战力
    """
    try:
        base_power = await get_base_battle_power(data, entity_type, level)
        grade_value = await get_hero_grade_value(data, grade)
        level_grade_value = await get_hero_level_grade_value(data, level)
        
        total_power = (
            base_power +
            (level_grade_value - 1.0) * base_power +
            (grade_value - 1.0) * base_power +
            equipment_power +
            equipment_power_per * base_power +
            signature_power_per * base_power +
            contents_buff_power +
            contents_buff_power_per * base_power
        )

        if total_power == float('inf'):
            return 0
        
        return int(total_power)
        
    except Exception as e:
        logger.error(f"计算总战力时发生错误: {e}")
        return 0
    

async def get_hero_grade_value(data: dict, grade: int) -> float:
    """
    获取角色品质加成值
    Args:
        data: JSON 数据字典
        grade: 品质
        
    Returns:
        float: 品质加成值
    """

    try:
        for grade_info in data["hero_grade"]["json"]:
            if grade_info.get("name_sno") == grade:
                return grade_info.get("hero_grade_value", 0.85)
            
        return 0.85
    
    except Exception as e:
        logger.error(f"获取角色品质加成值时发生错误: {e}")
        return 0.85


async def get_hero_level_grade_value(data: dict, level: int) -> float:
    """
    获取角色等级加成值
    Args:
        data: JSON 数据字典
        level: 等级
        
    Returns:
        float: 等级加成值, 默认1.0 (无加成)
    """
    try:
        level_grade_value = 1.0
        level_grades = data["hero_level_grade"]["json"]
        level_grades.sort(key=lambda x: x.get("level", 0))
        
        for grade_data in level_grades:
            if grade_data.get("level", 0) <= level:
                level_grade_value = grade_data.get("value", 1.0)
            else:
                break
                
        max_level_data = max(level_grades, key=lambda x: x.get("level", 0))
        if level >= int(max_level_data.get("level", 0)):
            level_grade_value = max_level_data.get("value", 1.0)
        
        return level_grade_value
        
    except Exception as e:
        logger.error(f"获取角色等级加成率时发生错误: {e}")
        return 1.0


async def get_character_skill_pattern(data: dict, hero_no: int, review: bool = False) -> list:
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
                        skill_name_zh_tw = (await get_string_by_type(data, "skill", skill["name_sno"])).get("zh_tw", "")
                        skill_name_kr = (await get_string_by_type(data, "skill", skill["name_sno"])).get("kr", "")
                        skill_type = (await get_string_by_type(data, "system", skill["type"])).get("zh_tw", "")

                        skill_name = await select_text_by_priority(skill_name_zh_tw, skill_name_kr, review)
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
            return float(skill.get("range", 0))

    return 0.0