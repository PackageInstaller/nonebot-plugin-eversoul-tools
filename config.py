from enum import IntEnum
from matplotlib.font_manager import FontProperties
from pathlib import Path
from pydantic import BaseModel, model_validator
from typing import ClassVar
from nonebot import get_driver, get_plugin_config
from nonebot.log import logger
import json
from typing import Dict


class LazyJsonData:
    """
    懒加载JSON数据的容器类
    只有在访问具体表时才会加载对应的JSON文件
    """

    def __init__(self, json_path: Path, command_name: str = "unknown"):
        self._json_path = json_path
        self._cache: Dict[str, dict] = {}
        self._command_name = command_name  # 记录调用的命令名

    def __getitem__(self, key: str) -> dict:
        """按需加载并返回JSON数据"""
        if key not in self._cache:
            self._load_table(key)
        return self._cache[key]

    def __contains__(self, key: str) -> bool:
        """检查键是否存在于映射表中"""
        return key in JSON_FILE_MAPPING

    def get(self, key: str, default=None):
        """获取数据，如果不存在则返回默认值"""
        if key not in JSON_FILE_MAPPING:
            return default
        try:
            return self[key]
        except Exception:
            return default

    def _load_table(self, key: str):
        """加载单个JSON表"""
        if key not in JSON_FILE_MAPPING:
            logger.warning(f"未知的JSON表: {key}")
            self._cache[key] = {"json": []}
            return

        filename = JSON_FILE_MAPPING[key]
        file_path = self._json_path / filename

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._cache[key] = data
        except FileNotFoundError:
            logger.warning(f"JSON文件不存在: {filename}")
            self._cache[key] = {"json": []}
        except Exception as e:
            logger.error(f"加载JSON文件出错: {filename}, 错误: {e}")
            self._cache[key] = {"json": []}

    def preload(self, keys: list):
        """预加载指定的表"""
        for key in keys:
            if key not in self._cache:
                self._load_table(key)


class Config(BaseModel):
    # Eversoul相关配置项
    eversoul_auto_update: bool = True  # 是否自动更新数据表


plugin_config = get_plugin_config(Config)

# 传送门类型
GATE_TYPE_MAPPING = {"自由": 4, "人类": 5, "野兽": 6, "妖精": 7, "不死": 8}

# 装备的数值整数属性映射
TIER_INTEGER_STAT_MAPPING = {"max_hp", "attack", "defence", "hit", "dodge"}

# 灵魂链接的数值整数属性映射
SOULLINK_INTEGER_STAT_MAPPING = {"attack", "defence", "hp", "hit", "dodge"}

# 属性限制映射，rate代表这是百分比数值的意思，但是字段是一样的
STAT_NAME_MAPPING = {
    "attack_rate": "攻击力",
    "attack": "攻击力",
    "defence_rate": "防御力",
    "defence": "防御力",
    "max_hp_rate": "体力",
    "max_hp": "体力",
    "hp_rate": "体力",
    "hp": "体力",
    "critical_rate": "暴击率",
    "critical_power": "暴击威力",
    "hit": "命中",
    "dodge": "闪避",
    "physical_resist": "物理抵抗",
    "magic_resist": "魔法抵抗",
    "life_leech": "噬血",
    "attack_speed": "攻击速度",
}

# 属性限制映射
STAT_TYPE_MAPPING = {"智力": 110044, "敏捷": 110043, "力量": 110042, "共用": 110041}


# 组合效果映射
EFFECT_TYPE_MAPPING = {
    "攻击力": 14101,
    "防御力": 14102,
    "体力": 14103,
    "暴击率": 14104,
    "暴击威力": 14105,
    "回避": 14107,
    "加速": 14111,
}

# 打工属性名称映射
TRAIT_NAME_MAPPING = {
    "conversation": "口才",
    "culture": "教养",
    "courage": "胆量",
    "knowledge": "知识",
    "guts": "毅力",
    "handicraft": "才艺",
}

