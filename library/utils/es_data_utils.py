import json
import yaml
import asyncio
import sys
from pathlib import Path
from typing import Tuple, Dict
from nonebot.log import logger
from ...config import *

driver = get_driver()


@driver.on_startup
async def init_plugin():
    """插件启动时初始化"""
    global DEFAULT_CONFIG
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # 使用本地数据表路径更新默认配置
    DEFAULT_CONFIG["json_path"] = str(GL_LIVE_TABLE_DIR)

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
    await load_data_source_config()


async def sync_aliases(file1: Path, file2: Path) -> None:
    """同步两个yaml文件中的别名，将file1中的别名完全同步到file2

    Args:
        file1: 源yaml文件路径
        file2: 目标yaml文件路径
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
    aliases1 = {
        hero["hero_id"]: hero.get("aliases", [])
        for hero in data1["names"]
        if "hero_id" in hero
    }

    # 将file1的别名直接同步到file2
    for hero_id in aliases1:
        for hero in data2["names"]:
            if hero.get("hero_id") == hero_id:
                hero["aliases"] = aliases1[hero_id]
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
            if (
                isinstance(sequence, (list, tuple))
                and len(sequence) > 0
                and isinstance(sequence[0], str)
            ):
                flow_style = True
            return super().represent_sequence(tag, sequence, flow_style=flow_style)

    try:
        # 保持原有的缩进格式
        with open(file1, "w", encoding="utf-8") as f:
            yaml.dump(
                data1,
                f,
                Dumper=CustomDumper,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
                indent=2,
            )
        with open(file2, "w", encoding="utf-8") as f:
            yaml.dump(
                data2,
                f,
                Dumper=CustomDumper,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
                indent=2,
            )
    except Exception as e:
        logger.error(f"同步出错: {e}")


async def generate_aliases() -> None:
    """生成别名文件"""
    # 使用本地数据表路径
    gl_live_json_path = GL_LIVE_TABLE_DIR
    gl_review_json_path = GL_REVIEW_TABLE_DIR
    cn_live_json_path = CN_LIVE_TABLE_DIR
    cn_review_json_path = CN_REVIEW_TABLE_DIR
    jp_live_json_path = JP_LIVE_TABLE_DIR
    jp_review_json_path = JP_REVIEW_TABLE_DIR

    # 检查国际服数据表是否存在
    if not gl_live_json_path.exists() or not any(gl_live_json_path.glob("*.json")):
        logger.warning("国际服Live数据表不存在，跳过别名生成")
        return

    if not gl_review_json_path.exists() or not any(gl_review_json_path.glob("*.json")):
        logger.warning("国际服Review数据表不存在，跳过别名生成")
        return

    # 生成Live版本别名（国际服+国服+日服）
    try:
        live_hero_aliases = CONFIG_DIR / "live_hero_aliases.yaml"
        live_raid_aliases = CONFIG_DIR / "live_raid_aliases.yaml"

        # 检查国服和日服数据表是否存在
        cn_live_path = (
            cn_live_json_path
            if cn_live_json_path.exists() and any(cn_live_json_path.glob("*.json"))
            else None
        )
        jp_live_path = (
            jp_live_json_path
            if jp_live_json_path.exists() and any(jp_live_json_path.glob("*.json"))
            else None
        )

        live_hero_count, live_raid_count = await process_json_files(
            gl_live_json_path,
            live_hero_aliases,
            live_raid_aliases,
            cn_live_path,
            jp_live_path,
        )
        if live_hero_count > 0 or live_raid_count > 0:
            logger.info(
                f"Live版本别名生成完成！总共生成 {live_hero_count} 个角色条目, {live_raid_count} 个讨伐条目"
            )
        else:
            logger.warning("Live版本别名生成失败，请检查数据表是否完整")
    except Exception as e:
        logger.error(f"处理live别名文件时出错: {e}")

    # 生成Review版本别名（国际服+国服+日服）
    try:
        review_hero_aliases = CONFIG_DIR / "review_hero_aliases.yaml"
        review_raid_aliases = CONFIG_DIR / "review_raid_aliases.yaml"

        # 检查国服和日服数据表是否存在
        cn_review_path = (
            cn_review_json_path
            if cn_review_json_path.exists() and any(cn_review_json_path.glob("*.json"))
            else None
        )
        jp_review_path = (
            jp_review_json_path
            if jp_review_json_path.exists() and any(jp_review_json_path.glob("*.json"))
            else None
        )

        review_hero_count, review_raid_count = await process_json_files(
            gl_review_json_path,
            review_hero_aliases,
            review_raid_aliases,
            cn_review_path,
            jp_review_path,
        )
        if review_hero_count > 0 or review_raid_count > 0:
            logger.info(
                f"Review版本别名生成完成！总共生成 {review_hero_count} 个角色条目, {review_raid_count} 个讨伐条目"
            )
        else:
            logger.warning("Review版本别名生成失败，请检查数据表是否完整")
    except Exception as e:
        logger.error(f"处理review别名文件时出错: {e}")

    # 同步别名
    try:
        await sync_aliases(live_hero_aliases, review_hero_aliases)
        await sync_aliases(live_raid_aliases, review_raid_aliases)
    except Exception as e:
        logger.error(f"同步别名时出错: {e}")


async def process_json_files(
    json_path: Path,
    hero_output_file: Path,
    raid_output_file: Path,
    cn_json_path: Path = None,
    jp_json_path: Path = None,
) -> Tuple[int, int]:
    """处理JSON文件生成别名文件

    根据 battle_power_type 字段区分不同类型的单位：
    - battle_power_type == 1: 可操控角色（Heroes）
    - battle_power_type == 3: 恶灵/讨伐目标（Raid Bosses）
    - battle_power_type == 2: 已废弃类型，不再处理

    Args:
        json_path: JSON文件目录（国际服）
        hero_output_file: 角色别名输出文件
        raid_output_file: 恶灵别名输出文件
        cn_json_path: 国服JSON文件目录（可选），用于获取zh_cn字段
        jp_json_path: 日服JSON文件目录（可选），用于获取额外数据

    Returns:
        Tuple[int, int]: 生成的角色数量和讨伐数量
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

    # 加载国服数据（如果提供了国服路径）
    cn_hero_data = None
    cn_string_char_data = None
    if cn_json_path and cn_json_path.exists():
        try:
            with open(cn_json_path / "Hero.json", "r", encoding="utf-8") as f:
                cn_hero_data = json.load(f)

            with open(
                cn_json_path / "StringCharacter.json", "r", encoding="utf-8"
            ) as f:
                cn_string_char_data = json.load(f)

        except Exception as e:
            logger.warning(f"加载国服数据失败: {e}，将只使用国际服数据")
            cn_hero_data = None
            cn_string_char_data = None

    # 加载日服数据（如果提供了日服路径）
    jp_hero_data = None
    jp_string_char_data = None
    if jp_json_path and jp_json_path.exists():
        try:
            with open(jp_json_path / "Hero.json", "r", encoding="utf-8") as f:
                jp_hero_data = json.load(f)

            with open(
                jp_json_path / "StringCharacter.json", "r", encoding="utf-8"
            ) as f:
                jp_string_char_data = json.load(f)

        except Exception as e:
            logger.warning(f"加载日服数据失败: {e}，将只使用国际服数据")
            jp_hero_data = None
            jp_string_char_data = None

    # 构建国际服名称映射
    hero_names = {}
    for string in string_char_data["json"]:
        if "no" in string:
            if string["no"] not in hero_names:
                hero_names[string["no"]] = {
                    "zh_tw": string.get("zh_tw", ""),
                    "zh_cn": string.get("zh_cn", ""),
                    "kr": string.get("kr", ""),
                    "en": string.get("en", ""),
                    "ja": string.get("ja", ""),
                }

    # 构建国服名称映射，并用国服的zh_cn覆盖国际服的
    cn_hero_names = {}
    if cn_string_char_data:
        for string in cn_string_char_data["json"]:
            if "no" in string:
                # 如果国际服有这个no，用国服的zh_cn覆盖
                if string["no"] in hero_names:
                    if "zh_cn" in string:
                        hero_names[string["no"]]["zh_cn"] = string["zh_cn"]
                # 如果国际服没有这个no，创建新条目（国服独有）
                else:
                    hero_names[string["no"]] = {
                        "zh_tw": string.get("zh_tw", ""),
                        "zh_cn": string.get("zh_cn", ""),
                        "kr": string.get("kr", ""),
                        "en": string.get("en", ""),
                        "ja": string.get("ja", ""),
                    }

                # 记录国服的name_sno，用于后续查找国服独有角色
                if "zh_cn" in string:
                    cn_hero_names[string["no"]] = string["zh_cn"]

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

    # 准备数据容器
    new_data = {"names": []}  # 角色数据容器
    raid_data = {"names": []}  # 恶灵数据容器
    raid_name_count = {}

    # 处理函数：构建角色条目
    def process_hero(hero, hero_names, existing_aliases, existing_zh_cn_names):
        """处理单个角色数据，返回角色条目"""
        hero_id = hero["hero_id"]
        name_data = hero_names.get(
            hero["name_sno"],
            {"zh_tw": "", "zh_cn": "", "kr": "", "en": "", "ja": ""},
        )
        zh_cn_name = name_data["zh_cn"]
        if not zh_cn_name and hero_id in existing_zh_cn_names:
            zh_cn_name = existing_zh_cn_names[hero_id]

        # 构建单位条目（适用于角色和恶灵）
        # zh_cn字段已经在前面从国服数据源读取（如果有的话）
        hero_entry = {
            "zh_tw_name": name_data["zh_tw"],
            "zh_cn_name": zh_cn_name,
            "kr_name": name_data["kr"],
            "en_name": name_data["en"],
            "ja_name": name_data["ja"],
            "aliases": existing_aliases.get(hero_id, []),
            "hero_id": hero_id,
        }
        return hero_entry, hero["battle_power_type"]

    # 建立名称映射并分类处理国际服的所有单位
    for hero in hero_data["json"]:
        if (
            "hero_id" in hero
            and "name_sno" in hero
            and hero["hero_id"] not in seen_hero_ids
        ):
            hero_entry, battle_power_type = process_hero(
                hero, hero_names, existing_aliases, existing_zh_cn_names
            )

            # 根据 battle_power_type 分类存储
            if battle_power_type == 3:
                # 恶灵/讨伐目标 (Raid Bosses)
                raid_name_count[hero_entry["zh_tw_name"]] = 0
                raid_data["names"].append(hero_entry)
            elif battle_power_type == 1:
                # 可操控角色 (Heroes)
                new_data["names"].append(hero_entry)
            # battle_power_type == 2 的数据被忽略，不再处理

            seen_hero_ids.add(hero["hero_id"])

    # 处理国服独有的角色（如果有国服数据）
    if cn_hero_data:
        cn_only_count = 0
        for hero in cn_hero_data["json"]:
            if (
                "hero_id" in hero
                and "name_sno" in hero
                and hero["hero_id"] not in seen_hero_ids
            ):
                hero_entry, battle_power_type = process_hero(
                    hero, hero_names, existing_aliases, existing_zh_cn_names
                )

                # 根据 battle_power_type 分类存储
                if battle_power_type == 3:
                    # 恶灵/讨伐目标 (Raid Bosses)
                    raid_name_count[hero_entry["zh_tw_name"]] = 0
                    raid_data["names"].append(hero_entry)
                    cn_only_count += 1
                elif battle_power_type == 1:
                    # 可操控角色 (Heroes)
                    new_data["names"].append(hero_entry)
                    cn_only_count += 1
                # battle_power_type == 2 的数据被忽略，不再处理

                seen_hero_ids.add(hero["hero_id"])

        if cn_only_count > 0:
            logger.info(f"发现 {cn_only_count} 个国服独有的角色/恶灵")

    # 处理日服独有的角色（如果有日服数据）
    if jp_hero_data:
        jp_only_count = 0
        for hero in jp_hero_data["json"]:
            if (
                "hero_id" in hero
                and "name_sno" in hero
                and hero["hero_id"] not in seen_hero_ids
            ):
                hero_entry, battle_power_type = process_hero(
                    hero, hero_names, existing_aliases, existing_zh_cn_names
                )

                # 根据 battle_power_type 分类存储
                if battle_power_type == 3:
                    # 恶灵/讨伐目标 (Raid Bosses)
                    raid_name_count[hero_entry["zh_tw_name"]] = 0
                    raid_data["names"].append(hero_entry)
                    jp_only_count += 1
                elif battle_power_type == 1:
                    # 可操控角色 (Heroes)
                    new_data["names"].append(hero_entry)
                    jp_only_count += 1
                # battle_power_type == 2 的数据被忽略，不再处理

                seen_hero_ids.add(hero["hero_id"])

        if jp_only_count > 0:
            logger.info(f"发现 {jp_only_count} 个日服独有的角色/恶灵")

    class CustomDumper(yaml.SafeDumper):
        def increase_indent(self, flow=False, indentless=False):
            return super().increase_indent(flow, False)

        def represent_scalar(self, tag, value, style=None):
            if isinstance(value, str):
                style = None
            return super().represent_scalar(tag, value, style)

        def represent_sequence(self, tag, sequence, flow_style=None):
            """对于字符串列表使用flow风格（单行）"""
            if (
                isinstance(sequence, (list, tuple))
                and len(sequence) > 0
                and isinstance(sequence[0], str)
            ):
                flow_style = True
            return super().represent_sequence(tag, sequence, flow_style=flow_style)

    # 确保输出目录存在
    hero_output_file.parent.mkdir(parents=True, exist_ok=True)

    # 写入角色别名文件 (battle_power_type == 1)
    with open(hero_output_file, "w", encoding="utf-8") as f:
        yaml.dump(
            new_data,
            f,
            Dumper=CustomDumper,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            indent=2,
        )

    # 写入恶灵别名文件 (battle_power_type == 3)
    with open(raid_output_file, "w", encoding="utf-8") as f:
        yaml.dump(
            raid_data,
            f,
            Dumper=CustomDumper,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            indent=2,
        )

    return len(new_data["names"]), len(raid_data["names"])


