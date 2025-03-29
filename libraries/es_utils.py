import ast
import os
import re
import json
import yaml
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Tuple, List
from io import BytesIO
from datetime import datetime
from ..config import *
from PIL import Image
from difflib import get_close_matches
from zhenxun.services.log import logger
from nonebot.adapters.onebot.v11 import (
    MessageSegment
)


# 加载别名配置文件
def load_aliases(group_id=None):
    """加载角色别名配置"""
    config = get_group_data_source(group_id)
    hero_alias_file = config["hero_alias_file"]
    
    if not hero_alias_file.exists():
        return {}
    
    try:
        with open(hero_alias_file, "r", encoding="utf-8") as f:
            aliases_data = yaml.safe_load(f)
            if not aliases_data or "names" not in aliases_data:
                return {}
    except Exception as e:
        logger.error(f"加载别名配置文件出错: {e}")
        return {}
    
    # 创建别名到hero_id的映射
    alias_map = {}
    for hero in aliases_data["names"]:
        if isinstance(hero, dict) and "hero_id" in hero:
            # 添加所有语言版本的名称
            name_fields = [
                "zh_tw_name",
                "zh_cn_name",
                "kr_name",
                "en_name"
            ]
            
            # 添加所有非空的名称作为可能的匹配
            for field in name_fields:
                if hero.get(field):  # 只添加非空的名称
                    alias_map[hero[field]] = hero["hero_id"]
                    # 为英文名称添加小写版本
                    if field == "en_name":
                        alias_map[hero[field].lower()] = hero["hero_id"]
            
            # 添加所有别名
            for alias in hero.get("aliases", []):
                alias_map[alias] = hero["hero_id"]
                # 如果别名看起来是英文(只包含ASCII字符),也添加小写版本
                if alias.isascii():
                    alias_map[alias.lower()] = hero["hero_id"]
    
    return alias_map

# 加载所需的JSON文件
def load_json_data(group_id=None):
    config = get_group_data_source(group_id)
    json_path = config["json_path"]
    
    # 确保json_path是Path对象
    if not isinstance(json_path, Path):
        json_path = Path(json_path)

    json_files = {
        "hero": "Hero.json", # 角色
        "hero_option": "HeroOption.json", # 角色潜能
        "hero_gift": "HeroGift.json", # 角色喜好礼物
        "string_character": "StringCharacter.json", # 角色文本
        "string_system": "StringSystem.json", # 系统文本
        "skill": "Skill.json", # 技能
        "string_skill": "StringSkill.json", # 技能文本
        "skill_code": "SkillCode.json", # 技能代码
        "skill_buff": "SkillBuff.json", # 技能效果
        "skill_icon": "SkillIcon.json", # 技能图标
        "signature": "Signature.json", # 遗物
        "hero_desc": "HeroDesc.json", # 角色描述
        "signature_level": "SignatureLevel.json", # 遗物等级
        "string_evertalk": "StringEverTalk.json",
        "story_info": "StoryInfo.json", # 故事信息
        "talk": "Talk.json", # 对话
        "string_talk": "StringTalk.json", # 对话文本
        "item_costume": "ItemCostume.json", # 物品信息
        "item": "Item.json", # 物品
        "item_stat": "ItemStat.json", # 物品属性
        "string_item": "StringItem.json", # 物品文本
        "illust": "Illust.json", # 插画
        "item_drop_group": "ItemDropGroup.json", # 掉落组
        "item_set_effect": "ItemSetEffect.json", # 套装效果
        "stage": "Stage.json", # 关卡
        "stage_battle": "StageBattle.json", # 关卡战斗
        "formation": "Formation.json", # 队伍
        "message_mail": "MessageMail.json", # 邮件
        "level": "Level.json", # 等级
        "ark_enhance": "ArkEnhance.json", # 方舟强化
        "ark_overclock": "ArkOverClock.json", # 超频
        "promotion_movie": "PromotionMovie.json", # 宣传片
        "localization_schedule": "LocalizationSchedule.json", # 活动日历
        "event_calender": "EventCalender.json", # 活动日历
        "event_info": "EventInfo.json", # 活动信息
        "string_ui": "StringUI.json", # UI文本
        "eden_alliance": "EdenAlliance.json", # 联合作战
        "stage_equip": "StageEquip.json", # 关卡装备
        "string_stage": "StringStage.json", # 关卡文本
        "cash_shop_item": "CashShopItem.json", # 商店物品
        "string_cashshop": "StringCashshop.json", # 商店文本
        "barrier": "Barrier.json", # 传送门相关信息
        "trip_hero": "TripHero.json", # 角色关键字
        "trip_keyword": "TripKeyword.json", # 角色关键字
        "key_values": "KeyValues.json", # 关键字
        "town_location": "TownLocation.json", # 地点
        "town_object": "TownObjet.json", # 专属领地物品
        "string_town": "StringTown.json", # 地点文本
        "town_lost_item": "TownLostItem.json", # 遗失物品
        "arbeit_fairy_level": "ArbeitFairyLevel.json", # 打工等级
        "tower": "Tower.json", # 起源塔
        "contents_buff": "ContentsBuff.json", # buff数值内容
        "world_raid_partner_buff": "WorldRaidPartnerBuff.json", # 支援伙伴buff
        "arbeit_choice": "ArbeitChoice.json", # 专属物品任务选择
        "arbeit_list": "ArbeitList.json",   # 专属物品任务列表
        "evertalk_desc": "EverTalkDesc.json", # everphton聊天相关，拿插图
        "soullink": "Soullink.json", # 灵魂链接文本相关
        "soullink_collection": "SoullinkCollection.json", # 灵魂链接数值相关
        "gacha": "Gacha.json", # 抽卡相关
    }
    
    data = {}
    for key, filename in json_files.items():
        try:
            with open(json_path / filename, "r", encoding="utf-8") as f:
                data[key] = json.load(f)
        except Exception as e:
            logger.error(f"加载JSON文件出错: {filename}, 错误: {e}")
            data[key] = {"json": []}  # 提供一个空的默认值
    return data


async def generate_ark_level_chart(data: dict) -> MessageSegment:
    """生成主方舟等级与超频等级关系图以及超频等级升级消耗图"""
    try:
        # 收集数据点
        levels = []
        overclock_levels = []
        
        for ark in data["ark_enhance"]["json"]:
            if ark.get("core_type02") == 110051:  # 主方舟
                level = ark.get("core_level")
                overclock = ark.get("overclock_max_level")
                if level is not None and overclock is not None:
                    levels.append(level)
                    overclock_levels.append(overclock)
        
        # 收集超频消耗数据
        overclock_costs = []
        overclock_levels_cost = []
        for overclock in data["ark_overclock"]["json"]:
            level = overclock.get("overclock_level", 0)
            cost = overclock.get("mana_crystal", 0)
            if level is not None and cost is not None:
                overclock_levels_cost.append(level)
                overclock_costs.append(cost)
        
        # 创建两个子图
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12))
        
        # 第一个子图：主方舟等级与最大超频等级关系图
        ax1.plot(levels, overclock_levels, 'b-', marker='o', markersize=3)
        ax1.set_title('主方舟等级与最大超频等级关系图', fontproperties=CUSTOM_FONT)
        ax1.set_xlabel('主方舟等级', fontproperties=CUSTOM_FONT)
        ax1.set_ylabel('最大超频等级', fontproperties=CUSTOM_FONT)
        ax1.grid(True, linestyle='--', alpha=0.7)
        ax1.set_xticks(range(0, max(levels)+1, 50))
        
        # 添加关键点标注
        ax1.annotate(f'最大值: ({max(levels)}, {max(overclock_levels)})',
                    xy=(max(levels), max(overclock_levels)),
                    xytext=(10, 10),
                    textcoords='offset points',
                    fontproperties=CUSTOM_FONT)
        
        # 第二个子图：超频等级升级消耗图
        ax2.plot(overclock_levels_cost, overclock_costs, 'r-', marker='o', markersize=3)
        ax2.set_title('超频等级升级消耗图', fontproperties=CUSTOM_FONT)
        ax2.set_xlabel('超频等级', fontproperties=CUSTOM_FONT)
        ax2.set_ylabel('魔力水晶消耗', fontproperties=CUSTOM_FONT)
        ax2.grid(True, linestyle='--', alpha=0.7)
        
        # 添加关键点标注
        ax2.annotate(f'最大消耗: ({overclock_levels_cost[overclock_costs.index(max(overclock_costs))]}, {max(overclock_costs)})',
                    xy=(overclock_levels_cost[overclock_costs.index(max(overclock_costs))], max(overclock_costs)),
                    xytext=(10, 10),
                    textcoords='offset points',
                    fontproperties=CUSTOM_FONT)
        
        # 调整子图之间的间距
        plt.tight_layout()
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 获取bytes数据
        buffer.seek(0)
        image_bytes = buffer.getvalue()
        
        # 返回MessageSegment对象
        return MessageSegment.image(image_bytes)
        
    except Exception as e:
        logger.error(f"生成统计图时发生错误: {str(e)}")
        return MessageSegment.text("生成统计图失败")