# 阵型类型映射
FORMATION_TYPE_MAPPING = {1: "基本阵型", 2: "狙击型", 3: "防守阵型", 4: "突击型"}

# 角色名称映射
HERO_NAME_MAPPING = {
    "Naiah": "Nyah",
    "Catherine (Radiance)": "CatherineBrave",
    "Haru": "Mia",
    "Claire": "Beatrice",
    "Cherrie": "Catarina",
    "Rose (Prominence)": "RoseCrimson",
    "Sakuyo (Inferno)": "SakuyoShin",
    "Garnet": "Olivia",
    "Renee": "Leah",
    "Violette": "Amelia",
    "Bryce": "Blyce",
    "Mephistopheles (Dawn)": "MephistoDawn",
    "CherrieRomanRaid": "CherrieRoman",
}

# 潜能buff类型
HERO_OPTION_BUFF_MAPPING = {
    "attack": 0,
    "attack_rate": 1,
    "defence": 2,
    "defence_rate": 3,
    "hp": 4,
    "hp_rate": 5,
    "critical_rate": 6,
    "critical_power": 7,
    "hit": 8,
    "dodge": 9,
    "physical_resist": 10,
    "magic_resist": 11,
    "life_leech": 12,
    "attack_speed": 13,
    "mana_crystal": 14,
    "mana_dust": 15,
    "gold": 16,
    "attack_per_level": 17,
    "defence_per_level": 18,
    "hp_per_level": 19,
    "critical_resist": 801,
    "life_leech_buff": 1001,
    "human_type_damage": 1802,
    "furry_type_damage": 1803,
    "undead_type_damage": 1804,
    "elf_type_damage": 1805,
    "angel_type_damage": 1806,
    "demon_type_damage": 1807,
    "chaos_type_damage": 1808,
}

# 潜能buff类型的反向映射
HERO_OPTION_BUFF_REVERSE_MAPPING = {v: k for k, v in HERO_OPTION_BUFF_MAPPING.items()}

# 礼包类型映射
PACKAGE_TYPE_MAPPING = {
    "barrier": "通关礼包",
    "stage": "主线礼包",
    "tower": "起源之塔礼包",
    "grade_eternal": "角色升阶礼包",
}

SERVER_APP_ID_MAPPING = {
    "asia": 743491,  # 亚服
    "kr": 743487,  # 韩服
    "en": 750066,  # 欧美服
    "cn": 743493,  # 国服
    "jp": 981921,  # 日服
}

SERVER_NAME_MAPPING = {
    "asia": "亚服",
    "kr": "韩服",
    "en": "欧美服",
    "cn": "国服",
    "jp": "日服",
}

# 恶灵讨伐护盾削减系数映射
SINGLE_RAID_GROGGY_TYPE_MAPPING = {
    201: "暈眩",
    202: "睡眠",
    206: "沉默",
    207: "魅惑",
    # 212: "無力",
    215: "束縛",
}

# 恶灵讨伐护盾削减系数映射，适用于国服旧版
SINGLE_RAID_GROGGY_REDUCE_MAPPING = [1, 2, 1, 1, 1, 3, 4]

# app_id到服务器名称的反向映射
SERVER_NAME_REVERSE_MAPPING = {v: k for k, v in SERVER_APP_ID_MAPPING.items()}

