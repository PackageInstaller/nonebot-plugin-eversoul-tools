"""
字符串和多语言文本处理模块
"""
import os
import re
import ast
import math
from nonebot.log import logger
from difflib import get_close_matches
from ...config import (
    TOWN_DIR, TRAIT_NAME_MAPPING, 
    PACKAGE_TYPE_MAPPING, STAT_NAME_MAPPING,
    FORMATION_TYPE_MAPPING, SIGNATURE_GRADE_LEVEL_MAP
)


def format_number(num):
    """
    将数字转换为中文单位表示，精确到两个单位
    例如：123456789 -> 1.2亿3456万
    对于能够用一个单位精确表示的数字，仍使用一个单位
    例如：50000000 -> 5千万
    支持负数
    """
    # 处理负数情况
    is_negative = False
    if num < 0:
        is_negative = True
        num = abs(num)

    units = [
        "",
        "万",
        "亿",
        "兆",
        "京",
        "垓",
        "秭",
        "穰",
        "沟",
        "涧",
        "正",
        "载",
        "极",
        "恒河沙",
        "阿僧祗",
        "那由他",
        "不思议",
        "无量大",
        "万无量大",
        "亿无量大",
        "兆无量大",
        "京无量大",
        "垓无量大",
        "秭无量大",
        "穰无量大",
        "沟无量大",
        "涧无量大",
        "正无量大",
        "载无量大",
        "极无量大",
    ]
    
    # 千单位特殊处理
    sub_units = ["", "十", "百", "千"]
    
    # 处理科学计数法
    if "e" in str(num):
        num = float(f"{num:.1f}")
    
    # 处理0和小数
    if num == 0:
        return "0"
    if num < 1:
        return str(round(num, 2))
    
    # 首先确定最大单位
    def get_unit_level(n):
        level = 0
        while n >= 10000:
            n /= 10000
            level += 1
        return n, level
    
    main_num, main_level = get_unit_level(num)
    
    # 检查是否需要显示第二个单位
    # 判断条件：主单位的小数部分不为0，且数值足够大
    main_int = int(main_num)
    main_decimal = main_num - main_int
    
    # 如果没有小数部分或不足以表示第二个单位，直接返回一个单位
    if main_decimal < 0.0001 or main_level == 0:
        if main_level >= len(units):
            main_level = len(units) - 1
        result = f"{main_int}{units[main_level]}"
        if is_negative:
            return f"负{result}"
        return result
    
    # 计算第二个单位
    second_num = main_decimal * 10000  # 转换到下一个单位
    
    # 对于万以上单位，尝试使用千/百/十进行表示
    if main_level > 0 and second_num < 10:
        # 数值太小，不足以用第二个单位表示，直接使用一个单位
        if main_level >= len(units):
            main_level = len(units) - 1
        result = f"{main_int}{units[main_level]}"
        if is_negative:
            return f"负{result}"
        return result
    
    second_level = main_level - 1
    
    # 如果第二个单位是个位数（小于万），使用千/百/十表示
    if second_level == 0:
        # 确定sub_unit
        sub_unit_index = 0
        temp_num = second_num
        while temp_num >= 10:
            temp_num /= 10
            sub_unit_index += 1
            if sub_unit_index >= len(sub_units) - 1:
                break
        
        second_display = int(second_num / (10 ** sub_unit_index))
        
        # 最终结果
        if main_level >= len(units):
            main_level = len(units) - 1
        result = f"{main_int}{units[main_level]}{second_display}{sub_units[sub_unit_index]}"
    else:
        # 第二个单位是万及以上，直接使用
        second_int = int(second_num)
        if second_level >= len(units):
            second_level = len(units) - 1
        result = f"{main_int}{units[main_level]}{second_int}{units[second_level]}"
    
    if is_negative:
        return f"负{result}"
    return result


def clean_tags(text):
    """清理富文本标签"""
    # 处理 <color=#XXXXXX> 格式
    text = re.sub(r'<color=#[A-Fa-f0-9]+>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</color>', '', text, flags=re.IGNORECASE)
    
    # 处理 <COLOR=#XXXXXX> 格式
    text = re.sub(r'<COLOR=#[A-Fa-f0-9]+>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</COLOR>', '', text, flags=re.IGNORECASE)
    
    # 处理可能存在的空格
    text = re.sub(r'<color\s*=#[A-Fa-f0-9]+\s*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</color\s*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<COLOR\s*=#[A-Fa-f0-9]+\s*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</COLOR\s*>', '', text, flags=re.IGNORECASE)
    
    # 处理 <color="#XXXXXX"> 格式（带引号的情况）
    text = re.sub(r'<color="[#A-Fa-f0-9]+"\s*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<COLOR="[#A-Fa-f0-9]+"\s*>', '', text, flags=re.IGNORECASE)
    
    # 处理 <effect:none> 标签
    text = re.sub(r'<effect:none>', '', text, flags=re.IGNORECASE)
    
    return text


def get_formation_type(formation_no):
    """获取阵型类型"""
    return FORMATION_TYPE_MAPPING.get(formation_no, "")


def get_string_system(data, no):
    """从StringSystem.json中获取文本
    
    Args:
        data: JSON数据字典 
        no: 字符串编号
        
    Returns:
        dict: 包含不同语言文本的字典，键为'zh_tw', 'zh_cn', 'kr', 'en'
    """
    for string in data["string_system"]["json"]:
        if string["no"] == no:
            return {
                "zh_tw": string.get("zh_tw", ""),
                "zh_cn": string.get("zh_cn", ""),
                "kr": string.get("kr", ""),
                "en": string.get("en", "")
            }
    return {"zh_tw": "", "zh_cn": "", "kr": "", "en": ""}


def get_string_ui(data, no):
    """从StringUI.json中获取文本
    
    Args:
        data: JSON数据字典 
        no: 字符串编号
        
    Returns:
        dict: 包含不同语言文本的字典，键为'zh_tw', 'zh_cn', 'kr', 'en'
    """
    for string in data["string_ui"]["json"]:
        if string["no"] == no:
            return {
                "zh_tw": string.get("zh_tw", "").replace('\\r\\n', ' ').replace('\r\n', ' ').replace('\n', ' '),
                "zh_cn": string.get("zh_cn", "").replace('\\r\\n', ' ').replace('\r\n', ' ').replace('\n', ' '),
                "kr": string.get("kr", "").replace('\\r\\n', ' ').replace('\r\n', ' ').replace('\n', ' '),
                "en": string.get("en", "").replace('\\r\\n', ' ').replace('\r\n', ' ').replace('\n', ' ')
            }
    return {"zh_tw": "", "zh_cn": "", "kr": "", "en": ""}


def get_string_character(data, hero_no, special=False):
    """获取角色名称
    
    Args:
        data: JSON数据字典
        hero_no: 角色编号
        special: 是否为特殊模式，用于没法直接从string_character中获取文本的情况
    Returns:
        dict: 包含不同语言文本的字典，键为'zh_tw', 'zh_cn', 'kr', 'en'
    """
    name_sno = hero_no
    
    if special:
        # 在角色模式下，先找到hero_no对应的name_sno
        for hero in data["hero"]["json"]:
            if hero["no"] == hero_no:
                name_sno = hero.get("name_sno")
                break
    
    # 根据name_sno查找对应的文本
    for char in data["string_character"]["json"]:
        if char["no"] == name_sno:
            return {
                "zh_tw": char.get("zh_tw", ""),
                "zh_cn": char.get("zh_cn", ""),
                "kr": char.get("kr", ""),
                "en": char.get("en", "")
            }
            
    return {"zh_tw": "", "zh_cn": "", "kr": "", "en": ""}


def get_drop_item_rate(data, group_no):
    """获取掉落物品信息，对于相同名称的物品保留概率最高的一个
    
    Args:
        data: JSON数据字典
        group_no: 掉落组编号
    
    Returns:
        list: [(物品名称, 数量, 掉落率)] 的列表
    """
    drop_items = []
    
    if group_no is None:
        return []
    
    for drop_group in data["item_drop_group"]["json"]:
        if drop_group["no"] == group_no:
            item_no = drop_group.get("item_no")
            amount = drop_group.get("amount", 0)
            drop_rate = drop_group.get("drop_rate", 0)
            
            if item_no:
                item_name = get_string_item(data, item_no)
                # 转换掉落率 (1 = 0.001%)
                rate_percent = drop_rate * 0.001
                drop_items.append((item_name, amount, rate_percent))
    
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


def get_character_skill_type(data, type_no):
    """获取技能类型名称
    
    Args:
        data: JSON数据字典
        type_no: 技能类型编号
    
    Returns:
        dict: 包含不同语言文本的字典，键为'zh_tw', 'zh_cn', 'kr', 'en'
    """
    for string in data["string_system"]["json"]:
        if string["no"] == type_no:
            return {
                "zh_tw": string.get("zh_tw", ""),
                "zh_cn": string.get("zh_cn", ""),
                "kr": string.get("kr", ""),
                "en": string.get("en", "")
            }
    return {"zh_tw": "", "zh_cn": "", "kr": "", "en": ""}


