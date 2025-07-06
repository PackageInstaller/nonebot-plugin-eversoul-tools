"""
字符串和多语言文本处理模块
"""
import os
import re
import ast
from nonebot.log import logger
from difflib import get_close_matches
from ...config import (
    TOWN_DIR, TRAIT_NAME_MAPPING, 
    PACKAGE_TYPE_MAPPING, STAT_NAME_MAPPING,
    FORMATION_TYPE_MAPPING, SIGNATURE_GRADE_LEVEL_MAP
)


def format_number(num):
    """Convert numbers to Chinese units, accurate to two units
    For example: 123456789 -> 120 million 34560000
    For numbers that can be accurately expressed with one unit, still use one unit
    For example: 50000000 -> 50 million
    Support negative numbers
    args:
        num: number
    return:
        str: formatted number
    exception:
        None
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
    """clean text tags
    
    Args:
        text: text
    
    Returns:
        str: cleaned text
    """
    # 处理 <color=#XXXXXX> 格式
    # handle <color=#XXXXXX> format
    text = re.sub(r'<color=#[A-Fa-f0-9]+>', '', text, flags=re.IGNORECASE)
    # handle </color> format
    text = re.sub(r'</color>', '', text, flags=re.IGNORECASE)
    
    # 处理 <COLOR=#XXXXXX> 格式
    # handle <COLOR=#XXXXXX> format
    text = re.sub(r'<COLOR=#[A-Fa-f0-9]+>', '', text, flags=re.IGNORECASE)
    # handle </COLOR> format
    text = re.sub(r'</COLOR>', '', text, flags=re.IGNORECASE)
    
    # 处理可能存在的空格
    # handle possible spaces
    text = re.sub(r'<color\s*=#[A-Fa-f0-9]+\s*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</color\s*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<COLOR\s*=#[A-Fa-f0-9]+\s*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'</COLOR\s*>', '', text, flags=re.IGNORECASE)
    
    # 处理 <color="#XXXXXX"> 格式（带引号的情况）
    # handle <color="#XXXXXX"> format (with quotes)
    text = re.sub(r'<color="[#A-Fa-f0-9]+"\s*>', '', text, flags=re.IGNORECASE)
    # handle <COLOR="#XXXXXX"> format (with quotes)
    text = re.sub(r'<COLOR="[#A-Fa-f0-9]+"\s*>', '', text, flags=re.IGNORECASE)
    
    # 处理 <effect:none> 标签
    # handle <effect:none> tag
    text = re.sub(r'<effect:none>', '', text, flags=re.IGNORECASE)
    
    return text


def get_formation_type(formation_no):
    """get formation type
    
    Args:
        formation_no: formation no
    
    Returns:
        str: formation type
    """
    return FORMATION_TYPE_MAPPING.get(formation_no, "")


def get_string_system(data, no):
    """get string system
    
    Args:
        data: JSON data dictionary
        no: string no
        
    Returns:
        dict: include different language text, keys are 'zh_tw', 'zh_cn', 'kr', 'en'
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
    """get string ui
    
    Args:
        data: JSON data dictionary
        no: string no
        
    Returns:
        dict: include different language text, keys are 'zh_tw', 'zh_cn', 'kr', 'en'
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


def get_string_talk(data, no):
    """get string talk
    
    Args:
        data: JSON data dictionary
        no: string no
        
    Returns:
        dict: include different language text, keys are 'zh_tw', 'zh_cn', 'kr', 'en'
    """
    for string in data["string_talk"]["json"]:
        if string["no"] == no:
            return {
                "zh_tw": string.get("zh_tw", "").replace('\\r\\n', '\n').replace('\r\n', '\n'),
                "zh_cn": string.get("zh_cn", "").replace('\\r\\n', '\n').replace('\r\n', '\n'),
                "kr": string.get("kr", "").replace('\\r\\n', '\n').replace('\r\n', '\n'),
                "en": string.get("en", "").replace('\\r\\n', '\n').replace('\r\n', '\n')
            }
    return {"zh_tw": "", "zh_cn": "", "kr": "", "en": ""}


def get_string_character(data, hero_no, special=False):
    """get string character
    
    Args:
        data: JSON data dictionary
        hero_no: hero no
        special: special, used when the text cannot be directly obtained from string_character
    Returns:
        dict: include different language text, keys are 'zh_tw', 'zh_cn', 'kr', 'en'

    get string character
    args:
        data: JSON data dictionary
        hero_no: hero no
        special: special
    return:
        dict: string character
    exception:
        None
    """
    name_sno = hero_no
    
    if special:
        # 在角色模式下，先找到hero_no对应的name_sno
        # in character mode, first find the name_sno corresponding to hero_no
        for hero in data["hero"]["json"]:
            if hero["no"] == hero_no:
                name_sno = hero.get("name_sno")
                break
    
    # 根据name_sno查找对应的文本
    # find the corresponding text according to name_sno
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
    """get drop item info, keep the item with the highest probability for the same name
    
    Args:
        data: JSON data dictionary
        group_no: drop group no
    
    Returns:
        list: [(item name, amount, drop rate)]
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
                # convert drop rate (1 = 0.001%)
                rate_percent = drop_rate * 0.001
                drop_items.append((item_name, amount, rate_percent))
    
    # 名称作为键，保存概率最高的物品
    # name as key, save the item with the highest probability
    name_to_best_item = {}
    
    for item in drop_items:
        item_name = item[0]['zh_tw']
        item_rate = item[2]
        
        # 如果名称还没有记录，或者当前概率更高，则更新
        # if the name is not recorded, or the current probability is higher, then update
        if item_name not in name_to_best_item or item_rate > name_to_best_item[item_name][2]:
            name_to_best_item[item_name] = item
    
    # 将字典值转换为列表
    # convert dictionary values to list
    unique_items = list(name_to_best_item.values())
    
    # sort by drop rate from high to low
    # 按掉落率从高到低排序
    return sorted(unique_items, key=lambda x: -x[2])


def get_character_skill_type(data, type_no):
    """get character skill type
    
    Args:
        data: JSON data dictionary
        type_no: skill type no
    
    Returns:
        dict: include different language text, keys are 'zh_tw', 'zh_cn', 'kr', 'en'
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
    get string item

    Args:
        data: JSON data dictionary
        item_no: item no
    
    Returns:
        dict: include different language text, keys are 'zh_tw', 'zh_cn', 'kr', 'en'
    """
    # 在Item.json中查找物品
    # find the item in Item.json
    for item in data["item"]["json"]:
        if item["no"] == item_no:
            name_sno = item.get("name_sno")
            if name_sno:
                # 在StringItem.json中查找物品名称
                # find the item name in StringItem.json
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
    """get character cv
    
    Args:
        data: JSON data dictionary
        hero_desc: hero desc
    
    Returns:
        dict: include korean and japanese cv, keys are 'kr', 'ja'
    """
    cv_kr = get_string_character(data, hero_desc.get("cv_sno", 0))["zh_tw"] if hero_desc else "？？？"
    cv_ja = get_string_character(data, hero_desc.get("cv_jp_sno", 0))["zh_tw"] if hero_desc else "？？？"
    cv_ja = cv_ja if cv_ja != cv_kr and cv_ja != "" else "？？？"

    return {"kr": cv_kr, "ja": cv_ja}


