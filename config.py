from matplotlib.font_manager import FontProperties
from pathlib import Path
from pydantic import BaseModel, model_validator
from typing import ClassVar
from nonebot import get_driver, get_plugin_config
from nonebot.log import logger
import sys

driver = get_driver()

class Config(BaseModel):
    # Eversoul相关配置项，live和review数据源
    eversoul_live_path: str | None = None
    eversoul_review_path: str | None = None
    _warned: ClassVar[bool] = False
    
    @model_validator(mode='after')
    def check_paths(self):
        if not Config._warned:
            if self.eversoul_live_path is None:
                logger.error("eversoul_live_path 未配置，这会导致功能无法正常使用。")
                logger.error("请在配置文件中添加 eversoul_live_path 配置项。")
            
            if self.eversoul_review_path is None:
                logger.warning("eversoul_review_path 未配置，这会导致部分功能无法正常使用。")
                logger.warning("请在配置文件中添加 eversoul_review_path 配置项。")
            
            Config._warned = True
        
        return self



plugin_config = get_plugin_config(Config)

# 传送门类型
GATE_TYPE_MAPPING = {
    "自由": 4,
    "人类": 5,
    "野兽": 6,
    "妖精": 7,
    "不死": 8
}

# 属性限制映射
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
    "attack_speed": "攻击速度"
}

# 属性限制映射
STAT_TYPE_MAPPING = {
    "智力": 110044,
    "敏捷": 110043,
    "力量": 110042,
    "共用": 110041
}

# 组合效果映射
EFFECT_TYPE_MAPPING = {
    "攻击力": 14101,
    "防御力": 14102,
    "体力": 14103,
    "暴击率": 14104,
    "暴击威力": 14105,
    "回避": 14107,
    "加速": 14111
}

# 打工属性名称映射
TRAIT_NAME_MAPPING = {
    "conversation": "口才",
    "culture": "教养",
    "courage": "胆量",
    "knowledge": "知识",
    "guts": "毅力",
    "handicraft": "才艺"
}

# 阵型类型映射
FORMATION_TYPE_MAPPING = {
    1: "基本阵型",
    2: "狙击型",
    3: "防守阵型",
    4: "突击型"
}

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
    "Mephistopheles (Dawn)": "MephistoDawn"
}

# 礼包类型映射
PACKAGE_TYPE_MAPPING = {
    'barrier': '通关礼包',
    'stage': '主线礼包',
    'tower': '起源之塔礼包',
    'grade_eternal': '角色升阶礼包'
}

SERVER_APP_ID_MAPPING = {
    "asia": "743491",  # 亚服
    "kr": "743487",    # 韩服
    "en": "750066",     # 欧美服
    "jp": "981921"     # 日服
}

SERVER_NAME_MAPPING = {
    "asia": "亚服",
    "kr": "韩服",
    "en": "欧美服",
    "jp": "日服"
}

# 恶灵讨伐护盾削减系数映射
SINGLE_RAID_GROGGY_TRIGGER_MAPPING = {
    201: "暈眩",
    202: "睡眠",
    206: "沉默",
    207: "魅惑"
}

# 定义品质和等级的映射关系
SIGNATURE_GRADE_LEVEL_MAP = {
    110014: "SignatureLevel1",
    110015: "SignatureLevel2", 
    110016: "SignatureLevel3",
    110017: "SignatureLevel4",
    110018: "SignatureLevel5",
    110019: "SignatureLevel6",
    110020: "SignatureLevel7"
}

# 恶灵讨伐削减系数数组映射
SINGLE_RAID_GROGGY_TRIGGER_ARRAY = [1, 2, 1, 1, 1, 3, 4]

# app_id到服务器名称的反向映射
APP_ID_TO_SERVER_NAME = {v: k for k, v in SERVER_APP_ID_MAPPING.items()}

# 资源路径
RESOURCE_DIR = Path(__file__).parent / "resource"

# 添加数据源配置文件路径
DATA_DIR = Path(__file__).parent / "data"
CONFIG_DIR = DATA_DIR / "config"
DATABASE_DIR = DATA_DIR / "database"
COUPON_DIR = DATA_DIR / "coupon"
DATA_SOURCE_CONFIG = CONFIG_DIR / "data_source_config.yaml"

# 默认配置
DEFAULT_CONFIG = {
    "type": "live",
    "json_path": str(Path(plugin_config.eversoul_live_path)) if plugin_config.eversoul_live_path else "",
    "hero_alias_file": CONFIG_DIR / "live_hero_aliases.yaml"
}

CURRENT_DATA_SOURCE = {
    "default": {
        "type": "live", 
        "json_path": str(Path(plugin_config.eversoul_live_path)) if plugin_config.eversoul_live_path else "",
        "hero_alias_file": CONFIG_DIR / "live_hero_aliases.yaml"
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