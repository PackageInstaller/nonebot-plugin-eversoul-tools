import re
import os
from pathlib import Path
from io import BytesIO
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from nonebot.adapters.onebot.v11 import MessageSegment
from typing import List, Tuple
from nonebot.log import logger
import matplotlib.pyplot as plt


def get_banner_suffix(server: str) -> str:
    """根据服务器类型获取banner文件后缀

    Args:
        server: 服务器类型 ("global", "cn", "jp")

    Returns:
        str: banner文件后缀 (如 "ZH_TW", "ZH_CN", "JA")
    """
    suffix_map = {"global": "ZH_TW", "cn": "ZH_CN", "jp": "JA"}
    return suffix_map.get(server, "ZH_TW")


def _resolve_raid_video_path(base_dir: Path, filename: str, dir_name_hint: str) -> Path:
    """解析 Raid 视频路径，兼容目录名大小写差异（如 guildraid vs GuildRaid）"""
    path = base_dir / filename
    if path.exists():
        return path
    # 尝试 alternate 目录名（config 可能是 guildraid，实际为 GuildRaid）
    parent = base_dir.parent
    candidates = (
        ["GuildRaid", "guildraid"]
        if "Guild" in dir_name_hint
        else ["WorldRaid", "worldraid"]
    )
    for dir_name in candidates:
        if parent / dir_name == base_dir:
            continue
        alt_path = parent / dir_name / filename
        if alt_path.exists():
            return alt_path
    return path


def _extract_raid_video_banner(video_path: Path, schedule_key: str) -> str:
    """从 Raid 视频提取首帧并生成 400x200 banner 缩略图

    缩略图保存在视频所在目录，与视频同名的 .png 文件。
    若已存在该图片则直接使用，否则从视频提取首帧生成。

    Args:
        video_path: 视频文件路径
        schedule_key: 活动 key（未使用，保留接口兼容）

    Returns:
        str: 缩略图绝对路径，失败返回空字符串
    """
    if not video_path or not video_path.exists():
        return ""

    # 缩略图与视频同目录、同名，扩展名为 .png
    thumb_path = video_path.with_suffix(".png")
    if thumb_path.exists():
        return str(thumb_path.resolve())

    try:
        import cv2
    except ImportError:
        return ""

    try:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return ""
        ret, frame = cap.read()
        cap.release()
        if not ret or frame is None:
            return ""

        resized = cv2.resize(frame, (400, 200), interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(thumb_path), resized)
        return str(thumb_path.resolve())
    except Exception:
        return ""


async def apply_color_to_icon(icon_path: str, color: str) -> bytes:
    """对图标应用颜色

    Args:
        icon_path: 图标文件路径
        color: 十六进制颜色代码 (#RRGGBB)

    Returns:
        bytes: 处理后的图片数据
    """
    # 打开图片
    with Image.open(icon_path) as img:
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        # 将十六进制颜色转换为RGB
        color = color.lstrip("#")
        r, g, b = tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))

        # 创建底层彩色图片
        base = Image.new("RGBA", img.size, (r, g, b, 255))

        # 将原图作为遮罩覆盖在彩色底图上
        result = Image.alpha_composite(base, img)

        # 保存为字节流
        from io import BytesIO

        output = BytesIO()
        result.save(output, format="PNG")
        return output.getvalue()


async def get_character_portrait(data, hero_id):
    """获取角色头像（包括基础头像和所有皮肤头像）。

    逻辑：
    1. 在Hero表中查找hero_id对应的角色，获取prefab_path
    2. 使用prefab_path作为no在ItemCostume表中查找对应时装（基础时装）
    3. 如果找到基础时装，获取其hero_no
    4. 使用hero_no在ItemCostume表中查找所有相关时装（皮肤）
    5. 如果没找到基础时装，直接使用prefab_path作为头像路径

    Args:
        data: JSON数据字典.
        hero_id: 角色ID.

    Returns:
        list: 头像图片路径列表，第一个是基础头像，后面是按no排序的皮肤头像.
    """
    from ...config import SOUL_DIR

    if not hero_id:
        return []

    hero_data = None
    for hero in data["hero"]["json"]:
        if hero.get("hero_id") == hero_id:
            hero_data = hero
            break

    if not hero_data:
        return []

    prefab_key = hero_data.get("prefab_path")
    if not prefab_key:
        return []

    portraits = []
    base_costume = None
    target_no = None
    try:
        target_no = int(prefab_key)
    except (ValueError, TypeError):
        pass

    if target_no:
        for costume in data["item_costume"]["json"]:
            if costume.get("no") == target_no:
                base_costume = costume
                break

    # 基础时装和皮肤
    if base_costume:
        base_path = base_costume.get("portrait_path") or base_costume.get("prefab_path")
        if base_path:
            full_path = SOUL_DIR / f"{base_path}_512.png"
            if full_path.exists():
                portraits.append(str(full_path))

        hero_id = base_costume.get("hero_no")
        if hero_id:
            skin_costumes = []
            for costume in data["item_costume"]["json"]:
                # 找同一个组的，且不是基础时装的
                if costume.get("hero_no") == hero_id and costume.get("no") != target_no:
                    skin_costumes.append(costume)

            # no排序
            skin_costumes.sort(key=lambda x: x.get("no", 0))

            for skin in skin_costumes:
                skin_path = skin.get("portrait_path") or skin.get("prefab_path")
                if skin_path:
                    # 检查重复
                    full_path = SOUL_DIR / f"{skin_path}_512.png"
                    if full_path.exists() and str(full_path) not in portraits:
                        portraits.append(str(full_path))

        else:
            # 没找到hero_id，直接使用 prefab_key 构建
            full_path = SOUL_DIR / f"{prefab_key}_512.png"
            if full_path.exists():
                portraits.append(str(full_path))

    return portraits


async def get_character_illustration(data, hero_id):
    """获取角色立绘

    Args:
        data: JSON数据字典
        hero_id: 角色ID
    Returns:
        list: [dict] 字典列表
    """
    from .es_string_utils import get_string_by_type
    from ...config import SOUL_DIR

    image_path = Path(SOUL_DIR)
    if not image_path.exists():
        return[]
    
    item_desc_map = {
        item.get("no"): item.get("desc_sno") 
        for item in data.get("item", {}).get("json",[])
    }

    costume_info = {}
    for costume in data.get("item_costume", {}).get("json",[]):
        if costume.get("hero_no") != hero_id:
            continue
            
        portrait_path = costume.get("portrait_path", "")
        costume_no = costume.get("no")
        name_sno = costume.get("name_sno")
        type_sno = costume.get("type_sno")

        if not all([portrait_path, name_sno, type_sno, costume_no]):
            continue

        desc_sno = item_desc_map.get(costume_no)
        name_data = (await get_string_by_type(data, "item", name_sno)) or {}
        cond_data = (await get_string_by_type(data, "ui", type_sno)) or {}
        desc_data = (await get_string_by_type(data, "item", desc_sno)) or {} if desc_sno else {}

        costume_info[portrait_path] = {
            "name": name_data,
            "cond": cond_data,
            "desc": desc_data
        }

    file_map = {}
    for file in image_path.glob("*_2048*.*"):
        file_stem = file.stem
        
        if "_2048" not in file_stem or "(2)" in file_stem:
            continue

        base_name = file_stem.split("_2048")[0]
        
        if base_name not in costume_info:
            continue

        if base_name not in file_map:
            file_map[base_name] = {}

        # 分类存储常规立绘和旧设立绘
        if "(1)" in file_stem:
            file_map[base_name]["old"] = file
        else:
            file_map[base_name]["normal"] = file

    result_dict = {}
    for base_name, files in file_map.items():
        info = costume_info[base_name]
        result_dict[base_name] =[]

        def build_entry(img_path, is_old=False):
            name_d, cond_d, desc_d = info["name"], info["cond"], info["desc"]
            return {
                "img_path": img_path,
                "display_name_tw": f"{name_d.get('zh_tw', '')}_旧设" if is_old else name_d.get('zh_tw', ''),
                "display_name_cn": f"{name_d.get('zh_cn', '')}_旧设" if is_old else name_d.get('zh_cn', ''),
                "display_name_kr": f"{name_d.get('kr', '')}_旧设" if is_old else name_d.get('kr', ''),
                "display_name_en": f"{name_d.get('en', '')}_old" if is_old else name_d.get('en', ''),
                "condition_tw": "敬請期待" if is_old else cond_d.get("zh_tw", ""),
                "condition_cn": "敬请期待" if is_old else cond_d.get("zh_cn", ""),
                "condition_kr": "기대해 주세요" if is_old else cond_d.get("kr", ""),
                "condition_en": "Stay tuned" if is_old else cond_d.get("en", ""),
                "desc_tw": desc_d.get("zh_tw", ""),
                "desc_cn": desc_d.get("zh_cn", ""),
                "desc_kr": desc_d.get("kr", ""),
                "desc_en": desc_d.get("en", ""),
            }

        if "normal" in files:
            result_dict[base_name].append(build_entry(files["normal"], is_old=False))
        if "old" in files:
            result_dict[base_name].append(build_entry(files["old"], is_old=True))

    images =[]
    for base_name in sorted(result_dict.keys()):
        images.extend(result_dict[base_name])

    return images


async def get_character_affection_cg(data, hero_id, server, data_type):
    """获取角色好感CG

    Args:
        data: JSON数据字典
        hero_id: 角色ID
        server: 服务器类型
        data_type: 数据类型
    Returns:
        list: [(图片路径, CG编号, 章节标题)] 的列表
    """
    from ...config import CG_DIR
    from .es_string_utils import get_string_by_type, select_text_by_priority

    if not CG_DIR.exists():
        return []

    # 将hero_id转换为act格式
    act = hero_id

    # 收集所有相关的故事编号和章节信息
    story_info = {}  # 使用字典存储故事编号和章节信息的映射
    for story in data["story_info"]["json"]:
        if "act" in story and story["act"] == act:
            story_nos = story_info.get(story["no"], [])
            story_nos.append(
                {
                    "episode": story.get("episode"),
                    "episode_name_sno": story.get("episode_name_sno"),
                }
            )
            story_info[story["no"]] = story_nos

    # 从Illust.json中获取CG信息
    cg_info = []
    for illust in data["illust"]["json"]:
        if (
            "open_condition" in illust
            and illust["open_condition"] in story_info
            and "bg_movie_path" in illust
        ):
            # 从路径中提取CG名称
            path_parts = illust["bg_movie_path"].split("/")
            cg_name = path_parts[-1]
            # 获取对应的章节信息
            story_no = illust["open_condition"]
            episode_info = story_info[story_no][0]  # 取第一个匹配的章节信息
            cg_info.append((illust["no"], cg_name, episode_info))

    # 查找匹配的CG图片
    images = []
    for no, cg_name, episode_info in sorted(cg_info):  # 按编号排序
        for file in CG_DIR.glob(f"{cg_name}.*"):
            # 获取章节标题
            episode_title = ""
            if episode_info["episode_name_sno"]:

                string_data = await get_string_by_type(
                    data, "talk", episode_info["episode_name_sno"]
                )
                episode_title = await select_text_by_priority(
                    string_data.get("zh_tw", ""),
                    string_data.get("zh_cn", ""),
                    string_data.get("kr", ""),
                    string_data.get("en", ""),
                    server,
                    data_type,
                )
            images.append((file, f"CG_{no}", episode_info["episode"], episode_title))
            break  # 找到一个匹配的文件就跳出

    return images