def get_character_release_date(data, hero_id):
    """get character release date
    
    Args:
        data: JSON data dictionary
        hero_id: hero id
    
    Returns:
        str: formatted release date, if not found, return default date (2023-01-05)
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


def get_character_arbeit(data, hero_id):
    """get character arbeit
    
    Args:
        data: JSON data dictionary
        hero_id: hero id
    
    Returns:
        dict: include initial and max level attributes, keys are 'initial', 'max'

    get character arbeit
    args:
        data: JSON data dictionary
        hero_id: hero id
    return:
        dict: character arbeit, if not found, return "？？？"
    exception:
        None
    """
    # 收集所有相关等级的数据
    # collect all related level data
    level_data = []
    for level in data["arbeit_fairy_level"]["json"]:
        if level.get("hero_no") == hero_id:
            level_data.append(level)
    
    if not level_data:
        return {"initial": "？？？", "max": "？？？"}
    
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


def get_character_prefer_gift(data, hero_id):
    """get character prefer gift
    
    Args:
        data: JSON data dictionary
        hero_id: hero id
    
    Returns:
        str: prefer gift items, separated by comma

    get character prefer gift
    args:
        data: JSON data dictionary
        hero_id: hero id
    return:
        str: prefer gift items, separated by comma
    exception:
        None
    """
    # 在HeroGift.json中查找角色的喜好礼物
    # find the character's prefer gift in HeroGift.json
    gift_items = []
    for gift in data["hero_gift"]["json"]:
        if gift.get("hero_no") == hero_id:
            # 获取prefer_gift_items字符串并分割成列表
            # get prefer_gift_items string and split into list
            prefer_items = gift.get("prefer_gift_items", "").split(",")
            prefer_items = [item.strip() for item in prefer_items if item.strip()]
            # process each item_no
            # 对每个物品ID进行处理
            for item_no in prefer_items:
                # 在Item.json中查找物品信息
                # find the item in Item.json
                for item in data["item"]["json"]:
                    if str(item.get("no")) == item_no:
                        # 获取物品名称
                        # get item name
                        name_sno = item.get("name_sno")
                        if name_sno:
                            # 在StringItem.json中查找物品名称
                            # find the item name in StringItem.json
                            for string in data["string_item"]["json"]:
                                if string.get("no") == name_sno:
                                    gift_items.append(string.get("zh_tw", ""))
                                    break
                        break
    
    return "、".join(gift_items) if gift_items else "？？？"


def get_character_similar_name(query, alias_map):
    """get character similar name
    Args:
        query: query name
        alias_map: alias map
    
    Returns:
        list: character similar name list [(name, aliases), ...]
    """
    # 创建反向映射：hero_id -> (name, aliases)
    # create reverse mapping: hero_id -> (name, aliases)
    hero_map = {}
    for name, hero_id in alias_map.items():
        if hero_id not in hero_map:
            hero_map[hero_id] = [name, []]
        else:
            if len(hero_map[hero_id][1]) == 0:  # 第一个名字是主名称. the first name is main name
                hero_map[hero_id][1].append(name)
            else:
                hero_map[hero_id][1].append(name)
    
    # 收集所有可能的名称（主名称和别名）
    # collect all possible names (main name and aliases)
    all_names = []
    for name, hero_id in alias_map.items():
        all_names.append(name)
    
    # 使用 difflib 查找相似名称
    # use difflib to find similar names
    similar_names = get_close_matches(query, all_names, n=3, cutoff=0.4)
    
    # 收集匹配到的角色信息
    # collect matched character info
    results = []
    for similar_name in similar_names:
        hero_id = alias_map[similar_name]
        main_name = hero_map[hero_id][0]
        aliases = [alias for alias in hero_map[hero_id][1] if alias != main_name]
        if (main_name, aliases) not in results:
            results.append((main_name, aliases))
    
    return results


def get_character_skill_value(data, value_id, value_type="VALUE"):
    """get character skill value
    
    Args:
        data: JSON data dictionary
        value_id: skill id
        value_type: value type ("VALUE" or "DURATION")
    """
    # 查找SkillCode
    # find SkillCode
    skill_code = None
    for code in data["skill_code"]["json"]:
        if code["no"] == value_id:
            skill_code = code
            break
    
    if not skill_code:
        return "？？？"
    
    function_key = skill_code.get("function_key", 0)
    
    # 根据官方逻辑判断特殊处理的function_key
    # determine special handling function_key according to official logic
    if function_key > 29:
        # function_key == 300 或 30 的特殊处理
        # special handling for function_key == 300 or 30
        if function_key == 300 or function_key == 30:
            skill_value = skill_code.get("value", 0)
            value_as_int = int(skill_value) if isinstance(skill_value, float) and skill_value.is_integer() else skill_value
            
            # 在SkillBuff中查找
            # find in SkillBuff
            for buff in data["skill_buff"]["json"]:
                if buff["no"] == value_as_int:
                    if value_type == "VALUE":
                        buff_value = buff.get("value", 0)
                        buff_effect = buff.get("buff_effect", 0)
                        abs_value = abs(buff_value)
                        
                        # 使用BuffValueText的逻辑判断整数还是百分比
                        # use BuffValueText logic to determine integer or percentage
                        if get_buff_value_text_is_integer(buff_effect):
                            return str(int(abs_value))
                        else:
                            percent_value = abs_value * 100
                            rounded_value = round(percent_value, 1)
                            if rounded_value.is_integer():
                                return f"{int(rounded_value)}%"
                            return f"{rounded_value}%"
                    elif value_type == "DURATION":
                        duration = buff.get("duration", 0)
                        return str(int(abs(duration)))
                    break
            return "？？？"
    else:
        # function_key <= 29 的处理
        # handling for function_key <= 29
        if function_key in [25, 28, 29]:
            # 特殊类型的处理逻辑
            # special type handling logic
            if value_type == "DURATION":
                duration = skill_code.get("duration", 0)
                return str(int(abs(duration)))
            
            # VALUE类型需要递归查找
            # VALUE type needs recursive lookup
            skill_value = skill_code.get("value", 0)
            value_as_int = int(skill_value) if isinstance(skill_value, float) and skill_value.is_integer() else skill_value
            
            # 递归查找引用的SkillCode
            # recursively find referenced SkillCode
            referenced_code = None
            for code in data["skill_code"]["json"]:
                if code["no"] == value_as_int:
                    referenced_code = code
                    break
            
            if referenced_code:
                ref_function_key = referenced_code.get("function_key", 0)
                ref_value = referenced_code.get("value", 0)
                
                # 如果引用的是SkillBuff类型
                # if referencing SkillBuff type
                if ref_function_key == 300 or ref_function_key == 30:
                    ref_value_as_int = int(ref_value) if isinstance(ref_value, float) and ref_value.is_integer() else ref_value
                    for buff in data["skill_buff"]["json"]:
                        if buff["no"] == ref_value_as_int:
                            buff_value = buff.get("value", 0)
                            buff_effect = buff.get("buff_effect", 0)
                            abs_value = abs(buff_value)
                            
                            if get_buff_value_text_is_integer(buff_effect):
                                return str(int(abs_value))
                            else:
                                percent_value = abs_value * 100
                                rounded_value = round(percent_value, 1)
                                if rounded_value.is_integer():
                                    return f"{int(rounded_value)}%"
                                return f"{rounded_value}%"
                            break
                    return "？？？"
                else:
                    # 直接使用引用代码的值
                    # directly use referenced code value
                    abs_value = abs(ref_value)
                    if get_code_value_text_is_integer(ref_function_key):
                        return str(int(abs_value))
                    else:
                        percent_value = abs_value * 100
                        rounded_value = round(percent_value, 1)
                        if rounded_value.is_integer():
                            return f"{int(rounded_value)}%"
                        return f"{rounded_value}%"
        
        # 常规处理逻辑
        # regular handling logic
        if value_type == "VALUE":
            skill_value = skill_code.get("value", 0)
            abs_value = abs(skill_value)
            
            if get_code_value_text_is_integer(function_key):
                return str(int(abs_value))
            else:
                percent_value = abs_value * 100
                rounded_value = round(percent_value, 1)
                if rounded_value.is_integer():
                    return f"{int(rounded_value)}%"
                return f"{rounded_value}%"
        elif value_type == "DURATION":
            duration = skill_code.get("duration", 0)
            return str(int(abs(duration)))
    
    return "？？？"


def get_code_value_text_is_integer(skill_effect_type):
    """Determine whether the skill value should be formatted as integer in SkillTextUtil::GetCodeValueText
    
    Official logic from SkillTextUtil::GetCodeValueText:
    if (type <= 0x1B && ((1 << type) & 0xC000010) != 0 || type - 1026 < 2)
    
    Args:
        skill_effect_type: SkillEffect enum value (function_key)
    Returns:
        bool: True if should format as integer, False if should format as percentage
    """
    condition1 = (skill_effect_type <= 0x1B) and (((1 << skill_effect_type) & 0xC000010) != 0)
    condition2 = (skill_effect_type >= 1026) and (skill_effect_type < 1028)
    
    return condition1 or condition2


def get_buff_value_text_is_integer(buff_type):
    """Determine whether the buff value should be formatted as integer in SkillTextUtil::GetBuffValueText
    
    Official logic from SkillTextUtil::GetBuffValueText:
    if (type <= 10102) {
        if ((type - 10101) >= 2 && type != 420)
            goto LABEL_12;  // percentage
    LABEL_11:
        // integer format
    }
    if ((type - 10106) <= 4 && ((1 << (type - 122)) & 0x13) != 0)
        goto LABEL_11;  // integer
    LABEL_12:
        // percentage format
    
    Args:
        buff_type: buff effect type
    Returns:
        bool: True if should format as integer, False if should format as percentage
    """
    if buff_type <= 10102:
        # Special cases that format as integer
        if buff_type in {10101, 10102, 420}:
            return True
        # All other values <= 10102 format as percentage
        return False
    
    # For buff_type > 10102, check second condition
    if (buff_type - 10106) <= 4 and ((1 << (buff_type - 122)) & 0x13) != 0:
        return True
    
    # Default to percentage format
    return False


def process_skill_description(data, description):
    """process skill description
    
    Args:
        data: JSON data dictionary
        description: skill description
    """
    def replace_value(match):
        value_id = int(match.group(1))
        value_type = match.group(2)
        return get_character_skill_value(data, value_id, value_type)
    
    # 替换所有形如 <数字.VALUE> 或 <数字.DURATION> 的内容
    # replace all content like <number.VALUE> or <number.DURATION>
    processed_desc = re.sub(r'<\s*(\d+)\.(VALUE|DURATION)\s*>', replace_value, description)
    return processed_desc


def get_character_skill(data, skill_no, is_support=False, hero_data=None):
    """get character skill
    
    Args:
        data: JSON data dictionary
        skill_no: skill no
        is_support: is support skill
        hero_data: hero data (used to get auxiliary partner skill info)
    
    Returns:
        dict: include skill info
    """
    skill_data_list = []
    skill_name_zh_tw = ""
    skill_name_zh_cn = ""
    skill_name_kr = ""
    skill_name_en = ""
    skill_descriptions = []
    skill_icon_info = None
    
    # 查找所有相同编号的技能数据
    # find all skills with the same no
    for skill in data["skill"]["json"]:
        if skill["no"] == skill_no:
            skill_data_list.append(skill)
            # 只在第一次找到技能时获取图标信息
            # only get icon info once
            if not skill_icon_info:
                icon_prefab = skill.get("icon_prefab")
                # 这里是适配数据表里面没有的转变形态技能的着色(光凯)
                # here is to adapt the coloring of the transformation skill that is not in the data table
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
        # get skill name
        for string in data["string_skill"]["json"]:
            if string["no"] == skill_data_list[0]["name_sno"]:
                skill_name_zh_tw = string.get("zh_tw", "")
                skill_name_zh_cn = string.get("zh_cn", "")
                skill_name_kr = string.get("kr", "")
                skill_name_en = string.get("en", "")
                break
        
        if is_support:
            # 找出最高等级的技能数据
            # find the highest level skill data
            max_level_skill = max(skill_data_list, key=lambda x: x.get("level", 0))
            
            # 获取主要伙伴技能描述
            # get main partner skill description
            for string in data["string_skill"]["json"]:
                if string["no"] == max_level_skill["tooltip_sno"]:
                    desc_tw = string.get("zh_tw", "")
                    desc_cn = string.get("zh_cn", "")
                    desc_kr = string.get("kr", "")
                    desc_en = string.get("en", "")
                    # 清理颜色标签. clean color tags
                    desc_tw = clean_tags(desc_tw)
                    desc_cn = clean_tags(desc_cn)
                    desc_kr = clean_tags(desc_kr)
                    desc_en = clean_tags(desc_en)
                    # 处理数值标签. process value tags
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
            # if hero_data is provided, get auxiliary partner skill description
            if hero_data:
                sub_class_sno = hero_data.get("sub_class_sno")
                max_grade_sno = hero_data.get("max_grade_sno")
                
                if sub_class_sno and max_grade_sno:
                    # 在WorldRaidPartnerBuff中查找匹配的buff
                    # find matching buff in WorldRaidPartnerBuff.json
                    for buff in data["world_raid_partner_buff"]["json"]:
                        if (buff["sub_class"] == sub_class_sno and 
                            buff["grade"] == max_grade_sno):
                            buff_sno = buff.get("buff_sno")
                            buff_no = buff.get("buff_no")
                            
                            if buff_sno and buff_no:
                                # 获取buff数值. get buff value
                                buff_values = []  # 改用列表存储数值. use list to store values
                                for content_buff in data["contents_buff"]["json"]:
                                    # find the buff in contents_buff.json
                                    if content_buff.get("no") == buff_no:
                                        # 遍历所有属性，按顺序收集非零数值. traverse all attributes, collect non-zero values in order
                                        for key, value in content_buff.items():
                                            if (isinstance(value, (int, float)) and 
                                                value != 0 and 
                                                key != "no"):  # 排除 no 字段. exclude no field
                                                # 根据数值大小判断是否为百分比，取绝对值
                                                # determine if it is an integer or percentage based on value
                                                if abs(value) < 20:  # 小于等于20的按百分比处理. less than or equal to 20 is processed as percentage
                                                    buff_values.append(int(abs(value) * 100))
                                                else:  # 大于20的按整数处理. greater than 20 is processed as integer
                                                    buff_values.append(int(abs(value)))
                                
                                # 在StringUI中查找描述文本. find description text in StringUI.json
                                for string in data["string_ui"]["json"]:
                                    if string["no"] == buff_sno:
                                        desc_tw = string.get("zh_tw", "")
                                        desc_cn = string.get("zh_cn", "")
                                        desc_kr = string.get("kr", "")
                                        desc_en = string.get("en", "")
                                        
                                        # 正则表达式找出所有占位符. find all placeholders using regex
                                        placeholders = re.findall(r'{([^}]+)}', desc_tw)
                                        
                                        # 按顺序替换所有占位符. replace all placeholders in order
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
            # 非支援技能，获取所有等级的技能描述. non-support skill, get skill description for all levels
            for skill_data in skill_data_list:
                hero_level = skill_data.get("hero_level", 1)  # 获取技能解锁等级. get skill unlock level
                for string in data["string_skill"]["json"]:
                    if string["no"] == skill_data["tooltip_sno"]:
                        desc_tw = string.get("zh_tw", "")
                        desc_cn = string.get("zh_cn", "")
                        desc_kr = string.get("kr", "")
                        desc_en = string.get("en", "")
                        # 清理颜色标签. clean color tags
                        desc_tw = clean_tags(desc_tw)
                        desc_cn = clean_tags(desc_cn)
                        desc_kr = clean_tags(desc_kr)
                        desc_en = clean_tags(desc_en)
                        # 处理数值标签. process value tags
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
    """get character keyword location
    
    Args:
        data: JSON data dictionary
        keyword_get_details: keyword get details
        is_test: is test
    """    
    # 如果没有keyword_get_details或为0，返回"通用"
    # if keyword_get_details is not provided or is 0, return "通用"
    if not keyword_get_details:
        return "通用"
    
    # 在TownLocation.json中查找对应地点
    # find the corresponding location in TownLocation.json
    location = next((loc for loc in data["town_location"]["json"] 
                    if loc["no"] == keyword_get_details), None)
    
    if not location:
        return ""
    
    # 获取地点名称，优先使用zh_tw
    # get location name, use zh_tw first
    location_data = next((s for s in data["string_town"]["json"] 
                        if s["no"] == location.get("location_name_sno")), None)
    if location_data:
        zh_tw = location_data.get("zh_tw", "")
        kr = location_data.get("kr", "")
        return zh_tw if zh_tw else (kr if is_test else zh_tw)
    return ""


def get_character_lost_item(data: dict, hero_no: int, keyword_type: int, keyword_get_details: int, is_test: bool = False) -> str:
    """get character lost item
    
    Args:
        data: JSON data dictionary
        hero_no: hero no
        keyword_type: keyword type
        keyword_get_details: keyword get details
        is_test: is test
    """
    try:
        # 在TownLostItem.json中查找对应条目. find the corresponding item in TownLostItem.json
        lost_item = next((item for item in data["town_lost_item"]["json"] 
                        if item.get("hero_no") == hero_no and 
                        item.get("keyword_type") == keyword_type and 
                        item.get("keyword_get_details") == keyword_get_details), None)
        
        if not lost_item:
            return ""

        quest_type = lost_item.get("quest_type")

        if quest_type == 1: # 归还领地遗失物品. return lost item to town
            if group_end := lost_item.get("group_end"):
                talks = [t for t in data["talk"]["json"] if t.get("group_no") == group_end]
                # find the choice talk in Talk.json
                choice_talk = next((t for t in reversed(talks) if t.get("ui_type", "").lower() == "choice"), None)
                if choice_talk and choice_talk.get("no"):
                    action = next((s.get("kr" if is_test else "zh_tw", "") for s in data["string_talk"]["json"] 
                                if s.get("no") == choice_talk.get("no")), "")
                    return f"{action}"

        elif quest_type == 2: # 击杀魔物. kill monster
            if group_end := lost_item.get("group_end"):
                talks = [t for t in data["talk"]["json"] if t.get("group_no") == group_end]
                choice_talk = next((t for t in reversed(talks) if t.get("ui_type", "").lower() == "choice"), None)
                if choice_talk and choice_talk.get("no"):
                    action = next((s.get("kr" if is_test else "zh_tw", "") for s in data["string_talk"]["json"] 
                                if s.get("no") == choice_talk.get("no")), "")
                    return f"{action}"

        elif quest_type == 3: # 外出获取. get out
            # 获取地点信息. get location info
            if group_trip := lost_item.get("group_trip"):
                # 在Talk.json中查找对应对话. find the corresponding talk in Talk.json
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
    """get character keyword point
    
    Args:
        data: JSON data dictionary
        keyword_type: keyword type
    """
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
    return [20, 40, 60]  # 默认值. default value


def get_character_keyword_source(data: dict, source_sno: int, details: int, hero_no: int, keyword_type: int = 0, is_test: bool = False) -> str:
    """get character keyword source
    
    Args:
        data: JSON data dictionary
        source_sno: source sno
        details: details
        hero_no: hero no
        keyword_type: keyword type
        is_test: is test
    """
    # 优先获取zh_tw，当zh_tw为空时再根据is_test判断. get zh_tw first, then check is_test
    source_data = next((s for s in data["string_ui"]["json"] if s["no"] == source_sno), None)
    if source_data:
        zh_tw = source_data.get("zh_tw", "")
        kr = source_data.get("kr", "")
        source = zh_tw if zh_tw else (kr if is_test else zh_tw)
    else:
        source = ""
    
    if not source:
        return ""
        
    # 检查是否是遗失物品. check if it is lost item
    if hero_no and keyword_type:
        lost_item = get_character_lost_item(data, hero_no, keyword_type, details, is_test)
        if lost_item:
            return lost_item
        
    if 101 <= details <= 110:
        location = next((loc for loc in data["town_location"]["json"] 
                        if loc["no"] == details), None)
        if location:
            # 获取地点名称，优先使用zh_tw. get location name, use zh_tw first
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
    elif source_sno == 619006:  # 打工熟练度. work skill
        try:
            return source.format(details)
        except Exception as e:
            return f"打工熟练度达Lv.{details}时可获得"
    elif "好感達Lv.{0}" in source or "好感达等级{0}" in source:  # 好感等级. favor level
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
                # 分别处理章和节. handle chapter and episode separately
                if "{0}{1}" in source:
                    result = source.format(f"第{act}章", episode)
                else:
                    result = source.format(f"{act}-{episode}")
                return result
            except Exception as e:
                return f"完成主线故事第{act}章 {episode}话时可获得"
    return source


def get_character_keyword(data: dict, hero_id: int, is_test: bool = False) -> str:
    """get character keyword
    
    Args:
        data: JSON data dictionary
        hero_id: hero id
        is_test: is test
    """
    trip_keywords = []
    keyword_msgs = []
    
    for trip in data["trip_hero"]["json"]:
        if trip.get("hero_no") == hero_id:
            # 这里是先处理30个通用的关键字
            # here is to handle 30 generic keywords first
            keyword_info = next((k for k in data["trip_keyword"]["json"] 
                               if k["no"] == trip.get("keyword_no")), None)
            if keyword_info:
                # 确定关键字类型和好感度. determine keyword type and favor point
                keyword_type = "normal" # 粉心. pink heart
                if not trip.get("favor_point"): # 没这个键的话就是黄心. if no this key, then it is yellow heart
                    keyword_type = "bad"
                elif trip.get("favor_point") == 2: # 红心. red heart
                    keyword_type = "good"
                
                # 获取好感度加成. get favor point bonus
                points = get_character_keyword_point(data, keyword_type)
                grade_sno = keyword_info.get("keyword_grade")
                grade_index = 0 # 一般. normal
                if grade_sno == 110012:  # 稀有. rare
                    grade_index = 1
                elif grade_sno == 110014:  # 史诗. epic
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
    
    # 分组显示关键字. group and display keywords
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
        # 先显示没有获取条件的关键字. first display keywords without conditions
        normal_keywords = [k for k in good_keywords if not k["source"]]
        for keyword in normal_keywords:
            msg = f"・{keyword['name']}（{keyword['grade']}）"
            # 添加地点信息. add location info
            if location := get_character_keyword_location(data, keyword.get("keyword_get_details"), is_test):
                msg += f"\n  地点：{location}"
            keyword_msgs.append(msg)
        
        # 添加分隔线. add separator
        if normal_keywords and any(k["source"] for k in good_keywords):
            if good_keywords:
                keyword_msgs.append("")
            keyword_msgs.append("▼ 以下为需要解锁的关键字")
        
        for keyword in (k for k in good_keywords if k["source"]):
            msg = f"・{keyword['name']}（{keyword['grade']}）"
            # 添加地点信息. add location info
            if location := get_character_keyword_location(data, keyword.get("keyword_get_details"), is_test):
                msg += f"\n  地点：{location}"
            if keyword["source"]:
                msg += f"\n  条件：{keyword['source']}"
            keyword_msgs.append(msg)
    
    return "\n".join(keyword_msgs)


def get_character_town_object(data: dict, hero_id: int, is_test=False) -> list:
    """get character town object
    
    Args:
        data: JSON data dictionary
        hero_id: hero id
    
    Returns:
        list: object info list [(object no, object name, object grade, object type, object desc, image path), ...]
    """
    try:
        objects_info = []
        for obj in data["town_object"]["json"]:
            if obj.get("hero") == hero_id:
                obj_no = obj.get("no")
                buff2_sno = obj.get("buff2")
                if not obj_no:
                    continue
                
                # 获取prefab作为图片名称. get prefab as image name
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
                    
                # 在Item.json中查找对应物品信息. find the corresponding item in Item.json
                for item in data["item"]["json"]:
                    if item.get("no") == obj_no:
                        # 获取物品名称. get item name
                        name = ""
                        name_sno = item.get("name_sno")
                        if name_sno:
                            for string in data["string_item"]["json"]:
                                if string.get("no") == name_sno:
                                    zh_tw = string.get("zh_tw", "")
                                    kr = string.get("kr", "")
                                    name = zh_tw if zh_tw else (kr if is_test else zh_tw)
                                    break
                        
                        # 获取物品品质. get item grade
                        grade = ""
                        grade_sno = item.get("grade_sno")
                        if grade_sno:
                            for string in data["string_system"]["json"]:
                                if string.get("no") == grade_sno:
                                    zh_tw = string.get("zh_tw", "")
                                    kr = string.get("kr", "")
                                    grade = zh_tw if zh_tw else (kr if is_test else zh_tw)
                                    break
                        
                        # 获取物品类型. get item type
                        slot_type = ""
                        slot_limit_sno = item.get("slot_limit_sno")
                        if slot_limit_sno:
                            for string in data["string_ui"]["json"]:
                                if string.get("no") == slot_limit_sno:
                                    zh_tw = string.get("zh_tw", "")
                                    kr = string.get("kr", "")
                                    slot_type = zh_tw if zh_tw else (kr if is_test else zh_tw)
                                    break
                        
                        # 获取物品描述并清理颜色标签. get item description and clean color tags
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
                        
                        if name:  # 只添加有名称的物品. only add items with name
                            # 构建图片路径. build image path
                            img_path = None
                            if prefab:
                                for file in os.listdir(TOWN_DIR):
                                    if file.lower() == f"{prefab}.png":
                                        img_path = TOWN_DIR / file
                                        break
                                
                                if not os.path.exists(img_path):
                                    img_path = None
                            
                            objects_info.append((obj_no, name, grade, slot_type, desc, img_path, battle_power_per))
                        
        return objects_info
        
    except Exception as e:
        logger.error(f"获取专属领地物品信息时发生错误: {e}, hero_id={hero_id}")
        return []


def get_character_town_object_task(data: dict, obj_no: int, is_test=False) -> list:
    """get character town object task
    
    Args:
        data: JSON data dictionary
        obj_no: object no
    
    Returns:
        list: task info list
    """
    try:
        tasks_info = []
        
        # 在ArbeitChoice中查找对应物品的任务. find the corresponding item task in ArbeitChoice.json
        for choice in data["arbeit_choice"]["json"]:
            if choice.get("objet_no") == obj_no:
                arbeit_no = choice.get("arbeit_no")
                if not arbeit_no:
                    continue
                
                # 在ArbeitList中查找任务详情. find the corresponding task in ArbeitList.json
                for arbeit in data["arbeit_list"]["json"]:
                    if arbeit.get("no") == arbeit_no:
                        # 获取任务品质. get task grade
                        rarity = ""
                        rarity_sno = arbeit.get("rarity")
                        if rarity_sno:
                            for string in data["string_system"]["json"]:
                                if string.get("no") == rarity_sno:
                                    rarity_zh_tw = string.get("zh_tw", "")
                                    rarity_kr = string.get("kr", "")
                                    rarity = rarity_zh_tw if rarity_zh_tw else (rarity_kr if is_test else rarity_zh_tw)
                                    break
                        
                        # 获取任务名称. get task name
                        name = ""
                        name_sno = arbeit.get("name_sno")
                        if name_sno:
                            for string in data["string_town"]["json"]:
                                if string.get("no") == name_sno:
                                    name_zh_tw = string.get("zh_tw", "")
                                    name_kr = string.get("kr", "")
                                    name = name_zh_tw if name_zh_tw else (name_kr if is_test else name_zh_tw)
                                    break
                                    
                        # 获取所需时间. get required time
                        time_hours = arbeit.get("time", 0) / 3600
                        
                        # 获取要求特性. get required traits
                        traits = []
                        for trait, zh_name in TRAIT_NAME_MAPPING.items():
                            if stars := arbeit.get(trait):
                                traits.append(f"{zh_name}{stars}★")
                        
                        # 获取奖励物品. get rewards
                        rewards = []
                        for i in range(1, 3):  # 检查item1和item2. check item1 and item2
                            item_no = arbeit.get(f"item{i}_no")
                            item_amount = arbeit.get(f"item{i}_amount")
                            if item_no and item_amount:
                                # 查找物品名称. find item name
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
                        
                        # 添加任务信息. add task info
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
    """get cash pack
    
    Args:
        data: JSON data dictionary
        item_type: package type ('barrier'/'stage'/'tower'/'grade_eternal')
        gate_info: gate/hero info dictionary
    
    Returns:
        list: include package info message list
    """
    messages = []
    shop_items = []
    
    # 获取礼包类型显示名称. get package type display name
    package_type_name = PACKAGE_TYPE_MAPPING.get(item_type, '特殊礼包')
    
    # 获取符合条件的商店物品. get shop items that match the condition
    for shop_item in data["cash_shop_item"]["json"]:
        if shop_item.get("type") == item_type and shop_item.get("type_value") == str(gate_info["no"]):
            shop_items.append(shop_item)
    
    if shop_items:
        for shop_item in shop_items:
            package_info = []
            package_info.append(f"▼【{package_type_name}】")
            
            # 获取礼包名称和描述. get package name and description
            name_sno = shop_item.get("name_sno")
            package_name = next((s.get("zh_tw", "未知礼包") for s in data["string_cashshop"]["json"] 
                                if s["no"] == name_sno), "未知礼包")
            
            info_sno = shop_item.get("item_info_sno")
            package_desc = next((s.get("zh_tw", "") for s in data["string_cashshop"]["json"] 
                                if s["no"] == info_sno), "")
            
            desc_sno = shop_item.get("desc_sno")
            limit_desc = next((s.get("zh_tw", "").format(shop_item.get("limit_buy", 0)) 
                                for s in data["string_ui"]["json"] if s["no"] == desc_sno), "")
            
            # 基本信息部分. basic info
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
            
            # 礼包内容部分. package content
            content_info = []
            if item_infos := shop_item.get("item_infos"):
                try:
                    items = ast.literal_eval(item_infos)
                    content_info.append("\n礼包内容：")
                    for item_no, amount in items:
                        item_name = get_string_item(data, item_no)
                        content_info.append(f"・{item_name["zh_tw"]}x{amount}")
                except Exception as e:
                    logger.error(f"解析礼包内容时发生错误：{e}")
            if content_info:
                package_info.append("\n".join(content_info))
            
            # 价格信息部分. price info
            price_info = ["\n价格信息："]
            if price_krw := shop_item.get("price_krw"):
                price_info.append(f"・ {price_krw}韩元")
            if price_other := shop_item.get("price_other"):
                price_info.append(f"・ {price_other}日元")
            package_info.append("\n".join(price_info))
            
            # 添加分隔线. add separator
            package_info.append("-" * 25)
            
            # 将整个礼包信息作为一条消息添加到列表中. add the whole package info as a message to the list
            messages.append("\n".join(package_info))
    
    return messages


def get_character_soullink(data: dict, hero_id: int, is_test: bool = False) -> list:
    """get character soullink
    
    Args:
        data: JSON data dictionary
        hero_id: hero id
        is_test: is test
    """
    soullink_info = []
    
    # 查找所有包含该角色的灵魂链接. find all soul links that contain the character
    for link in data["soullink"]["json"]:
        # 动态查找所有hero槽位键. dynamic find all hero slot keys
        hero_keys = [key for key in link.keys() if key.startswith("group_hero") and link[key] == hero_id]
        
        if not hero_keys:
            continue  # 如果没有找到包含目标角色的槽位，跳过此链接. if no hero slot is found, skip this link
        
        # 收集所有角色ID. collect all hero ids
        hero_ids = []
        for key in link.keys():
            if key.startswith("group_hero") and link[key] > 0:
                hero_ids.append(link[key])
        
        if not hero_ids:
            continue
        
        # 获取灵魂链接标题和故事. get soul link title and story
        # 优先使用zh_tw内容的逻辑. use zh_tw content logic first
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
        
        # 获取所有角色名称. get all hero names
        hero_names = []
        for hid in hero_ids:
            name_data = get_string_character(data, hid, special=True)
            name_zh_tw = name_data["zh_tw"]
            name_kr = name_data["kr"]
            name = name_zh_tw if name_zh_tw else (name_kr if is_test else name_zh_tw)
            if name:
                hero_names.append(name)
                
        # 获取收集效果. get collection effects
        collection_effects = []
        
        if collection_id := link.get("Collection"):
            # 按condition_list排序. sort by condition_list
            collection_items = sorted(
                [item for item in data["soullink_collection"]["json"] 
                    if item.get("collection_group") == collection_id],
                key=lambda x: x.get("condition_list", 0)
            )
            
            for item in collection_items:
                # 获取条件文本，修改为优先使用zh_tw内容的逻辑. get condition text, modify to use zh_tw content logic first
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
                
                # 获取buff效果. get buff effects
                buff_effects = []
                if buff_no := item.get("contents_buff_no"):
                    buff = next((b for b in data["contents_buff"]["json"] 
                                if b.get("no") == buff_no), None)
                    if buff:
                        # 处理所有属性，包括战力加成. process all attributes, including battle power bonus
                        for key, value in buff.items():
                            if key in STAT_NAME_MAPPING and value != 0:
                                # 获取属性名称，优先使用zh_tw. get attribute name, use zh_tw first
                                stat_name = STAT_NAME_MAPPING[key]
                                if value < 1:  # 小于1的显示为百分比. less than 1 is displayed as percentage
                                    buff_effects.append(f"{stat_name}：{value*100:.1f}%")
                                else:
                                    buff_effects.append(f"{stat_name}：{int(value)}")
                        
                        # 战力百分比加成. battle power percentage bonus
                        battle_power_per = buff.get("battle_power_per", 0)
                        if battle_power_per != 0:
                            buff_effects.append(f"战力百分比加成：{battle_power_per}")
                        
                        # 固定值战力加成. fixed value battle power bonus
                        battle_power = buff.get("battle_power", 0)
                        if battle_power != 0:
                            buff_effects.append(f"战力加成：{int(battle_power)}")
                
                if condition_text and buff_effects:
                    collection_effects.append({
                        "condition": condition_text,
                        "effects": buff_effects
                    })
        
        # 添加到结果列表. add to result list
        soullink_info.append({
            "title": title,
            "heroes": hero_names,
            "story": story,
            "effects": collection_effects,
            "open_date": link.get("open_date", "")
        })
    
    return soullink_info


def get_character_signature_value(data, level_group):
    """get character signature value
    
    Args:
        data: JSON data dictionary
        level_group: signature level group id
    
    Returns:
        dict: signature attribute stats
    """
    max_level_data = None
    max_level = 0
    
    # 这个遗物的最大等级（40或45）. this signature's max level (40 or 45)
    for level_data in data["signature_level"]["json"]:
        if level_data["group"] == level_group:
            if level_data["signature_level"] > max_level:
                max_level = level_data["signature_level"]
    
    # 再找到最大等级的数据. find the data with the max level
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
            if stat_key in ["hit", "dodge"]:
                formatted_stats.append(f"{stat_name}：{int(value)}")
            else:
                # 处理百分比值，使用round避免浮点数精度问题. process percentage value, use round to avoid floating point precision problem
                percent_value = round(value * 100, 1)
                formatted_value = f"{percent_value:.1f}"
                # 检查是否为整数（包括像29.0这样的值）. check if it is an integer (including values like 29.0)
                if formatted_value.endswith('.0'):
                    formatted_stats.append(f"{stat_name}：{int(percent_value)}%")
                else:
                    formatted_stats.append(f"{stat_name}：{formatted_value}%")
    
    return formatted_stats, max_level, max_level_data["battle_power_per"]


def get_character_signature(data, hero_id):
    """get character signature
    
    Args:
        data: JSON data dictionary
        hero_id: hero id
    
    Returns:
        dict: include signature info
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
    
    # 在Signature.json中查找对应角色的遗物. find the corresponding signature in Signature.json
    for signature in data["signature"]["json"]:
        if signature["hero_sno"] == hero_id:
            signature_data = signature
            # 获取遗物图标路径. get signature icon path
            if signature_bg_path := signature.get("signature_bg_path"):
                signature_bg_path = f"Img_Signature_{signature_bg_path}.png"
            break
    
    if signature_data:
        # 获取遗物名称. get signature name
        for string in data["string_skill"]["json"]:
            if string["no"] == signature_data["signature_name_sno"]:
                signature_name_zh_tw = string.get("zh_tw", "")
                signature_name_zh_cn = string.get("zh_cn", "")
                signature_name_kr = string.get("kr", "")
                signature_name_en = string.get("en", "")
                break
        
        # 获取遗物技能名称. get signature skill name
        for string in data["string_skill"]["json"]:
            if string["no"] == signature_data["skill_name_sno"]:
                signature_title_zh_tw = string.get("zh_tw", "")
                signature_title_zh_cn = string.get("zh_cn", "")
                signature_title_kr = string.get("kr", "")
                signature_title_en = string.get("en", "")
                break
                
        # 获取遗物简介. get signature description
        signature_desc_zh_tw = signature_desc_zh_cn = "无遗物简介信息"  # 设置默认值. set default value
        signature_desc_kr = "유물 프로필 정보 없음"
        signature_desc_en = "No signature description information"  # 设置默认值. set default value
        for string in data["string_skill"]["json"]:
            if string["no"] == signature_data["tooltip_explain_sno"]:
                desc_tw = string.get("zh_tw", "")
                desc_cn = string.get("zh_cn", "")
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
        
        # 获取所有等级的技能描述. get all skill descriptions of all levels
        for i in range(1, 8):  # 1-7级. 1-7 levels
            sno_key = f"skill_tooltip_sno{i}"
            if sno_key in signature_data:
                tooltip_sno = signature_data[sno_key]
                for string in data["string_skill"]["json"]:
                    if string["no"] == tooltip_sno:
                        desc_tw = string.get("zh_tw", "")
                        desc_cn = string.get("zh_cn", "")
                        desc_kr = string.get("kr", "")
                        desc_en = string.get("en", "")
                        
                        # 先清理颜色标签. clean color tags first
                        desc_tw = clean_tags(desc_tw)
                        desc_cn = clean_tags(desc_cn)
                        desc_kr = clean_tags(desc_kr)
                        desc_en = clean_tags(desc_en)
                        
                        # 处理数值标签，模拟官方parse逗号分隔的数值. process numeric tags, simulate official parse comma separated values
                        desc_tw = process_skill_description(data, desc_tw)
                        desc_cn = process_skill_description(data, desc_cn)
                        desc_kr = process_skill_description(data, desc_kr)
                        desc_en = process_skill_description(data, desc_en)
                        
                        # 处理技能描述中可能包含的逗号分隔数值. process numeric values that may contain commas in skill description
                        # 模拟官方Info_SignatureSkillInfos__Parse方法的行为. simulate official Info_SignatureSkillInfos__Parse method behavior
                        def parse_comma_values(text):
                            # 识别可能包含的逗号分隔数值，如"1,2,3". recognize possible comma separated values, such as "1,2,3"
                            import re
                            pattern = r'\b\d+(?:,\d+)*\b'
                            
                            def replace_parsed_values(match):
                                values_str = match.group(0)
                                # 分割字符串，过滤空值，转换为整数列表. split string, filter empty values, convert to integer list
                                values = [int(v.strip()) for v in values_str.split(',') if v.strip()]
                                # 返回处理后的字符串（例如可以添加格式或者直接显示）. return processed string (e.g. can add format or display directly)
                                return ','.join(str(v) for v in values)
                                
                            return re.sub(pattern, replace_parsed_values, text)
                        
                        # 应用逗号分隔数值处理. apply comma separated values processing
                        desc_tw = parse_comma_values(desc_tw)
                        desc_cn = parse_comma_values(desc_cn)
                        desc_kr = parse_comma_values(desc_kr)
                        desc_en = parse_comma_values(desc_en)
                        
                        # 添加等级、品质信息. add level and grade info
                        grade_sno = 110014 + i - 1  # 按顺序映射等级. map level in order
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
        
    # 修改返回值，添加图标路径. modify return value, add icon path
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
    
    # 如果没有找到遗物数据，返回空字典. if no signature data is found, return empty dictionary
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
    """calculate normal ending choice
    
    Args:
        all_episodes_choices: all episodes choices
        bad_threshold: bad threshold
        normal_threshold: normal threshold
    """
    # 提取好结局和坏结局的选项及其好感度. extract good and bad ending choices and their affinity
    good_ending_choices = []
    bad_ending_choices = []
    
    for episode_data in all_episodes_choices:
        episode_choices = episode_data["choices"]
        episode_num = episode_data["episode"]
        
        # 按talk_index分组. group by talk_index
        choices_by_index = {}
        for choice in episode_choices:
            talk_index = choice["talk_index"]
            if talk_index not in choices_by_index:
                choices_by_index[talk_index] = []
            choices_by_index[talk_index].append(choice)
        
        # 为每个talk_index找出好结局和坏结局的选项. find good and bad ending choices for each talk_index
        for talk_index, choices in choices_by_index.items():
            # 好结局选择最高好感度. good ending choice with highest affinity
            max_affinity = max(c["affinity"] for c in choices)
            good_choices = [c for c in choices if c["affinity"] == max_affinity]
            good_ending_choices.append({
                "episode": episode_num,
                "talk_index": talk_index,
                "choice": good_choices[0],  # 取第一个最高好感度选项. take the first highest affinity option
                "affinity": max_affinity
            })
            
            # 坏结局选择最低好感度. bad ending choice with lowest affinity
            min_affinity = min(c["affinity"] for c in choices)
            bad_choices = [c for c in choices if c["affinity"] == min_affinity]
            bad_ending_choices.append({
                "episode": episode_num,
                "talk_index": talk_index,
                "choice": bad_choices[0],  # 取第一个最低好感度选项. take the first lowest affinity option
                "affinity": min_affinity
            })
    
    # 计算好结局和坏结局的总好感度. calculate total affinity of good and bad endings
    good_total_affinity = sum(choice["affinity"] for choice in good_ending_choices)
    bad_total_affinity = sum(choice["affinity"] for choice in bad_ending_choices)
    
    # 计算需要减少的好感度，使总好感度落在一般结局区间内. calculate affinity to reduce, so that total affinity falls within the normal ending range
    target_affinity = (bad_threshold + normal_threshold) / 2  # 取区间中点作为目标. take the midpoint as the target
    affinity_to_reduce = good_total_affinity - target_affinity
    
    # 如果好结局总好感度已经在区间内，直接返回好结局选项. if good ending total affinity is already within the range, return good ending options
    if good_total_affinity <= normal_threshold and good_total_affinity >= bad_threshold:
        normal_end_note = f"注意：按照好结局选项选择即可达到一般结局条件（总好感度：{good_total_affinity}）"
        return [{
            "episode": 0,
            "choices": [normal_end_note]
        }]
    
    # 如果坏结局总好感度已经在区间内，直接返回坏结局选项. if bad ending total affinity is already within the range, return bad ending options
    if bad_total_affinity <= normal_threshold and bad_total_affinity >= bad_threshold:
        normal_end_note = f"注意：按照坏结局选项选择即可达到一般结局条件（总好感度：{bad_total_affinity}）"
        return [{
            "episode": 0,
            "choices": [normal_end_note]
        }]
    
    # 计算好结局和坏结局选项的好感度差值. calculate affinity difference between good and bad ending choices
    choice_diffs = []
    for i in range(len(good_ending_choices)):
        good_choice = good_ending_choices[i]
        bad_choice = bad_ending_choices[i]
        diff = good_choice["affinity"] - bad_choice["affinity"]
        if diff > 0:  # 只考虑有差异的选项. only consider options with difference
            choice_diffs.append({
                "index": i,
                "diff": diff,
                "good_choice": good_choice,
                "bad_choice": bad_choice
            })
    
    # 按差值从大到小排序. sort by difference in descending order
    choice_diffs.sort(key=lambda x: x["diff"], reverse=True)
    
    # 创建一般结局选项列表（初始为好结局选项）. create normal ending choices list (initially good ending choices)
    normal_ending_choices = good_ending_choices.copy()
    current_affinity = good_total_affinity
    
    # 替换部分选项，使总好感度落在区间内. replace some options, so that total affinity falls within the range
    choices_to_replace = []
    for diff_info in choice_diffs:
        if current_affinity <= normal_threshold:
            break
            
        good_choice = diff_info["good_choice"]
        bad_choice = diff_info["bad_choice"]
        diff = diff_info["diff"]
        
        # 如果替换这个选项后总好感度仍然大于normal_threshold，则替换. if replacing this option makes total affinity still greater than normal_threshold, then replace
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
            
        # 如果总好感度已经在区间内，停止替换. if total affinity is already within the range, stop replacing
        if current_affinity <= normal_threshold and current_affinity >= bad_threshold:
            break
    
    # 如果替换后总好感度仍然不在区间内，提供说明. if total affinity is still not within the range after replacement, provide explanation
    if current_affinity > normal_threshold:
        normal_end_note = f"警告：即使替换部分选项，总好感度({current_affinity})仍然超过一般结局上限({normal_threshold})，请额外注意控制好感度"
    elif current_affinity < bad_threshold:
        normal_end_note = f"警告：替换选项后总好感度({current_affinity})低于一般结局下限({bad_threshold})，请选择部分好结局选项"
    else:
        normal_end_note = f"提示：按照以下选项选择可达到一般结局条件（预计总好感度：{current_affinity}）"
    
    # 按章节组织一般结局选项. organize normal ending choices by episode
    normal_choices_by_episode = {}
    for choice in normal_ending_choices:
        episode = choice["episode"]
        if episode not in normal_choices_by_episode:
            normal_choices_by_episode[episode] = []
        normal_choices_by_episode[episode].append(choice)
    
    # 格式化结果. format result
    result = [{
        "episode": 0,
        "choices": [normal_end_note]
    }]
    
    # 如果有需要特别替换的选项，添加说明. if there are options to be replaced, add explanation
    if choices_to_replace:
        replace_notes = ["需要替换的选项："]
        for replace in choices_to_replace:
            replace_notes.append(f"EP{replace['episode']}：将 {replace['from_choice']} 替换为 {replace['to_choice']}")
        result[0]["choices"].extend(replace_notes)
    
    # 添加每章节的选项. add options for each episode
    for episode, choices in normal_choices_by_episode.items():
        # 按talk_index排序. sort by talk_index
        choices.sort(key=lambda x: x["talk_index"])
        
        # 提取选项文本. extract choice text
        choice_texts = [choice["choice"]["text"] for choice in choices]
        
        result.append({
            "episode": episode,
            "choices": choice_texts
        })
    
    return result