# JSON文件名映射表
JSON_FILE_MAPPING = {
    "hero": "Hero.json",  # 角色
    "hero_option": "HeroOption.json",  # 角色潜能
    "hero_gift": "HeroGift.json",  # 角色喜好礼物
    "hero_desc": "HeroDesc.json",  # 角色描述
    "hero_level_grade": "HeroLevelGrade.json",  # 角色等级加成率
    "hero_grade": "HeroGrade.json",  # 角色品质
    "string_character": "StringCharacter.json",  # 角色文本
    "string_system": "StringSystem.json",  # 系统文本
    "skill": "Skill.json",  # 技能
    "string_skill": "StringSkill.json",  # 技能文本
    "skill_code": "SkillCode.json",  # 技能代码
    "skill_buff": "SkillBuff.json",  # 技能效果
    "skill_icon": "SkillIcon.json",  # 技能图标
    "skill_pattern": "SkillPattern.json",  # 技能释放顺序
    "signature": "Signature.json",  # 遗物
    "signature_level": "SignatureLevel.json",  # 遗物等级
    "signature_grade": "SignatureGrade.json",  # 遗物品质
    "string_evertalk": "StringEverTalk.json",  # 聊天文本
    "story_info": "StoryInfo.json",  # 故事信息
    "talk": "Talk.json",  # 对话
    "string_talk": "StringTalk.json",  # 对话文本
    "item_costume": "ItemCostume.json",  # 物品信息
    "item": "Item.json",  # 物品
    "item_stat": "ItemStat.json",  # 物品属性
    "string_item": "StringItem.json",  # 物品文本
    "illust": "Illust.json",  # 插画
    "item_drop_group": "ItemDropGroup.json",  # 掉落组
    "item_set_effect": "ItemSetEffect.json",  # 套装效果
    "stage": "Stage.json",  # 关卡
    "stage_battle": "StageBattle.json",  # 关卡战斗
    "formation": "Formation.json",  # 队伍
    "message_mail": "MessageMail.json",  # 邮件
    "level": "Level.json",  # 等级
    "love_level": "LoveLevel.json",  # 好感等级
    "ark_enhance": "ArkEnhance.json",  # 方舟强化
    "ark_overclock": "ArkOverClock.json",  # 超频
    "promotion_movie": "PromotionMovie.json",  # 宣传片
    "localization_schedule": "LocalizationSchedule.json",  # 活动日历
    "event_calender": "EventCalender.json",  # 活动日历
    "event_info": "EventInfo.json",  # 活动信息
    "event_story": "EventStory.json",  # 活动剧情
    "string_ui": "StringUI.json",  # UI文本
    "eden_alliance": "EdenAlliance.json",  # 联合作战
    "stage_equip": "StageEquip.json",  # 关卡装备
    "string_stage": "StringStage.json",  # 关卡文本
    "cash_shop_item": "CashShopItem.json",  # 商店物品
    "string_cashshop": "StringCashshop.json",  # 商店文本
    "barrier": "Barrier.json",  # 传送门相关信息
    "trip_hero": "TripHero.json",  # 角色关键字
    "trip_keyword": "TripKeyword.json",  # 角色关键字
    "key_values": "KeyValues.json",  # 一些数值定义
    "town_location": "TownLocation.json",  # 地点
    "town_object": "TownObjet.json",  # 专属领地物品
    "string_town": "StringTown.json",  # 地点文本
    "town_lost_item": "TownLostItem.json",  # 遗失物品
    "town_buff": "TownBuff.json",  # 专属领地物品buff
    "thumbnail": "Thumbnail.json",  # 缩略图
    "arbeit_fairy_level": "ArbeitFairyLevel.json",  # 打工等级
    "tower": "Tower.json",  # 起源塔
    "contents_buff": "ContentsBuff.json",  # buff数值内容
    "battle_buff": "BattleBuff.json",  # 战斗buff
    "world_raid_partner_buff": "WorldRaidPartnerBuff.json",  # 支援伙伴buff
    "arbeit_choice": "ArbeitChoice.json",  # 专属物品任务选择
    "arbeit_list": "ArbeitList.json",  # 专属物品任务列表
    "evertalk_desc": "EverTalkDesc.json",  # everphton聊天相关，拿插图
    "soullink": "Soullink.json",  # 灵魂链接文本相关
    "soullink_collection": "SoullinkCollection.json",  # 灵魂链接数值相关
    "gacha": "Gacha.json",  # 抽卡相关
    "guild_raid": "GuildRaid.json",  # 工会讨伐boss相关
    "guild_raid_affix": "GuildRaidAffix.json",  # 工会讨伐boss词条相关
    "single_raid_boss": "SingleRaidBoss.json",  # 恶灵讨伐BOSS
    "single_raid": "SingleRaid.json",  # 恶灵讨伐
    "single_raid_boss_level_grade": "SingleRaidBossLevelGrade.json",  # 恶灵讨伐BOSS等级
    "single_raid_schedule": "SingleRaidSchedule.json",  # 恶灵讨伐日程(记录了赛季，以及日程键值)
    "single_raid_season": "SingleRaidSeason.json",  # 恶灵讨伐赛季
    "single_raid_boss_interaction_detail": "SingleRaidBossInteractionDetail.json",  # 恶灵讨伐开场白角色
    "single_raid_boss_groggy_trigger": "SingleRaidBossGroggyTrigger.json",  # 恶灵讨伐护盾削减系数
    "single_raid_boss_groggy_condition": "SingleRaidBossGroggyCondition.json",  # 恶灵讨伐各类CCBuff削减系数定义
    "single_raid_season_gimmick": "SingleRaidSeasonGimmick.json",  # 恶灵讨伐特殊之人
    "world_raid_boss": "WorldRaidBoss.json",  # 世界讨伐boss相关
    "zodiac": "Zodiac.json",  # 星座
}

