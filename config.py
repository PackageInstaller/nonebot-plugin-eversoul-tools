from matplotlib.font_manager import FontProperties
from pathlib import Path
from pydantic import BaseModel
from nonebot import get_driver, get_plugin_config
driver = get_driver()

class Config(BaseModel):
    # Eversoul相关配置项
    eversoul_live_path: str
    eversoul_review_path: str

plugin_config = get_plugin_config(Config)

# 传送门类型
GATE_TYPES = {
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

FORMATION_TYPE_MAPPING = {
    1: "基本阵型",
    2: "狙击型",
    3: "防守阵型",
    4: "突击型"
}

# 资源路径
RESOURCES_DIR = Path(__file__).parent / "resources"

# 添加数据源配置文件路径
DATA_DIR = RESOURCES_DIR / "data"
DATA_SOURCE_CONFIG = DATA_DIR / "data_source_config.yaml"

# 默认配置 - 使用配置文件中的路径
DEFAULT_CONFIG = {
    "type": "live",
    "json_path": str(Path(plugin_config.eversoul_live_path)),  # 使用配置文件中的路径
    "hero_alias_file": DATA_DIR / "live_hero_aliases.yaml"
}

# 全局变量来存储当前数据源配置
CURRENT_DATA_SOURCE = {
    "default": {
        "type": "live", 
        "json_path": Path(plugin_config.eversoul_live_path),  # 使用配置文件中的路径
        "hero_alias_file": DATA_DIR / "live_hero_aliases.yaml"
    }
}

# 字体路径
FONT_DIR = RESOURCES_DIR / "font" / "Sarasa-Regular.ttc"
CUSTOM_FONT = FontProperties(fname=FONT_DIR)

CG_DIR = RESOURCES_DIR / "image" / "cg"
EVERTALK_DIR = RESOURCES_DIR / "image" / "evertalk"
HERO_DIR = RESOURCES_DIR / "image" / "hero"
ICON_DIR = RESOURCES_DIR / "image" / "icon"
SIGNATURE_DIR = RESOURCES_DIR / "image" / "signature"
TIER_DIR = RESOURCES_DIR / "image" / "tier"
TOWN_DIR = RESOURCES_DIR / "image" / "town"
BANNER_DIR = RESOURCES_DIR / "image" / "banner"