async def generate_level_cost_chart(data: dict) -> MessageSegment:
    """生成等级升级消耗统计图"""
    try:
        # 收集数据
        levels = []
        gold_costs = []
        mana_dust_costs = []
        mana_crystal_costs = []
        
        # 按等级排序
        sorted_levels = sorted([item for item in data["level"]["json"] if "level_" in item], 
                             key=lambda x: x["level_"])
        
        for item in sorted_levels:
            level = item.get("level_")
            if level is not None:
                levels.append(level)
                gold_costs.append(item.get("gold", 0))
                mana_dust_costs.append(item.get("mana_dust", 0))
                mana_crystal_costs.append(item.get("mana_crystal", 0) if "mana_crystal" in item else 0)
        
        # 创建三个子图
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 18))
        
        # 计算合适的x轴刻度间隔
        max_level = max(levels)
        if max_level <= 100:
            x_interval = 10
        elif max_level <= 200:
            x_interval = 20
        else:
            x_interval = 50
        
        # 绘制金币消耗
        ax1.plot(levels, gold_costs, 'g-', marker='o', markersize=2)
        ax1.set_title('金币消耗统计', fontproperties=CUSTOM_FONT)
        ax1.set_xlabel('等级', fontproperties=CUSTOM_FONT)
        ax1.set_ylabel('消耗数量', fontproperties=CUSTOM_FONT)
        ax1.grid(True, linestyle='--', alpha=0.7)
        ax1.set_xticks(range(0, max_level+1, x_interval))
        ax1.tick_params(axis='x', rotation=45)
        ax1.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
        
        # 绘制魔力粉尘消耗
        ax2.plot(levels, mana_dust_costs, 'b-', marker='o', markersize=2)
        ax2.set_title('魔力粉尘消耗统计', fontproperties=CUSTOM_FONT)
        ax2.set_xlabel('等级', fontproperties=CUSTOM_FONT)
        ax2.set_ylabel('消耗数量', fontproperties=CUSTOM_FONT)
        ax2.grid(True, linestyle='--', alpha=0.7)
        ax2.set_xticks(range(0, max_level+1, x_interval))
        ax2.tick_params(axis='x', rotation=45)
        ax2.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
        
        # 绘制魔力水晶消耗
        ax3.plot(levels, mana_crystal_costs, 'r-', marker='o', markersize=2)
        ax3.set_title('魔力水晶消耗统计', fontproperties=CUSTOM_FONT)
        ax3.set_xlabel('等级', fontproperties=CUSTOM_FONT)
        ax3.set_ylabel('消耗数量（万）', fontproperties=CUSTOM_FONT)
        ax3.grid(True, linestyle='--', alpha=0.7)
        ax3.set_xticks(range(0, max_level+1, x_interval))
        ax3.tick_params(axis='x', rotation=45)
        
        # 将魔力水晶的数值转换为"万"为单位
        def format_func(x, p):
            return f"{x/10000:.1f}"
        ax3.yaxis.set_major_formatter(plt.FuncFormatter(format_func))
        
        # 调整子图之间的间距和整体布局
        plt.tight_layout(pad=3.0)
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 获取bytes数据
        buffer.seek(0)
        image_bytes = buffer.getvalue()
        
        # 返回MessageSegment对象
        return MessageSegment.image(image_bytes)
        
    except Exception as e:
        logger.error(f"生成等级消耗统计图时发生错误: {str(e)}")
        return MessageSegment.text("生成统计图失败")


def format_number(num):
    '''
    递归实现，精确为最大单位值 + 小数点后一位
    处理科学计数法表示的数值
    '''
    def strofsize(num, level):
        if level >= 29:
            return num, level
        elif num >= 10000:
            num /= 10000
            level += 1
            return strofsize(num, level)
        else:
            return num, level
        
    units = ['', '万', '亿', '兆', '京', '垓', '秭', '穰', '沟', '涧', '正', '载', '极', 
             '恒河沙', '阿僧祗', '那由他', '不思议', '无量大', '万无量大', '亿无量大', 
             '兆无量大', '京无量大', '垓无量大', '秭无量大', '穰无量大', '沟无量大', 
             '涧无量大', '正无量大', '载无量大', '极无量大']
    # 处理科学计数法
    if "e" in str(num):
        num = float(f"{num:.1f}")
    num, level = strofsize(num, 0)
    if level >= len(units):
        level = len(units) - 1
    return f"{round(num, 1)}{units[level]}"


def clean_tags(text):
    """清理颜色标签"""
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


def get_keyword_grade(data: dict, grade_sno: int, is_test: bool = False) -> str:
    """获取关键字稀有度"""
    return next((s.get("kr" if is_test else "zh_tw", "未知") for s in data["string_system"]["json"] 
                if s["no"] == grade_sno), "未知")


def get_keyword_name(data: dict, string_sno: int, is_test: bool = False) -> str:
    """获取关键字名称"""
    return next((s.get("kr" if is_test else "zh_tw", "未知") for s in data["string_ui"]["json"] 
                if s["no"] == string_sno), "未知")


def get_keyword_source(data: dict, source_sno: int, details: int, hero_no: int = None, keyword_type: int = None, is_test: bool = False) -> str:
    """获取关键字解锁条件"""
    source = next((s.get("kr" if is_test else "zh_tw", "") for s in data["string_ui"]["json"] 
                  if s["no"] == source_sno), "")
    
    if not source:
        return ""
        
    # 检查是否是遗失物品
    if hero_no and keyword_type:
        lost_item_info = get_lost_item_info(data, hero_no, keyword_type, details, is_test)
        if lost_item_info:
            return lost_item_info
        
    if 101 <= details <= 110:
        location = next((loc for loc in data["town_location"]["json"] 
                       if loc["no"] == details), None)
        if location:
            location_name = next((s.get("kr" if is_test else "zh_tw", "未知") for s in data["string_town"]["json"] 
                                if s["no"] == location.get("location_name_sno")), "未知")
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


def get_keyword_location(data: dict, keyword_get_details: int, is_test: bool = False) -> str:
    """获取非遗失物品关键字对应的地点"""    
    # 如果没有keyword_get_details或为0，返回"通用"
    if not keyword_get_details:
        return "通用"
    
    # 在TownLocation.json中查找对应地点
    location = next((loc for loc in data["town_location"]["json"] 
                    if loc["no"] == keyword_get_details), None)
    
    if not location:
        return ""
    
    # 获取地点名称
    location_name = next((s.get("kr" if is_test else "zh_tw", "") for s in data["string_town"]["json"] 
                        if s["no"] == location.get("location_name_sno")), "")
    return location_name


def get_lost_item_info(data: dict, hero_no: int, keyword_type: int, keyword_get_details: int, is_test: bool = False) -> str:
    """获取遗失物品信息"""
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


def get_keyword_points(data: dict, keyword_type: str) -> list:
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


def get_character_portrait(data, hero_id, hero_name_en):
    """获取角色头像
    
    Args:
        data: JSON数据字典
        hero_id: 角色ID
        hero_name_en: 角色英文名称
    Returns:
        Path: 头像图片路径或None
    """
    # 头像路径
    portrait_path = str(HERO_DIR / f"{hero_name_en}_512.png")
    if Path(portrait_path).exists():
        return portrait_path
    
    # 如果直接用英文名找不到，尝试从item_costume获取portrait_path
    for costume in data["item_costume"]["json"]:
        if costume.get("hero_no") == hero_id:
            portrait_path = costume.get("portrait_path", "")
            if portrait_path:
                # 构建头像路径
                portrait_file = str(HERO_DIR / f"{portrait_path}_512.png")
                if Path(portrait_file).exists():
                    return portrait_file
                break
    
    return None


def get_character_illustration(data, hero_id):
    """获取角色立绘
    
    Args:
        data: JSON数据字典
        hero_id: 角色ID 
    Returns:
        list: [(图片路径, 显示名称_tw, 显示名称_cn, 显示名称_kr, 显示名称_en, 解锁条件_tw, 解锁条件_cn, 解锁条件_kr, 解锁条件_en)] 的列表
    """
    image_path = str(HERO_DIR)
    if not Path(image_path).exists():
        return []
    
    # 获取所有该角色的立绘信息
    costume_info = {}
    for costume in data["item_costume"]["json"]:
        if costume.get("hero_no") == hero_id:
            portrait_path = costume.get("portrait_path", "")
            name_sno = costume.get("name_sno")
            type_sno = costume.get("type_sno")  # 获取时装的type_sno
            if portrait_path and name_sno and type_sno:
                # 从StringItem.json获取立绘名称
                for string in data["string_item"]["json"]:
                    if string["no"] == name_sno:
                        costume_name_zh_tw = string.get("zh_tw", "")
                        costume_name_zh_cn = string.get("zh_cn", "") or string.get("zh_tw", "")
                        costume_name_kr = string.get("kr", "")
                        costume_name_en = string.get("en", "")
                        if costume_name_zh_tw and costume_name_zh_cn and costume_name_kr and costume_name_en:
                            # 从StringUI.json获取解锁条件
                            condition_tw = ""
                            condition_cn = ""
                            condition_kr = ""
                            condition_en = ""
                            for ui_string in data["string_ui"]["json"]:
                                if ui_string["no"] == type_sno:
                                    condition_tw = ui_string.get("zh_tw", "")
                                    condition_cn = ui_string.get("zh_cn", "")
                                    condition_kr = ui_string.get("kr", "")
                                    condition_en = ui_string.get("en", "")
                                    break
                            costume_info[portrait_path] = (costume_name_zh_tw, costume_name_zh_cn, costume_name_kr, costume_name_en,\
                                                            condition_tw, condition_cn, condition_kr, condition_en)
                        break
    
    # 查找匹配的图片
    images = []
    for file in Path(image_path).glob('*_2048.*'):
        base_name = file.stem[:-5]  # 移除 _2048 后缀
        if base_name in costume_info:
            # 构建 "角色名_立绘名" 的格式
            costume_name_zh_tw, costume_name_zh_cn, costume_name_kr, costume_name_en, condition_tw, condition_cn, condition_kr, condition_en = costume_info[base_name]
            display_name_tw = f"{costume_name_zh_tw}"
            display_name_cn = f"{costume_name_zh_cn}"
            display_name_kr = f"{costume_name_kr}"
            display_name_en = f"{costume_name_en}"
            images.append((file, display_name_tw, display_name_cn, display_name_kr, display_name_en, condition_tw, condition_cn, condition_kr, condition_en))
    
    return sorted(images)  # 排序以保持顺序一致