async def get_character_evertalk_cg(data: dict, hero_id: int) -> List[Tuple[Path, str]]:
    """获取角色的EverPhone插图

    Args:
        data: 游戏数据字典
        hero_id: 角色ID

    Returns:
        List[Tuple[Path, str]]: 插图信息列表，每个元素为(插图路径, 插图基础名称)的元组
    """
    from ...config import EVERTALK_DIR

    evertalk_illusts = []
    seen_illusts = set()

    # 从EverTalkDesc.json中查找插图
    for talk in data["evertalk_desc"]["json"]:
        if talk.get("hero_no") == hero_id and talk.get("ui_type") == "Illust":
            talk_no = talk.get("no")
            # 从StringEverTalk.json中获取插图名称
            for string in data["string_evertalk"]["json"]:
                if string.get("no") == talk_no:
                    # 提取插图基础名称
                    illust_match = re.search(r"<display:(.+?)>", string.get("kr", ""))
                    if not illust_match:
                        illust_match = re.search(
                            r"<display:(.+?)>", string.get("zh_cn", "")
                        )
                    if illust_match:
                        illust_base = illust_match.group(1)
                        if illust_base not in seen_illusts:
                            seen_illusts.add(illust_base)
                            illust_path = EVERTALK_DIR / f"{illust_base}.png"
                            if Path(illust_path).exists():
                                evertalk_illusts.append((illust_path, illust_base))

    return evertalk_illusts


async def get_schedule_event(
    data, target_month, target_year, schedule_prefix, event_type, server="global"
):
    """获取活动日程事件信息

    Args:
        data: JSON数据字典
        target_month: 目标月份
        target_year: 目标年份
        schedule_prefix: 日程key前缀(如"Calender_PickUp_")
        event_type: 事件类型显示名称(如"Pickup")
        server: 服务器类型 ("global", "cn", "jp")

    Returns:
        list: 事件信息列表
    """
    events = []
    now = datetime.now()
    from .es_string_utils import get_string_by_type

    # 跳过已经迁移到get_calendar_event函数中的类型
    if (
        schedule_prefix.startswith("EventInfo_Side_")
        or schedule_prefix.startswith("Calender_SingleRaid_")
        or schedule_prefix.startswith("Calender_EdenAlliance_")
        or schedule_prefix.startswith("Calender_WorldBoss_")
        or schedule_prefix.startswith("Calender_GuildRaid_")
    ):
        return events

    for schedule in data["localization_schedule"]["json"]:
        # 对于主要活动，使用完全匹配而不是startswith
        if schedule_prefix.endswith("_Main") or schedule_prefix.endswith(
            "_Return_Main"
        ):
            if schedule.get("schedule_key", "") != schedule_prefix:
                continue
        else:
            if not schedule.get("schedule_key", "").startswith(schedule_prefix):
                continue

        start_date = schedule.get("start_date")
        end_date = schedule.get("end_date")

        # 跳过无效的日期数据（如 '0' 或空字符串）
        if not (start_date and end_date) or start_date == "0" or end_date == "0":
            continue

        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
            end_date = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            # 跳过无法解析的日期
            continue

        is_in_month = (
            (start_date.year == target_year and start_date.month == target_month)
            or (end_date.year == target_year and end_date.month == target_month)
        ) and end_date >= now

        if not is_in_month:
            continue

        schedule_key = schedule["schedule_key"]
        event_name_tw = ""
        banner_path = ""
        name_sno = None

        # 从EventCalender中获取name_sno和gacha_no
        for event in data["event_calender"]["json"]:
            if event.get("schedule_key") == schedule_key:
                name_sno = event.get("name_sno")
                if name_sno:
                    # 从StringUI中获取名称
                    string_data = await get_string_by_type(data, "ui", name_sno)
                    event_name_tw = (
                        string_data.get("zh_tw", "")
                        .replace("\\r\\n", " ")
                        .replace("\r\n", " ")
                        .replace("\\n", " ")
                        .replace("\n", " ")
                    )

        # 获取banner后缀
        banner_suffix = get_banner_suffix(server)

        # 对于Pickup类型，从Gacha.json中获取banner_path
        # 需要找到schedule_key_1时间范围包含当前Pickup开始时间的Gacha
        if schedule_key.startswith("Calender_PickUp_") and "gacha" in data:
            # 从schedule_key中提取角色名: Calender_PickUp_HeroName -> HeroName
            hero_name = schedule_key.replace("Calender_PickUp_", "")

            # 遍历所有Gacha，找到正确的那个
            for gacha in data["gacha"]["json"]:
                gacha_schedule_key_1 = gacha.get("schedule_key_1", "")
                if not gacha_schedule_key_1:
                    continue

                # 检查banner_path是否包含角色名（不区分大小写）
                banner_raw = gacha.get("banner_path", "")
                if not banner_raw or hero_name.lower() not in banner_raw.lower():
                    continue

                # 在LocalizationSchedule中查找对应的时间信息
                for schedule_item in data["localization_schedule"]["json"]:
                    if schedule_item.get("schedule_key") == gacha_schedule_key_1:
                        gacha_start_date = schedule_item.get("start_date")
                        gacha_end_date = schedule_item.get("end_date")

                        # 检查当前Pickup的开始时间是否在Gacha的schedule_key_1时间范围内
                        if gacha_start_date and gacha_end_date:
                            try:
                                gacha_start = datetime.strptime(
                                    gacha_start_date, "%Y-%m-%d %H:%M:%S"
                                )
                                gacha_end = datetime.strptime(
                                    gacha_end_date, "%Y-%m-%d %H:%M:%S"
                                )

                                # 如果Pickup的开始时间在Gacha的时间范围内，且banner匹配
                                if gacha_start <= start_date <= gacha_end:
                                    banner_path = f"{banner_raw}_{banner_suffix}.png"
                                    break
                            except (ValueError, TypeError):
                                continue
                        break

                if banner_path:
                    break
        # 从EventInfo中获取banner路径
        elif name_sno:
            for event_info in data["event_info"]["json"]:
                if event_info.get("name_sno") == name_sno:
                    banner_raw = event_info.get("banner_path", "")
                    if banner_raw:
                        banner_path = f"{banner_raw}_{banner_suffix}.png"
                    break

        if event_name_tw:
            event_info = []
            event_info.append(f"【{event_type}】")
            event_info.append(f"名称：{event_name_tw}")
            event_info.append(f"持续时间：{start_date} 至 {end_date}")
            if banner_path:
                event_info.append(f"banner：{banner_path}")
            # 返回带开始时间的元组
            events.append((start_date, "\n".join(event_info)))
    return events


async def get_mail_event(data, target_month, target_year):
    """获取邮箱事件信息"""
    from .es_string_utils import get_string_character, get_string_item

    mail_events = []
    now = datetime.now()

    for mail in data["message_mail"]["json"]:
        start_date = mail.get("start_date")
        end_date = mail.get("end_date")

        # 跳过无效的日期数据（如 '0' 或空字符串）
        if not (start_date and end_date) or start_date == "0" or end_date == "0":
            continue

        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except (ValueError, TypeError):
            continue

        is_in_month = (
            (start_date.year == target_year and start_date.month == target_month)
            or (end_date.year == target_year and end_date.month == target_month)
        ) and end_date >= now

        if not is_in_month:
            continue

        sender_name_tw = "未知"
        sender_name_en = "Unknown"
        if sender_sno := mail.get("sender_sno"):
            sender_data = await get_string_character(data, sender_sno, special=True)
            if sender_data:
                sender_name_tw = sender_data.get("zh_tw", "未知")
                sender_name_en = sender_data.get("en", "Unknown")

        title_data = await get_string_character(data, mail.get("title_sno", 0))
        title_tw = (
            title_data.get("zh_tw", "无标题")
            if isinstance(title_data, dict)
            else "无标题"
        )

        desc_data = await get_string_character(data, mail.get("desc_sno", 0))
        desc_tw = (
            desc_data.get("zh_tw", "无描述")
            if isinstance(desc_data, dict)
            else "无描述"
        )

        # 奖励信息（支持 reward_no_1..10 或 reward_no1..4）
        rewards = []
        for i in range(1, 11):
            reward_no = mail.get(f"reward_no_{i}") or mail.get(f"reward_no{i}")
            if not reward_no:
                continue
            amount = mail.get(f"reward_amount_{i}") or mail.get(f"reward_amount{i}", 0)
            item_name = await get_string_item(data, reward_no)
            if item_name and amount:
                rewards.append(f"{item_name.get('zh_tw', '')}x{amount}")

        event_info = []
        event_info.append(f"【邮箱事件】")
        event_info.append(f"名称：{sender_name_tw}的信件")
        event_info.append(f"标题：{title_tw}")
        event_info.append(f"描述：{desc_tw}")
        event_info.append(
            f"持续时间：{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}"
        )

        if rewards:
            event_info.append("奖励：")
            event_info.extend([f"- {r}" for r in rewards])

        mail_events.append((start_date, "\n".join(event_info)))
    return mail_events