def get_string_item(data, item_no):
    """
    获取物品名称

    Args:
        data: JSON数据字典
        item_no: 物品编号
    
    Returns:
        dict: 包含不同语言文本的字典，键为'zh_tw', 'zh_cn', 'kr', 'en'
    """
    # 在Item.json中查找物品
    for item in data["item"]["json"]:
        if item["no"] == item_no:
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


def get_character_cv(data, hero_desc):
    """获取角色声优信息
    
    Args:
        data: JSON数据字典
        hero_desc: 角色描述数据
    
    Returns:
        dict: 包含韩语和日语声优信息的字典，键为'kr', 'ja'
    """
    cv_kr = get_string_character(data, hero_desc.get("cv_sno", 0))["zh_tw"] if hero_desc else "？？？"
    cv_ja = get_string_character(data, hero_desc.get("cv_jp_sno", 0))["zh_tw"] if hero_desc else "？？？"
    cv_ja = cv_ja if cv_ja != cv_kr and cv_ja != "" else "？？？"

    return {"kr": cv_kr, "ja": cv_ja}


def get_character_release_date(data, hero_id):
    """获取角色实装日期
    
    Args:
        data: JSON数据字典
        hero_id: 角色ID
    
    Returns:
        str: 格式化后的实装日期，如果未找到则返回默认日期（2023-01-05）
    """
    release_date = None
    for movie in data["promotion_movie"]["json"]:
        if movie.get("hero_check") == hero_id:
            # 只取日期部分，不要时间
            start_date = movie.get("start_date", "").split()[0]
            if start_date and start_date != "2999-12-31":  # 排除默认日期
                release_date = start_date
                break
    
    # 如果找到日期返回该日期，否则返回默认日期
    return f"{release_date}" if release_date else "2023-01-05"


def get_character_arbeit(data, hero_id):
    """获取角色的打工属性信息
    
    Args:
        data: JSON数据字典
        hero_id: 角色ID
    
    Returns:
        dict: 包含初始和满级属性的字典，键为'initial', 'max'
    """
    # 收集所有相关等级的数据
    level_data = []
    for level in data["arbeit_fairy_level"]["json"]:
        if level.get("hero_no") == hero_id:
            level_data.append(level)
    
    if not level_data:
        return {"initial": "？？？", "max": "？？？"}
    
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


def get_character_prefer_gift(data, hero_id):
    """获取角色的喜好礼物信息
    
    Args:
        data: JSON数据字典
        hero_id: 角色ID
    
    Returns:
        str: 喜好礼物名称列表，用顿号分隔
    """
    # 在HeroGift.json中查找角色的喜好礼物
    gift_items = []
    for gift in data["hero_gift"]["json"]:
        if gift.get("hero_no") == hero_id:
            # 获取prefer_gift_items字符串并分割成列表
            prefer_items = gift.get("prefer_gift_items", "").split(",")
            prefer_items = [item.strip() for item in prefer_items if item.strip()]
            
            # 对每个物品ID进行处理
            for item_no in prefer_items:
                # 在Item.json中查找物品信息
                for item in data["item"]["json"]:
                    if str(item.get("no")) == item_no:
                        # 获取物品名称
                        name_sno = item.get("name_sno")
                        if name_sno:
                            # 在StringItem.json中查找物品名称
                            for string in data["string_item"]["json"]:
                                if string.get("no") == name_sno:
                                    gift_items.append(string.get("zh_tw", ""))
                                    break
                        break
    
    return "、".join(gift_items) if gift_items else "？？？"


def get_character_similar_name(query, alias_map):
    """查找相似的角色名称
    
    Args:
        query: 用户输入的查询名称
        alias_map: 别名映射字典
    
    Returns:
        list: 可能匹配的角色信息列表 [(角色名, 别名列表), ...]
    """
    # 创建反向映射：hero_id -> (name, aliases)
    hero_map = {}
    for name, hero_id in alias_map.items():
        if hero_id not in hero_map:
            hero_map[hero_id] = [name, []]
        else:
            if len(hero_map[hero_id][1]) == 0:  # 第一个名字是主名称
                hero_map[hero_id][1].append(name)
            else:
                hero_map[hero_id][1].append(name)
    
    # 收集所有可能的名称（主名称和别名）
    all_names = []
    for name, hero_id in alias_map.items():
        all_names.append(name)
    
    # 使用 difflib 查找相似名称
    similar_names = get_close_matches(query, all_names, n=3, cutoff=0.4)
    
    # 收集匹配到的角色信息
    results = []
    for similar_name in similar_names:
        hero_id = alias_map[similar_name]
        main_name = hero_map[hero_id][0]
        aliases = [alias for alias in hero_map[hero_id][1] if alias != main_name]
        if (main_name, aliases) not in results:
            results.append((main_name, aliases))
    
    return results


def get_character_skill_value(data, value_id, value_type="VALUE"):
    """处理技能数值
    
    Args:
        data: JSON数据字典
        value_id: 技能ID
        value_type: 值类型（"VALUE" 或 "DURATION"）
    """
    # 如果是DURATION类型，需要从SkillCode和SkillBuff中获取
    if value_type == "DURATION":
        # 先检查SkillCode中的value
        for code in data["skill_code"]["json"]:
            if code["no"] == value_id:
                value_without_decimal = int(code["value"]) if code["value"].is_integer() else code["value"]
                # 在SkillBuff中查找对应的duration
                for buff in data["skill_buff"]["json"]:
                    if buff["no"] == value_without_decimal:
                        return str(int(abs(buff["duration"])))  # 返回duration值
        
        # 如果在SkillCode中没找到，直接查找SkillBuff
        for buff in data["skill_buff"]["json"]:
            if buff["no"] == value_id:
                return str(int(abs(buff["duration"])))  # 取绝对值
        return "？？？"

    # 从SkillCode.json中查找数值
    for code in data["skill_code"]["json"]:
        if code["no"] == value_id:
            # 检查value是否为整数形式（去掉.0后）的数字
            value_without_decimal = int(code["value"]) if code["value"].is_integer() else code["value"]
            
            # 如果value是引用SkillBuff的编号
            if isinstance(value_without_decimal, int):
                for buff in data["skill_buff"]["json"]:
                    if buff["no"] == value_without_decimal:
                        value = buff["value"]  # 获取原始值
                        abs_value = abs(value)  # 取绝对值
                        buff_effect = buff.get("buff_effect", 0)
                        
                        # 根据buff_effect类型判断是整数还是百分比
                        if is_percent_value_type(buff_effect, abs_value):
                            # 处理为百分比
                            percent_value = abs_value * 100
                            rounded_value = round(percent_value, 1)
                            if rounded_value.is_integer():
                                return f"{int(rounded_value)}%"
                            return f"{rounded_value}%"
                        else:
                            # 处理为整数
                            return str(int(abs_value))
            
            # 如果不是引用其他no，则直接使用code中的value
            value = code["value"]  # 获取原始值
            abs_value = abs(value)  # 取绝对值
            function_key = code.get("function_key", 0)
            # 根据function_key判断是整数还是百分比
            if is_integer_value_type(function_key):
                # 处理为整数
                return str(int(abs_value))
            else:
                # 处理为百分比
                percent_value = abs_value * 100
                rounded_value = round(percent_value, 1)
                if rounded_value.is_integer():
                    return f"{int(rounded_value)}%"
                return f"{rounded_value}%"
    return "？？？"


def is_integer_value_type(function_key):
    """判断是否为整数类型的技能值
    
    SkillTextUtil__GetCodeValueText中的逻辑:
    if ( type <= 27 && ((1 << type) & 0xC000010) != 0 || type - 1026 < 2 )
    
    0x0C000010转成2进制是  00001100 00000000 00000000 00010000
    """
    integer_types = {4, 26, 27, 1026, 1027}
    return function_key in integer_types


def is_percent_value_type(buff_effect, value):
    """判断是否为百分比类型的技能值"""
    # 以下类型直接按整数处理（不带百分比）
    integer_types = {10101, 10102, 420}
    
    # 特殊处理，((1 << (type - 122)) & 0x13) != 0判断
    special_types = {10106 + offset for offset in [0, 2, 4] if (1 << (offset)) & 0x13 != 0}
    
    # 返回是否为百分比类型（取反，因为判断的是整数类型）
    is_integer = (buff_effect in integer_types) or (buff_effect in special_types)
    
    return not is_integer