def get_character_story(data, hero_id):
    """get character story
    
    Args:
        data: JSON data dictionary
        hero_id: hero id
    """
    try:
        # 收集所有相关的故事信息. collect all related story info
        story_episodes = []
        ending_episodes = []
        
        # 从Story_Info中获取所有相关剧情. get all related story info from Story_Info
        for story in data["story_info"]["json"]:
            if ("act" in story and story["act"] == hero_id):
                if story["episode"] in [8, 9, 10]:
                    ending_episodes.append(story)
                else:
                    story_episodes.append(story)
        
        # 如果没有8-10中的任意一个，则无好感故事. if none of 8-10, then no good ending story
        if not ending_episodes:
            return False, [], {}
        
        # 获取结局信息. get ending info
        endings = {}
        for episode in ending_episodes:
            if "ending_affinity" in episode:
                if episode["episode"] == 8:
                    endings["bad"] = episode["ending_affinity"]
                elif episode["episode"] == 9:
                    endings["normal"] = episode["ending_affinity"]
                elif episode["episode"] == 10:
                    endings["good"] = episode["ending_affinity"]
        
        # 如果没有找到任何结局信息，返回False. if no ending info is found, return False
        if not endings:
            return False, [], {}
        
        # 收集每个章节的信息. collect info for each episode
        episode_info = []
        for episode in story_episodes:
            # 获取选项和好感度. get options and affinity
            choices = {}  # 使用字典来按position_type分组. use dictionary to group by position_type
            
            # 先找出所有有好感度的选项的talk_index. first find all talk_indexes with affinity
            valid_talk_indexes = set()
            for talk in data["talk"]["json"]:
                if talk.get("group_no") == episode.get("talk_group") and "affinity_point" in talk:
                    valid_talk_indexes.add(talk.get("talk_index", 0))
            
            # 收集所有相关选项（包括有好感度和对应talk_index的无好感度选项）. 
            # collect all related options (including options with affinity and corresponding talk_indexes without affinity)
            for talk in data["talk"]["json"]:
                if (talk.get("group_no") == episode.get("talk_group") and 
                    talk.get("talk_index", 0) in valid_talk_indexes):
                    choice_text_zh_tw = ""
                    choice_text_zh_cn = ""
                    choice_text_kr = ""
                    choice_text_en = ""
                    
                    # 安全获取对话文本. safe get choice text
                    talk_no = talk.get("no")
                    if talk_no is not None:
                        for string in data["string_talk"]["json"]:
                            if string.get("no") == talk_no:
                                choice_text_zh_tw = string.get("zh_tw", "")
                                choice_text_zh_cn = string.get("zh_cn", "")
                                choice_text_kr = string.get("kr", "")
                                choice_text_en = string.get("en", "")
                                break
                    
                    # 按position_type分组存储选项. store options by position_type
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
            
            # 获取章节标题. get episode title
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
            
            # 添加章节信息. add episode info
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
    """format character story
    
    Args:
        episode_info: episode info
        endings: endings
        is_test: is test
    """
    # 创建三个结局的信息列表. create list of info for three endings
    good_end = ["😃好结局攻略："]
    normal_end = ["🙂一般结局攻略："]
    bad_end = ["🥲坏结局攻略："]
    
    # 添加结局条件. add ending conditions
    bad_threshold = endings.get('bad', 0)
    normal_threshold = endings.get('normal', 0)
    
    if "bad" in endings:
        good_end.append(f"条件：好感度大于{normal_threshold}")
        normal_end.append(f"条件：好感度{bad_threshold}-{normal_threshold}")
        bad_end.append(f"条件：好感度低于{bad_threshold}")
    
    # 收集所有章节的选项信息，用于计算总好感度. collect all episode choices info, for calculating total affinity
    all_episodes_choices = []
    
    # 添加各章节信息. add info for each episode
    for ep in episode_info:
        # 收集所有选项. collect all options
        all_choices = []
        for position_type, choices in ep["choices"].items():
            for choice in choices:
                talk_index = choice.get("talk_index", 0)
                affinity = choice.get("affinity", 0)
                affinity_str = str(affinity) if affinity < 0 else f"+{affinity}" if affinity > 0 else "0"
                
                choice_info = {
                    "talk_index": talk_index,
                    "choice_group": choice["choice_group"],
                    # 清理好感选项里面的富文本标签. clean rich text tags in affinity options
                    "text": f"（{choice['choice_group']}）{clean_tags(choice['zh_tw_text'] if choice['zh_tw_text'] else (choice['kr_text' if is_test else 'zh_tw_text']))}({affinity_str})",
                    "affinity": affinity,
                    "position_type": position_type,
                    "group_no": choice.get("group_no"),
                    "episode": ep['episode']
                }
                all_choices.append(choice_info)
        
        if not all_choices:
            continue
        
        # 保存本章节的所有选项. save all options for this episode
        all_episodes_choices.append({
            "episode": ep['episode'],
            "title": ep['zh_tw_title'] if ep['zh_tw_title'] else (ep['kr_title'] if is_test else ep['zh_tw_title']),
            "choices": all_choices
        })
        
        # 为每个结局添加章节标题. add episode title for each ending
        title = ep['zh_tw_title'] if ep['zh_tw_title'] else (ep['kr_title'] if is_test else ep['zh_tw_title'])
        good_end.append(f"\nEP{ep['episode']}：{title}")
        normal_end.append(f"\nEP{ep['episode']}：{title}")
        bad_end.append(f"\nEP{ep['episode']}：{title}")

        # 按talk_index排序所有选项. sort all options by talk_index
        all_choices.sort(key=lambda x: x["talk_index"])
        
        # 处理好结局选项. handle good ending options
        good_choices = []
        current_index = None
        current_group = []
        
        for choice in all_choices:
            if current_index != choice["talk_index"]:
                # 处理上一组的选项. handle previous group of options
                if current_group:
                    # 找出最高好感度的选项. find option with highest affinity
                    max_affinity = max((c["affinity"] for c in current_group))
                    # 只添加最高好感度的选项. only add option with highest affinity
                    for c in current_group:
                        if c["affinity"] == max_affinity:
                            good_choices.append(c["text"])
                # 开始新的一组. start new group
                current_index = choice["talk_index"]
                current_group = [choice]
            else:
                current_group.append(choice)
        
        # 处理最后一组. handle last group
        if current_group:
            max_affinity = max((c["affinity"] for c in current_group))
            for c in current_group:
                if c["affinity"] == max_affinity:
                    good_choices.append(c["text"])
        
        good_end.extend(good_choices)
        
        # 处理坏结局选项. handle bad ending options
        bad_choices = []
        current_index = None
        current_group = []
        
        for choice in all_choices:
            if current_index != choice["talk_index"]:
                # 处理上一组的选项. handle previous group of options
                if current_group:
                    # 首先查找是否有负数好感度的选项. first check if there are options with negative affinity
                    min_affinity = min((c["affinity"] for c in current_group))
                    if min_affinity < 0:
                        # 找出所有具有最小负数好感度的选项. find all options with minimum negative affinity
                        min_aff_choices = [c["text"] for c in current_group if c["affinity"] == min_affinity]
                        if len(min_aff_choices) > 1:
                            bad_choices.append("或者".join(min_aff_choices))
                        else:
                            bad_choices.extend(min_aff_choices)
                    else:
                        # 如果没有负数好感度，查找0好感度的选项. if no negative affinity, find options with 0 affinity
                        zero_choices = [c["text"] for c in current_group if c["affinity"] == 0]
                        if zero_choices:
                            if len(zero_choices) > 1:
                                bad_choices.append("或者".join(zero_choices))
                            else:
                                bad_choices.extend(zero_choices)
                        else:
                            # 如果既没有负数也没有0，则选择最小的正数好感度. if neither negative nor 0, select option with minimum positive affinity
                            min_positive = min((c["affinity"] for c in current_group))
                            min_pos_choices = [c["text"] for c in current_group if c["affinity"] == min_positive]
                            if len(min_pos_choices) > 1:
                                bad_choices.append("或者".join(min_pos_choices))
                            else:
                                bad_choices.extend(min_pos_choices)
                
                # 开始新的一组. start new group
                current_index = choice["talk_index"]
                current_group = [choice]
            else:
                current_group.append(choice)
        
        # 处理最后一组. handle last group
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

    # 计算一般结局的选项. calculate normal ending choices
    normal_choices_by_episode = calculate_normal_ending_choice(all_episodes_choices, bad_threshold, normal_threshold)
    
    # 添加一般结局的选项到结果中. add normal ending choices to result
    for episode_data in normal_choices_by_episode:
        episode_num = episode_data["episode"]
        choices = episode_data["choices"]
        
        # 找到对应章节在normal_end中的位置. find position in normal_end
        for i, line in enumerate(normal_end):
            if line.startswith(f"\nEP{episode_num}："):
                # 在章节标题后添加选项. add options after episode title
                normal_end[i+1:i+1] = choices
                break
    
    # 合并所有结局信息. merge all ending info
    result = ["【好感故事攻略】"]
    result.extend(good_end)
    result.extend([""] + normal_end)
    result.extend([""] + bad_end)
    
    return "\n".join(result)