# 资源路径
RESOURCE_DIR = Path(__file__).parent / "resource"
# 添加数据源配置文件路径
DATA_DIR = Path(__file__).parent / "data"
CONFIG_DIR = DATA_DIR / "config"
DATABASE_DIR = DATA_DIR / "database"
COUPON_DIR = DATA_DIR / "coupon"
COUPON_YAML_PATH = COUPON_DIR / "coupons.yaml"
DATA_SOURCE_CONFIG = CONFIG_DIR / "data_source_config.yaml"
HELP_CONFIG = CONFIG_DIR / "help_commands.yaml"

# 数据表路径（从插件目录下的data/table获取）
TABLE_DIR = DATA_DIR / "table"
GL_LIVE_TABLE_DIR = TABLE_DIR / "global" / "live"
GL_REVIEW_TABLE_DIR = TABLE_DIR / "global" / "review"
CN_LIVE_TABLE_DIR = TABLE_DIR / "cn" / "live"
CN_REVIEW_TABLE_DIR = TABLE_DIR / "cn" / "review"
JP_LIVE_TABLE_DIR = TABLE_DIR / "jp" / "live"
JP_REVIEW_TABLE_DIR = TABLE_DIR / "jp" / "review"

# Schema路径
SCHEMA_DIR = RESOURCE_DIR / "schema"
GL_SCHEMA_DIR = SCHEMA_DIR / "global"
CN_SCHEMA_DIR = SCHEMA_DIR / "cn"
JP_SCHEMA_DIR = SCHEMA_DIR / "jp"

# 默认配置
DEFAULT_CONFIG = {
    "server": "cn",  # 服务器: global(国际服) 或 cn(国服)
    "type": "live",  # 数据类型: live 或 review
    "json_path": str(CN_LIVE_TABLE_DIR),
    "hero_alias_file": CONFIG_DIR / "live_hero_aliases.yaml",
}

CURRENT_DATA_SOURCE = {
    "default": {
        "server": "cn",
        "type": "live",
        "json_path": str(CN_LIVE_TABLE_DIR),
        "hero_alias_file": CONFIG_DIR / "live_hero_aliases.yaml",
    }
}

# 字体路径
FONT_DIR = RESOURCE_DIR / "font" / "Sarasa-Regular.ttc"
CUSTOM_FONT = FontProperties(fname=FONT_DIR)

CG_DIR = RESOURCE_DIR / "image" / "cg"
EVERTALK_DIR = RESOURCE_DIR / "image" / "evertalk"
SOUL_DIR = RESOURCE_DIR / "image" / "soul"
ICON_DIR = RESOURCE_DIR / "image" / "icon"
TIER_DIR = RESOURCE_DIR / "image" / "tier"
TOWN_DIR = RESOURCE_DIR / "image" / "town"
BANNER_DIR = RESOURCE_DIR / "image" / "banner"
STICKER_DIR = RESOURCE_DIR / "image" / "sticker"