# 加载别名配置文件
async def load_aliases(group_id=None):
    """加载角色别名配置"""
    config = await get_group_data_source(group_id)
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
            name_fields = ["zh_tw_name", "zh_cn_name", "kr_name", "en_name", "ja_name"]

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


async def load_raid_aliases(group_id=None):
    """加载恶灵/讨伐别名配置
    
    Returns:
        tuple: (alias_map, aliases_data)
            - alias_map: 名称/别名 -> hero_id列表 的映射（同名恶灵可能有多个id）
            - aliases_data: 原始yaml数据
    """
    config = await get_group_data_source(group_id)
    data_type = config.get("type", "live")
    raid_alias_file = CONFIG_DIR / f"{data_type}_raid_aliases.yaml"

    if not raid_alias_file.exists():
        return {}, {"names": []}

    try:
        with open(raid_alias_file, "r", encoding="utf-8") as f:
            aliases_data = yaml.safe_load(f)
            if not aliases_data or "names" not in aliases_data:
                return {}, {"names": []}
    except Exception as e:
        logger.error(f"加载恶灵别名配置文件出错: {e}")
        return {}, {"names": []}

    # 创建别名到hero_id列表的映射（同名恶灵可能有多个id）
    alias_map = {}
    for raid in aliases_data["names"]:
        if isinstance(raid, dict) and "hero_id" in raid:
            hero_id = raid["hero_id"]
            name_fields = ["zh_tw_name", "zh_cn_name", "kr_name", "en_name", "ja_name"]

            for field in name_fields:
                name = raid.get(field)
                if name:
                    if name not in alias_map:
                        alias_map[name] = []
                    if hero_id not in alias_map[name]:
                        alias_map[name].append(hero_id)
                    # 英文名添加小写版本
                    if field == "en_name":
                        name_lower = name.lower()
                        if name_lower not in alias_map:
                            alias_map[name_lower] = []
                        if hero_id not in alias_map[name_lower]:
                            alias_map[name_lower].append(hero_id)

            # 添加所有别名
            for alias in raid.get("aliases", []):
                if alias not in alias_map:
                    alias_map[alias] = []
                if hero_id not in alias_map[alias]:
                    alias_map[alias].append(hero_id)
                if alias.isascii():
                    alias_lower = alias.lower()
                    if alias_lower not in alias_map:
                        alias_map[alias_lower] = []
                    if hero_id not in alias_map[alias_lower]:
                        alias_map[alias_lower].append(hero_id)

    return alias_map, aliases_data