def process_skill_description(data, description):
    """处理技能描述中的数值标签"""
    def replace_value(match):
        value_id = int(match.group(1))
        value_type = match.group(2)
        return get_character_skill_value(data, value_id, value_type)
    
    # 替换所有形如 <数字.VALUE> 或 <数字.DURATION> 的内容
    processed_desc = re.sub(r'<\s*(\d+)\.(VALUE|DURATION)\s*>', replace_value, description)
    return processed_desc


def get_character_skill(data, skill_no, is_support=False, hero_data=None):
    """获取技能信息
    
    Args:
        data: JSON数据字典
        skill_no: 技能编号
        is_support: 是否为支援技能
        hero_data: 角色数据（用于获取辅助伙伴技能信息）
    
    Returns:
        dict: 包含技能信息的字典
    """
    skill_data_list = []
    skill_name_zh_tw = ""
    skill_name_zh_cn = ""
    skill_name_kr = ""
    skill_name_en = ""
    skill_descriptions = []
    skill_icon_info = None
    
    # 查找所有相同编号的技能数据
    for skill in data["skill"]["json"]:
        if skill["no"] == skill_no:
            skill_data_list.append(skill)
            # 只在第一次找到技能时获取图标信息
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
        # 获取技能名称
        for string in data["string_skill"]["json"]:
            if string["no"] == skill_data_list[0]["name_sno"]:
                skill_name_zh_tw = string.get("zh_tw", "")
                skill_name_zh_cn = string.get("zh_cn", "")
                skill_name_kr = string.get("kr", "")
                skill_name_en = string.get("en", "")
                break
        
        if is_support:
            # 找出最高等级的技能数据
            max_level_skill = max(skill_data_list, key=lambda x: x.get("level", 0))
            
            # 获取主要伙伴技能描述
            for string in data["string_skill"]["json"]:
                if string["no"] == max_level_skill["tooltip_sno"]:
                    desc_tw = string.get("zh_tw", "")
                    desc_cn = string.get("zh_cn", "")
                    desc_kr = string.get("kr", "")
                    desc_en = string.get("en", "")
                    # 清理颜色标签
                    desc_tw = clean_tags(desc_tw)
                    desc_cn = clean_tags(desc_cn)
                    desc_kr = clean_tags(desc_kr)
                    desc_en = clean_tags(desc_en)
                    # 处理数值标签
                    desc_tw = process_skill_description(data, desc_tw)
                    desc_cn = process_skill_description(data, desc_cn)
                    desc_kr = process_skill_description(data, desc_kr)
                    desc_en = process_skill_description(data, desc_en)
                    skill_descriptions.append({
                        "desc_zh_tw": f"主要夥伴：{desc_tw}",
                        "desc_zh_cn": f"主要伙伴：{desc_cn}",
                        "desc_kr": f"메인 파트너：{desc_kr}",
                        "desc_en": f"Main Partner Effect：{desc_en}",
                        "type": "main_partner"
                    })
                    break
            
            # 如果提供了hero_data，获取辅助伙伴技能描述
            if hero_data:
                sub_class_sno = hero_data.get("sub_class_sno")
                max_grade_sno = hero_data.get("max_grade_sno")
                
                if sub_class_sno and max_grade_sno:
                    # 在WorldRaidPartnerBuff中查找匹配的buff
                    for buff in data["world_raid_partner_buff"]["json"]:
                        if (buff["sub_class"] == sub_class_sno and 
                            buff["grade"] == max_grade_sno):
                            buff_sno = buff.get("buff_sno")
                            buff_no = buff.get("buff_no")
                            
                            if buff_sno and buff_no:
                                # 获取buff数值
                                buff_values = []  # 改用列表存储数值
                                for content_buff in data["contents_buff"]["json"]:
                                    if content_buff.get("no") == buff_no:
                                        # 遍历所有属性，按顺序收集非零数值
                                        for key, value in content_buff.items():
                                            if (isinstance(value, (int, float)) and 
                                                value != 0 and 
                                                key != "no"):  # 排除 no 字段
                                                # 根据数值大小判断是否为百分比，取绝对值
                                                if abs(value) < 20:  # 小于等于20的按百分比处理
                                                    buff_values.append(int(abs(value) * 100))
                                                else:  # 大于20的按整数处理
                                                    buff_values.append(int(abs(value)))
                                
                                # 在StringUI中查找描述文本
                                for string in data["string_ui"]["json"]:
                                    if string["no"] == buff_sno:
                                        desc_tw = string.get("zh_tw", "")
                                        desc_cn = string.get("zh_cn", "")
                                        desc_kr = string.get("kr", "")
                                        desc_en = string.get("en", "")
                                        
                                        # 正则表达式找出所有占位符
                                        placeholders = re.findall(r'{([^}]+)}', desc_tw)
                                        
                                        # 按顺序替换所有占位符
                                        for i, value in enumerate(buff_values):
                                            if i < len(placeholders):
                                                placeholder = f"{{{placeholders[i]}}}"
                                                desc_tw = desc_tw.replace(placeholder, str(value))
                                                desc_cn = desc_cn.replace(placeholder, str(value))
                                                desc_kr = desc_kr.replace(placeholder, str(value))
                                                desc_en = desc_en.replace(placeholder, str(value))
                                        
                                        skill_descriptions.append({
                                            "desc_zh_tw": f"輔助夥伴：{desc_tw}",
                                            "desc_zh_cn": f"辅助伙伴：{desc_cn}",
                                            "desc_kr": f"서브 파트너：{desc_kr}",
                                            "desc_en": f"Support Effect：{desc_en}",
                                            "type": "support_partner"
                                        })
                                        break
                            break
        else:
            # 非支援技能，获取所有等级的技能描述
            for skill_data in skill_data_list:
                hero_level = skill_data.get("hero_level", 1)  # 获取技能解锁等级
                for string in data["string_skill"]["json"]:
                    if string["no"] == skill_data["tooltip_sno"]:
                        desc_tw = string.get("zh_tw", "")
                        desc_cn = string.get("zh_cn", "")
                        desc_kr = string.get("kr", "")
                        desc_en = string.get("en", "")
                        # 清理颜色标签
                        desc_tw = clean_tags(desc_tw)
                        desc_cn = clean_tags(desc_cn)
                        desc_kr = clean_tags(desc_kr)
                        desc_en = clean_tags(desc_en)
                        # 处理数值标签
                        desc_tw = process_skill_description(data, desc_tw)
                        desc_cn = process_skill_description(data, desc_cn)
                        desc_kr = process_skill_description(data, desc_kr)
                        desc_en = process_skill_description(data, desc_en)
                        skill_descriptions.append({
                            "desc_zh_tw": desc_tw,
                            "desc_zh_cn": desc_cn,
                            "desc_kr": desc_kr,
                            "desc_en": desc_en,
                            "hero_level": hero_level
                        })
                        break
    
    return {
        "name": {
            "zh_tw": skill_name_zh_tw,
            "zh_cn": skill_name_zh_cn,
            "kr": skill_name_kr,
            "en": skill_name_en
        },
        "descriptions": skill_descriptions,
        "icon_info": skill_icon_info,
        "is_support": is_support
    }


def get_character_keyword_location(data: dict, keyword_get_details: int, is_test: bool = False) -> str:
    """获取非遗失物品关键字对应的地点"""    
    # 如果没有keyword_get_details或为0，返回"通用"
    if not keyword_get_details:
        return "通用"
    
    # 在TownLocation.json中查找对应地点
    location = next((loc for loc in data["town_location"]["json"] 
                    if loc["no"] == keyword_get_details), None)
    
    if not location:
        return ""
    
    # 获取地点名称，优先使用zh_tw
    location_data = next((s for s in data["string_town"]["json"] 
                      if s["no"] == location.get("location_name_sno")), None)
    if location_data:
        zh_tw = location_data.get("zh_tw", "")
        kr = location_data.get("kr", "")
        return zh_tw if zh_tw else (kr if is_test else zh_tw)
    return ""


