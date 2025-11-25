from enum import IntEnum
from matplotlib.font_manager import FontProperties
from pathlib import Path
from pydantic import BaseModel, model_validator
from typing import ClassVar
from nonebot import get_driver, get_plugin_config
from nonebot.log import logger

driver = get_driver()


class Config(BaseModel):
    # Eversoul相关配置项，live和review数据源
    eversoul_live_path: str | None = None  # 国际服live数据源
    eversoul_review_path: str | None = None  # 国际服review数据源
    eversoul_cn_live_path: str | None = None  # 国服live数据源
    _warned: ClassVar[bool] = False

    @model_validator(mode="after")
    def check_paths(self):
        if not Config._warned:
            if self.eversoul_live_path is None:
                logger.error("eversoul_live_path 未配置，这会导致功能无法正常使用。")
                logger.error("请在配置文件中添加 eversoul_live_path 配置项。")

            if self.eversoul_review_path is None:
                logger.warning(
                    "eversoul_review_path 未配置，这会导致部分功能无法正常使用。"
                )
                logger.warning("请在配置文件中添加 eversoul_review_path 配置项。")

            if self.eversoul_cn_live_path is None:
                logger.warning("eversoul_cn_live_path 未配置，国服功能将无法使用。")
                logger.warning("请在配置文件中添加 eversoul_cn_live_path 配置项。")

            Config._warned = True

        return self


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
}

SERVER_NAME_MAPPING = {
    "asia": "亚服",
    "kr": "韩服",
    "en": "欧美服",
    "cn": "国服",
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

# app_id到服务器名称的反向映射
SERVER_NAME_REVERSE_MAPPING = {v: k for k, v in SERVER_APP_ID_MAPPING.items()}

# 资源路径
RESOURCE_DIR = Path(__file__).parent / "resource"
# 添加数据源配置文件路径
DATA_DIR = Path(__file__).parent / "data"
CONFIG_DIR = DATA_DIR / "config"
DATABASE_DIR = DATA_DIR / "database"
COUPON_DIR = DATA_DIR / "coupon"
COUPON_YAML_PATH = COUPON_DIR / "coupons.yaml"
DATA_SOURCE_CONFIG = CONFIG_DIR / "data_source_config.yaml"

# 默认配置
DEFAULT_CONFIG = {
    "server": "global",  # 服务器: global(国际服) 或 cn(国服)
    "type": "live",  # 数据类型: live 或 review
    "json_path": (
        str(Path(plugin_config.eversoul_live_path))
        if plugin_config.eversoul_live_path
        else ""
    ),
    "hero_alias_file": CONFIG_DIR / "live_hero_aliases.yaml",
}

CURRENT_DATA_SOURCE = {
    "default": {
        "server": "global",
        "type": "live",
        "json_path": (
            str(Path(plugin_config.eversoul_live_path))
            if plugin_config.eversoul_live_path
            else ""
        ),
        "hero_alias_file": CONFIG_DIR / "live_hero_aliases.yaml",
    }
}

# 字体路径
FONT_DIR = RESOURCE_DIR / "font" / "Sarasa-Regular.ttc"
CUSTOM_FONT = FontProperties(fname=FONT_DIR)

CG_DIR = RESOURCE_DIR / "image" / "global" / "cg"
EVERTALK_DIR = RESOURCE_DIR / "image" / "global" / "evertalk"
SOUL_DIR = RESOURCE_DIR / "image" / "global" / "soul"
ICON_DIR = RESOURCE_DIR / "image" / "global" / "icon"
TIER_DIR = RESOURCE_DIR / "image" / "global" / "tier"
TOWN_DIR = RESOURCE_DIR / "image" / "global" / "town"
BANNER_DIR = RESOURCE_DIR / "image" / "global" / "banner"
STICKER_DIR = RESOURCE_DIR / "image" / "global" / "sticker"