async def get_calendar_event(data, target_month, target_year, server="global"):
    """获取一般活动信息

    Args:
        data: JSON数据字典
        target_month: 目标月份
        target_year: 目标年份
        server: 服务器类型 ("global", "cn", "jp")
    """
    from .es_string_utils import get_string_by_type
    from ...config import (
        HERO_NAME_MAPPING,
        STICKER_DIR,
        WORLD_RAID_NAME_MAPPING,
        GUILD_RAID_NAME_MAPPING,
        WORLD_RAID_DIR,
        GUILD_RAID_DIR,
    )

    calendar_events_with_date = []
    now = datetime.now()

    for schedule in data["localization_schedule"]["json"]:
        schedule_key = schedule.get("schedule_key", "")
        # 排除以下类型：
        #  - Calender_PickUp_ （Pickup活动）
        #  - *_Main 结尾的主要活动
        if (
            (
                not schedule_key.startswith("Calender_")
                and not schedule_key.startswith("EventInfo_")
            )
            or schedule_key.startswith("Calender_PickUp_")
            or schedule_key.endswith("_Main")  # 主要活动
            or schedule_key.endswith("_Quest")  # 7日任务
            or schedule_key.endswith("_Infinity")  # 无限挑战
            or schedule_key.endswith("_Rewardgame")  # 小游戏
            or schedule_key.endswith("_Pass")
            or schedule_key.endswith("_Attend")
            or (
                schedule_key.startswith("EventInfo_")
                and not schedule_key.endswith("_Pass")
                and not schedule_key.endswith("_Attend")
            )
        ):
            continue

        start_date = schedule.get("start_date")
        end_date = schedule.get("end_date")

        # 跳过无效的日期数据（如 '0' 或空字符串）
        if not (start_date and end_date) or start_date == "0" or end_date == "0":
            continue

        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
            end_date = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            # 跳过无法解析的日期
            continue

        is_in_month = (
            (start_date.year == target_year and start_date.month == target_month)
            or (end_date.year == target_year and end_date.month == target_month)
        ) and end_date >= now

        if not is_in_month:
            continue

        event_name_tw = ""
        event_name_cn = ""
        banner_path = ""
        name_sno = None
        gacha_no = None

        # 获取banner后缀
        banner_suffix = get_banner_suffix(server)

        # 对于EventInfo_开头的活动，直接从event_info中获取信息
        if schedule_key.startswith("EventInfo_") and (
            (schedule_key.endswith("_Pass")) or (schedule_key.endswith("_Attend"))
        ):
            for event_info in data["event_info"]["json"]:
                if event_info.get("schedule_key") == schedule_key:
                    name_sno = event_info.get("name_sno")
                    banner_raw = event_info.get("banner_path", "")
                    if banner_raw:
                        banner_path = f"{banner_raw}_{banner_suffix}.png"
                    # 如果找到name_sno，从StringUI中获取名称
                    if name_sno:
                        string_data = await get_string_by_type(data, "ui", name_sno)
                        event_name_tw = (
                            string_data.get("zh_tw", "")
                            .replace("\\r\\n", " ")
                            .replace("\r\n", " ")
                            .replace("\\n", " ")
                            .replace("\n", " ")
                        )
                        break
                    break
        else:
            # 从EventCalender中获取name_sno
            for event in data["event_calender"]["json"]:
                if event.get("schedule_key") == schedule_key:
                    name_sno = event.get("name_sno")
                    if name_sno:
                        # 从StringUI中获取名称
                        string_data = await get_string_by_type(data, "ui", name_sno)
                        event_name_tw = (
                            string_data.get("zh_tw", "")
                            .replace("\\r\\n", " ")
                            .replace("\r\n", " ")
                            .replace("\\n", " ")
                            .replace("\n", " ")
                        )
                        break
                    break

            # 从EventInfo中获取名称
            for event in data["event_info"]["json"]:
                if event.get("schedule_key") == schedule_key:
                    name_sno = event.get("name_sno")
                    if name_sno:
                        string_data = await get_string_by_type(data, "ui", name_sno)
                        event_name_tw = (
                            string_data.get("zh_tw", "")
                            .replace("\\r\\n", " ")
                            .replace("\r\n", " ")
                            .replace("\\n", " ")
                            .replace("\n", " ")
                        )
                        break
                    break

        # 处理不同类型活动的banner
        # World Raid / Guild Raid: 从视频提取首帧作为 banner
        if schedule_key in WORLD_RAID_NAME_MAPPING:
            name = schedule_key.replace("Calender_", "")
            video_path = _resolve_raid_video_path(
                WORLD_RAID_DIR, f"WorldRaid_{name}.mp4", "WorldRaid"
            )
            banner_path = _extract_raid_video_banner(video_path, schedule_key)
        elif schedule_key in GUILD_RAID_NAME_MAPPING:
            name = schedule_key.split("_")[-1]
            video_path = _resolve_raid_video_path(
                GUILD_RAID_DIR, f"GuildeRaid_{name}.mp4", "GuildRaid"
            )
            banner_path = _extract_raid_video_banner(video_path, schedule_key)
        elif schedule_key.startswith("Calender_SingleRaid_"):
            # 从schedule_key中提取角色名称：Calender_SingleRaid_HeroName
            parts = schedule_key.split("_")
            if len(parts) > 2:
                hero_name = parts[-1]
                # 这里是给数据表中不同字段角色名称做适配
                hero_name = HERO_NAME_MAPPING.get(
                    hero_name, hero_name
                )  # 如果不在映射表中，使用原名
                sticker_path = f"sticker_singleraid_{hero_name}_01.png"
                # 检查文件是否存在
                if (STICKER_DIR / sticker_path).exists():
                    banner_path = sticker_path
        # 联合作战类型，从schedule_key提取角色名生成徽章路径
        elif schedule_key.startswith("Calender_EdenAlliance_"):
            # 从schedule_key中提取角色名称：Calender_EdenAlliance_HeroName
            parts = schedule_key.split("_")
            if len(parts) > 2:
                hero_name = parts[-1].lower()
                max_tier = 0
                found_sticker = None
                # 查找基础贴纸（不带_1后缀）
                for tier in range(1, 20):
                    sticker_name = f"sticker_eas_{hero_name}_tier_{tier}.png"
                    sticker_path = STICKER_DIR / sticker_name
                    if sticker_path.exists():
                        max_tier = tier
                        found_sticker = sticker_name

                # 带_1后缀的贴纸
                if found_sticker:
                    variant_sticker = f"sticker_eas_{hero_name}_tier_{max_tier}_1.png"
                    variant_path = STICKER_DIR / variant_sticker
                    if variant_path.exists():
                        banner_path = variant_sticker
                    else:
                        banner_path = found_sticker
        elif name_sno and not banner_path:
            for event_info in data["event_info"]["json"]:
                if event_info.get("name_sno") == name_sno:
                    banner_raw = event_info.get("banner_path", "")
                    if banner_raw:
                        banner_path = f"{banner_raw}_{banner_suffix}.png"
                    break

        if event_name_tw:
            event_info = []
            event_info.append(f"【活动】")
            event_info.append(f"名称：{event_name_tw}")
            event_info.append(f"持续时间：{start_date} 至 {end_date}")
            if banner_path:
                event_info.append(f"banner：{banner_path}")
            calendar_events_with_date.append((start_date, "\n".join(event_info)))

    calendar_events_with_date.sort(key=lambda x: x[0])
    return [event_info for _, event_info in calendar_events_with_date]


async def get_potential_value(data: dict, effect_type: int, effect_no: int) -> str:
    """获取潜能数值

    Args:
        data: JSON数据字典
        effect_no: 效果编号
        level: 潜能等级

    Returns:
        str: 格式化后的数值
    """
    from .es_string_utils import get_stat_string_in_hero_option
    from ...config import HERO_OPTION_BUFF_REVERSE_MAPPING

    if effect_type == 1:
        for buff in data["contents_buff"]["json"]:
            if buff.get("no") == effect_no:
                ignore_keys = ["no", "battle_power_per", "hero_level_base"]
                for key, value in buff.items():
                    if key not in ignore_keys:
                        return await get_stat_string_in_hero_option(value, key)
    else:
        for buff in data["skill_buff"]["json"]:
            if buff.get("no") == effect_no:
                value = buff.get("value", 0)
                key = HERO_OPTION_BUFF_REVERSE_MAPPING.get(
                    buff.get("buff_effect", 0), 0
                )
                return await get_stat_string_in_hero_option(value, key)


async def get_event_name(event):
    """获取事件名称"""
    lines = event.split("\n")

    # 邮件事件
    if lines and "【邮箱事件】" in lines[0]:
        for line in lines:
            if line.startswith("名称："):
                name = line.replace("名称：", "").replace("的信件", "").strip()
                return name

    for line in lines:
        if line.startswith("名称："):
            name = line.replace("名称：", "").strip()
            name = (
                name.replace("\r", "")
                .replace("\n", " ")
                .replace("\\r", "")
                .replace("\\n", " ")
            )
            name = " ".join(name.split())
            return name

    return "未知活动"