def get_character_lost_item(data: dict, hero_no: int, keyword_type: int, keyword_get_details: int, is_test: bool = False) -> str:
    """获取遗失物品"""
    try:
        # 在TownLostItem.json中查找对应条目
        lost_item = next((item for item in data["town_lost_item"]["json"] 
                        if item.get("hero_no") == hero_no and 
                        item.get("keyword_type") == keyword_type and 
                        item.get("keyword_get_details") == keyword_get_details), None)
        
        if not lost_item:
            return ""

        quest_type = lost_item.get("quest_type")

        if quest_type == 1: # 归还领地遗失物品
            if group_end := lost_item.get("group_end"):
                talks = [t for t in data["talk"]["json"] if t.get("group_no") == group_end]
                choice_talk = next((t for t in reversed(talks) if t.get("ui_type", "").lower() == "choice"), None)
                if choice_talk and choice_talk.get("no"):
                    action = next((s.get("kr" if is_test else "zh_tw", "") for s in data["string_talk"]["json"] 
                                if s.get("no") == choice_talk.get("no")), "")
                    return f"{action}"

        elif quest_type == 2: # 击杀魔物
            if group_end := lost_item.get("group_end"):
                talks = [t for t in data["talk"]["json"] if t.get("group_no") == group_end]
                choice_talk = next((t for t in reversed(talks) if t.get("ui_type", "").lower() == "choice"), None)
                if choice_talk and choice_talk.get("no"):
                    action = next((s.get("kr" if is_test else "zh_tw", "") for s in data["string_talk"]["json"] 
                                if s.get("no") == choice_talk.get("no")), "")
                    return f"{action}"

        elif quest_type == 3: # 外出获取
            # 获取地点信息
            if group_trip := lost_item.get("group_trip"):
                # 在Talk.json中查找对应对话
                talks = [t for t in data["talk"]["json"] if t.get("group_no") == group_trip]
                choice_talk = next((t for t in reversed(talks) if t.get("ui_type", "").lower() == "choice"), None)
                if choice_talk and choice_talk.get("no"):
                    location = next((s.get("kr" if is_test else "zh_tw", "") for s in data["string_talk"]["json"] 
                                if s.get("no") == choice_talk.get("no")), "")
                    if location:
                        return f"{location}"
        
        return ""

    except Exception as e:
        logger.error(f"处理遗失物品信息时发生错误: {e}, hero_no={hero_no}, keyword_type={keyword_type}, details={keyword_get_details}")
        return ""


def get_character_keyword_point(data: dict, keyword_type: str) -> list:
    """获取关键字好感度点数"""
    key_name = {
        "normal": "TRIP_KEYWORD_GRADE_POINT",
        "bad": "TRIP_KEYWORD_GRADE_POINT_BAD",
        "good": "TRIP_KEYWORD_GRADE_POINT_GOOD"
    }[keyword_type]
    
    points = next((kv.get("values_data") for kv in data["key_values"]["json"] 
                  if kv.get("key_name") == key_name), None)
    if points:
        try:
            return ast.literal_eval(points)
        except:
            pass
    return [20, 40, 60]  # 默认值


def get_character_keyword_source(data: dict, source_sno: int, details: int, hero_no: int = None, keyword_type: int = None, is_test: bool = False) -> str:
    """获取关键字解锁条件"""
    # 优先获取zh_tw，当zh_tw为空时再根据is_test判断
    source_data = next((s for s in data["string_ui"]["json"] if s["no"] == source_sno), None)
    if source_data:
        zh_tw = source_data.get("zh_tw", "")
        kr = source_data.get("kr", "")
        source = zh_tw if zh_tw else (kr if is_test else zh_tw)
    else:
        source = ""
    
    if not source:
        return ""
        
    # 检查是否是遗失物品
    if hero_no and keyword_type:
        lost_item = get_character_lost_item(data, hero_no, keyword_type, details, is_test)
        if lost_item:
            return lost_item
        
    if 101 <= details <= 110:
        location = next((loc for loc in data["town_location"]["json"] 
                       if loc["no"] == details), None)
        if location:
            # 获取地点名称，优先使用zh_tw
            location_data = next((s for s in data["string_town"]["json"] 
                                if s["no"] == location.get("location_name_sno")), None)
            if location_data:
                zh_tw = location_data.get("zh_tw", "")
                kr = location_data.get("kr", "")
                location_name = zh_tw if zh_tw else (kr if is_test else zh_tw)
            else:
                location_name = "未知"
            return f"在{location_name}解锁"
    elif details == 1:
        try:
            return source.format(1)
        except Exception as e:
            return f"完成好感故事篇章1"
    elif source_sno == 619006:  # 打工熟练度
        try:
            return source.format(details)
        except Exception as e:
            return f"打工熟练度达Lv.{details}时可获得"
    elif "好感達Lv.{0}" in source or "好感达等级{0}" in source:  # 好感等级
        try:
            return source.format(details)
        except Exception as e:
            return f"好感达Lv.{details}时可获得"
    else:
        story = next((s for s in data["story_info"]["json"] 
                     if s["no"] == details), None)
        if story:
            act = story.get('act', '?')
            episode = story.get('episode', '?')
            try:
                # 分别处理章和节
                if "{0}{1}" in source:
                    result = source.format(f"第{act}章", episode)
                else:
                    result = source.format(f"{act}-{episode}")
                return result
            except Exception as e:
                return f"完成主线故事第{act}章 {episode}话时可获得"
    return source


def get_character_keyword(data: dict, hero_id: int, is_test: bool = False) -> str:
    """获取角色关键字信息"""
    trip_keywords = []
    keyword_msgs = []
    
    for trip in data["trip_hero"]["json"]:
        if trip.get("hero_no") == hero_id:
            # 这里是先处理30个通用的关键字
            keyword_info = next((k for k in data["trip_keyword"]["json"] 
                               if k["no"] == trip.get("keyword_no")), None)
            if keyword_info:
                # 确定关键字类型和好感度
                keyword_type = "normal" # 粉心
                if not trip.get("favor_point"): # 没这个键的话就是黄心
                    keyword_type = "bad"
                elif trip.get("favor_point") == 2: # 红心
                    keyword_type = "good"
                
                # 获取好感度加成
                points = get_character_keyword_point(data, keyword_type)
                grade_sno = keyword_info.get("keyword_grade")
                grade_index = 0 # 一般
                if grade_sno == 110012:  # 稀有
                    grade_index = 1
                elif grade_sno == 110014:  # 史诗
                    grade_index = 2
                favor_point = points[grade_index]
                    
                trip_keywords.append({
                    "name": get_string_ui(data, keyword_info.get("keyword_string"))["kr" if is_test else "zh_tw"],
                    "type": keyword_type,
                    "favor_point": favor_point,
                    "grade": get_string_system(data, grade_sno)["zh_tw"],
                    "source": get_character_keyword_source(
                        data, 
                        keyword_info.get("keyword_source", 0),
                        keyword_info.get("keyword_get_details", 0),
                        hero_id,
                        keyword_info.get("keyword_type"),
                        is_test
                    ),
                    "keyword_get_details": keyword_info.get("keyword_get_details")
                })
    
    # 分组显示关键字
    bad_keywords = [k for k in trip_keywords if k["type"] == "bad"]
    good_keywords = [k for k in trip_keywords if k["type"] == "good"]
    
    if not (bad_keywords or good_keywords):
        return ""
        
    keyword_msgs.append("【角色关键字】")
    if bad_keywords:
        keyword_msgs.append("▼ 讨厌的话题")
        for keyword in bad_keywords:
            msg = f"・{keyword['name']}（{keyword['grade']}）"
            # 添加地点信息
            if location := get_character_keyword_location(data, keyword.get("keyword_get_details"), is_test):
                msg += f"\n  地点：{location}"
            keyword_msgs.append(msg)
    
    if good_keywords:
        if bad_keywords:
            keyword_msgs.append("")
        keyword_msgs.append("▼ 喜欢的话题")
        # 先显示没有获取条件的关键字
        normal_keywords = [k for k in good_keywords if not k["source"]]
        for keyword in normal_keywords:
            msg = f"・{keyword['name']}（{keyword['grade']}）"
            # 添加地点信息
            if location := get_character_keyword_location(data, keyword.get("keyword_get_details"), is_test):
                msg += f"\n  地点：{location}"
            keyword_msgs.append(msg)
        
        # 添加分隔线
        if normal_keywords and any(k["source"] for k in good_keywords):
            if good_keywords:
                keyword_msgs.append("")
            keyword_msgs.append("▼ 以下为需要解锁的关键字")
        
        for keyword in (k for k in good_keywords if k["source"]):
            msg = f"・{keyword['name']}（{keyword['grade']}）"
            # 添加地点信息
            if location := get_character_keyword_location(data, keyword.get("keyword_get_details"), is_test):
                msg += f"\n  地点：{location}"
            if keyword["source"]:
                msg += f"\n  条件：{keyword['source']}"
            keyword_msgs.append(msg)
    
    return "\n".join(keyword_msgs)