def get_base_battle_power(data: dict, entity_type: int, level: int) -> int:
    """calculate base battle power
    
    Args:
        data: JSON data dictionary
        entity_type: entity type (1=hero, 2=monster, 3=raid)
        level: level
    
    Returns:
        int: calculated base battle power
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
        
        # 计算战力，向下取整. calculate battle power, round down
        # 公式：base + (level_value + level_per_value * level) * (level - 1).
        battle_power = int(base_value + (level_value + level_per_value * level) * (level - 1))
        return battle_power
    
    except Exception as e:
        logger.error(f"计算基础战力时发生错误: {e}")
        return 0


def calculate_battle_power(data: dict, entity_type: int, level: int, grade: int, 
                            equipment_power: int = 0, equipment_power_per: float = 0.0, 
                            signature_power_per: float = 0.0, contents_buff_power: float = 0.0, 
                            contents_buff_power_per: float = 0.0) -> int:
    """calculate total battle power
    
    Args:
        data: JSON data dictionary
        entity_type: entity type (1=hero, 2=monster, 3=raid)
        level: level
        grade: grade
        level_grade: level grade, default 1.0
        equipment_power: equipment power, default 0
        equipment_power_per: equipment power percent, default 0.0
        signature_power_per: signature power percent, default 0.0
        contents_buff_power: contents buff power, default 0.0
        contents_buff_power_per: contents buff power percent, default 0.0
        
    Returns:
        int: calculated total battle power
    """
    try:
        base_power = get_base_battle_power(data, entity_type, level)
        grade_value = get_hero_grade_value(data, grade)
        level_grade_value = get_hero_level_grade_value(data, level)
        
        total_power = (
            base_power +                                # 基础战力. base power
            (level_grade_value - 1.0) * base_power +    # 等级加成. level grade bonus
            (grade_value - 1.0) * base_power +          # 品质加成. grade bonus
            equipment_power +                           # 装备战力. equipment power
            equipment_power_per * base_power +          # 装备战力百分比. equipment power percent
            signature_power_per * base_power +          # 遗物战力百分比. signature power percent
            contents_buff_power +                       # 内容buff战力. contents buff power
            contents_buff_power_per * base_power        # 内容buff战力百分比. contents buff power percent
        )

        if total_power == float('inf'):
            return 0
        
        return int(total_power)
        
    except Exception as e:
        logger.error(f"计算总战力时发生错误: {e}")
        return 0
    

def get_hero_grade_value(data: dict, grade: int) -> float:
    """get hero grade value
    
    Args:
        data: JSON data dictionary
        grade: grade
        
    Returns:
        float: grade value
    """

    try:
        for grade_info in data["hero_grade"]["json"]:
            if grade_info.get("name_sno") == grade:
                return grade_info.get("hero_grade_value", 0.85)
            
        return 0.85
    
    except Exception as e:
        logger.error(f"获取角色品质加成值时发生错误: {e}")
        return 0.85
    

def get_hero_level_grade_value(data: dict, level: int) -> float:
    """get hero level grade value
    
    Args:
        data: JSON data dictionary
        level: level
        
    Returns:
        float: level grade value, default 1.0 (no bonus)
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