# 加载所需的JSON文件
async def load_json_data(
    group_id: int = None, command_name: str = "unknown"
) -> LazyJsonData:
    """
    加载JSON数据（懒加载模式）

    Args:
        group_id: 群组ID，用于获取数据源配置
        tables: 需要预加载的表名列表（可选），如果不提供则使用懒加载
        command_name: 调用的命令名称，用于日志记录

    Returns:
        LazyJsonData: 懒加载数据容器，访问时自动加载对应的表

    Usage:
        # 懒加载模式 - 只在访问时才加载
        data = await load_json_data(group_id, command_name="es角色")
        heroes = data["hero"]["json"]  # 此时才加载 Hero.json

        # 预加载模式 - 提前加载指定的表
        data = await load_json_data(group_id, tables=["hero", "hero_desc"], command_name="es角色")
    """
    config = await get_group_data_source(group_id)
    json_path = config["json_path"]

    # 检查json_path是否有效
    if not json_path:
        logger.error("数据源路径未配置，无法加载游戏数据")
        return LazyJsonData(Path("."), command_name)  # 返回空的懒加载容器

    # 确保json_path是Path对象
    if not isinstance(json_path, Path):
        json_path = Path(json_path)

    # 检查路径是否存在
    if not json_path.exists():
        logger.error(f"数据源路径不存在: {json_path}")
        logger.error("请检查配置的路径是否正确")
        return LazyJsonData(Path("."), command_name)  # 返回空的懒加载容器

    # 创建懒加载容器
    lazy_data = LazyJsonData(json_path, command_name)

    return lazy_data