def get_schedule_events(data, target_month, current_year, schedule_prefix, event_type):
    """获取日程事件信息
    
    Args:
        data: JSON数据字典
        target_month: 目标月份
        current_year: 当前年份
        schedule_prefix: 日程key前缀(如"Calender_SingleRaid_")
        event_type: 事件类型显示名称(如"恶灵讨伐")
    
    Returns:
        list: 事件信息列表
    """
    events = []
    now = datetime.now()
    
    for schedule in data["localization_schedule"]["json"]:
        # 对于主要活动，使用完全匹配而不是startswith
        if schedule_prefix.endswith("_Main"):
            if schedule.get("schedule_key", "") != schedule_prefix:
                continue
        else:
            if not schedule.get("schedule_key", "").startswith(schedule_prefix):
                continue
            
        start_date = schedule.get("start_date")
        end_date = schedule.get("end_date")
        
        if not (start_date and end_date):
            continue
            
        start_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        end_date = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
        
        is_in_month = (
            (start_date.year == current_year and start_date.month == target_month) or
            (end_date.year == current_year and end_date.month == target_month)
        ) and end_date >= now
        
        if not is_in_month:
            continue
            
        schedule_key = schedule["schedule_key"]
        event_name_tw = ""
        banner_path = ""
        name_sno = None
        gacha_no = None
        
        # 从EventCalender中获取name_sno和gacha_no
        for event in data["event_calender"]["json"]:
            if event.get("schedule_key") == schedule_key:
                name_sno = event.get("name_sno")
                # 如果是Pickup类型，获取gacha_no
                if schedule_key.startswith("Calender_PickUp_"):
                    gacha_no = event.get("gacha_no")
                if name_sno:
                    # 从StringUI中获取名称
                    for string in data["string_ui"]["json"]:
                        if string["no"] == name_sno:
                            event_name_tw = string.get("zh_tw", "").replace('\\r\\n', ' ').replace('\r\n', ' ').replace('\n', ' ')
                            break
                break
        
        # 对于Pickup类型，从Gacha.json中获取banner_path
        if schedule_key.startswith("Calender_PickUp_") and gacha_no:
            if "gacha" in data:
                for gacha in data["gacha"]["json"]:
                    if gacha.get("no") == gacha_no:
                        banner_raw = gacha.get("banner_path", "")
                        if banner_raw:
                            banner_path = f"{banner_raw}_ZH_TW.png"
                        break
        # 恶灵讨伐类型，从schedule_key提取英雄名生成贴纸路径                        
        elif schedule_key.startswith("Calender_SingleRaid_"):
            # 从schedule_key中提取英雄名称：Calender_SingleRaid_HeroName
            parts = schedule_key.split('_')
            if len(parts) > 2:
                hero_name = parts[-1]  # 获取最后一部分，保持原始大小写
                # 这里是给数据表中不同字段角色名称做适配
                hero_name = HERO_NAME_MAPPING.get(hero_name, hero_name)  # 如果不在映射表中，使用原名
                sticker_path = f"sticker_singleraid_{hero_name}_01.png"
                # 检查文件是否存在
                if (STICKER_DIR / sticker_path).exists():
                    banner_path = sticker_path
        # 联合作战类型，从schedule_key提取英雄名生成徽章路径
        elif schedule_key.startswith("Calender_EdenAlliance_"):
            # 从schedule_key中提取英雄名称：Calender_EdenAlliance_HeroName
            parts = schedule_key.split('_')
            if len(parts) > 2:
                hero_name = parts[-1].lower()  # 获取最后一部分并转为小写
                # 寻找最大tier值的贴纸
                max_tier = 0
                found_sticker = None
                # 查找基础贴纸（不带_1后缀）
                for tier in range(1, 20):  # 假设tier最多到20
                    sticker_name = f"sticker_eas_{hero_name}_tier_{tier}.png"
                    sticker_path = STICKER_DIR / sticker_name
                    if sticker_path.exists():
                        max_tier = tier
                        found_sticker = sticker_name
                
                # 如果找到了基础贴纸，尝试查找带_1后缀的贴纸
                if found_sticker:
                    variant_sticker = f"sticker_eas_{hero_name}_tier_{max_tier}_1.png"
                    variant_path = STICKER_DIR / variant_sticker
                    if variant_path.exists():
                        banner_path = variant_sticker
                    else:
                        banner_path = found_sticker
        # 其他类型，从EventInfo中获取banner路径
        elif name_sno:
            for event_info in data["event_info"]["json"]:
                if event_info.get("name_sno") == name_sno:
                    banner_raw = event_info.get("banner_path", "")
                    if banner_raw:
                        banner_path = f"{banner_raw}_ZH_TW.png"
                    break
        
        if event_name_tw:
            event_info = []
            event_info.append(f"【{event_type}】")
            event_info.append(f"名称：{event_name_tw}")
            event_info.append(f"持续时间：{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
            if banner_path:
                event_info.append(f"banner：{banner_path}")
            # 返回带开始时间的元组
            events.append((start_date, "\n".join(event_info)))
    
    return events


def get_mail_events(data, target_month, current_year):
    """获取邮箱事件信息"""
    mail_events = []
    now = datetime.now()
    
    for mail in data["message_mail"]["json"]:
        start_date = mail.get("start_date")
        end_date = mail.get("end_date")
        
        if not (start_date and end_date):
            continue
            
        # 将日期字符串转换为datetime对象
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        
        # 检查事件是否在目标月份内
        is_in_month = (
            (start_date.year == current_year and start_date.month == target_month) or
            (end_date.year == current_year and end_date.month == target_month)
        ) and end_date >= now
        
        if not is_in_month:
            continue
            
        # 获取发送者名称
        sender_name_tw = "未知"
        sender_name_en = "Unknown"
        if sender_sno := mail.get("sender_sno"):
            sender_name_tw, sender_name_cn, sender_name_kr, sender_name_en = get_hero_name_by_id(data, sender_sno)
        
        # 获取标题和描述
        title_tw, title_cn, title_kr, title_en = get_string_character(data, mail.get("title_sno", 0)) or "无标题"
        desc_tw, desc_cn, desc_kr, desc_en = get_string_character(data, mail.get("desc_sno", 0)) or "无描述"
        
        # 处理奖励信息
        rewards = []
        for i in range(1, 5):
            reward_no_key = f"reward_no{i}"
            reward_amount_key = f"reward_amount{i}"
            
            if reward_no := mail.get(reward_no_key):
                amount = mail.get(reward_amount_key, 0)
                item_name = get_item_name(data, reward_no)
                if item_name and amount:
                    rewards.append(f"{item_name} x{amount}")
        
        # 构建事件信息
        event_info = []
        event_info.append(f"【邮箱事件】")  # 使用统一的格式
        event_info.append(f"名称：{sender_name_tw}的信件")  # 添加名称行以统一格式
        event_info.append(f"标题：{title_tw}")
        event_info.append(f"描述：{desc_tw}")
        event_info.append(f"持续时间：{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
        
        # 添加贴纸作为banner
        if sender_name_en and sender_name_en != "Unknown":
            sender_name_en = HERO_NAME_MAPPING.get(sender_name_en, sender_name_en)  # 如果不在映射表中，使用原名
            sticker_path = f"sticker_love_{sender_name_en}01.png"
            # 检查文件是否存在
            if (STICKER_DIR / sticker_path).exists():
                event_info.append(f"banner：{sticker_path}")
        
        if rewards:
            event_info.append("奖励：")
            event_info.extend([f"- {reward}" for reward in rewards])
        
        mail_events.append((start_date, "\n".join(event_info)))
    
    return mail_events


def get_calendar_events(data, target_month, current_year):
    """获取一般活动信息"""
    calendar_events_with_date = []
    now = datetime.now()
    
    for schedule in data["localization_schedule"]["json"]:
        schedule_key = schedule.get("schedule_key", "")
        # 排除特殊事件和主要活动
        if not schedule_key.startswith("Calender_") or \
           schedule_key.startswith("Calender_SingleRaid_") or \
           schedule_key.startswith("Calender_EdenAlliance_") or \
           schedule_key.startswith("Calender_PickUp_") or \
           schedule_key.startswith("Calender_WorldBoss_") or \
           schedule_key.startswith("Calender_GuildRaid_") or \
           schedule_key.endswith("_Main"):
            continue
            
        start_date = schedule.get("start_date")
        end_date = schedule.get("end_date")
        
        if not (start_date and end_date):
            continue
            
        start_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        end_date = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
        
        is_in_month = (
            (start_date.year == current_year and start_date.month == target_month) or
            (end_date.year == current_year and end_date.month == target_month)
        ) and end_date >= now
        
        if not is_in_month:
            continue
            
        event_name_tw = ""
        event_name_cn = ""
        banner_path = ""
        name_sno = None
        
        # 从EventCalender中获取name_sno
        for event in data["event_calender"]["json"]:
            if event.get("schedule_key") == schedule_key:
                name_sno = event.get("name_sno")
                if name_sno:
                    # 从StringUI中获取名称并处理换行
                    for string in data["string_ui"]["json"]:
                        if string["no"] == name_sno:
                            # 在这里处理换行符
                            event_name_tw = string.get("zh_tw", "").replace('\\r\\n', ' ').replace('\r\n', ' ').replace('\n', ' ')
                            event_name_cn = string.get("zh_cn", "").replace('\\r\\n', ' ').replace('\r\n', ' ').replace('\n', ' ')
                            break
                break
        
        # 从EventInfo中获取banner路径
        if name_sno:
            for event_info in data["event_info"]["json"]:
                if event_info.get("name_sno") == name_sno:
                    banner_raw = event_info.get("banner_path", "")
                    if banner_raw:
                        banner_path = f"{banner_raw}_ZH_TW.png"
                    break
        
        if event_name_tw:
            event_info = []
            event_info.append(f"【活动】")
            event_info.append(f"名称：{event_name_tw}")
            event_info.append(f"持续时间：{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
            if banner_path:
                event_info.append(f"banner：{banner_path}")
            calendar_events_with_date.append((start_date, "\n".join(event_info)))
    
    calendar_events_with_date.sort(key=lambda x: x[0])
    return [event_info for _, event_info in calendar_events_with_date]


def get_item_name(data, item_no):
    """获取物品名称"""
    item_name = "未知物品"
    # 在Item.json中查找物品
    for item in data["item"]["json"]:
        if item["no"] == item_no:
            name_sno = item.get("name_sno")
            if name_sno:
                # 在StringItem.json中查找物品名称
                for string in data["string_item"]["json"]:
                    if string["no"] == name_sno:
                        return string.get("zh_tw", "未知物品")
    return item_name


def get_town_object_info(data: dict, hero_id: int, is_test=False) -> list:
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
                prefab = obj.get("prefab", "")
                    
                # 在Item.json中查找对应物品信息
                for item in data["item"]["json"]:
                    if item.get("no") == obj_no:
                        # 获取物品名称
                        name = ""
                        name_sno = item.get("name_sno")
                        if name_sno:
                            for string in data["string_item"]["json"]:
                                if string.get("no") == name_sno:
                                    name = string.get("kr", "") if is_test else string.get("zh_tw", "")
                                    break
                        
                        # 获取物品品质
                        grade = ""
                        grade_sno = item.get("grade_sno")
                        if grade_sno:
                            for string in data["string_system"]["json"]:
                                if string.get("no") == grade_sno:
                                    grade = string.get("kr", "") if is_test else string.get("zh_tw", "")
                                    break
                        
                        # 获取物品类型
                        slot_type = ""
                        slot_limit_sno = item.get("slot_limit_sno")
                        if slot_limit_sno:
                            for string in data["string_ui"]["json"]:
                                if string.get("no") == slot_limit_sno:
                                    slot_type = string.get("kr", "") if is_test else string.get("zh_tw", "")
                                    break
                        
                        # 获取物品描述并清理颜色标签
                        desc = ""
                        desc_sno = item.get("desc_sno")
                        if desc_sno:
                            for string in data["string_item"]["json"]:
                                if string.get("no") == desc_sno:
                                    desc = clean_tags(string.get("kr", "") if is_test else string.get("zh_tw", ""))
                                    break
                        
                        if name:  # 只添加有名称的物品
                            # 构建图片路径
                            img_path = None
                            if prefab:
                                img_path = TOWN_DIR / f"{prefab}.png"
                                if not os.path.exists(img_path):
                                    img_path = None
                            
                            objects_info.append((obj_no, name, grade, slot_type, desc, img_path))
                        
        return objects_info
        
    except Exception as e:
        logger.error(f"获取专属领地物品信息时发生错误: {e}, hero_id={hero_id}")
        return []


def get_town_object_tasks(data: dict, obj_no: int, is_test=False) -> list:
    """获取专属领地物品可进行的任务信息
    
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
                                    rarity = string.get("kr", "") if is_test else string.get("zh_tw", "")
                                    break
                        
                        # 获取任务名称
                        name = ""
                        name_sno = arbeit.get("name_sno")
                        if name_sno:
                            for string in data["string_town"]["json"]:
                                if string.get("no") == name_sno:
                                    name = string.get("kr", "") if is_test else string.get("zh_tw", "")
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
                                                    item_name = string.get("kr", "") if is_test else string.get("zh_tw", "")
                                                    rewards.append(f"{item_name} x{item_amount}")
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


def load_data_source_config():
    """加载数据源配置文件"""
    global CURRENT_DATA_SOURCE
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # 重置配置为默认值
    CURRENT_DATA_SOURCE = {"default": DEFAULT_CONFIG.copy()}
    
    file_config_loaded = False
    if DATA_SOURCE_CONFIG.exists():
        try:
            with open(DATA_SOURCE_CONFIG, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            if config:
                # 确保配置中有default键
                if "default" not in config:
                    config["default"] = DEFAULT_CONFIG.copy()
                
                # 明确转换路径字符串为Path对象
                for group_id, group_config in config.items():
                    # 确保group_id是字符串
                    group_id_str = str(group_id)
                    
                    if "json_path" in group_config:
                        # 确保json_path是Path对象
                        if not isinstance(group_config["json_path"], Path):
                            group_config["json_path"] = Path(group_config["json_path"])
                    
                    if "hero_alias_file" in group_config:
                        # 确保hero_alias_file是Path对象
                        if not isinstance(group_config["hero_alias_file"], Path):
                            if str(group_config["hero_alias_file"]).startswith("./"):
                                group_config["hero_alias_file"] = Path(__file__).parent.parent / \
                                    str(group_config["hero_alias_file"])[2:]
                            else:
                                group_config["hero_alias_file"] = Path(group_config["hero_alias_file"])
                    
                    # 使用字符串键存储配置
                    CURRENT_DATA_SOURCE[group_id_str] = group_config
                
                file_config_loaded = True
        except Exception as e:
            logger.error(f"加载数据源配置文件出错: {e}")
    
    if not file_config_loaded:
        try:
            save_data_source_config(CURRENT_DATA_SOURCE)
        except Exception as e:
            logger.error(f"创建默认数据源配置文件失败: {e}")
    
    if hasattr(plugin_config, 'eversoul_group_config') and plugin_config.eversoul_group_config:
        for group_id, group_settings in plugin_config.eversoul_group_config.items():
            if group_id not in CURRENT_DATA_SOURCE:
                CURRENT_DATA_SOURCE[group_id] = CURRENT_DATA_SOURCE["default"].copy()

            if "type" in group_settings:
                CURRENT_DATA_SOURCE[group_id]["type"] = group_settings["type"]
            
            if CURRENT_DATA_SOURCE[group_id]["type"] == "live":
                if hasattr(plugin_config, 'eversoul_live_path'):
                    json_path = plugin_config.eversoul_live_path
                else:
                    json_path = str(CURRENT_DATA_SOURCE["default"]["json_path"])
            else:  # review
                if hasattr(plugin_config, 'eversoul_review_path'):
                    json_path = plugin_config.eversoul_review_path
                else:
                    json_path = str(CURRENT_DATA_SOURCE["default"]["json_path"]).replace("live_jsons", "review_jsons")
                
            if "json_path" in group_settings:
                json_path = group_settings["json_path"]
                
            CURRENT_DATA_SOURCE[group_id]["json_path"] = Path(json_path)
            
            alias_type = CURRENT_DATA_SOURCE[group_id]["type"]
            CURRENT_DATA_SOURCE[group_id]["hero_alias_file"] = DATA_DIR / f"{alias_type}_hero_aliases.yaml"
            if "hero_alias_file" in group_settings:
                CURRENT_DATA_SOURCE[group_id]["hero_alias_file"] = Path(group_settings["hero_alias_file"])
        
        try:
            save_data_source_config(CURRENT_DATA_SOURCE)
        except Exception as e:
            logger.error(f"更新数据源配置文件失败: {e}")


def save_data_source_config(config):
    """保存数据源配置"""
    try:
        save_config = {}
        plugin_dir = str(Path(__file__).parent)
        
        for group_id, group_config in config.items():
            save_config[group_id] = group_config.copy()
            if "json_path" in group_config:
                save_config[group_id]["json_path"] = str(group_config["json_path"])
            if "hero_alias_file" in group_config:
                hero_alias_path = str(group_config["hero_alias_file"])
                if hero_alias_path.startswith(plugin_dir):
                    rel_path = hero_alias_path[len(plugin_dir):].lstrip('/')
                    save_config[group_id]["hero_alias_file"] = f"./{rel_path}"
                else:
                    save_config[group_id]["hero_alias_file"] = hero_alias_path
        
        with open(DATA_SOURCE_CONFIG, "w", encoding="utf-8") as f:
            yaml.dump(save_config, f, allow_unicode=True)
    except Exception as e:
        logger.error(f"保存数据源配置出错: {e}")


def get_group_data_source(group_id):
    """获取群组的数据源配置
    
    Args:
        group_id: 群组ID，如果不是群消息则为None
        
    Returns:
        dict: 数据源配置
    """
    if group_id is not None:
        group_id_str = str(group_id)

        if group_id_str in CURRENT_DATA_SOURCE:
            return CURRENT_DATA_SOURCE[group_id_str]
        else:
            keys_match = [k for k in CURRENT_DATA_SOURCE.keys() if str(k) == group_id_str]
            if keys_match:
                return CURRENT_DATA_SOURCE[keys_match[0]]
    
    return CURRENT_DATA_SOURCE["default"]


def get_cash_item_info(data: dict, item_type: str, gate_info: dict) -> list:
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
    package_types = {
        'barrier': '通关礼包',
        'stage': '主线礼包',
        'tower': '起源之塔礼包',
        'grade_eternal': '角色升阶礼包'
    }
    package_type_name = package_types.get(item_type, '特殊礼包')
    
    # 获取符合条件的商店物品
    for shop_item in data["cash_shop_item"]["json"]:
        if shop_item.get("type") == item_type and shop_item.get("type_value") == str(gate_info["no"]):
            shop_items.append(shop_item)
    
    if shop_items:
        for shop_item in shop_items:
            package_info = []
            package_info.append(f"\n【{package_type_name}】")
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
                        item_name = get_item_name(data, item_no)
                        content_info.append(f"・{item_name} x{amount}")
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


def get_drop_items(data, group_no):
    """获取掉落物品信息，并去重保留最高概率
    
    Args:
        data: JSON数据字典
        group_no: 掉落组编号
    
    Returns:
        list: [(物品名称, 数量, 掉落率)] 的列表
    """
    drop_items_dict = {}  # 用字典存储物品信息，键为物品名称
    
    # 获取所有符合条件的掉落组
    for drop_group in data["item_drop_group"]["json"]:
        if drop_group["no"] <= group_no:
            item_no = drop_group.get("item_no")
            amount = drop_group.get("amount", 0)
            drop_rate = drop_group.get("drop_rate", 0)
            
            if item_no:
                item_name = get_item_name(data, item_no)
                # 转换掉落率 (1 = 0.001%)
                rate_percent = drop_rate * 0.001
                
                # 如果物品已存在，比较掉落率
                if item_name in drop_items_dict:
                    old_amount, old_rate = drop_items_dict[item_name]
                    # 只有当新的掉落率更高时才更新
                    if rate_percent > old_rate:
                        drop_items_dict[item_name] = (amount, rate_percent)
                else:
                    # 新物品直接添加
                    drop_items_dict[item_name] = (amount, rate_percent)
    
    # 将字典转换为列表
    drop_items = [(name, amount, rate) 
                  for name, (amount, rate) in drop_items_dict.items()]
    
    # 按掉落率从高到低排序
    return sorted(drop_items, key=lambda x: (-x[2], x[0]))


def get_soullink_info(data: dict, hero_id: int, is_test: bool = False) -> list:
    """获取角色的灵魂链接信息"""
    soullink_info = []
    
    # 查找所有包含该角色的灵魂链接
    for link in data["soullink"]["json"]:
        # 动态查找所有hero槽位键
        hero_keys = [key for key in link.keys() if key.startswith("group_hero") and link[key] == hero_id]
        
        if not hero_keys:
            continue  # 如果没有找到包含目标角色的槽位，跳过此链接
        
        # 收集所有英雄ID
        hero_ids = []
        for key in link.keys():
            if key.startswith("group_hero") and link[key] > 0:
                hero_ids.append(link[key])
        
        if not hero_ids:
            continue
        
        # 获取灵魂链接标题和故事
        title = next((s.get("kr" if is_test else "zh_tw", "") 
                    for s in data["string_character"]["json"] 
                    if s["no"] == link.get("group_title")), "")
        story = next((s.get("kr" if is_test else "zh_tw", "") 
                    for s in data["string_character"]["json"] 
                    if s["no"] == link.get("group_story")), "")
        
        # 获取所有角色名称
        hero_names = []
        for hid in hero_ids:
            name = get_hero_name(data, hid)[2 if is_test else 0]  # 2是kr，0是zh_tw
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
                condition_text = next((s.get("kr" if is_test else "zh_tw", "").format(
                    item.get("condition_count", 0),
                    item.get("condition_count", 0)
                ) for s in data["string_ui"]["json"] 
                if s["no"] == item.get("condition_string")), "")
                
                # 获取buff效果
                buff_effects = []
                if buff_no := item.get("contents_buff_no"):
                    buff = next((b for b in data["contents_buff"]["json"] 
                               if b.get("no") == buff_no), None)
                    if buff:
                        for key, value in buff.items():
                            if key in STAT_NAME_MAPPING and value != 0:
                                if value < 1:  # 小于1的显示为百分比
                                    buff_effects.append(f"{STAT_NAME_MAPPING[key]}：{value*100:.1f}%")
                                else:
                                    buff_effects.append(f"{STAT_NAME_MAPPING[key]}：{int(value)}")
                
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


def get_affection_cgs(data, hero_id):
    """获取角色好感CG
    
    Args:
        data: JSON数据字典
        hero_id: 角色ID
    
    Returns:
        list: [(图片路径, CG编号, 章节标题)] 的列表
    """
    cg_path = CG_DIR
    if not cg_path.exists():
        return []
    
    # 将hero_id转换为act格式
    act = hero_id
    
    # 收集所有相关的故事编号和章节信息
    story_info = {}  # 使用字典存储故事编号和章节信息的映射
    for story in data["story_info"]["json"]:
        if "act" in story and story["act"] == act:
            story_nos = story_info.get(story["no"], [])
            story_nos.append({
                "episode": story["episode"],
                "episode_name_sno": story.get("episode_name_sno")
            })
            story_info[story["no"]] = story_nos
    
    # 从Illust.json中获取CG信息
    cg_info = []
    for illust in data["illust"]["json"]:
        if ("open_condition" in illust and 
            illust["open_condition"] in story_info and 
            "bg_movie_path" in illust):
            # 从路径中提取CG名称
            path_parts = illust["bg_movie_path"].split('/')
            cg_name = path_parts[-1]
            # 获取对应的章节信息
            story_no = illust["open_condition"]
            episode_info = story_info[story_no][0]  # 取第一个匹配的章节信息
            cg_info.append((illust["no"], cg_name, episode_info))
    
    # 查找匹配的CG图片
    images = []
    for no, cg_name, episode_info in sorted(cg_info):  # 按编号排序
        for file in Path(cg_path).glob(f"{cg_name}.*"):
            # 获取章节标题
            episode_title = ""
            if episode_info["episode_name_sno"]:
                for string in data["string_talk"]["json"]:
                    if string["no"] == episode_info["episode_name_sno"]:
                        episode_title = string.get("zh_tw", "")
                        break
            images.append((file, f"CG_{no}", episode_info["episode"], episode_title))
            break  # 找到一个匹配的文件就跳出
    
    return images


def get_evertalk_illustrations(data: dict, hero_id: int) -> List[Tuple[Path, str]]:
    """获取角色的EverPhone插图
    
    Args:
        data: 游戏数据字典
        hero_id: 角色ID
    
    Returns:
        List[Tuple[Path, str]]: 插图信息列表，每个元素为(插图路径, 插图基础名称)的元组
    """
    evertalk_illusts = []
    
    # 从EverTalkDesc.json中查找插图
    for talk in data["evertalk_desc"]["json"]:
        if talk.get("hero_no") == hero_id and talk.get("ui_type") == "Illust":
            talk_no = talk.get("no")
            # 从StringEverTalk.json中获取插图名称
            for string in data["string_evertalk"]["json"]:
                if string.get("no") == talk_no:
                    # 提取插图基础名称
                    illust_match = re.search(r"<display:(.+?)>", string.get("kr", ""))
                    if illust_match:
                        illust_base = illust_match.group(1)
                        illust_path = EVERTALK_DIR / f"{illust_base}.png"
                        if Path(illust_path).exists():
                            evertalk_illusts.append((illust_path, illust_base))
    
    return evertalk_illusts


def get_skill_value(data, value_id, value_type="VALUE"):
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
        return "???"

    # 从SkillCode.json中查找数值
    for code in data["skill_code"]["json"]:
        if code["no"] == value_id:
            # 检查value是否为整数形式（去掉.0后）的数字
            value_without_decimal = int(code["value"]) if code["value"].is_integer() else code["value"]
            
            # 如果value（去掉.0后）等于另一个no，则从SkillBuff中查找这个no的值
            if isinstance(value_without_decimal, int):
                for buff in data["skill_buff"]["json"]:
                    if buff["no"] == value_without_decimal:
                        value = buff["value"]  # 获取原始值
                        abs_value = abs(value)  # 取绝对值
                        
                        # 小于20的值按百分比处理
                        if abs_value < 20:
                            # 检查百分比值是否为整数
                            percent_value = abs_value * 100
                            # 使用round函数处理浮点数精度问题
                            rounded_value = round(percent_value, 1)
                            if rounded_value.is_integer():
                                return f"{int(rounded_value)}%"
                            return f"{rounded_value}%"
                        else:
                            # 大于等于20的值按整数处理
                            return str(int(abs_value))
            
            # 如果不是引用其他no，则直接使用code中的value
            value = code["value"]  # 获取原始值
            abs_value = abs(value)  # 取绝对值
            
            # 小于20的值按百分比处理
            if abs_value < 20:
                # 检查百分比值是否为整数
                percent_value = abs_value * 100
                # 使用round函数处理浮点数精度问题
                rounded_value = round(percent_value, 1)
                if rounded_value.is_integer():
                    return f"{int(rounded_value)}%"
                return f"{rounded_value}%"
            # 大于20的值按整数处理
            return str(int(abs_value))
    return "???"


def process_skill_description(data, description):
    """处理技能描述中的数值标签"""
    def replace_value(match):
        value_id = int(match.group(1))
        value_type = match.group(2)
        return get_skill_value(data, value_id, value_type)
    
    # 替换所有形如 <数字.VALUE> 或 <数字.DURATION> 的内容
    processed_desc = re.sub(r'<\s*(\d+)\.(VALUE|DURATION)\s*>', replace_value, description)
    return processed_desc


def get_skill_info(data, skill_no, is_support=False, hero_data=None):
    """获取技能信息
    
    Args:
        data: JSON数据字典
        skill_no: 技能编号
        is_support: 是否为支援技能
        hero_data: 英雄数据（用于获取辅助伙伴技能信息）
    
    Returns:
        tuple: (技能名称, 技能描述列表, 技能图标信息, 是否为支援技能)
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
                    skill_descriptions.append((
                        f"主要夥伴：{desc_tw}",  # 添加主要伙伴标记
                        f"主要伙伴：{desc_cn}",
                        f"메인 파트너：{desc_kr}",
                        f"Main Partner Effect：{desc_en}"
                    ))
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
                                        
                                        skill_descriptions.append((
                                            f"輔助夥伴：{desc_tw}",
                                            f"辅助伙伴：{desc_cn}",
                                            f"서브 파트너：{desc_kr}",
                                            f"Support Effect：{desc_en}"
                                        ))
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
                        skill_descriptions.append((desc_tw, desc_cn, desc_kr, desc_en, hero_level))
                        break
    
    return skill_name_zh_tw, skill_name_zh_cn, skill_name_kr, skill_name_en,\
            skill_descriptions, skill_icon_info, is_support


def apply_color_to_icon(icon_path: str, color: str) -> bytes:
    """对图标应用颜色
    
    Args:
        icon_path: 图标文件路径
        color: 十六进制颜色代码 (#RRGGBB)
    
    Returns:
        bytes: 处理后的图片数据
    """
    # 打开图片
    with Image.open(icon_path) as img:
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # 将十六进制颜色转换为RGB
        color = color.lstrip('#')
        r, g, b = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        
        # 创建底层彩色图片
        base = Image.new('RGBA', img.size, (r, g, b, 255))
        
        # 将原图作为遮罩覆盖在彩色底图上
        result = Image.alpha_composite(base, img)
        
        # 保存为字节流
        from io import BytesIO
        output = BytesIO()
        result.save(output, format='PNG')
        return output.getvalue()


def get_character_release_date(data, hero_id):
    """获取角色实装日期
    
    Args:
        data: JSON数据字典
        hero_id: 角色ID
    
    Returns:
        str: 实装日期，如果未找到则返回None
    """
    for movie in data["promotion_movie"]["json"]:
        if movie.get("hero_check") == hero_id:
            # 只取日期部分，不要时间
            start_date = movie.get("start_date", "").split()[0]
            if start_date and start_date != "2999-12-31":  # 排除默认日期
                return start_date
    return None


def format_event_content(event_text):
    """格式化事件内容，提取banner信息"""
    lines = event_text.split('\n')
    formatted_lines = []
    banner_path = None
    
    for line in lines:
        if line.startswith("banner："):
            banner_path = line.replace("banner：", "").strip()
        else:
            # 移除事件类型标题行
            if not (line.startswith("【") and line.endswith("】")):
                # 跳过名称行，因为名称已经在event-type标签中显示了
                if not line.startswith("名称："):
                    formatted_lines.append(line)
    
    # 返回一个字典，包含内容和banner路径
    return {
        "content": "<br>".join(formatted_lines),
        "banner": banner_path
    }


def generate_event_html(event, event_type):
    """生成事件HTML，包括内容和banner图片"""
    # 首先调用 format_event_content 获取格式化的内容和banner路径
    event_data = format_event_content(event)
    
    # 确保 event_data 是一个字典
    if isinstance(event_data, dict):
        html = f'<div class="event-content">{event_data["content"]}</div>'
        
        # 如果有banner，添加到HTML中
        if event_data["banner"]:
            # 检查是否是联合作战的sticker图片或恶灵讨伐或邮箱事件的sticker图片
            if (event_data["banner"].startswith("sticker_eas_") or 
                event_data["banner"].startswith("sticker_singleraid_") or 
                event_data["banner"].startswith("sticker_love_")):
                banner_path = str(STICKER_DIR / event_data["banner"])
            else:
                banner_path = str(BANNER_DIR / event_data["banner"])
            html += f'<img class="event-banner" src="{banner_path}" alt="活动Banner">'
        else:
            # 如果没有找到banner图片，显示默认图片
            default_banner_path = str(BANNER_DIR / "banner_No_Image.png")
            html += f'<img class="event-banner" src="{default_banner_path}" alt="默认Banner">'

    return html


def format_date_info(release_date):
    """格式化日期信息"""
    return f"实装日期：{release_date}" if release_date else "实装日期：2023-01-05"


async def generate_timeline_html(month: int, events: list) -> str:
    """生成时间线HTML"""
    # 分离特殊活动、一般活动和邮箱事件
    special_events_with_date = []
    normal_events = []
    mail_events_with_date = []
    
    for event in events:
        if isinstance(event, tuple):
            # 已经带有时间信息的事件
            start_date, event_text = event
            if "【邮箱事件】" in event_text:
                mail_events_with_date.append((start_date, event_text))
            elif "【活动】" not in event_text:
                special_events_with_date.append((start_date, event_text))
        else:
            # 一般活动
            if "【活动】" in event:
                normal_events.append(event)
            elif "【邮箱事件】" in event:
                # 解析时间信息
                lines = event.split('\n')
                for line in lines:
                    if "持续时间：" in line:
                        start_date = datetime.strptime(line.split('至')[0].replace('持续时间：', '').strip(), '%Y-%m-%d')
                        mail_events_with_date.append((start_date, event))
                        break
            else:
                # 解析其他特殊活动时间信息
                lines = event.split('\n')
                for line in lines:
                    if "持续时间：" in line:
                        start_date = datetime.strptime(line.split('至')[0].replace('持续时间：', '').strip(), '%Y-%m-%d')
                        special_events_with_date.append((start_date, event))
                        break
    
    # 按时间排序
    special_events_with_date.sort(key=lambda x: x[0])
    mail_events_with_date.sort(key=lambda x: x[0])
    special_events = [event for _, event in special_events_with_date]
    mail_events = [event for _, event in mail_events_with_date]
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: "Microsoft YaHei", Arial, sans-serif;
                margin: 20px;
                background-color: #ffffff;
            }}
            .timeline-container {{
                max-width: 1600px;
                margin: 0 auto;
                display: flex;
                flex-direction: column;
            }}
            .title {{
                color: #333;
                font-size: 24px;
                margin-bottom: 30px;
                text-align: center;
            }}
            .content-container {{
                display: flex;
                gap: 20px;
                justify-content: center;
            }}
            .column {{
                flex: 1;
                max-width: 520px;  /* 调整每列的最大宽度 */
            }}
            .column-title {{
                color: #333;
                font-size: 18px;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 2px solid #eee;
            }}
            .event {{
                margin-bottom: 20px;
                padding: 15px 15px 15px 20px;
                background-color: #ffffff;
                border-radius: 5px;
                position: relative;
            }}
            .event::before {{
                content: '';
                position: absolute;
                left: 0;
                top: 0;
                bottom: 0;
                width: 4px;
                border-radius: 2px;
            }}
            .event-type {{
                display: inline-block;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 16px;
                font-weight: bold;
                margin-bottom: 10px;
                color: #fff;
            }}
            .event-banner {{
                width: 400px;
                height: 200px;
                object-fit: contain;
                margin: 10px 0;
                border-radius: 4px;
            }}

            /* 主要活动 - 玫瑰红 */
            .event.main::before {{
                background-color: #b61274;
            }}
            .event.main .event-type {{
                background-color: #b61274;
            }}
            
            /* Pickup - 紫色 */
            .event.pickup::before {{
                background-color: #6a1b9a;
            }}
            .event.pickup .event-type {{
                background-color: #6a1b9a;
            }}
            
            /* 恶灵讨伐 - 红色 */
            .event.raid::before {{
                background-color: #c62828;
            }}
            .event.raid .event-type {{
                background-color: #c62828;
            }}
            
            /* 联合作战 - 绿色 */
            .event.eden::before {{
                background-color: #2e7d32;
            }}
            .event.eden .event-type {{
                background-color: #2e7d32;
            }}
            
            /* 世界Boss - 橙色 */
            .event.worldboss::before {{
                background-color: #e65100;
            }}
            .event.worldboss .event-type {{
                background-color: #e65100;
            }}
            
            /* 工会突袭 - 棕色 */
            .event.guildraid::before {{
                background-color: #4e342e;
            }}
            .event.guildraid .event-type {{
                background-color: #4e342e;
            }}
            
            /* 邮箱事件 - 青色 */
            .event.mail::before {{
                background-color: #00838f;
            }}
            .event.mail .event-type {{
                background-color: #00838f;
            }}
            
            /* 一般活动 - 深灰色 */
            .event.calendar::before {{
                background-color: #37474f;
            }}
            .event.calendar .event-type {{
                background-color: #37474f;
            }}
            .event-content {{
                color: #333;
                white-space: pre-wrap;
                font-size: 15px;
                line-height: 1.6;
            }}
        </style>
    </head>
    <body>
        <div class="timeline-container">
            <div class="title">{month}月份活动时间线</div>
            <div class="content-container">
                <div class="column">
                    <div class="column-title">特殊活动</div>
                    {''.join([f'''
                    <div class="event {get_event_type_class(event)}">
                        <div class="event-type">{get_event_name(event)}</div>
                        {generate_event_html(event, "special")}
                    </div>
                    ''' for event in special_events])}
                </div>
                <div class="column">
                    <div class="column-title">一般活动</div>
                    {''.join([f'''
                    <div class="event {get_event_type_class(event)}">
                        <div class="event-type">{get_event_name(event)}</div>
                        {generate_event_html(event, "normal")}
                    </div>
                    ''' for event in normal_events])}
                </div>
                <div class="column">
                    <div class="column-title">邮箱事件</div>
                    {''.join([f'''
                    <div class="event {get_event_type_class(event)}">
                        <div class="event-type">{get_event_name(event)}</div>
                        {generate_event_html(event, "mail")}
                    </div>
                    ''' for event in mail_events])}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html


def get_event_name(event: str) -> str:
    """提取活动名称"""
    lines = event.split('\n')
    
    # 检查是否是邮件事件
    if lines and "【邮箱事件】" in lines[0]:
        # 从名称行提取发送者名称
        for line in lines:
            if line.startswith("名称："):
                name = line.replace("名称：", "").replace("的信件", "").strip()
                return name
    
    # 其他类型的活动
    for line in lines:
        if line.startswith("名称："):
            # 移除名称前缀，清理特殊字符
            name = line.replace("名称：", "").strip()
            # 处理可能的转义字符和换行
            name = name.replace('\r', '').replace('\n', ' ').replace('\\r', '').replace('\\n', ' ')
            # 合并多个空格
            name = ' '.join(name.split())
            return name
    
    return "未知活动"


def get_event_type_class(event: str) -> str:
    """根据事件内容返回对应的CSS类名"""
    if "主要活动" in event:
        return "main"
    elif "活动" in event:
        return "calendar"
    elif "邮箱事件" in event:
        return "mail"
    elif "恶灵讨伐" in event:
        return "raid"
    elif "联合作战" in event:
        return "eden"
    elif "Pickup" in event:
        return "pickup"
    elif "世界Boss" in event:
        return "worldboss"
    elif "工会突袭" in event:
        return "guildraid"
    return "calendar"


def get_potential_value(data: dict, effect_no: int, level: int) -> str:
    """获取潜能数值
    
    Args:
        data: JSON数据字典
        effect_no: 效果编号
        level: 潜能等级
    
    Returns:
        str: 格式化后的数值
    """
    try:
        if str(effect_no).startswith('4'):
            # 从ContentsBuff中获取数值
            for buff in data["contents_buff"]["json"]:
                if buff.get("no") == effect_no:
                    # 遍历所有属性，忽略特定字段
                    ignore_keys = ["no", "battle_power_per", "hero_level_base"]
                    for key, value in buff.items():
                        if key not in ignore_keys and isinstance(value, (int, float)):
                            if value < 1 and key not in ["attack", "defence"]:
                                # 百分比处理
                                return f"{value * 100:.1f}%"
                            else:
                                # 对于attack等属性，如果是小数就保留一位小数
                                if value < 1 and key in ["attack", "defence"]:
                                    return f"{value:.1f}"
                                else:
                                    return str(int(value))
        else:
            # 从SkillBuff中获取数值
            for buff in data["skill_buff"]["json"]:
                if buff.get("no") == effect_no:
                    value = buff.get("value", 0)
                    if value < 1:  # 小于1的按百分比处理
                        return f"{value * 100:.1f}%"
                    else:  # 大于等于1的按整数处理
                        return str(int(value))
    except Exception as e:
        logger.error(f"处理潜能数值时发生错误: {e}, effect_no: {effect_no}, level: {level}")
    return "-"


async def generate_potential_html(data: dict) -> str:
    """生成潜能信息HTML"""
    try:
        # 收集所有潜能信息
        potentials = {}  # {tooltip_sno: [(level, effect_no, option), ...]}
        
        # 从HeroOption中获取所有潜能信息
        for option in data["hero_option"]["json"]:
            tooltip_sno = option.get("tooltip_sno")
            if tooltip_sno:
                if tooltip_sno not in potentials:
                    potentials[tooltip_sno] = []
                potentials[tooltip_sno].append((
                    option.get("level", 0),
                    option.get("effect_no1", 0),
                    option.get("option", 0)
                ))
        
        # 获取潜能名称
        potential_names = {}  # {tooltip_sno: name}
        for string in data["string_ui"]["json"]:
            if string.get("no") in potentials:
                potential_names[string["no"]] = string.get("zh_tw", "未知潜能")
        
        # 生成HTML
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {
                    font-family: "Microsoft YaHei", Arial, sans-serif;
                    margin: 20px;
                    background-color: #ffffff;
                }
                table {
                    border-collapse: collapse;
                    width: 100%;
                    background-color: #ffffff;
                }
                th, td {
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: center;
                }
                th {
                    background-color: #f5f5f5;
                }
                tr:nth-child(even) {
                    background-color: #f9f9f9;
                }
                .title {
                    font-size: 24px;
                    margin-bottom: 20px;
                    text-align: center;
                }
                .potential-name {
                    text-align: left;
                    font-weight: bold;
                }
            </style>
        </head>
        <body>
            <div class="title">潜能数值一览</div>
            <table>
                <tr>
                    <th>潜能名称</th>
        """
        
        # 添加等级列
        max_level = max(level for tooltip_sno in potentials for level, _, _ in potentials[tooltip_sno])
        for level in range(1, max_level + 1):
            html += f"<th>Lv.{level}</th>"
        
        html += "</tr>"
        
        # 添加潜能数据
        for tooltip_sno, name in sorted(potential_names.items(), key=lambda x: x[0]):  # 修改排序键为x[0]
            html += f"<tr><td class='potential-name'>{name}</td>"
            
            # 获取该潜能的所有等级数据
            level_data = {level: (effect_no, option) for level, effect_no, option in potentials[tooltip_sno]}
            
            # 填充每个等级的数值
            for level in range(1, max_level + 1):
                if level in level_data:
                    effect_no, option = level_data[level]
                    value = get_potential_value(data, effect_no, level)
                    html += f"<td>{value}</td>"
                else:
                    html += "<td>-</td>"
            
            html += "</tr>"
        
        html += """
            </table>
        </body>
        </html>
        """
        
        return html
    except Exception as e:
        logger.error(f"生成潜能HTML时发生错误: {e}")
        raise


def get_signature_stats(data, level_group):
    """获取遗物最高等级总属性
    
    Args:
        data: JSON数据字典
        level_group: 遗物等级组ID
    
    Returns:
        dict: 遗物属性统计
    """
    # 找到最高等级的属性数据
    max_level_data = None
    max_level = 0
    
    # 先遍历一遍找出这个遗物的最大等级（40或45）
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
    
    # 格式化输出文本
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
    
    return formatted_stats, max_level


def get_signature_info(data, hero_id):
    """获取遗物信息
    
    Args:
        data: JSON数据字典
        hero_id: 英雄ID
    
    Returns:
        tuple: (遗物名称, 遗物技能名称, 遗物简介, 遗物技能描述列表)
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
    
    # 在Signature.json中查找对应英雄的遗物
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
                        # 处理数值标签
                        desc_tw = process_skill_description(data, desc_tw)
                        desc_cn = process_skill_description(data, desc_cn)
                        desc_kr = process_skill_description(data, desc_kr)
                        desc_en = process_skill_description(data, desc_en)
                        skill_descriptions.append((desc_tw, desc_cn, desc_kr, desc_en))  # 将四种语言的描述作为元组存储
                        break
        
    # 修改返回值，添加图标路径
    if signature_data:
        level_group = signature_data.get("level_group")
        signature_stats = get_signature_stats(data, level_group) if level_group else []
        
        return (signature_name_zh_tw, signature_name_zh_cn, signature_name_kr, signature_name_en, signature_title_zh_tw, signature_title_zh_cn, signature_title_kr, signature_title_en, 
                signature_desc_zh_tw, signature_desc_zh_cn, signature_desc_kr, signature_desc_en, skill_descriptions, signature_stats, signature_bg_path) 
    
    # 如果没有找到遗物数据，返回空值
    return "", "", "", "",\
            "", "", "", "",\
            "", "", "", "", [], [], ""


def get_skill_type(data, type_no):
    """获取技能类型名称
    
    Args:
        data: JSON数据字典
        type_no: 技能类型编号
    
    Returns:
        tuple: (繁中类型名称, 简中类型名称, 韩语类型名称)
    """
    for string in data["string_system"]["json"]:
        if string["no"] == type_no:
            return string.get("zh_tw", "未知类型"), string.get("zh_cn", "未知类型"), string.get("kr", "알수없는유형"), string.get("en", "Unknown type")
    return "未知类型", "未知类型", "알수없는유형", "Unknown type"


def get_string_character(data, sno):
    """从StringCharacter.json中获取文本"""
    for string in data["string_character"]["json"]:
        if string["no"] == sno:
            return string.get("zh_tw", ""), string.get("zh_cn", ""), string.get("kr", ""), string.get("en", "")
    return "", "", "", ""


def get_system_string(data, sno):
    for string in data["string_system"]["json"]:
        if string["no"] == sno:
            return string.get("zh_tw", ""), string.get("zh_cn", ""), string.get("kr", ""), string.get("en", "")
    return "", "", "", ""


def get_hero_name(data, hero_no):
    """获取角色名称"""
    # 在Hero.json中查找角色
    for hero in data["hero"]["json"]:
        if hero["no"] == hero_no:
            name_sno = hero.get("name_sno")
            if name_sno:
                # 在StringCharacter.json中查找名称
                for char in data["string_character"]["json"]:
                    if char["no"] == name_sno:
                        return char.get("zh_tw", ""), char.get("zh_cn", ""), char.get("kr", ""), char.get("en", "")
    return "", "", "", ""


def get_grade_name(data, grade_no):
    """获取阶级名称"""
    for system in data["string_system"]["json"]:
        if system["no"] == grade_no:
            return system.get("zh_tw", ""), system.get("zh_cn", ""), system.get("kr", ""), system.get("en", "")
    return "", "", "", ""


def get_formation_type(formation_no):
    """获取阵型类型"""
    return FORMATION_TYPE_MAPPING.get(formation_no, "")


def get_hero_name_by_id(data, hero_id):
    """通过hero_id获取角色名称"""
    # 在Hero.json中查找角色
    for hero in data["hero"]["json"]:
        if hero["no"] == hero_id:  # 使用no而不是hero_id
            name_sno = hero.get("name_sno")
            if name_sno:
                # 在StringCharacter.json中查找名称
                return get_string_character(data, name_sno)
    return "未知角色", "未知角色", "알수없는캐릭터", "Unknown character"


def get_story_info(data, hero_id):
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


def calculate_normal_ending_choices(all_episodes_choices, bad_threshold, normal_threshold):
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


def format_story_info(episode_info, endings, is_test=False):
    """格式化好感故事攻略"""
    # 创建三个结局的信息列表
    good_end = ["好结局攻略："]
    normal_end = ["一般结局攻略："]
    bad_end = ["坏结局攻略："]
    
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
                    "text": f"（{choice['choice_group']}）{clean_tags(choice['kr_text' if is_test else 'zh_tw_text'])}({affinity_str})",
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
            "title": ep['kr_title' if is_test else 'zh_tw_title'],
            "choices": all_choices
        })
        
        # 为每个结局添加章节标题
        title = ep['kr_title'] if is_test else ep['zh_tw_title']
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
                        for c in current_group:
                            if c["affinity"] == min_affinity:
                                bad_choices.append(c["text"])
                    else:
                        # 如果没有负数好感度，查找0好感度的选项
                        zero_choices = [c for c in current_group if c["affinity"] == 0]
                        if zero_choices:
                            for c in zero_choices:
                                bad_choices.append(c["text"])
                        else:
                            # 如果既没有负数也没有0，则选择最小的正数好感度
                            min_positive = min((c["affinity"] for c in current_group))
                            for c in current_group:
                                if c["affinity"] == min_positive:
                                    bad_choices.append(c["text"])
                
                # 开始新的一组
                current_index = choice["talk_index"]
                current_group = [choice]
            else:
                current_group.append(choice)
        
        # 处理最后一组
        if current_group:
            min_affinity = min((c["affinity"] for c in current_group))
            if min_affinity < 0:
                for c in current_group:
                    if c["affinity"] == min_affinity:
                        bad_choices.append(c["text"])
            else:
                zero_choices = [c for c in current_group if c["affinity"] == 0]
                if zero_choices:
                    for c in zero_choices:
                        bad_choices.append(c["text"])
                else:
                    min_positive = min((c["affinity"] for c in current_group))
                    for c in current_group:
                        if c["affinity"] == min_positive:
                            bad_choices.append(c["text"])
        
        bad_end.extend(bad_choices)

    # 计算一般结局的选项
    normal_choices_by_episode = calculate_normal_ending_choices(all_episodes_choices, bad_threshold, normal_threshold)
    
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