def get_character_skill_pattern(data: dict, hero_no: int, is_test: bool = False) -> list:
    """get character skill pattern
    
    Args:
        data: JSON data dictionary
        hero_no: hero no
    
    Returns:
        list: skill pattern list, each element is (skill name, is normal attack)
    """
    try:
        # 查找角色的技能释放顺序. find skill pattern
        pattern_data = None
        for pattern in data["skill_pattern"]["json"]:
            if pattern.get("hero_no") == hero_no:
                pattern_data = pattern
                break
        if not pattern_data:
            return []
        
        # 收集所有pattern键. collect all pattern keys
        pattern_keys = [key for key in pattern_data.keys() if key.startswith("pattern")]
        # 处理两种格式：pattern1 和 pattern_1
        pattern_keys.sort(key=lambda x: int(x.replace("pattern", "").replace("_", "")))
        # 获取技能顺序. get skill pattern
        skill_pattern = []
        for key in pattern_keys:
            skill_no = pattern_data.get(key)
            if skill_no == hero_no:
                # 普通攻击. normal attack
                skill_pattern.append(("普通攻击", True))
            else:
                # 获取技能名称. get skill name
                skill_name = ""
                for skill in data["skill"]["json"]:
                    if skill["no"] == skill_no:
                        if "name_sno" not in skill:
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


def get_character_attack_range(data: dict, hero_id: int) -> float:
    """获取角色攻击范围
    
    Args:
        data: JSON数据字典
        hero_id: 角色ID
    
    Returns:
        float: 攻击范围，如果没有找到则返回0.0
    """
    try:
        # 在skill数据中查找该角色的技能
        for skill in data["skill"]["json"]:
            if skill.get("no") == hero_id and skill.get("range"):
                return float(skill.get("range"))
        
        # 如果没有找到有range的技能，返回0.0
        return 0.0
        
    except Exception as e:
        logger.error(f"获取角色攻击范围时发生错误: {e}, hero_id: {hero_id}")
        return 0.0