async def load_data_source_config():
    """加载数据源配置文件"""
    global CURRENT_DATA_SOURCE

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # 使用本地数据表路径
    live_path = str(GL_LIVE_TABLE_DIR)
    review_path = str(GL_REVIEW_TABLE_DIR)
    cn_live_path = str(CN_LIVE_TABLE_DIR)
    cn_review_path = str(CN_REVIEW_TABLE_DIR)
    jp_live_path = str(JP_LIVE_TABLE_DIR)
    jp_review_path = str(JP_REVIEW_TABLE_DIR)

    # 检查是否有路径变更
    config_updated = False

    # 保存当前的配置
    current_config = CURRENT_DATA_SOURCE.copy() if CURRENT_DATA_SOURCE else {}

    # 确保有默认配置
    default_config = DEFAULT_CONFIG.copy()
    # 确保json_path为字符串而不是Path对象
    default_config["json_path"] = live_path

    # 如果没有任何配置或者没有default配置，则初始化
    if not current_config or "default" not in current_config:
        CURRENT_DATA_SOURCE = {"default": default_config}
    else:
        # 确保default配置存在
        if "default" not in CURRENT_DATA_SOURCE:
            CURRENT_DATA_SOURCE["default"] = default_config

    file_config_loaded = False
    if DATA_SOURCE_CONFIG.exists():
        try:
            with open(DATA_SOURCE_CONFIG, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if config:
                # 确保配置中有default键
                if "default" not in config:
                    config["default"] = default_config.copy()
                    config_updated = True
                else:
                    # 确保有server字段
                    if "server" not in config["default"]:
                        config["default"]["server"] = "global"
                        config_updated = True

                    # 根据server和type检查路径变更
                    server = config["default"].get("server", "global")
                    data_type = config["default"].get("type", "live")

                    if server == "cn":
                        if data_type == "live":
                            if str(config["default"].get("json_path")) != cn_live_path:
                                config["default"]["json_path"] = cn_live_path
                                config_updated = True
                                logger.info(f"检测到国服live路径变更: {cn_live_path}")
                        elif data_type == "review":
                            if (
                                str(config["default"].get("json_path"))
                                != cn_review_path
                            ):
                                config["default"]["json_path"] = cn_review_path
                                config_updated = True
                                logger.info(
                                    f"检测到国服review路径变更: {cn_review_path}"
                                )
                    elif server == "jp":
                        if data_type == "live":
                            if str(config["default"].get("json_path")) != jp_live_path:
                                config["default"]["json_path"] = jp_live_path
                                config_updated = True
                                logger.info(f"检测到日服live路径变更: {jp_live_path}")
                        elif data_type == "review":
                            if (
                                str(config["default"].get("json_path"))
                                != jp_review_path
                            ):
                                config["default"]["json_path"] = jp_review_path
                                config_updated = True
                                logger.info(
                                    f"检测到日服review路径变更: {jp_review_path}"
                                )
                    elif server == "global":
                        if data_type == "live":
                            if str(config["default"].get("json_path")) != live_path:
                                config["default"]["json_path"] = live_path
                                config_updated = True
                                logger.info(f"检测到国际服live路径变更: {live_path}")
                        elif data_type == "review":
                            if str(config["default"].get("json_path")) != review_path:
                                config["default"]["json_path"] = review_path
                                config_updated = True
                                logger.info(
                                    f"检测到国际服review路径变更: {review_path}"
                                )

                # 明确转换路径字符串为Path对象
                for group_id, group_config in config.items():
                    # 确保group_id是字符串
                    group_id_str = str(group_id)

                    # 确保有server字段
                    if "server" not in group_config:
                        group_config["server"] = "global"
                        config_updated = True

                    # 根据server和type检查并更新路径
                    server = group_config.get("server", "global")
                    data_type = group_config.get("type", "live")

                    if server == "cn":
                        if data_type == "live":
                            if str(group_config.get("json_path", "")) != cn_live_path:
                                group_config["json_path"] = cn_live_path
                                config_updated = True
                                logger.info(
                                    f"群组{group_id}的国服live路径已更新: {cn_live_path}"
                                )
                        elif data_type == "review":
                            if str(group_config.get("json_path", "")) != cn_review_path:
                                group_config["json_path"] = cn_review_path
                                config_updated = True
                                logger.info(
                                    f"群组{group_id}的国服review路径已更新: {cn_review_path}"
                                )
                    elif server == "jp":
                        if data_type == "live":
                            if str(group_config.get("json_path", "")) != jp_live_path:
                                group_config["json_path"] = jp_live_path
                                config_updated = True
                                logger.info(
                                    f"群组{group_id}的日服live路径已更新: {jp_live_path}"
                                )
                        elif data_type == "review":
                            if str(group_config.get("json_path", "")) != jp_review_path:
                                group_config["json_path"] = jp_review_path
                                config_updated = True
                                logger.info(
                                    f"群组{group_id}的日服review路径已更新: {jp_review_path}"
                                )
                    elif server == "global":
                        if data_type == "live":
                            if str(group_config.get("json_path", "")) != live_path:
                                group_config["json_path"] = live_path
                                config_updated = True
                                logger.info(
                                    f"群组{group_id}的国际服live路径已更新: {live_path}"
                                )
                        elif data_type == "review":
                            if str(group_config.get("json_path", "")) != review_path:
                                group_config["json_path"] = review_path
                                config_updated = True
                                logger.info(
                                    f"群组{group_id}的国际服review路径已更新: {review_path}"
                                )

                    if "json_path" in group_config:
                        # 确保json_path是Path对象
                        if not isinstance(group_config["json_path"], Path):
                            # 如果json_path为空字符串，保持为空字符串
                            if group_config["json_path"]:
                                group_config["json_path"] = Path(
                                    group_config["json_path"]
                                )

                    if "hero_alias_file" in group_config:
                        # 确保hero_alias_file是Path对象
                        if not isinstance(group_config["hero_alias_file"], Path):
                            if str(group_config["hero_alias_file"]).startswith("./"):
                                group_config["hero_alias_file"] = (
                                    Path(__file__).parent.parent
                                    / str(group_config["hero_alias_file"])[2:]
                                )
                            else:
                                group_config["hero_alias_file"] = Path(
                                    group_config["hero_alias_file"]
                                )

                    # 使用字符串键存储配置
                    CURRENT_DATA_SOURCE[group_id_str] = group_config

                file_config_loaded = True

                # 如果有更新，保存配置
                if config_updated:
                    try:
                        await save_data_source_config(CURRENT_DATA_SOURCE)
                        logger.info("检测到配置路径更新，已更新配置文件")
                    except Exception as e:
                        logger.error(f"更新配置文件失败: {e}")

        except Exception as e:
            logger.error(f"加载数据源配置文件出错: {e}")

    if not file_config_loaded:
        try:
            await save_data_source_config(CURRENT_DATA_SOURCE)
        except Exception as e:
            logger.error(f"创建默认数据源配置文件失败: {e}")

    if hasattr(plugin_config, "eversoul_group_config") and getattr(
        plugin_config, "eversoul_group_config", None
    ):
        for group_id, group_settings in getattr(
            plugin_config, "eversoul_group_config", {}
        ).items():
            if group_id not in CURRENT_DATA_SOURCE:
                CURRENT_DATA_SOURCE[group_id] = CURRENT_DATA_SOURCE["default"].copy()

            # 处理server配置
            if "server" in group_settings:
                CURRENT_DATA_SOURCE[group_id]["server"] = group_settings["server"]

            # 确保有server字段
            if "server" not in CURRENT_DATA_SOURCE[group_id]:
                CURRENT_DATA_SOURCE[group_id]["server"] = "global"

            if "type" in group_settings:
                CURRENT_DATA_SOURCE[group_id]["type"] = group_settings["type"]

            # 处理json_path
            json_path = ""
            server = CURRENT_DATA_SOURCE[group_id].get("server", "global")
            data_type = CURRENT_DATA_SOURCE[group_id].get("type", "live")

            if server == "cn":
                if data_type == "live":
                    json_path = cn_live_path
                elif data_type == "review":
                    json_path = cn_review_path
            elif server == "jp":
                if data_type == "live":
                    json_path = jp_live_path
                elif data_type == "review":
                    json_path = jp_review_path
            else:  # global
                if data_type == "live":
                    json_path = live_path
                elif data_type == "review":
                    json_path = review_path

            if "json_path" in group_settings:
                json_path = group_settings["json_path"]

            # 只有在json_path不为空时才转换为Path对象
            if json_path:
                CURRENT_DATA_SOURCE[group_id]["json_path"] = Path(json_path)
            else:
                CURRENT_DATA_SOURCE[group_id]["json_path"] = ""

            alias_type = CURRENT_DATA_SOURCE[group_id]["type"]
            CURRENT_DATA_SOURCE[group_id]["hero_alias_file"] = (
                CONFIG_DIR / f"{alias_type}_hero_aliases.yaml"
            )
            if "hero_alias_file" in group_settings:
                CURRENT_DATA_SOURCE[group_id]["hero_alias_file"] = Path(
                    group_settings["hero_alias_file"]
                )

        try:
            await save_data_source_config(CURRENT_DATA_SOURCE)
        except Exception as e:
            logger.error(f"更新数据源配置文件失败: {e}")


async def save_data_source_config(config):
    """保存数据源配置"""
    try:
        # 读取现有配置（如果存在）
        existing_config = {}
        if DATA_SOURCE_CONFIG.exists():
            with open(DATA_SOURCE_CONFIG, "r", encoding="utf-8") as f:
                existing_config = yaml.safe_load(f) or {}

        save_config = existing_config.copy()  # 基于现有配置创建
        plugin_dir = str(Path(__file__).parent)

        # 更新或添加新配置
        for group_id, group_config in config.items():
            save_config[group_id] = group_config.copy()
            if "json_path" in group_config:
                # 确保json_path是字符串而不是Path对象
                if isinstance(group_config["json_path"], Path):
                    save_config[group_id]["json_path"] = str(group_config["json_path"])
                else:
                    save_config[group_id]["json_path"] = group_config["json_path"]
            if "hero_alias_file" in group_config:
                hero_alias_path = str(group_config["hero_alias_file"])
                if hero_alias_path.startswith(plugin_dir):
                    rel_path = hero_alias_path[len(plugin_dir) :].lstrip("/")
                    save_config[group_id]["hero_alias_file"] = f"./{rel_path}"
                else:
                    save_config[group_id]["hero_alias_file"] = hero_alias_path

        with open(DATA_SOURCE_CONFIG, "w", encoding="utf-8") as f:
            yaml.dump(save_config, f, allow_unicode=True)
    except Exception as e:
        logger.error(f"保存数据源配置出错: {e}")


async def get_group_data_source(group_id):
    """获取群组的数据源配置

    Args:
        group_id: 群组ID，如果不是群消息则为None

    Returns:
        dict: 数据源配置
    """

    # 先检查是否需要从文件刷新数据
    try:
        if DATA_SOURCE_CONFIG.exists():
            with open(DATA_SOURCE_CONFIG, "r", encoding="utf-8") as f:
                file_config = yaml.safe_load(f) or {}

            # 检查是否有新的群组配置在文件中但不在内存中
            for group_id_str, config in file_config.items():
                if group_id_str not in CURRENT_DATA_SOURCE:
                    # 处理路径
                    if "json_path" in config and config["json_path"]:
                        config["json_path"] = Path(config["json_path"])
                    if "hero_alias_file" in config and config["hero_alias_file"]:
                        config["hero_alias_file"] = Path(config["hero_alias_file"])

                    # 将配置添加到内存中
                    CURRENT_DATA_SOURCE[group_id_str] = config
    except Exception as e:
        logger.error(f"尝试从文件刷新配置时出错: {e}")

    result_config = None

    if group_id is not None:
        group_id_str = str(group_id)

        if group_id_str in CURRENT_DATA_SOURCE:
            result_config = CURRENT_DATA_SOURCE[group_id_str]
        else:
            keys_match = [
                k for k in CURRENT_DATA_SOURCE.keys() if str(k) == group_id_str
            ]
            if keys_match:
                result_config = CURRENT_DATA_SOURCE[keys_match[0]]

    if result_config is None:
        result_config = CURRENT_DATA_SOURCE.get("default", DEFAULT_CONFIG.copy())

    # 确保有server字段
    if "server" not in result_config:
        result_config["server"] = "global"

    # 确保json_path有值
    if "json_path" not in result_config or not result_config["json_path"]:
        # 根据server和type选择路径
        server = result_config.get("server", "global")
        data_type = result_config.get("type", "live")

        if server == "cn":
            if data_type == "live":
                result_config["json_path"] = CN_LIVE_TABLE_DIR
            elif data_type == "review":
                result_config["json_path"] = CN_REVIEW_TABLE_DIR
        elif server == "jp":
            if data_type == "live":
                result_config["json_path"] = JP_LIVE_TABLE_DIR
            elif data_type == "review":
                result_config["json_path"] = JP_REVIEW_TABLE_DIR
        else:  # global
            if data_type == "live":
                result_config["json_path"] = GL_LIVE_TABLE_DIR
            elif data_type == "review":
                result_config["json_path"] = GL_REVIEW_TABLE_DIR
            else:
                # 默认使用国际服live路径
                result_config["json_path"] = GL_LIVE_TABLE_DIR
                result_config["type"] = "live"

    # 确保hero_alias_file有值
    if "hero_alias_file" not in result_config or not result_config["hero_alias_file"]:
        result_config["hero_alias_file"] = (
            CONFIG_DIR / f"{result_config.get('type', 'live')}_hero_aliases.yaml"
        )

    return result_config