def find_similar_names(query, alias_map):
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


def get_character_keywords(data: dict, hero_id: int, is_test: bool = False) -> str:
    """获取角色关键字信息"""
    # 获取所有关键字
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
                points = get_keyword_points(data, keyword_type)
                grade_sno = keyword_info.get("keyword_grade")
                grade_index = 0 # 一般
                if grade_sno == 110012:  # 稀有
                    grade_index = 1
                elif grade_sno == 110014:  # 史诗
                    grade_index = 2
                favor_point = points[grade_index]
                    
                trip_keywords.append({
                    "name": get_keyword_name(data, keyword_info.get("keyword_string"), is_test),
                    "grade": get_keyword_grade(data, grade_sno, is_test),
                    "type": keyword_type,
                    "favor_point": favor_point,
                    "source": get_keyword_source(
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
            if location := get_keyword_location(data, keyword.get("keyword_get_details"), is_test):
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
            if location := get_keyword_location(data, keyword.get("keyword_get_details"), is_test):
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
            if location := get_keyword_location(data, keyword.get("keyword_get_details"), is_test):
                msg += f"\n  地点：{location}"
            if keyword["source"]:
                msg += f"\n  获取条件：{keyword['source']}"
            keyword_msgs.append(msg)
    
    return "\n".join(keyword_msgs)


def sync_aliases(file1: Path, file2: Path) -> None:
    """同步两个yaml文件中的别名，将别名较多的文件覆盖别名较少的文件
    
    Args:
        file1: 第一个yaml文件路径
        file2: 第二个yaml文件路径
    """
    try:
        with open(file1, "r", encoding="utf-8") as f:
            data1 = yaml.safe_load(f)
        with open(file2, "r", encoding="utf-8") as f:
            data2 = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"读取yaml文件时出错: {e}")
        return

    if not data1 or not data2 or "names" not in data1 or "names" not in data2:
        return

    # 创建hero_id到别名的映射
    aliases1 = {hero["hero_id"]: set(hero.get("aliases", [])) for hero in data1["names"] if "hero_id" in hero}
    aliases2 = {hero["hero_id"]: set(hero.get("aliases", [])) for hero in data2["names"] if "hero_id" in hero}

    # 找出需要同步的英雄
    for hero_id in set(aliases1.keys()) & set(aliases2.keys()):
        if len(aliases1[hero_id]) != len(aliases2[hero_id]):
            # 如果别名数量不同，使用数量较多的那个
            if len(aliases1[hero_id]) > len(aliases2[hero_id]):
                # 更新file2中的别名
                for hero in data2["names"]:
                    if hero.get("hero_id") == hero_id:
                        hero["aliases"] = list(aliases1[hero_id])
                        break
            else:
                # 更新file1中的别名
                for hero in data1["names"]:
                    if hero.get("hero_id") == hero_id:
                        hero["aliases"] = list(aliases2[hero_id])
                        break

    # 保存更新后的文件
    class CustomDumper(yaml.SafeDumper):
        def increase_indent(self, flow=False, indentless=False):
            return super().increase_indent(flow, False)

        def represent_scalar(self, tag, value, style=None):
            if isinstance(value, str):
                style = None
            return super().represent_scalar(tag, value, style)

        def represent_sequence(self, tag, sequence, flow_style=None):
            if len(sequence) > 0 and isinstance(sequence[0], str):
                flow_style = True
            return super().represent_sequence(tag, sequence, flow_style=flow_style)

    try:
        # 保持原有的缩进格式
        with open(file1, "w", encoding="utf-8") as f:
            yaml.dump(data1, f, 
                    Dumper=CustomDumper,
                    allow_unicode=True, 
                    sort_keys=False,
                    default_flow_style=False,
                    indent=2)
        with open(file2, "w", encoding="utf-8") as f:
            yaml.dump(data2, f, 
                    Dumper=CustomDumper,
                    allow_unicode=True, 
                    sort_keys=False,
                    default_flow_style=False,
                    indent=2)
    except Exception as e:
        logger.error(f"同步出错: {e}")

def generate_aliases() -> None:
    """生成别名文件"""
    live_json_path = Path(plugin_config.eversoul_live_path)
    review_json_path = Path(plugin_config.eversoul_review_path)
    
    try:
        live_hero_aliases = DATA_DIR / "live_hero_aliases.yaml"
        live_monster_aliases = DATA_DIR / "live_monster_aliases.yaml"
        live_hero_count, live_monster_count = process_json_files(live_json_path, live_hero_aliases, live_monster_aliases)
        if live_hero_count > 0 or live_monster_count > 0:
            logger.info(f"Live版本别名生成完成！总共生成 {live_hero_count} 个英雄条目, {live_monster_count} 个怪物条目")
        else:
            logger.info("请检查Live版本JSON文件路径配置是否正确")
    except Exception as e:
        logger.error(f"处理live别名文件时出错: {e}")
    
    try:
        review_hero_aliases = DATA_DIR / "review_hero_aliases.yaml"
        review_monster_aliases = DATA_DIR / "review_monster_aliases.yaml"
        review_hero_count, review_monster_count = process_json_files(review_json_path, review_hero_aliases, review_monster_aliases)
        if review_hero_count > 0 or review_monster_count > 0:
            logger.info(f"Review版本别名生成完成！总共生成 {review_hero_count} 个英雄条目, {review_monster_count} 个怪物条目")
        else:
            logger.info("请检查Review版本JSON文件路径配置是否正确")
    except Exception as e:
        logger.error(f"处理review别名文件时出错: {e}")

    try:
        sync_aliases(live_hero_aliases, review_hero_aliases)
        sync_aliases(live_monster_aliases, review_monster_aliases)
    except Exception as e:
        logger.error(f"同步别名时出错: {e}")


def process_json_files(json_path: Path, hero_output_file: Path, monster_output_file: Path) -> Tuple[int, int]:
    """处理JSON文件生成别名文件
    
    Args:
        json_path: JSON文件目录
        hero_output_file: 英雄别名输出文件
        monster_output_file: 怪物别名输出文件
    
    Returns:
        Tuple[int, int]: 生成的英雄数量和怪物数量
    """
    if not json_path.exists():
        logger.error(f"JSON路径不存在: {json_path}")
        return 0, 0
    
    try:
        with open(json_path / "Hero.json", "r", encoding="utf-8") as f:
            hero_data = json.load(f)
        
        with open(json_path / "StringCharacter.json", "r", encoding="utf-8") as f:
            string_char_data = json.load(f)
    except Exception as e:
        logger.error(f"加载JSON文件失败: {e}")
        return 0, 0
    
    hero_names = {}
    for string in string_char_data["json"]:
        if "no" in string:
            if string["no"] not in hero_names:
                hero_names[string["no"]] = {
                    "zh_tw": string.get("zh_tw", ""),
                    "zh_cn": string.get("zh_cn", ""),
                    "kr": string.get("kr", ""),
                    "en": string.get("en", ""),
                    "ja": string.get("ja", "")
                }

    seen_hero_ids = set()
    
    existing_data = {}
    if hero_output_file.exists():
        try:
            with open(hero_output_file, "r", encoding="utf-8") as f:
                existing_data = yaml.safe_load(f)
    
            existing_aliases = {}
            existing_zh_cn_names = {}
            if existing_data and "names" in existing_data:
                for hero in existing_data["names"]:
                    if "hero_id" in hero:
                        hero_id = hero["hero_id"]
                        if "aliases" in hero:
                            existing_aliases[hero_id] = hero.get("aliases", [])
                        if "zh_cn_name" in hero and hero["zh_cn_name"]:
                            existing_zh_cn_names[hero_id] = hero["zh_cn_name"]
        except Exception as e:
            logger.error(f"读取现有别名文件时出错: {e}")
            existing_aliases = {}
            existing_zh_cn_names = {}
    else:
        existing_aliases = {}
        existing_zh_cn_names = {}
    
    name_to_min_id = {}
    
    for hero in hero_data["json"]:
        if ("hero_id" in hero and 
            "name_sno" in hero and 
            hero["hero_id"] >= 7000):
            
            name_data = hero_names.get(hero["name_sno"], {
                "zh_tw": "",
                "zh_cn": "",
                "kr": "",
                "en": "",
                "ja": ""
            })
            current_id = hero["hero_id"]
            
            zh_tw_name = name_data["zh_tw"]
            if zh_tw_name in name_to_min_id:
                name_to_min_id[zh_tw_name] = min(name_to_min_id[zh_tw_name], current_id)
            else:
                name_to_min_id[zh_tw_name] = current_id

    new_data = {"names": []}
    monster_data = {"names": []}
    monster_name_count = {}
    
    for hero in hero_data["json"]:
        if ("hero_id" in hero and 
            "name_sno" in hero and 
            hero["hero_id"] not in seen_hero_ids):
            
            hero_id = hero["hero_id"]
            name_data = hero_names.get(hero["name_sno"], {
                "zh_tw": "",
                "zh_cn": "",
                "kr": "",
                "en": "",
                "ja": ""
            })
            zh_cn_name = name_data["zh_cn"]
            if not zh_cn_name and hero_id in existing_zh_cn_names:
                zh_cn_name = existing_zh_cn_names[hero_id]
            
            hero_entry = {
                "zh_tw_name": name_data["zh_tw"],
                "zh_cn_name": zh_cn_name,
                "kr_name": name_data["kr"],
                "en_name": name_data["en"],
                "ja_name": name_data["ja"],
                "aliases": existing_aliases.get(hero_id, []), 
                "hero_id": hero_id
            }
            
            if hero_id >= 7000:
                monster_name_count[name_data["zh_tw"]] = 0
                monster_data["names"].append(hero_entry)
            else:
                new_data["names"].append(hero_entry)
            
            seen_hero_ids.add(hero_id)
    
    class CustomDumper(yaml.SafeDumper):
        def increase_indent(self, flow=False, indentless=False):
            return super().increase_indent(flow, False)

        def represent_scalar(self, tag, value, style=None):
            if isinstance(value, str):
                style = None
            return super().represent_scalar(tag, value, style)

        def represent_sequence(self, tag, sequence, flow_style=None):
            """对于字符串列表使用flow风格（单行）"""
            if len(sequence) > 0 and isinstance(sequence[0], str):
                flow_style = True
            return super().represent_sequence(tag, sequence, flow_style=flow_style)
    
    hero_output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(hero_output_file, "w", encoding="utf-8") as f:
        yaml.dump(new_data, f, 
                Dumper=CustomDumper,
                allow_unicode=True, 
                sort_keys=False,
                default_flow_style=False,
                indent=2)
    
    with open(monster_output_file, "w", encoding="utf-8") as f:
        yaml.dump(monster_data, f, 
                Dumper=CustomDumper,
                allow_unicode=True, 
                sort_keys=False,
                default_flow_style=False,
                indent=2)
    
    return len(new_data['names']), len(monster_data['names']) 


def get_arbeit_traits(data, hero_id):
    """获取角色的打工属性信息
    
    Args:
        data: JSON数据字典
        hero_id: 角色ID
    
    Returns:
        tuple: (初始属性文本, 满级属性文本)
    """
    # 收集所有相关等级的数据
    level_data = []
    for level in data["arbeit_fairy_level"]["json"]:
        if level.get("hero_no") == hero_id:
            level_data.append(level)
    
    if not level_data:
        return "???", "???"
    
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
    
    return initial_text, max_text


def get_preferred_gifts(data, hero_id):
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
    
    return "、".join(gift_items) if gift_items else "???"