async def get_event_type_class(event: str) -> str:
    """根据事件内容返回对应的CSS类名"""
    if "【主要活动】" in event:
        return "main"
    elif "【活动】" in event:
        return "calendar"
    elif "【邮箱事件】" in event:
        return "mail"
    elif "【Pickup】" in event:
        return "pickup"
    return "calendar"


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
                lines = event.split("\n")
                for line in lines:
                    if "持续时间：" in line:
                        start_date = datetime.strptime(
                            line.split("至")[0].replace("持续时间：", "").strip(),
                            "%Y-%m-%d",
                        )
                        mail_events_with_date.append((start_date, event))
                        break
            else:
                # 解析其他特殊活动时间信息
                lines = event.split("\n")
                for line in lines:
                    if "持续时间：" in line:
                        start_date = datetime.strptime(
                            line.split("至")[0].replace("持续时间：", "").strip(),
                            "%Y-%m-%d",
                        )
                        special_events_with_date.append((start_date, event))
                        break

    # 按时间排序
    special_events_with_date.sort(key=lambda x: x[0])
    mail_events_with_date.sort(key=lambda x: x[0])
    special_events = [event for _, event in special_events_with_date]
    mail_events = [event for _, event in mail_events_with_date]

    html = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{month}月份活动时间线</title>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/css/all.min.css" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/font-awesome@4.7.0/css/font-awesome.min.css" rel="stylesheet">
        <style>
            /* 全局样式 */
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f4f4f4;
                color: #333;
            }}

            :root {{
                --primary-color: #165DFF;
                --secondary-color: #4080FF;
                --accent-color: #86B4FF;
                --active-color: #0DC6E8;
                --main-color: #b61274;
                --pickup-color: #6a1b9a;
                --mail-color: #00838f;
                --calendar-color: #37474f;
            }}

            .flex {{
                display: flex;
            }}

            .flex_align_center {{
                align-items: center;
            }}

            .topTitle {{
                font-size: 45px;
                font-weight: 900;
                margin: 0;
                background: linear-gradient(90deg, var(--active-color) 0%, var(--active-color) 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                text-shadow: 0 4px 8px rgba(142, 45, 226, 0.15),
                    0 2px 4px rgba(142, 45, 226, 0.1);
                letter-spacing: -2px;
                position: relative;
                text-align: center;
                margin-bottom: 2rem;
            }}

            .topTitle::after {{
                content: '';
                position: absolute;
                bottom: -10px;
                left: 50%;
                transform: translateX(-50%);
                width: 150px;
                height: 3px;
                background: linear-gradient(90deg, var(--active-color), var(--secondary-color), var(--accent-color));
                border-radius: 3px;
                box-shadow: 0 2px 4px rgba(22, 93, 255, 0.2);
            }}

            .container {{
                max-width: 1600px;
                margin: 0 auto;
                padding: 32px 16px;
            }}

            h2 {{
                font-size: 1.8rem;
                margin-bottom: 1rem;
                color: var(--active-color);
                border-bottom: 2px solid var(--active-color);
                padding-bottom: 0.5rem;
                display: inline-block;
            }}

            /* 活动网格样式 */
            .event-grid {{
                display: flex;
                flex-wrap: wrap;
                margin: 0 -0.75rem;
                margin-bottom: 2rem;
            }}

            /* 活动卡片样式 */
            .event-card {{
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                overflow: hidden;
                transition: all 0.3s ease;
                display: flex;
                flex-direction: column;
                height: auto;
                margin: 0.75rem;
                /* 4 items per row: 25% width minus the margins (1.5rem total for left+right) */
                width: calc(25% - 1.5rem);
                box-sizing: border-box;
            }}

            .event-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
            }}

            .event-card-email {{
                flex-direction: column;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 1.2rem;
            }}

            .event-card .content {{
                padding: 0.8rem;
            }}

            .event-card-email .content-email {{
                display: flex;
                flex-direction: column;
                padding: 1rem;
                flex: 1;
                align-items: flex-start;
            }}

            .mail-event .content-email {{
                text-align: left;
            }}

            .mail-event .event-author {{
                font-size: 1.35rem;
                margin: 0 0 0.5rem 0;
            }}

            .mail-event .event-time {{
                font-size: 1rem;
                text-align: left;
            }}

            .mail-event .event-content {{
                text-align: left;
                text-indent: 0;
                font-size: 16px;
                line-height: 1.6;
                max-height: none;
                overflow: visible;
            }}

            .event-author {{
                font-weight: bold;
                font-size: 1.1rem;
                margin: 0 auto 0.5rem auto;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                position: relative;
                padding: 2px 12px;
                border-radius: 20px;
                display: inline-block;
                color: #fff;
                max-width: 90%;
                text-align: center;
            }}

            .main-event .event-author {{
                background: linear-gradient(90deg, var(--main-color) 0%, #e9559e 100%);
                box-shadow: 0 2px 5px rgba(182, 18, 116, 0.3);
            }}

            .pickup-event .event-author {{
                background: linear-gradient(90deg, var(--pickup-color) 0%, #9c41c9 100%);
                box-shadow: 0 2px 5px rgba(106, 27, 154, 0.3);
            }}

            .calendar-event .event-author {{
                background: linear-gradient(90deg, var(--calendar-color) 0%, #607d8b 100%);
                box-shadow: 0 2px 5px rgba(55, 71, 79, 0.3);
            }}

            .mail-event .event-author {{
                background: linear-gradient(90deg, var(--mail-color) 0%, #26c6da 100%);
                box-shadow: 0 2px 5px rgba(0, 131, 143, 0.3);
            }}

            .event-time {{
                font-size: 1rem;
                color: #000;
                margin: 0.5rem 0;
                font-weight: bold;
                text-align: center;
            }}

            .event-content {{
                width: 100%;
                text-indent: 2em;
                margin: 10px 0;
                white-space: pre-wrap;
                font-size: 14px;
                line-height: 1.5;
                overflow: hidden;
                max-height: 125px;
            }}

            .event-img {{
                width: 100%;
                height: 200px;
                object-fit: contain;
                display: block;
                background-color: #f8f8f8;
            }}

            .event-img-email {{
                width: 20%;
                height: auto;
            }}

            .icon {{
                font-size: 1.6rem;
                background: linear-gradient(90deg, #0587f1 0%, #84c1f3 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                text-shadow: 0 4px 8px rgba(142, 45, 226, 0.15),
                    0 2px 4px rgba(142, 45, 226, 0.1);
                margin-bottom: -0.3rem;
                margin-left: 0.3rem;
            }}

            .section-title {{
                margin-bottom: 1rem;
                justify-content: center;
            }}

            /* 响应式布局 */
            @media (max-width: 768px) {{
                .event-card {{
                    width: calc(50% - 1.5rem);
                }}
            }}
            @media (max-width: 480px) {{
                .event-card {{
                    width: calc(100% - 1.5rem);
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="topTitle">{month}月份活动时间线</h1>

            <!-- 特殊活动部分 -->
            {f'''
            <div class="mb-8">
                <div class="flex flex_align_center section-title">
                    <h2 style="text-align: center;">特殊活动</h2>
                    <span class="icon"><i class="fa fa-pagelines"></i></span>
                </div>

                <div class="event-grid">
                    {''.join([f"""
                    <div class="event-card main-event">
                        <div class="content">
                            <div class="event-author">{await get_event_name(event)}</div>
                            <div class="event-time">{await get_event_time(event)}</div>
                            <div class="event-content">{await get_event_description(event)}</div>
                        </div>
                        <img src="{await get_event_banner(event)}" alt="{await get_event_name(event)}" class="event-img">
                    </div>
                    """ for event in special_events])}
                </div>
            </div>
            ''' if special_events else ''}

            <!-- 一般活动部分 -->
            {f'''
            <div class="mb-8">
                <div class="flex flex_align_center section-title">
                    <h2 style="text-align: center;">一般活动</h2>
                    <span class="icon"><i class="fa fa-pagelines"></i></span>
                </div>
                <div class="event-grid">
                    {''.join([f"""
                    <div class="event-card calendar-event">
                        <div class="content">
                            <div class="event-author">{await get_event_name(event)}</div>
                            <div class="event-time">{await get_event_time(event)}</div>
                            <div class="event-content">{await get_event_description(event)}</div>
                        </div>
                        <img src="{await get_event_banner(event)}" alt="{await get_event_name(event)}" class="event-img">
                    </div>
                    """ for event in normal_events])}
                </div>
            </div>
            ''' if normal_events else ''}

            <!-- 邮箱事件部分 -->
            {f'''
            <div class="mb-8">
                <div class="flex flex_align_center section-title">
                    <h2 style="text-align: center;">邮箱事件</h2>
                    <span class="icon"><i class="fa fa-envelope"></i></span>
                </div>
                <div class="event-grid">
                    {''.join([f"""
                    <div class="event-card mail-event event-card-email">
                        <div class="content content-email">
                            <div class="event-author">{await get_event_name(event)}</div>
                            <div class="event-time">{await get_event_time(event)}</div>
                            <div class="event-content">{await get_event_description(event)}</div>
                        </div>
                    </div>
                    """ for event in mail_events])}
                </div>
            </div>
            ''' if mail_events else ''}
        </div>
    </body>
    </html>
    """
    return html


async def get_event_time(event):
    """获取事件时间"""
    lines = event.split("\n")
    for line in lines:
        if "持续时间：" in line:
            time_str = line.replace("持续时间：", "").strip()
            return time_str
    return "时间未知"


async def get_event_description(event):
    """获取事件描述"""
    lines = event.split("\n")
    description_lines = []
    skip_lines = 0

    for i, line in enumerate(lines):
        if i < skip_lines:
            continue

        if (
            "【" in line
            and "】" in line
            or "持续时间：" in line
            or line.startswith("名称：")
            or line.startswith("banner：")
        ):
            skip_lines = i + 1
            continue

        if line.strip():
            description_lines.append(line)

    return "\n".join(description_lines)


async def get_event_banner(event):
    """获取事件banner图片路径（返回 file:// URL 供 HTML img src 使用）"""
    from ...config import STICKER_DIR, BANNER_DIR, ICON_DIR

    no_image_path = (BANNER_DIR / "banner_No_Image.png").resolve().as_uri()

    lines = event.split("\n")
    for line in lines:
        if line.startswith("banner："):
            banner_path = line.replace("banner：", "").strip()
            if Path(banner_path).is_absolute():
                full_path = Path(banner_path)
            elif banner_path.startswith("icon:"):
                full_path = ICON_DIR / banner_path.replace("icon:", "")
            elif (
                banner_path.startswith("sticker_eas_")
                or banner_path.startswith("sticker_singleraid_")
                or banner_path.startswith("sticker_love_")
            ):
                full_path = STICKER_DIR / banner_path
            else:
                full_path = BANNER_DIR / banner_path
            if full_path.exists():
                return full_path.resolve().as_uri()
            return no_image_path
    return no_image_path


async def generate_ark_level_chart(data: dict, target_level: int) -> MessageSegment:
    """生成主方舟等级与超频等级关系图以及超频等级升级消耗图

    Args:
        data: 游戏数据
        target_level: 指定的目标超频等级，如果提供则会在图中标注，并将图表范围限制到该等级

    Returns:
        MessageSegment: 包含图表的消息段
    """
    from .es_string_utils import get_string_item
    from ...config import CUSTOM_FONT

    try:
        if "ark_enhance" not in data or "json" not in data["ark_enhance"]:
            logger.error("数据中缺少ark_enhance或其json字段")
            return MessageSegment.text("生成统计图失败: 缺少方舟强化数据")

        if "ark_overclock" not in data or "json" not in data["ark_overclock"]:
            logger.error("数据中缺少ark_overclock或其json字段")
            return MessageSegment.text("生成统计图失败: 缺少超频数据")
        all_overclock_costs = []
        all_overclock_levels_cost = []

        extra_items_data = {}  # 格式: {item_no: {levels: [], costs: []}}

        level_cost_map = {}
        for overclock in data["ark_overclock"]["json"]:
            level = overclock.get("overclock_level", 0)
            cost = overclock.get("mana_crystal", 0)
            if level is not None and cost is not None:
                level_cost_map[level] = cost

                for i in range(10):  # 最多有10个魔力粉尘
                    item_no_key = f"pay_item_no_{i}"
                    item_amount_key = f"pay_amount_{i}"
                    if item_no_key in overclock and item_amount_key in overclock:
                        item_no = overclock[item_no_key]
                        item_amount = overclock[item_amount_key]
                        if item_no and item_amount:
                            if item_no not in extra_items_data:
                                extra_items_data[item_no] = {"levels": [], "costs": []}
                            if level not in [
                                l for l in extra_items_data[item_no]["levels"]
                            ]:
                                extra_items_data[item_no]["levels"].append(level)
                                extra_items_data[item_no]["costs"].append(item_amount)

        sorted_cost_levels = sorted(level_cost_map.keys())
        for level in sorted_cost_levels:
            all_overclock_levels_cost.append(level)
            all_overclock_costs.append(level_cost_map[level])

        max_overclock_level = (
            max(all_overclock_levels_cost) if all_overclock_levels_cost else 0
        )

        plot_max_level = target_level if target_level else max_overclock_level

        overclock_levels_cost = []
        overclock_costs = []
        for i, level in enumerate(all_overclock_levels_cost):
            if level <= plot_max_level:
                overclock_levels_cost.append(level)
                overclock_costs.append(all_overclock_costs[i])

        filtered_extra_items_data = {}
        for item_no, item_data in extra_items_data.items():
            filtered_levels = []
            filtered_costs = []
            for i, level in enumerate(item_data["levels"]):
                if i < len(item_data["costs"]) and level <= plot_max_level:
                    filtered_levels.append(level)
                    filtered_costs.append(item_data["costs"][i])
            if filtered_levels:
                item_name = (await get_string_item(data, item_no)).get("zh_tw", "")
                if not item_name:
                    item_name = f"{item_no}"
                filtered_extra_items_data[item_no] = {
                    "levels": filtered_levels,
                    "costs": filtered_costs,
                    "name": item_name,
                }

        fig, ax1 = plt.subplots(figsize=(12, 8))
        ax1.set_xlabel("超频等级", fontproperties=CUSTOM_FONT)
        ax1.set_ylabel("魔力水晶消耗", color="red", fontproperties=CUSTOM_FONT)
        ax1.plot(
            overclock_levels_cost,
            overclock_costs,
            "r-",
            marker="o",
            markersize=3,
            label="魔力水晶",
        )
        ax1.tick_params(axis="y", labelcolor="red")
        ax1.grid(True, linestyle="--", alpha=0.7, axis="both")

        if filtered_extra_items_data:
            ax2 = ax1.twinx()
            ax2.set_ylabel("魔力粉尘消耗", color="blue", fontproperties=CUSTOM_FONT)

            # 颜色循环
            colors = ["g", "c", "m", "y", "k", "b"]
            color_index = 0

            for item_no, item_data in filtered_extra_items_data.items():
                if len(item_data["levels"]) != len(item_data["costs"]):
                    logger.warning(
                        f"物品 {item_no} 数据维度不匹配: levels({len(item_data['levels'])}) != costs({len(item_data['costs'])})"
                    )
                    continue

                if len(item_data["levels"]) == 0:
                    continue

                color = colors[color_index % len(colors)]
                ax2.plot(
                    item_data["levels"],
                    item_data["costs"],
                    f"{color}-",
                    marker="o",
                    markersize=3,
                    label=item_data["name"],
                )
                color_index += 1

            ax2.tick_params(axis="y", labelcolor="blue")

            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(
                lines1 + lines2, labels1 + labels2, loc="upper left", prop=CUSTOM_FONT
            )
        else:
            ax1.legend(loc="upper left", prop=CUSTOM_FONT)

        plt.title(
            f"超频等级升级消耗图 (1-{plot_max_level}级)", fontproperties=CUSTOM_FONT
        )

        if overclock_levels_cost:
            x_max = max(overclock_levels_cost)
            if x_max <= 50:
                x_interval = 5
            elif x_max <= 100:
                x_interval = 10
            elif x_max <= 500:
                x_interval = 50
            else:
                x_interval = 100
            ax1.set_xlim(0, x_max)
            ax1.set_xticks(range(0, x_max + 1, x_interval))

        ax1.grid(True, linestyle="--", alpha=0.7)
        if target_level and target_level <= plot_max_level:
            ax1.axvline(x=target_level, color="purple", linestyle="--", alpha=0.7)
            ax1.text(
                target_level,
                ax1.get_ylim()[1] * 0.95,
                f"当前等级: {target_level}",
                color="purple",
                ha="right",
                va="top",
                fontproperties=CUSTOM_FONT,
            )

        plt.tight_layout()

        buffer = BytesIO()
        plt.savefig(buffer, format="webp", dpi=300, bbox_inches="tight")
        plt.close()

        buffer.seek(0)
        image_bytes = buffer.getvalue()

        return MessageSegment.image(image_bytes)

    except Exception as e:
        import traceback

        error_trace = traceback.format_exc()
        logger.error(f"生成统计图时发生错误: {str(e)}\n{error_trace}")
        return MessageSegment.text("生成统计图失败")


async def generate_level_cost_chart(data: dict) -> MessageSegment:
    """生成等级升级消耗统计图"""
    from ...config import CUSTOM_FONT

    try:
        # 收集数据
        levels = []
        gold_costs = []
        mana_dust_costs = []
        mana_crystal_costs = []

        sorted_levels = sorted(
            [item for item in data["level"]["json"] if "level" in item],
            key=lambda x: x["level"],
        )

        for item in sorted_levels:
            level = item.get("level")
            if level is not None:
                levels.append(level)
                gold_costs.append(item.get("gold", 0))
                mana_dust_costs.append(item.get("mana_dust", 0))
                mana_crystal_costs.append(
                    item.get("mana_crystal", 0) if "mana_crystal" in item else 0
                )

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
        ax1.plot(levels, gold_costs, "g-", marker="o", markersize=2)
        ax1.set_title("金币消耗统计", fontproperties=CUSTOM_FONT)
        ax1.set_xlabel("等级", fontproperties=CUSTOM_FONT)
        ax1.set_ylabel("消耗数量", fontproperties=CUSTOM_FONT)
        ax1.grid(True, linestyle="--", alpha=0.7)
        ax1.set_xticks(range(0, max_level + 1, x_interval))
        ax1.tick_params(axis="x", rotation=45)
        ax1.ticklabel_format(style="sci", axis="y", scilimits=(0, 0))

        # 绘制魔力粉尘消耗
        ax2.plot(levels, mana_dust_costs, "b-", marker="o", markersize=2)
        ax2.set_title("魔力粉尘消耗统计", fontproperties=CUSTOM_FONT)
        ax2.set_xlabel("等级", fontproperties=CUSTOM_FONT)
        ax2.set_ylabel("消耗数量", fontproperties=CUSTOM_FONT)
        ax2.grid(True, linestyle="--", alpha=0.7)
        ax2.set_xticks(range(0, max_level + 1, x_interval))
        ax2.tick_params(axis="x", rotation=45)

        # 绘制魔力水晶消耗
        ax3.plot(levels, mana_crystal_costs, "r-", marker="o", markersize=2)
        ax3.set_title("魔力水晶消耗统计", fontproperties=CUSTOM_FONT)
        ax3.set_xlabel("等级", fontproperties=CUSTOM_FONT)
        ax3.set_ylabel("消耗数量", fontproperties=CUSTOM_FONT)
        ax3.grid(True, linestyle="--", alpha=0.7)
        ax3.set_xticks(range(0, max_level + 1, x_interval))
        ax3.tick_params(axis="x", rotation=45)

        plt.tight_layout(pad=3.0)

        buffer = BytesIO()
        plt.savefig(buffer, format="webp", dpi=300, bbox_inches="tight")
        plt.close()

        buffer.seek(0)
        image_bytes = buffer.getvalue()
        return MessageSegment.image(image_bytes)

    except Exception as e:
        logger.error(f"生成等级消耗统计图时发生错误: {str(e)}")
        return MessageSegment.text("生成统计图失败")


async def get_battle_power_percentage(
    data: dict, effect_type: int, effect_no: int
) -> float:
    """获取潜能对应的战力百分比

    Args:
        data: JSON数据字典
        effect_no: 效果编号

    Returns:
        float: 战力百分比，如果没有找到则返回None
    """
    if effect_type == 1:
        for buff in data["contents_buff"]["json"]:
            if buff.get("no") == effect_no:
                return buff.get("battle_power_per", 0)


def get_unique_level(unique_type: int, level: int) -> int:
    """获取潜能Unique等级
    HeroOptionInfoExtension_UniqueLevel__Enum Info::HeroOptionInfoExtension::GetUniqueLevel
    Args:
        unique_type: 潜能Unique类型
        level: 潜能等级

    Returns:
        int: Unique等级 (1-4)
    """
    # 废弃了
    if unique_type == 3:
        if level >= 1:  # HeroOptionUniqueLevel = 1
            return 4

    # 现在用的
    if unique_type == 2:
        if level >= 16:  # HeroOptionHighLevel4 = 16
            return 4
        if level >= 11:  # HeroOptionHighLevel3 = 11
            return 3
        if level >= 6:  # HeroOptionHighLevel2 = 6
            return 2
    return 1


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
                potentials[tooltip_sno].append(
                    (
                        option.get("level", 0),
                        option.get("effect_type", 0),
                        option.get("effect_no1", 0),
                        option.get("option", 0),
                        option.get("unique", 0),
                    )
                )

        # 获取潜能名称
        potential_names = {}  # {tooltip_sno: name}
        for string in data["string_ui"]["json"]:
            if string.get("no") in potentials:
                potential_names[string["no"]] = (
                    string.get("zh_tw", "")
                    if string.get("zh_tw", "") != ""
                    else string.get("zh_cn", "")
                )

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
                    text-align: center;
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

        # 等级列
        max_level = max(
            level
            for tooltip_sno in potentials
            for level, _, _, _, _ in potentials[tooltip_sno]
        )
        for level in range(1, max_level + 1):
            html += f"<th>Lv.{level}</th>"

        html += "</tr>"

        for tooltip_sno, name in sorted(
            potential_names.items(), key=lambda x: x[0]
        ):  # 修改排序键为x[0]
            html += f"<tr><td class='potential-name'>{name}</td>"
            level_data = {
                level: (effect_type, effect_no, option, unique)
                for level, effect_type, effect_no, option, unique in potentials[
                    tooltip_sno
                ]
            }
            for level in range(1, max_level + 1):
                if level in level_data:
                    effect_type, effect_no, option, unique = level_data[level]
                    value = await get_potential_value(data, effect_type, effect_no)
                    battle_power_per = await get_battle_power_percentage(
                        data, effect_type, effect_no
                    )

                    # 获取颜色样式
                    unique_level = get_unique_level(unique, level)
                    color_style = ""
                    if unique_level == 4:
                        color_style = "color: #FF8B99;"
                    elif unique_level == 3:
                        color_style = "color: #5DA4FF;"
                    elif unique_level == 2:
                        color_style = "color: #67CFB6;"

                    if battle_power_per:
                        html += f"<td class='value-cell' style='{color_style}'>{value}<br><span class='power-value'>+{battle_power_per}</span></td>"
                    else:
                        html += f"<td style='{color_style}'>{value}</td>"
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


async def generate_zodiac_html(data: dict) -> str:
    """生成星座信息HTML"""
    try:
        # 获取所有星座类型及其信息
        zodiac_info = {}
        for node in data["zodiac"]["json"]:
            zodiac_type = node.get("zodiac_type")
            zodiac_type_sno = node.get("zodiac_type_sno")
            if zodiac_type and zodiac_type_sno:
                zodiac_info[zodiac_type] = zodiac_type_sno

        # 按星座类型排序
        sorted_zodiac_types = sorted(zodiac_info.keys())

        html_content = ""

        for zodiac_type in sorted_zodiac_types:
            zodiac_type_sno = zodiac_info[zodiac_type]

            # 获取星座名称
            from .es_string_utils import get_zodiac_name, format_zodiac_nodes

            zodiac_name = await get_zodiac_name(data, zodiac_type_sno)

            # 获取该星座的所有节点和祝福信息
            zodiac_data = await format_zodiac_nodes(data, zodiac_type)
            nodes = zodiac_data["nodes"]
            blessing = zodiac_data["blessing"]

            if not nodes:
                continue

            # 为每个星座生成表格
            html_content += f"""
            <div class="zodiac-section">
                <h2>{zodiac_name}</h2>
                <table class="zodiac-table">
                    <thead>
                        <tr>
                            <th>数据表编号</th>
                            <th>节点编号</th>
                            <th>前置节点</th>
                            <th>消耗点数</th>
                            <th>效果描述</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            for node in nodes:
                # 格式化前置节点显示
                require_nodes = node["require_nodes"]
                if require_nodes == "0":
                    require_display = "无"
                else:
                    require_display = require_nodes.replace(",", ", ")

                # 消耗点数显示（0点消耗显示为"初始"）
                need_point_display = (
                    "初始" if node["need_point"] == 0 else str(node["need_point"])
                )

                html_content += f"""
                        <tr>
                            <td class="data-no">{node['no']}</td>
                            <td class="node-no">{node['node_no']}</td>
                            <td>{require_display}</td>
                            <td class="need-points">{need_point_display}</td>
                            <td class="description">{node['description']}</td>
                        </tr>
                """

            html_content += """
                    </tbody>
                </table>
            """

            # 如果有祝福效果，添加祝福信息
            if blessing:
                html_content += f"""
                <div class="blessing-section">
                    <h3>🌟 完成祝福</h3>
                    <div class="blessing-text">{blessing}</div>
                </div>
                """

            html_content += """
            </div>
            """

        # 完整的HTML模板
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>星座信息</title>
            <style>
                body {{
                    font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                    color: #333;
                }}
                
                .zodiac-section {{
                    margin-bottom: 30px;
                    background-color: #ffffff;
                    border-radius: 8px;
                    padding: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                
                h2 {{
                    color: #2c3e50;
                    text-align: center;
                    margin-bottom: 20px;
                    font-size: 24px;
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 10px;
                }}
                
                .zodiac-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                    font-size: 14px;
                }}
                
                .zodiac-table th {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 12px 6px;
                    text-align: center;
                    font-weight: bold;
                    border: 1px solid #ddd;
                    font-size: 12px;
                }}
                
                .zodiac-table td {{
                    padding: 8px 6px;
                    border: 1px solid #ddd;
                    text-align: center;
                    background-color: #fafafa;
                    font-size: 12px;
                }}
                
                .zodiac-table tbody tr:nth-child(even) {{
                    background-color: #f9f9f9;
                }}
                
                .zodiac-table tbody tr:hover {{
                    background-color: #e8f4f8;
                }}
                
                .data-no {{
                    font-weight: bold;
                    color: #8e44ad;
                    background-color: #f8f4ff !important;
                    font-size: 11px;
                }}
                
                .node-no {{
                    font-weight: bold;
                    color: #e74c3c;
                    background-color: #fff5f5 !important;
                }}
                
                .need-points {{
                    font-weight: bold;
                    color: #f39c12;
                }}
                
                .description {{
                    text-align: left;
                    max-width: 400px;
                    word-wrap: break-word;
                    font-size: 13px;
                    line-height: 1.4;
                }}
                
                .blessing-section {{
                    margin-top: 15px;
                    padding: 15px;
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                    border-radius: 8px;
                    color: white;
                    text-align: center;
                }}
                
                .blessing-section h3 {{
                    margin: 0 0 10px 0;
                    font-size: 18px;
                }}
                
                .blessing-text {{
                    font-size: 14px;
                    font-weight: bold;
                    background-color: rgba(255,255,255,0.2);
                    padding: 10px;
                    border-radius: 5px;
                }}
                
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                }}
                
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                }}
                
                .header p {{
                    margin: 10px 0 0 0;
                    font-size: 16px;
                    opacity: 0.9;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🌟 星座信息大全 🌟</h1>
                <p>EverSoul 星座系统详细信息</p>
            </div>
            {html_content}
        </body>
        </html>
        """

        return html

    except Exception as e:
        logger.error(f"生成星座HTML时发生错误: {e}")
        raise


async def generate_building_html(data: dict) -> str:
    """生成建筑信息HTML"""
    try:
        from .es_string_utils import format_building_data

        buildings = await format_building_data(data)

        if not buildings:
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>建筑信息</title>
                <style>
                    body {
                        font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
                        margin: 20px;
                        background-color: #f5f5f5;
                        color: #333;
                        text-align: center;
                        padding: 50px;
                    }
                </style>
            </head>
            <body>
                <h1>暂无建筑信息</h1>
                <p>未找到符合条件的建筑数据</p>
            </body>
            </html>
            """

        # 按buff_type分组建筑
        building_groups = {}
        buff_type_names = {
            50: "攻击力提升",
            51: "防御力提升",
            52: "生命值提升",
            53: "暴击威力提升",
            54: "命中率提升",
            55: "回避率提升",
            56: "魔法抗性提升",
            57: "物理抗性提升",
            58: "生命吸取提升",
        }

        for building in buildings:
            buff_type = building["buff_type"]
            type_name = buff_type_names.get(buff_type, f"类型{buff_type}")
            if type_name not in building_groups:
                building_groups[type_name] = []
            building_groups[type_name].append(building)

        html_content = ""

        for type_name, type_buildings in building_groups.items():
            html_content += f"""
            <div class="building-section">
                <h2>{type_name}</h2>
                <div class="buildings-grid">
            """

            for building in type_buildings:
                img_html = ""
                if building["img_path"] and os.path.exists(building["img_path"]):
                    img_html = f'<img src="file:///{building["img_path"]}" alt="{building["name"]}" class="building-image">'

                grade_class = (
                    "grade-"
                    + building["grade"].replace("★", "star").replace(" ", "").lower()
                    if building["grade"]
                    else "grade-default"
                )

                html_content += f"""
                <div class="building-card">
                    <div class="building-header">
                        {img_html}
                        <div class="building-info">
                            <h3 class="building-name">{building["name"]}</h3>
                            <div class="building-grade {grade_class}">{building["grade"]}</div>
                        </div>
                    </div>
                    <div class="building-content">
                        <div class="building-description">{building["description"]}</div>
                        <div class="building-buff">
                            <strong></strong>{building["buff_description"]}{building["battle_power_per"]}
                        </div>
                    </div>
                </div>
                """

            html_content += """
                </div>
            </div>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>建筑信息</title>
            <style>
                body {{
                    font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                    color: #333;
                }}
                
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                    background: linear-gradient(135deg, #8b4513 0%, #a0522d 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                }}
                
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                }}
                
                .header p {{
                    margin: 10px 0 0 0;
                    font-size: 16px;
                    opacity: 0.9;
                }}
                
                .building-section {{
                    margin-bottom: 30px;
                    background-color: #ffffff;
                    border-radius: 8px;
                    padding: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                
                .building-section h2 {{
                    color: #8b4513;
                    text-align: center;
                    margin-bottom: 20px;
                    font-size: 20px;
                    border-bottom: 2px solid #d2b48c;
                    padding-bottom: 10px;
                }}
                
                .buildings-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                    gap: 15px;
                }}
                
                .building-card {{
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    padding: 15px;
                    background-color: #fafafa;
                    transition: box-shadow 0.3s ease;
                }}
                
                .building-card:hover {{
                    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
                }}
                
                .building-header {{
                    display: flex;
                    align-items: center;
                    margin-bottom: 15px;
                }}
                
                .building-image {{
                    width: 60px;
                    height: 60px;
                    object-fit: cover;
                    border-radius: 6px;
                    margin-right: 15px;
                    border: 2px solid #ddd;
                }}
                
                .building-info {{
                    flex: 1;
                }}
                
                .building-name {{
                    margin: 0 0 5px 0;
                    font-size: 16px;
                    font-weight: bold;
                    color: #8b4513;
                }}
                
                .building-grade {{
                    font-size: 12px;
                    padding: 2px 8px;
                    border-radius: 4px;
                    display: inline-block;
                    font-weight: bold;
                }}
                
                .grade-default {{
                    background-color: #e0e0e0;
                    color: #666;
                }}
                
                .grade-1star {{
                    background-color: #f0f0f0;
                    color: #666;
                }}
                
                .grade-2star {{
                    background-color: #e8f5e8;
                    color: #2e7d32;
                }}
                
                .grade-3star {{
                    background-color: #e3f2fd;
                    color: #1976d2;
                }}
                
                .grade-4star {{
                    background-color: #f3e5f5;
                    color: #7b1fa2;
                }}
                
                .grade-5star {{
                    background-color: #fff3e0;
                    color: #f57c00;
                }}
                
                .building-content {{
                    border-top: 1px solid #eee;
                    padding-top: 15px;
                }}
                
                .building-description {{
                    font-size: 13px;
                    color: #666;
                    margin-bottom: 10px;
                    line-height: 1.4;
                }}
                
                .building-buff {{
                    font-size: 14px;
                    color: #2e7d32;
                    background-color: #e8f5e8;
                    padding: 8px 12px;
                    border-radius: 6px;
                    border-left: 3px solid #4caf50;
                }}
                
                .building-buff strong {{
                    color: #1b5e20;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🏰 建筑信息大全 🏰</h1>
                <p>EverSoul 建筑系统详细信息</p>
            </div>
            {html_content}
        </body>
        </html>
        """

        return html

    except Exception as e:
        logger.error(f"生成建筑HTML时发生错误: {e}")
        raise


async def generate_love_level_html(data: dict) -> str:
    """生成好感等级信息HTML"""
    try:
        from .es_string_utils import format_love_level_data, get_love_buff_type_name

        love_levels = await format_love_level_data(data)

        html_content = f"""
        <div class="love-level-section">
            <h2>好感等级信息</h2>
            <table class="love-level-table">
                <thead>
                    <tr>
                        <th>等级</th>
                        <th>所需好感度</th>
                        <th>累计好感度</th>
                        <th>效果列表</th>
                    </tr>
                </thead>
                <tbody>
        """

        for level_info in love_levels:
            # 好感度
            lovepoint_display = (
                f"{level_info['lovepoint']}" if level_info["lovepoint"] > 0 else "-"
            )
            total_lovepoint_display = (
                str(level_info["total_lovepoint"])
                if level_info["total_lovepoint"] > 0
                else "-"
            )

            # 效果
            effects_html = ""
            if level_info["buffs"]:
                for buff in level_info["buffs"]:
                    if buff["description"]:
                        effects_html += (
                            f"<div class='buff-item'>{buff['description']}</div>"
                        )
                    elif buff["type"]:
                        buff_name = await get_love_buff_type_name(buff["type"])
                        effects_html += f"<div class='buff-item'>新增{buff_name}</div>"

            html_content += f"""
                    <tr>
                        <td class="level">{level_info['level']}</td>
                        <td class="lovepoint">{lovepoint_display}</td>
                        <td class="total-lovepoint">{total_lovepoint_display}</td>
                        <td class="effects">{effects_html}</td>
                    </tr>
            """

        html_content += """
                </tbody>
            </table>
        </div>
        """

        # 完整的HTML模板
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>好感等级信息</title>
            <style>
                body {{
                    font-family: "Microsoft YaHei", "SimHei", Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                    color: #333;
                }}
                
                .love-level-section {{
                    margin-bottom: 30px;
                    background-color: #ffffff;
                    border-radius: 8px;
                    padding: 20px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                
                h2 {{
                    color: #2c3e50;
                    text-align: center;
                    margin-bottom: 20px;
                    font-size: 24px;
                    border-bottom: 2px solid #e74c3c;
                    padding-bottom: 10px;
                }}
                
                .love-level-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                    font-size: 14px;
                }}
                
                .love-level-table th {{
                    background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
                    color: white;
                    padding: 12px 8px;
                    text-align: center;
                    font-weight: bold;
                    border: 1px solid #ddd;
                }}
                
                .love-level-table td {{
                    padding: 10px 8px;
                    border: 1px solid #ddd;
                    text-align: center;
                    background-color: #fafafa;
                    vertical-align: top;
                }}
                
                .love-level-table tbody tr:nth-child(even) {{
                    background-color: #f9f9f9;
                }}
                
                .love-level-table tbody tr:hover {{
                    background-color: #fff5f5;
                }}
                
                .level {{
                    font-weight: bold;
                    color: #e74c3c;
                    background-color: #fff5f5 !important;
                    font-size: 16px;
                }}
                
                .lovepoint {{
                    font-weight: bold;
                    color: #f39c12;
                }}
                
                .total-lovepoint {{
                    font-weight: bold;
                    color: #27ae60;
                }}
                
                .effects {{
                    text-align: left;
                    max-width: 400px;
                    word-wrap: break-word;
                }}
                
                .buff-item {{
                    background-color: #e8f6f3;
                    margin: 2px 0;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 13px;
                    border-left: 3px solid #27ae60;
                }}
                
                .special-effect {{
                    background-color: #fef9e7;
                    margin: 2px 0;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 13px;
                    border-left: 3px solid #f39c12;
                }}
                
                .no-effect {{
                    color: #95a5a6;
                    font-style: italic;
                    font-size: 13px;
                }}
                
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                    background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                }}
                
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                }}
                
                .header p {{
                    margin: 10px 0 0 0;
                    font-size: 16px;
                    opacity: 0.9;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>💕 好感等级信息大全 💕</h1>
                <p>EverSoul 好感等级系统详细信息</p>
            </div>
            {html_content}
        </body>
        </html>
        """

        return html

    except Exception as e:
        logger.error(f"生成好感等级HTML时发生错误: {e}")
        raise


async def generate_skill_description_image(
    skill_descriptions: list,
    skill_name: str = "",
    skill_type: str = "",
    support: bool = False,
    icon_bytes: bytes = None,
    extra_info: dict = None,
    server: str = "global",
    data_type: str = "live",
) -> bytes:
    """
    生成技能描述图片
    Args:
        skill_descriptions: 技能描述列表
        skill_name: 技能名称（已根据服务器类型选择的语言）
        skill_type: 技能类型（已根据服务器类型选择的语言）
        support: 是否为支援技能
        icon_bytes: 技能图标字节流
        extra_info: 额外信息（如遗物属性），格式：
            {
                "description": "描述文字",
                "stats": ["属性1", "属性2", ...],
                "battle_power_per": 数值,
                "max_level": 数值
            }
        server: 服务器类型 (global/cn/jp)
        data_type: 数据类型 (live/review)
    Returns:
        bytes: WebP图片字节流（quality=85, method=6高压缩）
    """
    from ...config import FONT_DIR

    # 颜色定义
    BG_COLOR = (30, 32, 40, 255)
    TEXT_GRAY = (148, 150, 170)  # 灰色 #9495A9
    TEXT_GREEN = (45, 155, 0)  # 绿色 #2C9A00
    TEXT_HIGHLIGHT = (255, 255, 255)  # 白色高亮

    # 画布和字体设置
    CANVAS_WIDTH = 800
    PADDING_X = 40
    PADDING_Y = 40
    FONT_SIZE = 24
    FONT_SIZE_SMALL = 18  # 技能类型用小字号
    CHECKMARK_SIZE = 22
    ICON_SIZE = 64  # 技能图标大小

    try:
        font = ImageFont.truetype(str(FONT_DIR), FONT_SIZE, index=0)
        font_small = ImageFont.truetype(str(FONT_DIR), FONT_SIZE_SMALL, index=0)
    except Exception:
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()

    img = Image.new("RGBA", (CANVAS_WIDTH, 5000), BG_COLOR)
    draw = ImageDraw.Draw(img)

    cursor_y = PADDING_Y

    # 绘制标题
    if skill_type and skill_name:
        icon_x = PADDING_X
        text_x = PADDING_X + (ICON_SIZE + 15 if icon_bytes else 0)

        # 绘制技能图标
        if icon_bytes:
            try:
                icon_img = Image.open(BytesIO(icon_bytes))

                if icon_img.mode != "RGBA":
                    icon_img = icon_img.convert("RGBA")
                width, height = icon_img.size
                if width != height:
                    min_side = min(width, height)
                    left = (width - min_side) // 2
                    top = (height - min_side) // 2
                    right = left + min_side
                    bottom = top + min_side
                    icon_img = icon_img.crop((left, top, right, bottom))
                icon_img = icon_img.resize(
                    (ICON_SIZE, ICON_SIZE), Image.Resampling.LANCZOS
                )
                mask = Image.new("L", (ICON_SIZE, ICON_SIZE), 0)
                mask_draw = ImageDraw.Draw(mask)
                try:
                    mask_draw.rounded_rectangle(
                        [(0, 0), (ICON_SIZE, ICON_SIZE)], radius=8, fill=255
                    )
                except AttributeError:
                    mask_draw.ellipse([(0, 0), (ICON_SIZE, ICON_SIZE)], fill=255)

                output_icon = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
                output_icon.paste(icon_img, (0, 0))
                output_icon.putalpha(mask)

                img.paste(output_icon, (icon_x, cursor_y), output_icon)
            except Exception as e:
                logger.error(f"加载技能图标失败: {e}")

        # 技能类型文字尺寸
        try:
            if hasattr(font_small, "getbbox"):
                type_bbox = font_small.getbbox(skill_type)
                type_width = type_bbox[2] - type_bbox[0]
                type_height = type_bbox[3] - type_bbox[1]
            else:
                type_width, type_height = font_small.getsize(skill_type)
        except:
            type_width = len(skill_type) * FONT_SIZE_SMALL
            type_height = FONT_SIZE_SMALL

        type_y = cursor_y
        rect_padding_left = 4
        rect_padding_right = 12
        rect_padding_y = 2

        rect_x1 = text_x - rect_padding_left
        rect_y1 = type_y - rect_padding_y
        rect_x2 = text_x + type_width * 3 + rect_padding_right
        rect_y2 = type_y + type_height + rect_padding_y

        rect_bg_color = (45, 47, 55, 255)
        draw.rectangle([rect_x1, rect_y1, rect_x2, rect_y2], fill=rect_bg_color)
        draw.text((text_x, type_y), skill_type, font=font_small, fill=TEXT_GRAY)

        # 技能类型高度
        try:
            if hasattr(font_small, "getbbox"):
                type_height = font_small.getbbox(skill_type)[3]
            else:
                type_height = font_small.getsize(skill_type)[1]
        except:
            type_height = FONT_SIZE_SMALL

        # 技能名称
        name_y = type_y + type_height + 4
        draw.text((text_x, name_y), skill_name, font=font, fill=TEXT_HIGHLIGHT)

        try:
            if hasattr(font, "getbbox"):
                name_height = font.getbbox(skill_name)[3]
            else:
                name_height = font.getsize(skill_name)[1]
        except:
            name_height = FONT_SIZE

        text_total_height = type_height + 4 + name_height
        cursor_y += max(ICON_SIZE, text_total_height) + 20

    if extra_info:
        if extra_info.get("description"):
            desc_text = extra_info["description"]
            max_width = CANVAS_WIDTH - PADDING_X * 2
            current_line = ""

            i = 0
            while i < len(desc_text):
                char = desc_text[i]

                # \r\n
                if char == "\r" and i + 1 < len(desc_text) and desc_text[i + 1] == "\n":
                    if current_line:
                        draw.text(
                            (PADDING_X, cursor_y),
                            current_line,
                            font=font_small,
                            fill=TEXT_GRAY,
                        )
                        cursor_y += FONT_SIZE_SMALL + 2
                        current_line = ""
                    i += 2  # 跳过 \r\n
                    continue

                # \n 或 \r
                if char == "\n" or char == "\r":
                    if current_line:
                        draw.text(
                            (PADDING_X, cursor_y),
                            current_line,
                            font=font_small,
                            fill=TEXT_GRAY,
                        )
                        cursor_y += FONT_SIZE_SMALL + 2
                        current_line = ""
                    i += 1
                    continue

                test_line = current_line + char
                try:
                    if hasattr(font_small, "getlength"):
                        line_width = font_small.getlength(test_line)
                    else:
                        line_width = font_small.getsize(test_line)[0]
                except:
                    line_width = len(test_line) * FONT_SIZE_SMALL
                if line_width > max_width and current_line:
                    draw.text(
                        (PADDING_X, cursor_y),
                        current_line,
                        font=font_small,
                        fill=TEXT_GRAY,
                    )
                    cursor_y += FONT_SIZE_SMALL + 2
                    current_line = char
                else:
                    current_line = test_line

                i += 1

            if current_line:
                draw.text(
                    (PADDING_X, cursor_y), current_line, font=font_small, fill=TEXT_GRAY
                )
                cursor_y += FONT_SIZE_SMALL + 2

            cursor_y += 6

        if extra_info.get("battle_power_per"):
            battle_power_text = f"战力百分比：{extra_info['battle_power_per']}"
            draw.text(
                (PADDING_X, cursor_y),
                battle_power_text,
                font=font_small,
                fill=TEXT_GRAY,
            )
            cursor_y += FONT_SIZE_SMALL + 8

        if extra_info.get("max_level") and extra_info.get("stats"):
            for stat in extra_info["stats"]:
                draw.text((PADDING_X, cursor_y), stat, font=font_small, fill=TEXT_GRAY)
                cursor_y += FONT_SIZE_SMALL + 2

        line_y = cursor_y + 10
        draw.line(
            [(PADDING_X, line_y), (CANVAS_WIDTH - PADDING_X, line_y)],
            fill=(60, 62, 70),
            width=2,
        )
        cursor_y = line_y + 15

    for desc in skill_descriptions:
        level = desc.get("hero_level", desc.get("level", 1))

        # 根据服务器和数据类型选择描述语言
        if server == "cn":
            # 国服使用简体中文
            desc_text = desc.get(
                "desc_zh_cn", desc.get("desc_zh_tw", desc.get("desc", ""))
            )
        elif server == "jp":
            # 日服使用日文
            desc_text = desc.get("desc_ja", desc.get("desc_kr", desc.get("desc", "")))
        elif server == "global":
            if data_type == "review":
                # 国际服review使用韩文
                desc_text = desc.get(
                    "desc_kr", desc.get("desc_zh_tw", desc.get("desc", ""))
                )
            else:
                # 国际服live使用繁体中文
                desc_text = desc.get(
                    "desc_zh_tw", desc.get("desc_zh_cn", desc.get("desc", ""))
                )
        else:
            # 默认使用繁体中文
            desc_text = desc.get(
                "desc_zh_tw", desc.get("desc_zh_cn", desc.get("desc", ""))
            )

        is_upgrade = level > 1 and not support
        default_color = TEXT_GREEN if is_upgrade else TEXT_GRAY

        if not support:
            level_prefix = f"等级{level}："
            desc_text = level_prefix + desc_text

        segments = await _parse_rich_text_segments(desc_text, default_color)
        if is_upgrade:
            await _draw_checkmark(draw, PADDING_X, cursor_y + 4, CHECKMARK_SIZE)
            text_x = PADDING_X + CHECKMARK_SIZE + 15
            max_w = CANVAS_WIDTH - text_x - PADDING_X
            cursor_y = await _draw_text_block(
                draw, segments, text_x, cursor_y, max_w, font
            )
        else:
            max_w = CANVAS_WIDTH - PADDING_X * 2
            cursor_y = await _draw_text_block(
                draw, segments, PADDING_X, cursor_y, max_w, font
            )

        cursor_y += 15

    final_height = cursor_y + PADDING_Y
    final_img = img.crop((0, 0, CANVAS_WIDTH, int(final_height)))
    output = BytesIO()
    final_img.save(output, format="WEBP", quality=85, method=6)
    return output.getvalue()


async def _parse_rich_text_segments(text: str, default_color: tuple) -> list:
    """
    解析富文本为文本段落列表
    Args:
        text: 富文本字符串
        default_color: 默认颜色RGB元组
    Returns:
        list: [(文本, 颜色), ...]
    """
    TEXT_HIGHLIGHT = (255, 255, 255)
    TEXT_GRAY = (148, 149, 169)

    # 先清理不需要的标签（如 <effect:none>）
    text = re.sub(r"<effect:none>", "", text, flags=re.IGNORECASE)

    segments = []
    suffix_pattern = r"([（\(]等级\d+.*?解锁[）\)])$"
    suffix_match = re.search(suffix_pattern, text)
    main_text = text
    suffix_text = ""

    if suffix_match:
        suffix_text = suffix_match.group(1)
        main_text = text[: suffix_match.start()]

    i = 0
    current_text = ""
    current_color = default_color
    color_stack = []  # 颜色栈，用于处理嵌套

    while i < len(main_text):
        # 检查颜色标签开始
        if main_text[i : i + 7].lower() == "<color=" and i + 14 < len(main_text):
            color_match = re.match(
                r"<color=(#[0-9a-fA-F]{6})>", main_text[i:], re.IGNORECASE
            )
            if color_match:
                if current_text:
                    segments.append((current_text, current_color))
                    current_text = ""

                # 压栈当前颜色，切换到新颜色
                color_stack.append(current_color)
                hex_color = color_match.group(1)
                current_color = tuple(
                    int(hex_color.lstrip("#")[j : j + 2], 16) for j in (0, 2, 4)
                )
                i += len(color_match.group(0))
                continue

        # 检查颜色标签结束
        if main_text[i : i + 8].lower() == "</color>":
            if current_text:
                segments.append((current_text, current_color))
                current_text = ""

            # 出栈恢复颜色
            if color_stack:
                current_color = color_stack.pop()
            else:
                current_color = default_color
            i += 8
            continue

        if main_text[i] == "＜":
            end_idx = main_text.find("＞", i)
            if end_idx != -1:
                if current_text:
                    segments.append((current_text, current_color))
                    current_text = ""
                highlight_text = main_text[i : end_idx + 1]
                segments.append((highlight_text, TEXT_HIGHLIGHT))
                i = end_idx + 1
                continue

        # 检查是否是半角尖括号内容（比如 <火龙>）
        if main_text[i] == "<" and i + 1 < len(main_text):
            end_idx = main_text.find(">", i)
            if end_idx != -1:
                bracket_content = main_text[i + 1 : end_idx]
                if not re.match(r"^\d+\.(VALUE|DURATION)$", bracket_content):
                    current_text += main_text[i : end_idx + 1]
                    i = end_idx + 1
                    continue

        current_text += main_text[i]
        i += 1

    if current_text:
        segments.append((current_text, current_color))

    if suffix_text:
        segments.append((suffix_text, TEXT_GRAY))

    return segments


async def _draw_checkmark(draw: ImageDraw.Draw, x: int, y: int, size: int):
    """绘制勾号标记"""
    CHECKMARK_COLOR = (45, 155, 0)
    draw.ellipse([x, y, x + size, y + size], fill=CHECKMARK_COLOR)
    cx, cy = x + size / 2, y + size / 2
    points = [
        (cx - size * 0.25, cy),
        (cx - size * 0.05, cy + size * 0.2),
        (cx + size * 0.25, cy - size * 0.25),
    ]
    draw.line(points, fill="white", width=int(size * 0.12))


async def _draw_text_block(
    draw: ImageDraw.Draw,
    segments: list,
    x: int,
    y: int,
    max_width: int,
    font: ImageFont.FreeTypeFont,
) -> int:
    """
    绘制文本块（支持自动换行、换行符和两端对齐）
    Args:
        draw: PIL绘图对象
        segments: [(文本, 颜色), ...]
        x: 起始X坐标
        y: 起始Y坐标
        max_width: 最大宽度
        font: 字体对象
    Returns:
        int: 绘制后的Y坐标
    """
    start_x = x
    current_y = y

    # 行高
    try:
        ascent, descent = font.getmetrics()
        line_height = ascent + descent + 12
    except:
        line_height = 36

    char_list = []  # [(char, color), ...]
    for text, color in segments:
        i = 0
        while i < len(text):
            char = text[i]

            if char == "\r" and i + 1 < len(text) and text[i + 1] == "\n":
                char_list.append(("\n", color))
                i += 2
                continue

            if char == "\n" or char == "\r":
                char_list.append(("\n", color))
                i += 1
                continue

            if char == "\t":
                char_list.append(("\t", color))
                i += 1
                continue

            if ord(char) < 32:
                i += 1
                continue

            char_list.append((char, color))
            i += 1

    lines = []  # [[(char, color, width), ...], ...]
    current_line = []
    current_line_width = 0

    for char, color in char_list:
        if char == "\n":
            # 强制换行
            lines.append((current_line, current_line_width, True))
            current_line = []
            current_line_width = 0
            continue

        if char == "\t":
            try:
                if hasattr(font, "getlength"):
                    tab_width = font.getlength(" ") * 4
                else:
                    tab_width = font.getsize(" ")[0] * 4
            except:
                tab_width = 48

            if current_line_width + tab_width > max_width:
                lines.append((current_line, current_line_width, False))
                current_line = []
                current_line_width = 0
            else:
                current_line.append(("\t", color, tab_width))
                current_line_width += tab_width
            continue

        # 获取字符宽度
        try:
            if hasattr(font, "getlength"):
                char_width = font.getlength(char)
            else:
                char_width = font.getsize(char)[0]
        except:
            char_width = 24

        if current_line_width + char_width > max_width and current_line:
            lines.append((current_line, current_line_width, False))  # False表示自动换行
            current_line = []
            current_line_width = 0

        current_line.append((char, color, char_width))
        current_line_width += char_width

    if current_line:
        lines.append((current_line, current_line_width, True))  # 最后一行标记为强制换行

    for line_chars, line_width, is_hard_break in lines:
        if not line_chars:
            current_y += line_height
            continue

        extra_spacing = 0
        num_chars = len(line_chars)
        if (
            not is_hard_break
            and line_width < max_width
            and line_width > max_width * 0.7
            and num_chars > 1
        ):
            total_extra_space = max_width - line_width
            extra_spacing = total_extra_space / (num_chars - 1)
        current_x = start_x
        for i, (char, color, char_width) in enumerate(line_chars):
            if char == "\t":
                current_x += char_width
            else:
                draw.text((current_x, current_y), char, font=font, fill=color)
                current_x += char_width
                if i < num_chars - 1:
                    current_x += extra_spacing

        current_y += line_height

    return current_y
