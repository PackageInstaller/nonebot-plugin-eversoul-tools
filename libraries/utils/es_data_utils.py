"""
数据加载与配置管理模块
"""
import json
import yaml
from pathlib import Path
from typing import Tuple
from nonebot.log import logger
from ...config import *


driver = get_driver()

@driver.on_startup
async def init_plugin():
    """插件启动时初始化"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    if DATA_SOURCE_CONFIG.exists():
        try:
            with open(DATA_SOURCE_CONFIG, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            if config:
                new_config = {}
                for k, v in config.items():
                    new_config[str(k)] = v
                
                with open(DATA_SOURCE_CONFIG, "w", encoding="utf-8") as f:
                    yaml.dump(new_config, f, allow_unicode=True)
            else:
                logger.warning("配置文件存在但内容为空")
        except Exception as e:
            logger.error(f"初始化配置文件出错: {e}")
    else:
        logger.info("配置文件不存在，将创建默认配置")
    load_data_source_config()
    try:
        generate_aliases()
    except Exception as e:
        logger.error(f"生成别名文件时出错: {e}")


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

    # 找出需要同步的角色
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
            logger.info(f"Live版本别名生成完成！总共生成 {live_hero_count} 个角色条目, {live_monster_count} 个怪物条目")
        else:
            logger.info("请检查Live版本JSON文件路径配置是否正确")
    except Exception as e:
        logger.error(f"处理live别名文件时出错: {e}")
    
    try:
        review_hero_aliases = DATA_DIR / "review_hero_aliases.yaml"
        review_monster_aliases = DATA_DIR / "review_monster_aliases.yaml"
        review_hero_count, review_monster_count = process_json_files(review_json_path, review_hero_aliases, review_monster_aliases)
        if review_hero_count > 0 or review_monster_count > 0:
            logger.info(f"Review版本别名生成完成！总共生成 {review_hero_count} 个角色条目, {review_monster_count} 个怪物条目")
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
        hero_output_file: 角色别名输出文件
        monster_output_file: 怪物别名输出文件
    
    Returns:
        Tuple[int, int]: 生成的角色数量和怪物数量
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
        "single_raid_boss": "SingleRaidBoss.json", # 恶灵讨伐BOSS
        "single_raid": "SingleRaid.json", # 恶灵讨伐
        "single_raid_boss_level_grade": "SingleRaidBossLevelGrade.json", # 恶灵讨伐BOSS等级
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