def get_character_town_object(data: dict, hero_id: int, is_test=False) -> list:
    """获取角色专属领地物品信息
    
    Args:
        data: 游戏数据字典
        hero_id: 角色ID
    
    Returns:
        list: 物品信息列表 [(物品编号, 物品名称, 物品品质, 物品类型, 物品描述, 图片路径), ...]
    """
    try:
        objects_info = []
        for obj in data["town_object"]["json"]:
            if obj.get("hero") == hero_id:
                obj_no = obj.get("no")
                if not obj_no:
                    continue
                
                # 获取prefab作为图片名称
                prefab = obj.get("prefab", "").lower()
                    
                # 在Item.json中查找对应物品信息
                for item in data["item"]["json"]:
                    if item.get("no") == obj_no:
                        # 获取物品名称
                        name = ""
                        name_sno = item.get("name_sno")
                        if name_sno:
                            for string in data["string_item"]["json"]:
                                if string.get("no") == name_sno:
                                    zh_tw = string.get("zh_tw", "")
                                    kr = string.get("kr", "")
                                    name = zh_tw if zh_tw else (kr if is_test else zh_tw)
                                    break
                        
                        # 获取物品品质
                        grade = ""
                        grade_sno = item.get("grade_sno")
                        if grade_sno:
                            for string in data["string_system"]["json"]:
                                if string.get("no") == grade_sno:
                                    zh_tw = string.get("zh_tw", "")
                                    kr = string.get("kr", "")
                                    grade = zh_tw if zh_tw else (kr if is_test else zh_tw)
                                    break
                        
                        # 获取物品类型
                        slot_type = ""
                        slot_limit_sno = item.get("slot_limit_sno")
                        if slot_limit_sno:
                            for string in data["string_ui"]["json"]:
                                if string.get("no") == slot_limit_sno:
                                    zh_tw = string.get("zh_tw", "")
                                    kr = string.get("kr", "")
                                    slot_type = zh_tw if zh_tw else (kr if is_test else zh_tw)
                                    break
                        
                        # 获取物品描述并清理颜色标签
                        desc = ""
                        desc_sno = item.get("desc_sno")
                        if desc_sno:
                            for string in data["string_item"]["json"]:
                                if string.get("no") == desc_sno:
                                    zh_tw = string.get("zh_tw", "")
                                    kr = string.get("kr", "")
                                    desc_text = zh_tw if zh_tw else (kr if is_test else zh_tw)
                                    desc = clean_tags(desc_text)
                                    break
                        
                        if name:  # 只添加有名称的物品
                            # 构建图片路径
                            img_path = None
                            if prefab:
                                img_path = TOWN_DIR / f"{prefab}.png"
                                if os.path.exists(TOWN_DIR):
                                    for file in os.listdir(TOWN_DIR):
                                        if file.lower() == f"{prefab}.png":
                                            img_path = TOWN_DIR / file
                                            break
                                    
                                    if not os.path.exists(img_path):
                                        img_path = None
                            
                            objects_info.append((obj_no, name, grade, slot_type, desc, img_path))
                        
        return objects_info
        
    except Exception as e:
        logger.error(f"获取专属领地物品信息时发生错误: {e}, hero_id={hero_id}")
        return []


def get_character_town_object_task(data: dict, obj_no: int, is_test=False) -> list:
    """获取角色专属领地物品可进行的任务信息
    
    Args:
        data: 游戏数据字典
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
                                    rarity = rarity_zh_tw if rarity_zh_tw else (rarity_kr if is_test else rarity_zh_tw)
                                    break
                        
                        # 获取任务名称
                        name = ""
                        name_sno = arbeit.get("name_sno")
                        if name_sno:
                            for string in data["string_town"]["json"]:
                                if string.get("no") == name_sno:
                                    name_zh_tw = string.get("zh_tw", "")
                                    name_kr = string.get("kr", "")
                                    name = name_zh_tw if name_zh_tw else (name_kr if is_test else name_zh_tw)
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
                                            for string in data["string_item"]["json"]:
                                                if string.get("no") == name_sno:
                                                    item_name_zh_tw = string.get("zh_tw", "")
                                                    item_name_kr = string.get("kr", "")
                                                    item_name = item_name_zh_tw if item_name_zh_tw else (item_name_kr if is_test else item_name_zh_tw)
                                                    rewards.append(f"{item_name}x{item_amount}")
                                                    break
                        
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


def get_cash_pack(data: dict, item_type: str, gate_info: dict) -> list:
    """获取突发礼包信息
    
    Args:
        data: 游戏数据字典
        item_type: 礼包类型 ('barrier'/'stage'/'tower'/'grade_eternal')
        gate_info: 关卡/角色信息字典
    
    Returns:
        list: 包含礼包信息的消息列表
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
            package_info.append(f"【{package_type_name}】")
            package_info.append("▼ " + "-" * 20)
            
            # 获取礼包名称和描述
            name_sno = shop_item.get("name_sno")
            package_name = next((s.get("zh_tw", "未知礼包") for s in data["string_cashshop"]["json"] 
                               if s["no"] == name_sno), "未知礼包")
            
            info_sno = shop_item.get("item_info_sno")
            package_desc = next((s.get("zh_tw", "") for s in data["string_cashshop"]["json"] 
                               if s["no"] == info_sno), "")
            
            desc_sno = shop_item.get("desc_sno")
            limit_desc = next((s.get("zh_tw", "").format(shop_item.get("limit_buy", 0)) 
                             for s in data["string_ui"]["json"] if s["no"] == desc_sno), "")
            
            # 基本信息部分
            basic_info = [
                f"礼包名称：{package_name}"
            ]
            if package_desc:
                basic_info.append(f"礼包描述：{package_desc}")
            basic_info.extend([
                f"购买限制：{limit_desc}",
                f"剩余时间：{shop_item.get('limit_hour', 0)}小时"
            ])
            package_info.append("\n".join(basic_info))
            
            # 礼包内容部分
            content_info = []
            if item_infos := shop_item.get("item_infos"):
                try:
                    items = ast.literal_eval(item_infos)
                    content_info.append("\n礼包内容：")
                    for item_no, amount in items:
                        item_name = get_string_item(data, item_no)
                        content_info.append(f"・{item_name['zh_tw']}x{amount}")
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
            
            # 添加分隔线
            package_info.append("-" * 25)
            
            # 将整个礼包信息作为一条消息添加到列表中
            messages.append("\n".join(package_info))
    
    return messages


def get_character_soullink(data: dict, hero_id: int, is_test: bool = False) -> list:
    """获取角色的灵魂链接信息"""
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
        # 优先使用zh_tw内容的逻辑
        title_data = next((s for s in data["string_character"]["json"] 
                         if s["no"] == link.get("group_title")), {})
        title_zh_tw = title_data.get("zh_tw", "")
        title_kr = title_data.get("kr", "")
        title = title_zh_tw if title_zh_tw else (title_kr if is_test else title_zh_tw)
        
        story_data = next((s for s in data["string_character"]["json"] 
                         if s["no"] == link.get("group_story")), {})
        story_zh_tw = story_data.get("zh_tw", "")
        story_kr = story_data.get("kr", "")
        story = story_zh_tw if story_zh_tw else (story_kr if is_test else story_zh_tw)
        
        # 获取所有角色名称
        hero_names = []
        for hid in hero_ids:
            name_data = get_string_character(data, hid, special=True)
            name_zh_tw = name_data["zh_tw"]
            name_kr = name_data["kr"]
            name = name_zh_tw if name_zh_tw else (name_kr if is_test else name_zh_tw)
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
                # 获取条件文本，修改为优先使用zh_tw内容的逻辑
                condition_string_no = item.get("condition_string")
                condition_data = next((s for s in data["string_ui"]["json"] 
                                     if s["no"] == condition_string_no), {})
                condition_zh_tw = condition_data.get("zh_tw", "")
                condition_kr = condition_data.get("kr", "")
                
                condition_text = ""
                if condition_zh_tw:
                    condition_text = condition_zh_tw.format(
                        item.get("condition_count", 0),
                        item.get("condition_count", 0)
                    )
                elif is_test and condition_kr:
                    condition_text = condition_kr.format(
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
                            if key in STAT_NAME_MAPPING and value != 0:
                                # 获取属性名称，优先使用zh_tw
                                stat_name = STAT_NAME_MAPPING[key]
                                if value < 1:  # 小于1的显示为百分比
                                    buff_effects.append(f"{stat_name}：{value*100:.1f}%")
                                else:
                                    buff_effects.append(f"{stat_name}：{int(value)}")
                        
                        # 百分比战力加成
                        battle_power_per = buff.get("battle_power_per", 0)
                        if battle_power_per != 0:
                            buff_effects.append(f"战力加成：{battle_power_per*100:.1f}%")
                        
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


def get_character_signature_value(data, level_group):
    """获取遗物最高等级总属性
    
    Args:
        data: JSON数据字典
        level_group: 遗物等级组ID
    
    Returns:
        dict: 遗物属性统计
    """
    max_level_data = None
    max_level = 0
    
    # 这个遗物的最大等级（40或45）
    for level_data in data["signature_level"]["json"]:
        if level_data["group"] == level_group:
            if level_data["signature_level_"] > max_level:
                max_level = level_data["signature_level_"]
    
    # 再找到最大等级的数据
    for level_data in data["signature_level"]["json"]:
        if level_data["group"] == level_group and level_data["signature_level_"] == max_level:
            max_level_data = level_data
            break
    
    if not max_level_data:
        return []
    
    formatted_stats = []
    for stat_key, stat_name in STAT_NAME_MAPPING.items():
        if stat_key in max_level_data and max_level_data[stat_key] != 0:
            value = max_level_data[stat_key]
            if stat_key in ["hit", "dodge"]:
                formatted_stats.append(f"{stat_name}：{int(value)}")
            else:
                # 处理百分比值，使用round避免浮点数精度问题
                percent_value = round(value * 100, 1)
                formatted_value = f"{percent_value:.1f}"
                # 检查是否为整数（包括像29.0这样的值）
                if formatted_value.endswith('.0'):
                    formatted_stats.append(f"{stat_name}：{int(percent_value)}%")
                else:
                    formatted_stats.append(f"{stat_name}：{formatted_value}%")
    
    return formatted_stats, max_level, max_level_data["battle_power_per"]


def get_character_signature(data, hero_id):
    """获取遗物信息
    
    Args:
        data: JSON数据字典
        hero_id: 角色ID
    
    Returns:
        dict: 包含遗物信息的字典
    """
    signature_data = None
    signature_name_zh_tw = ""
    signature_name_zh_cn = ""
    signature_name_kr = ""
    signature_name_en = ""

    signature_title_zh_tw = ""
    signature_title_zh_cn = ""
    signature_title_kr = ""
    signature_title_en = ""

    signature_desc_zh_tw = ""
    signature_desc_zh_cn = ""
    signature_desc_kr = ""
    signature_desc_en = ""

    skill_descriptions = []
    signature_bg_path = ""
    
    # 在Signature.json中查找对应角色的遗物
    for signature in data["signature"]["json"]:
        if signature["hero_sno"] == hero_id:
            signature_data = signature
            # 获取遗物图标路径
            if signature_bg_path := signature.get("signature_bg_path"):
                signature_bg_path = f"Img_Signature_{signature_bg_path}.png"
            break
    
    if signature_data:
        # 获取遗物名称
        for string in data["string_skill"]["json"]:
            if string["no"] == signature_data["signature_name_sno"]:
                signature_name_zh_tw = string.get("zh_tw", "")
                signature_name_zh_cn = string.get("zh_cn", "")
                signature_name_kr = string.get("kr", "")
                signature_name_en = string.get("en", "")
                break
        
        # 获取遗物技能名称
        for string in data["string_skill"]["json"]:
            if string["no"] == signature_data["skill_name_sno"]:
                signature_title_zh_tw = string.get("zh_tw", "")
                signature_title_zh_cn = string.get("zh_cn", "")
                signature_title_kr = string.get("kr", "")
                signature_title_en = string.get("en", "")
                break
                
        # 获取遗物简介
        signature_desc_zh_tw = signature_desc_zh_cn = "无遗物简介信息"  # 设置默认值
        signature_desc_kr = "유물 프로필 정보 없음"
        signature_desc_en = "No signature description information"  # 设置默认值
        for string in data["string_skill"]["json"]:
            if string["no"] == signature_data["tooltip_explain_sno"]:
                desc_tw = string.get("zh_tw", "")
                desc_cn = string.get("zh_cn", "")  # 获取简体中文描述
                desc_kr = string.get("kr", "")
                desc_en = string.get("en", "")
                if desc_tw.strip():
                    signature_desc_zh_tw = desc_tw
                if desc_cn.strip():
                    signature_desc_zh_cn = desc_cn
                if desc_kr.strip():
                    signature_desc_kr = desc_kr
                if desc_en.strip():
                    signature_desc_en = desc_en
                break
        
        
        
        # 获取所有等级的技能描述
        for i in range(1, 8):  # 1-7级
            sno_key = f"skill_tooltip_sno{i}"
            if sno_key in signature_data:
                tooltip_sno = signature_data[sno_key]
                for string in data["string_skill"]["json"]:
                    if string["no"] == tooltip_sno:
                        desc_tw = string.get("zh_tw", "")
                        desc_cn = string.get("zh_cn", "")  # 获取简体中文描述
                        desc_kr = string.get("kr", "")
                        desc_en = string.get("en", "")
                        
                        # 先清理颜色标签
                        desc_tw = clean_tags(desc_tw)
                        desc_cn = clean_tags(desc_cn)
                        desc_kr = clean_tags(desc_kr)
                        desc_en = clean_tags(desc_en)
                        
                        # 处理数值标签，模拟官方parse逗号分隔的数值
                        desc_tw = process_skill_description(data, desc_tw)
                        desc_cn = process_skill_description(data, desc_cn)
                        desc_kr = process_skill_description(data, desc_kr)
                        desc_en = process_skill_description(data, desc_en)
                        
                        # 处理技能描述中可能包含的逗号分隔数值
                        # 模拟官方Info_SignatureSkillInfos__Parse方法的行为
                        def parse_comma_values(text):
                            # 识别可能包含的逗号分隔数值，如"1,2,3"
                            import re
                            pattern = r'\b\d+(?:,\d+)*\b'
                            
                            def replace_parsed_values(match):
                                values_str = match.group(0)
                                # 分割字符串，过滤空值，转换为整数列表
                                values = [int(v.strip()) for v in values_str.split(',') if v.strip()]
                                # 返回处理后的字符串（例如可以添加格式或者直接显示）
                                return ','.join(str(v) for v in values)
                                
                            return re.sub(pattern, replace_parsed_values, text)
                        
                        # 应用逗号分隔数值处理
                        desc_tw = parse_comma_values(desc_tw)
                        desc_cn = parse_comma_values(desc_cn)
                        desc_kr = parse_comma_values(desc_kr)
                        desc_en = parse_comma_values(desc_en)
                        
                        # 添加等级、品质信息
                        grade_sno = 110014 + i - 1  # 按顺序映射等级
                        level_name = SIGNATURE_GRADE_LEVEL_MAP.get(grade_sno, f"Level{i}")
                        
                        skill_descriptions.append({
                            "desc_zh_tw": desc_tw,
                            "desc_zh_cn": desc_cn,
                            "desc_kr": desc_kr,
                            "desc_en": desc_en,
                            "level": i,
                            "grade_sno": grade_sno,
                            "level_name": level_name
                        })
                        break
        
    # 修改返回值，添加图标路径
    if signature_data:
        level_group = signature_data.get("level_group")
        signature_stats = get_character_signature_value(data, level_group) if level_group else []
        
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
    
    # 如果没有找到遗物数据，返回空字典
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


def calculate_normal_ending_choice(all_episodes_choices, bad_threshold, normal_threshold):
    """计算一般结局的选项组合"""
    # 提取好结局和坏结局的选项及其好感度
    good_ending_choices = []
    bad_ending_choices = []
    
    for episode_data in all_episodes_choices:
        episode_choices = episode_data["choices"]
        episode_num = episode_data["episode"]
        
        # 按talk_index分组
        choices_by_index = {}
        for choice in episode_choices:
            talk_index = choice["talk_index"]
            if talk_index not in choices_by_index:
                choices_by_index[talk_index] = []
            choices_by_index[talk_index].append(choice)
        
        # 为每个talk_index找出好结局和坏结局的选项
        for talk_index, choices in choices_by_index.items():
            # 好结局选择最高好感度
            max_affinity = max(c["affinity"] for c in choices)
            good_choices = [c for c in choices if c["affinity"] == max_affinity]
            good_ending_choices.append({
                "episode": episode_num,
                "talk_index": talk_index,
                "choice": good_choices[0],  # 取第一个最高好感度选项
                "affinity": max_affinity
            })
            
            # 坏结局选择最低好感度
            min_affinity = min(c["affinity"] for c in choices)
            bad_choices = [c for c in choices if c["affinity"] == min_affinity]
            bad_ending_choices.append({
                "episode": episode_num,
                "talk_index": talk_index,
                "choice": bad_choices[0],  # 取第一个最低好感度选项
                "affinity": min_affinity
            })
    
    # 计算好结局和坏结局的总好感度
    good_total_affinity = sum(choice["affinity"] for choice in good_ending_choices)
    bad_total_affinity = sum(choice["affinity"] for choice in bad_ending_choices)
    
    # 计算需要减少的好感度，使总好感度落在一般结局区间内
    target_affinity = (bad_threshold + normal_threshold) / 2  # 取区间中点作为目标
    affinity_to_reduce = good_total_affinity - target_affinity
    
    # 如果好结局总好感度已经在区间内，直接返回好结局选项
    if good_total_affinity <= normal_threshold and good_total_affinity >= bad_threshold:
        normal_end_note = f"注意：按照好结局选项选择即可达到一般结局条件（总好感度：{good_total_affinity}）"
        return [{
            "episode": 0,
            "choices": [normal_end_note]
        }]
    
    # 如果坏结局总好感度已经在区间内，直接返回坏结局选项
    if bad_total_affinity <= normal_threshold and bad_total_affinity >= bad_threshold:
        normal_end_note = f"注意：按照坏结局选项选择即可达到一般结局条件（总好感度：{bad_total_affinity}）"
        return [{
            "episode": 0,
            "choices": [normal_end_note]
        }]
    
    # 计算好结局和坏结局选项的好感度差值
    choice_diffs = []
    for i in range(len(good_ending_choices)):
        good_choice = good_ending_choices[i]
        bad_choice = bad_ending_choices[i]
        diff = good_choice["affinity"] - bad_choice["affinity"]
        if diff > 0:  # 只考虑有差异的选项
            choice_diffs.append({
                "index": i,
                "diff": diff,
                "good_choice": good_choice,
                "bad_choice": bad_choice
            })
    
    # 按差值从大到小排序
    choice_diffs.sort(key=lambda x: x["diff"], reverse=True)
    
    # 创建一般结局选项列表（初始为好结局选项）
    normal_ending_choices = good_ending_choices.copy()
    current_affinity = good_total_affinity
    
    # 替换部分选项，使总好感度落在区间内
    choices_to_replace = []
    for diff_info in choice_diffs:
        if current_affinity <= normal_threshold:
            break
            
        good_choice = diff_info["good_choice"]
        bad_choice = diff_info["bad_choice"]
        diff = diff_info["diff"]
        
        # 如果替换这个选项后总好感度仍然大于normal_threshold，则替换
        if current_affinity - diff >= bad_threshold:
            current_affinity -= diff
            normal_ending_choices[diff_info["index"]] = bad_choice
            choices_to_replace.append({
                "episode": good_choice["episode"],
                "talk_index": good_choice["talk_index"],
                "from_choice": good_choice["choice"]["text"],
                "to_choice": bad_choice["choice"]["text"],
                "diff": diff
            })
            
        # 如果总好感度已经在区间内，停止替换
        if current_affinity <= normal_threshold and current_affinity >= bad_threshold:
            break
    
    # 如果替换后总好感度仍然不在区间内，提供说明
    if current_affinity > normal_threshold:
        normal_end_note = f"警告：即使替换部分选项，总好感度({current_affinity})仍然超过一般结局上限({normal_threshold})，请额外注意控制好感度"
    elif current_affinity < bad_threshold:
        normal_end_note = f"警告：替换选项后总好感度({current_affinity})低于一般结局下限({bad_threshold})，请选择部分好结局选项"
    else:
        normal_end_note = f"提示：按照以下选项选择可达到一般结局条件（预计总好感度：{current_affinity}）"
    
    # 按章节组织一般结局选项
    normal_choices_by_episode = {}
    for choice in normal_ending_choices:
        episode = choice["episode"]
        if episode not in normal_choices_by_episode:
            normal_choices_by_episode[episode] = []
        normal_choices_by_episode[episode].append(choice)
    
    # 格式化结果
    result = [{
        "episode": 0,
        "choices": [normal_end_note]
    }]
    
    # 如果有需要特别替换的选项，添加说明
    if choices_to_replace:
        replace_notes = ["需要替换的选项："]
        for replace in choices_to_replace:
            replace_notes.append(f"EP{replace['episode']}：将 {replace['from_choice']} 替换为 {replace['to_choice']}")
        result[0]["choices"].extend(replace_notes)
    
    # 添加每章节的选项
    for episode, choices in normal_choices_by_episode.items():
        # 按talk_index排序
        choices.sort(key=lambda x: x["talk_index"])
        
        # 提取选项文本
        choice_texts = [choice["choice"]["text"] for choice in choices]
        
        result.append({
            "episode": episode,
            "choices": choice_texts
        })
    
    return result


def get_character_story(data, hero_id):
    """获取角色好感故事信息"""
    try:
        act = hero_id
        
        # 收集所有相关的故事信息
        story_episodes = []
        ending_episodes = []
        
        # 从Story_Info中获取所有相关剧情
        for story in data["story_info"]["json"]:
            if ("act" in story and story["act"] == act and 
                "bundle_path" in story and "Story/Love" in story["bundle_path"]):
                if story["episode"] in [8, 9, 10]:
                    ending_episodes.append(story)
                else:
                    story_episodes.append(story)
        
        # 如果没有8-10中的任意一个，则无好感故事
        if not ending_episodes:
            return False, [], {}
        
        # 获取结局信息
        endings = {}
        for episode in ending_episodes:
            if "ending_affinity" in episode:
                if episode["episode"] == 8:
                    endings["bad"] = episode["ending_affinity"]
                elif episode["episode"] == 9:
                    endings["normal"] = episode["ending_affinity"]
                elif episode["episode"] == 10:
                    endings["good"] = episode["ending_affinity"]
        
        # 如果没有找到任何结局信息，返回False
        if not endings:
            return False, [], {}
        
        # 收集每个章节的信息
        episode_info = []
        for episode in story_episodes:
            # 获取选项和好感度
            choices = {}  # 使用字典来按position_type分组
            
            # 先找出所有有好感度的选项的talk_index
            valid_talk_indexes = set()
            for talk in data["talk"]["json"]:
                if talk.get("group_no") == episode.get("talk_group") and "affinity_point" in talk:
                    valid_talk_indexes.add(talk.get("talk_index", 0))
            
            # 收集所有相关选项（包括有好感度和对应talk_index的无好感度选项）
            for talk in data["talk"]["json"]:
                if (talk.get("group_no") == episode.get("talk_group") and 
                    talk.get("talk_index", 0) in valid_talk_indexes):
                    choice_text_zh_tw = ""
                    choice_text_zh_cn = ""
                    choice_text_kr = ""
                    choice_text_en = ""
                    
                    # 安全获取对话文本
                    talk_no = talk.get("no")
                    if talk_no is not None:
                        for string in data["string_talk"]["json"]:
                            if string.get("no") == talk_no:
                                choice_text_zh_tw = string.get("zh_tw", "")
                                choice_text_zh_cn = string.get("zh_cn", "")
                                choice_text_kr = string.get("kr", "")
                                choice_text_en = string.get("en", "")
                                break
                    
                    # 按position_type分组存储选项
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
            
            # 获取章节标题
            episode_title_zh_tw = ""
            episode_title_zh_cn = ""
            episode_title_kr = ""
            episode_title_en = ""
            episode_name_sno = episode.get("episode_name_sno")
            if episode_name_sno is not None:
                for string in data["string_talk"]["json"]:
                    if string.get("no") == episode_name_sno:
                        episode_title_zh_tw = string.get("zh_tw", "")
                        episode_title_zh_cn = string.get("zh_cn", "")
                        episode_title_kr = string.get("kr", "")
                        episode_title_en = string.get("en", "")
                        break
            
            # 添加章节信息
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


def format_character_story(episode_info, endings, is_test=False):
    """格式化好感故事攻略"""
    # 创建三个结局的信息列表
    good_end = ["😃好结局攻略："]
    normal_end = ["🙂一般结局攻略："]
    bad_end = ["🥲坏结局攻略："]
    
    # 添加结局条件
    bad_threshold = endings.get('bad', 0)
    normal_threshold = endings.get('normal', 0)
    
    if "bad" in endings:
        good_end.append(f"条件：好感度大于{normal_threshold}")
        normal_end.append(f"条件：好感度{bad_threshold}-{normal_threshold}")
        bad_end.append(f"条件：好感度低于{bad_threshold}")
    
    # 收集所有章节的选项信息，用于计算总好感度
    all_episodes_choices = []
    
    # 添加各章节信息
    for ep in episode_info:
        # 收集所有选项
        all_choices = []
        for position_type, choices in ep["choices"].items():
            for choice in choices:
                talk_index = choice.get("talk_index", 0)
                affinity = choice.get("affinity", 0)
                affinity_str = str(affinity) if affinity < 0 else f"+{affinity}" if affinity > 0 else "0"
                
                choice_info = {
                    "talk_index": talk_index,
                    "choice_group": choice["choice_group"],
                    # 清理好感选项里面的富文本标签
                    "text": f"（{choice['choice_group']}）{clean_tags(choice['zh_tw_text'] if choice['zh_tw_text'] else (choice['kr_text' if is_test else 'zh_tw_text']))}({affinity_str})",
                    "affinity": affinity,
                    "position_type": position_type,
                    "group_no": choice.get("group_no"),
                    "episode": ep['episode']
                }
                all_choices.append(choice_info)
        
        if not all_choices:
            continue
        
        # 保存本章节的所有选项
        all_episodes_choices.append({
            "episode": ep['episode'],
            "title": ep['zh_tw_title'] if ep['zh_tw_title'] else (ep['kr_title'] if is_test else ep['zh_tw_title']),
            "choices": all_choices
        })
        
        # 为每个结局添加章节标题
        title = ep['zh_tw_title'] if ep['zh_tw_title'] else (ep['kr_title'] if is_test else ep['zh_tw_title'])
        good_end.append(f"\nEP{ep['episode']}：{title}")
        normal_end.append(f"\nEP{ep['episode']}：{title}")
        bad_end.append(f"\nEP{ep['episode']}：{title}")

        # 按talk_index排序所有选项
        all_choices.sort(key=lambda x: x["talk_index"])
        
        # 处理好结局选项
        good_choices = []
        current_index = None
        current_group = []
        
        for choice in all_choices:
            if current_index != choice["talk_index"]:
                # 处理上一组的选项
                if current_group:
                    # 找出最高好感度的选项
                    max_affinity = max((c["affinity"] for c in current_group))
                    # 只添加最高好感度的选项
                    for c in current_group:
                        if c["affinity"] == max_affinity:
                            good_choices.append(c["text"])
                # 开始新的一组
                current_index = choice["talk_index"]
                current_group = [choice]
            else:
                current_group.append(choice)
        
        # 处理最后一组
        if current_group:
            max_affinity = max((c["affinity"] for c in current_group))
            for c in current_group:
                if c["affinity"] == max_affinity:
                    good_choices.append(c["text"])
        
        good_end.extend(good_choices)
        
        # 处理坏结局选项
        bad_choices = []
        current_index = None
        current_group = []
        
        for choice in all_choices:
            if current_index != choice["talk_index"]:
                # 处理上一组的选项
                if current_group:
                    # 首先查找是否有负数好感度的选项
                    min_affinity = min((c["affinity"] for c in current_group))
                    if min_affinity < 0:
                        # 找出所有具有最小负数好感度的选项
                        min_aff_choices = [c["text"] for c in current_group if c["affinity"] == min_affinity]
                        if len(min_aff_choices) > 1:
                            bad_choices.append("或者".join(min_aff_choices))
                        else:
                            bad_choices.extend(min_aff_choices)
                    else:
                        # 如果没有负数好感度，查找0好感度的选项
                        zero_choices = [c["text"] for c in current_group if c["affinity"] == 0]
                        if zero_choices:
                            if len(zero_choices) > 1:
                                bad_choices.append("或者".join(zero_choices))
                            else:
                                bad_choices.extend(zero_choices)
                        else:
                            # 如果既没有负数也没有0，则选择最小的正数好感度
                            min_positive = min((c["affinity"] for c in current_group))
                            min_pos_choices = [c["text"] for c in current_group if c["affinity"] == min_positive]
                            if len(min_pos_choices) > 1:
                                bad_choices.append("或者".join(min_pos_choices))
                            else:
                                bad_choices.extend(min_pos_choices)
                
                # 开始新的一组
                current_index = choice["talk_index"]
                current_group = [choice]
            else:
                current_group.append(choice)
        
        # 处理最后一组
        if current_group:
            min_affinity = min((c["affinity"] for c in current_group))
            if min_affinity < 0:
                min_aff_choices = [c["text"] for c in current_group if c["affinity"] == min_affinity]
                if len(min_aff_choices) > 1:
                    bad_choices.append("或者".join(min_aff_choices))
                else:
                    bad_choices.extend(min_aff_choices)
            else:
                zero_choices = [c["text"] for c in current_group if c["affinity"] == 0]
                if zero_choices:
                    if len(zero_choices) > 1:
                        bad_choices.append("或者".join(zero_choices))
                    else:
                        bad_choices.extend(zero_choices)
                else:
                    min_positive = min((c["affinity"] for c in current_group))
                    min_pos_choices = [c["text"] for c in current_group if c["affinity"] == min_positive]
                    if len(min_pos_choices) > 1:
                        bad_choices.append("或者".join(min_pos_choices))
                    else:
                        bad_choices.extend(min_pos_choices)
        
        bad_end.extend(bad_choices)

    # 计算一般结局的选项
    normal_choices_by_episode = calculate_normal_ending_choice(all_episodes_choices, bad_threshold, normal_threshold)
    
    # 添加一般结局的选项到结果中
    for episode_data in normal_choices_by_episode:
        episode_num = episode_data["episode"]
        choices = episode_data["choices"]
        
        # 找到对应章节在normal_end中的位置
        for i, line in enumerate(normal_end):
            if line.startswith(f"\nEP{episode_num}："):
                # 在章节标题后添加选项
                normal_end[i+1:i+1] = choices
                break
    
    # 合并所有结局信息
    result = ["【好感故事攻略】"]
    result.extend(good_end)
    result.extend([""] + normal_end)
    result.extend([""] + bad_end)
    
    return "\n".join(result)


def get_base_battle_power(data: dict, entity_type: int, level: int) -> int:
    """计算基础战力
    
    Args:
        data: 游戏数据字典
        entity_type: 实体类型 (1=角色, 2=怪物, 3=raid)
        level: 等级
    
    Returns:
        int: 计算出的基础战力(整数)
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
        
        # 计算战力，向下取整
        # 公式：base + (level_value + level_per_value * level) * (level - 1)
        battle_power = int(base_value + (level_value + level_per_value * level) * (level - 1))
        return battle_power
    
    except Exception as e:
        logger.error(f"计算基础战力时发生错误: {e}")
        return 0


def get_stage_team_battle_power(data: dict, level: int, hero_grade: int, hero_count: int = 5) -> int:
    """计算主线队伍总战力
    
    Args:
        data: 游戏数据字典
        level: 等级
        hero_grade: 角色品质
        hero_count: 队伍中的角色数量，默认为5
    
    Returns:
        int: 计算出的总战力(整数)
    """
    try:
        base_battle_power = get_base_battle_power(data, 2, level)
        level_grade_value = 1.0
        level_grades = data["hero_level_grade"]["json"]
        level_grades.sort(key=lambda x: x.get("level", 0))
        
        for grade_data in level_grades:
            if grade_data.get("level", 0) <= level:
                level_grade_value = grade_data.get("value", 1.0)
            else:
                break
                
        max_level_data = max(level_grades, key=lambda x: x.get("level", 0))
        if level >= max_level_data.get("level", 0):
            level_grade_value = max_level_data.get("value", 1.0)
        
        hero_grade_value = 0.85
        for grade_data in data["hero_grade"]["json"]:
            if grade_data.get("name_sno") == hero_grade:
                hero_grade_value = grade_data.get("hero_grade_value", 0.85)
                break
        
        # 计算总战力
        # 公式：(基础战力 + (等级加成率 - 1) * 基础战力 + (角色品质值 - 1) * 基础战力) * 角色数量
        level_bonus = int((level_grade_value - 1) * base_battle_power)
        grade_bonus = int((hero_grade_value - 1) * base_battle_power)
        team_power = int((base_battle_power + level_bonus + grade_bonus) * hero_count)
        return team_power
    
    except Exception as e:
        logger.error(f"计算主线队伍总战力时发生错误: {e}")
        return 0


def get_character_skill_pattern(data: dict, hero_no: int, is_test: bool = False) -> list:
    """获取角色技能释放顺序
    
    Args:
        data: 游戏数据字典
        hero_no: 角色编号
    
    Returns:
        list: 技能释放顺序列表，每个元素为(技能名称, 是否为普通攻击)
    """
    print(f"角色: {hero_no}")
    try:
        # 查找角色的技能释放顺序
        pattern_data = None
        for pattern in data["skill_pattern"]["json"]:
            if pattern.get("hero_no") == hero_no:
                pattern_data = pattern
                break
        print(f"pattern_data: {pattern_data}")
        if not pattern_data:
            return []
        
        # 收集所有pattern键
        pattern_keys = [key for key in pattern_data.keys() if key.startswith("pattern")]
        pattern_keys.sort(key=lambda x: int(x.replace("pattern", "")))
        print(f"pattern_keys: {pattern_keys}")
        # 获取技能顺序
        skill_pattern = []
        for key in pattern_keys:
            skill_no = pattern_data.get(key)
            if skill_no == hero_no:
                # 普通攻击
                skill_pattern.append(("普通攻击", True))
            else:
                # 获取技能名称
                skill_name = ""
                for skill in data["skill"]["json"]:
                    if skill["no"] == skill_no:
                        if "name_sno" not in skill:
                            skill_pattern.append(("返回原位", False))
                            break
                        for string in data["string_skill"]["json"]:
                            if string["no"] == skill["name_sno"]:
                                zh_tw = string.get("zh_tw", "")
                                kr = string.get("kr", "")
                                skill_name = zh_tw if zh_tw else (kr if is_test else zh_tw)
                                break
                        if skill_name:
                            skill_pattern.append((skill_name, False))
                        break
        
        return skill_pattern
    
    except Exception as e:
        logger.error(f"获取角色技能释放顺序时发生错误: {e}")
        return []