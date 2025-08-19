"""
UI和显示相关的工具函数
"""
import re
from pathlib import Path
from io import BytesIO
from datetime import datetime
from PIL import Image
from ...config import (
    BANNER_DIR, STICKER_DIR, 
    HERO_NAME_MAPPING, EVERTALK_DIR, 
    CG_DIR, SOUL_DIR, CUSTOM_FONT,
    HERO_OPTION_BUFF_REVERSE_MAPPING
)
from .es_string_utils import (
    get_string_item, get_string_character, get_string_by_type,
    get_stat_string_in_hero_option
)
from nonebot.adapters.onebot.v11 import (
    MessageSegment
)
from typing import List, Tuple
from nonebot.log import logger
import matplotlib.pyplot as plt



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
    

async def get_character_portrait(data, prefab_path):
    """获取角色头像（包括基础头像和所有皮肤头像），动态查找所有皮肤。
    
    Args:
        data: JSON数据字典 (保留以备将来使用或用于查找基础头像).
        hero_id: 角色ID (保留以备将来使用或用于查找基础头像).
        prefab_path: 角色预设头像路径.
    Returns:
        list: 头像图片路径列表，第一个是基础头像，后面是按名称排序的皮肤头像.
    """

    if prefab_path == "":
        return []
    
    portraits = []

    base_name = ""
    controller_path = ""

    # 基础头像
    for costume in data["item_costume"]["json"]:
        if costume.get("no") == prefab_path:
            base_name = costume.get("portrait_path", "")
            controller_path = costume.get("portrait_path", "")
            break
    
    if base_name:
        portraits.append(str(SOUL_DIR / f"{base_name}_512.png"))

    if controller_path:
        costume_portraits = set()
        for costume in data["item_costume"]["json"]:
            if (costume.get("controller_path") == controller_path and 
                costume.get("no") != prefab_path and costume.get("icon_path") != ""):  # 排除基础时装本身
                portrait_path = costume.get("portrait_path", "")
                if portrait_path:
                    costume_portraits.add(portrait_path)
        
        for portrait_name in sorted(costume_portraits):
            portraits.append(str(SOUL_DIR / f"{portrait_name}_512.png"))
        
    return portraits



async def get_character_illustration(data, hero_id):
    """获取角色立绘
    
    Args:
        data: JSON数据字典
        hero_id: 角色ID 
    Returns:
        list: [(图片路径, 显示名称_tw, 显示名称_cn, 显示名称_kr, 显示名称_en, 解锁条件_tw, 解锁条件_cn, 解锁条件_kr, 解锁条件_en)] 的列表
    """
    image_path = str(SOUL_DIR)
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
                costume_name_zh_tw = (await get_string_by_type(data, "item", name_sno)).get("zh_tw", "")
                costume_name_zh_cn = (await get_string_by_type(data, "item", name_sno)).get("zh_cn", "")
                costume_name_kr = (await get_string_by_type(data, "item", name_sno)).get("kr", "")
                costume_name_en = (await get_string_by_type(data, "item", name_sno)).get("en", "")
                condition_tw = (await get_string_by_type(data, "ui", type_sno)).get("zh_tw", "")
                condition_cn = (await get_string_by_type(data, "ui", type_sno)).get("zh_tw", "")
                condition_kr = (await get_string_by_type(data, "ui", type_sno)).get("zh_tw", "")
                condition_en = (await get_string_by_type(data, "ui", type_sno)).get("zh_tw", "")
                costume_info[portrait_path] = (costume_name_zh_tw, costume_name_zh_cn, costume_name_kr, costume_name_en,\
                                                condition_tw, condition_cn, condition_kr, condition_en)

    
    # 查找匹配的图片
    images = []
    result_dict = {} 
    old_design_suffix = " (1)"  # 旧设立绘的后缀
    
    # 列出所有可能的立绘文件
    all_files = list(Path(image_path).glob('*_2048*.*'))
    
    # 先处理常规立绘
    for file in all_files:
        file_stem = file.stem
        
        # 跳过旧设文件，稍后处理
        if " (1)" in file_stem:
            continue
            
        # 提取基础名称，移除_2048后缀
        if "_2048" in file_stem:
            base_name = file_stem.split("_2048")[0]
            
            # 处理常规立绘
            if base_name in costume_info:
                # 构建 "角色名_立绘名" 的格式
                costume_name_zh_tw, costume_name_zh_cn, costume_name_kr, costume_name_en, condition_tw,\
                condition_cn, condition_kr, condition_en = costume_info[base_name]
                display_name_tw = f"{costume_name_zh_tw}"
                display_name_cn = f"{costume_name_zh_cn}"
                display_name_kr = f"{costume_name_kr}"
                display_name_en = f"{costume_name_en}"
                
                # 添加到结果字典，键为立绘基础名称
                if base_name not in result_dict:
                    result_dict[base_name] = []
                
                # 添加原始立绘
                result_dict[base_name].append((file, display_name_tw, display_name_cn, display_name_kr, display_name_en,\
                                condition_tw, condition_cn, condition_kr, condition_en))
                
                # 检查是否存在对应的旧设立绘 (格式: 基础名称_2048 (1).后缀)
                old_design_file = file.parent / f"{base_name}_2048{old_design_suffix}{file.suffix}"
                
                if old_design_file.exists():
                    # 添加旧设立绘
                    display_name_tw = f"{costume_name_zh_tw}_旧设"
                    display_name_cn = f"{costume_name_zh_cn}_旧设"
                    display_name_kr = f"{costume_name_kr}_旧设"
                    display_name_en = f"{costume_name_en}_old"
                    
                    # 解锁条件设置为"尽请期待"
                    old_condition_tw = "敬請期待"
                    old_condition_cn = "尽请期待"
                    old_condition_kr = "기대해 주세요"
                    old_condition_en = "Stay tuned"
                    
                    # 将旧设立绘添加到结果列表中（在原始立绘后面）
                    result_dict[base_name].append((old_design_file, display_name_tw, display_name_cn, display_name_kr, display_name_en,\
                                    old_condition_tw, old_condition_cn, old_condition_kr, old_condition_en))
    
    # 处理独立的旧设立绘文件（没有对应的常规立绘）
    for file in all_files:
        file_stem = file.stem
        # 检查是否是旧设立绘
        if "(1)" in file_stem and "_2048" in file_stem:
            # 提取原始基础名称，要去掉_2048和 (1)
            original_base_name = file_stem.split("_2048")[0]
            
            # 如果这个基础名称已经处理过，跳过
            if original_base_name in result_dict:
                continue
                
            # 查找原始立绘的信息
            if original_base_name in costume_info:
                costume_name_zh_tw, costume_name_zh_cn, costume_name_kr, costume_name_en, _, _, _, _ = costume_info[original_base_name]
                
                # 添加"_旧设"标记
                display_name_tw = f"{costume_name_zh_tw}_旧设"
                display_name_cn = f"{costume_name_zh_cn}_旧设"
                display_name_kr = f"{costume_name_kr}_旧设"
                display_name_en = f"{costume_name_en}_old"
                condition_tw = "敬請期待"
                condition_cn = "尽请期待"
                condition_kr = "기대해 주세요"
                condition_en = "Stay tuned"
                
                # 创建新的结果条目
                if original_base_name not in result_dict:
                    result_dict[original_base_name] = []
                    
                # 添加旧设立绘
                result_dict[original_base_name].append((file, display_name_tw, display_name_cn, display_name_kr, display_name_en,\
                                condition_tw, condition_cn, condition_kr, condition_en))
    
    result_dict_sorted = dict(sorted(result_dict.items()))
    for base_name, entries in result_dict_sorted.items():
        images.extend(entries)
    
    return images  # 原始立绘在前，旧设立绘在后


async def get_character_affection_cg(data, hero_id):
    """获取角色好感CG
    
    Args:
        data: JSON数据字典
        hero_id: 角色ID
    
    Returns:
        list: [(图片路径, CG编号, 章节标题)] 的列表
    """
    if not CG_DIR.exists():
        return []
    
    # 将hero_id转换为act格式
    act = hero_id
    
    # 收集所有相关的故事编号和章节信息
    story_info = {}  # 使用字典存储故事编号和章节信息的映射
    for story in data["story_info"]["json"]:
        if "act" in story and story["act"] == act:
            story_nos = story_info.get(story["no"], [])
            story_nos.append({
                "episode": story.get("episode"),
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
        for file in CG_DIR.glob(f"{cg_name}.*"):
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


async def get_character_evertalk_cg(data: dict, hero_id: int) -> List[Tuple[Path, str]]:
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


async def get_schedule_event(data, target_month, current_year, schedule_prefix, event_type):
    """获取活动日程事件信息
    
    Args:
        data: JSON数据字典
        target_month: 目标月份
        current_year: 当前年份
        schedule_prefix: 日程key前缀(如"Calender_PickUp_")
        event_type: 事件类型显示名称(如"Pickup")
    
    Returns:
        list: 事件信息列表
    """
    events = []
    now = datetime.now()
    
    # 跳过已经迁移到get_calendar_event函数中的类型
    if (schedule_prefix.startswith("EventInfo_Side_") or 
        schedule_prefix.startswith("Calender_SingleRaid_") or 
        schedule_prefix.startswith("Calender_EdenAlliance_") or
        schedule_prefix.startswith("Calender_WorldBoss_") or
        schedule_prefix.startswith("Calender_GuildRaid_")):
        return events
    
    for schedule in data["localization_schedule"]["json"]:
        # 对于主要活动，使用完全匹配而不是startswith
        if schedule_prefix.endswith("_Main") or schedule_prefix.endswith("_Return_Main"):
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
        # 从EventInfo中获取banner路径
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
            event_info.append(f"持续时间：{start_date} 至 {end_date}")
            if banner_path:
                event_info.append(f"banner：{banner_path}")
            # 返回带开始时间的元组
            events.append((start_date, "\n".join(event_info)))
    return events


async def get_mail_event(data, target_month, current_year):
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
            sender_data = await get_string_character(data, sender_sno, special=True)
            sender_name_tw = sender_data["zh_tw"]
            sender_name_en = sender_data["en"]
        
        # 获取标题和描述
        title_data = await get_string_character(data, mail.get("title_sno", 0)) or "无标题"
        title_tw = title_data["zh_tw"] if isinstance(title_data, dict) else "无标题"
        
        desc_data = await get_string_character(data, mail.get("desc_sno", 0)) or "无描述"
        desc_tw = desc_data["zh_tw"] if isinstance(desc_data, dict) else "无描述"
        
        # 处理奖励信息
        rewards = []
        for i in range(1, 5):
            reward_no_key = f"reward_no{i}"
            reward_amount_key = f"reward_amount{i}"
            
            if reward_no := mail.get(reward_no_key):
                amount = mail.get(reward_amount_key, 0)
                item_name = await get_string_item(data, reward_no)
                if item_name and amount:
                    rewards.append(f"{item_name['zh_tw']}x{amount}")
        
        # 构建事件信息
        event_info = []
        event_info.append(f"【邮箱事件】")  # 使用统一的格式
        event_info.append(f"名称：{sender_name_tw}的信件")  # 添加名称行以统一格式
        event_info.append(f"标题：{title_tw}")
        event_info.append(f"描述：{desc_tw}")
        event_info.append(f"持续时间：{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
        
        # 添加贴纸作为banner
        if sender_name_en and sender_name_en != "Unknown":
            sender_name_en = HERO_NAME_MAPPING.get(sender_name_en, sender_name_en)
            sticker_path = f"sticker_love_{sender_name_en}01.png"
            # 检查文件是否存在
            if (STICKER_DIR / sticker_path).exists():
                event_info.append(f"banner：{sticker_path}")
        
        if rewards:
            event_info.append("奖励：")
            event_info.extend([f"- {reward}" for reward in rewards])
        
        mail_events.append((start_date, "\n".join(event_info)))
    
    return mail_events


async def get_calendar_event(data, target_month, current_year):
    """获取一般活动信息"""
    calendar_events_with_date = []
    now = datetime.now()
    
    for schedule in data["localization_schedule"]["json"]:
        schedule_key = schedule.get("schedule_key", "")
        # 排除以下类型：
        #   - Calender_PickUp_ （Pickup活动）
        #   - *_Main 结尾的主要活动
        if ((not schedule_key.startswith("Calender_") and not schedule_key.startswith("EventInfo_")) or 
            schedule_key.startswith("Calender_PickUp_") or 
            schedule_key.endswith("_Main") or  # 主要活动
            schedule_key.endswith("_Quest") or  # 7日任务
            schedule_key.endswith("_Infinity") or  # 无限挑战
            schedule_key.endswith("_Rewardgame") or  # 小游戏
            (schedule_key.startswith("EventInfo_") and 
             not schedule_key.endswith("_Pass") and 
             not schedule_key.endswith("_Attend"))):
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
        gacha_no = None
        
        # 对于EventInfo_开头的活动，直接从event_info中获取信息
        if schedule_key.startswith("EventInfo_") and ((schedule_key.endswith("_Pass")) or (schedule_key.endswith("_Attend"))):
            for event_info in data["event_info"]["json"]:
                if event_info.get("schedule_key") == schedule_key:
                    name_sno = event_info.get("name_sno")
                    banner_raw = event_info.get("banner_path", "")
                    if banner_raw:
                        banner_path = f"{banner_raw}_ZH_TW.png"
                    # 如果找到name_sno，从StringUI中获取名称
                    if name_sno:
                        event_name_tw = (await get_string_by_type(data, "ui", name_sno)).get("zh_tw", "")
                        break
                    break
        else:
            # 从EventCalender中获取name_sno
            for event in data["event_calender"]["json"]:
                if event.get("schedule_key") == schedule_key:
                    name_sno = event.get("name_sno")
                    if name_sno:
                        # 从StringUI中获取名称
                        event_name_tw = (await get_string_by_type(data, "ui", name_sno)).get("zh_tw", "")
                        break
                    break
            
            # 从EventInfo中获取名称
            for event in data["event_info"]["json"]:
                if event.get("schedule_key") == schedule_key:
                    name_sno = event.get("name_sno")
                    if name_sno:
                        event_name_tw = (await get_string_by_type(data, "ui", name_sno)).get("zh_tw", "")
                        break
                    break
        
        # 处理不同类型活动的banner
        if schedule_key.startswith("Calender_SingleRaid_"):
            # 从schedule_key中提取角色名称：Calender_SingleRaid_HeroName
            parts = schedule_key.split('_')
            if len(parts) > 2:
                hero_name = parts[-1]  # 获取最后一部分，保持原始大小写
                # 这里是给数据表中不同字段角色名称做适配
                hero_name = HERO_NAME_MAPPING.get(hero_name, hero_name)  # 如果不在映射表中，使用原名
                sticker_path = f"sticker_singleraid_{hero_name}_01.png"
                # 检查文件是否存在
                if (STICKER_DIR / sticker_path).exists():
                    banner_path = sticker_path
        # 联合作战类型，从schedule_key提取角色名生成徽章路径
        elif schedule_key.startswith("Calender_EdenAlliance_"):
            # 从schedule_key中提取角色名称：Calender_EdenAlliance_HeroName
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
        # 从EventInfo中获取banner路径
        elif name_sno and not banner_path:
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
            event_info.append(f"持续时间：{start_date} 至 {end_date}")
            if banner_path:
                event_info.append(f"banner：{banner_path}")
            calendar_events_with_date.append((start_date, "\n".join(event_info)))
    
    calendar_events_with_date.sort(key=lambda x: x[0])
    return [event_info for _, event_info in calendar_events_with_date]



async def format_event_content(event_text):
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
    
    return {
        "content": "<br>".join(formatted_lines),
        "banner": banner_path
    }


async def get_potential_value(data: dict, effect_type: int, effect_no: int) -> str:
    """获取潜能数值
    
    Args:
        data: JSON数据字典
        effect_no: 效果编号
        level: 潜能等级
    
    Returns:
        str: 格式化后的数值
    """

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
                key = HERO_OPTION_BUFF_REVERSE_MAPPING.get(buff.get("buff_effect", 0), 0)
                return await get_stat_string_in_hero_option(value, key)


async def generate_event_html(event, event_type):
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


async def get_event_name(event):
    """获取事件名称"""
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
    # mail_events = [event for _, event in mail_events_with_date]
    
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
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
                gap: 1rem;
                margin-bottom: 2rem;
            }}

            .event-grid-email {{
                grid-template-columns: repeat(1, 1fr);
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
                height: 100%;
            }}

            .event-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
            }}

            .event-card-email {{
                flex-direction: row;
                display: flex;
            }}

            .event-card .content {{
                padding: 0.8rem;
            }}

            .event-card-email .content-email {{
                display: flex;
                flex-direction: column;
                padding: 1rem;
                flex: 1;
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
            }}

            /* 响应式布局 */
            @media (max-width: 768px) {{
                .event-grid {{
                    grid-template-columns: repeat(2, 1fr);
                }}
            }}

            @media (max-width: 480px) {{
                .event-grid {{
                    grid-template-columns: 1fr;
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
                    <h2>特殊活动</h2>
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
                    <h2>一般活动</h2>
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
        </div>
    </body>
    </html>
    """
    return html


async def get_event_time(event):
    """获取事件时间"""
    lines = event.split('\n')
    for line in lines:
        if "持续时间：" in line:
            time_str = line.replace("持续时间：", "").strip()
            # 格式化为简短的月.日-月.日格式
            try:
                start_date_str, end_date_str = time_str.split("至")
                start_date = datetime.strptime(start_date_str.strip(), '%Y-%m-%d')
                end_date = datetime.strptime(end_date_str.strip(), '%Y-%m-%d')
                return f"{start_date.month}.{start_date.day}-{end_date.month}.{end_date.day}"
            except:
                return time_str
    return "时间未知"


async def get_event_description(event):
    """获取事件描述"""
    lines = event.split('\n')
    description_lines = []
    skip_lines = 0
    
    for i, line in enumerate(lines):
        if i < skip_lines:
            continue
        
        if "【" in line and "】" in line or "持续时间：" in line or line.startswith("名称：") or line.startswith("banner："):
            skip_lines = i + 1
            continue
            
        if line.strip():
            description_lines.append(line)
    
    return "\n".join(description_lines)


async def get_event_banner(event):
    """获取事件banner图片路径"""
    lines = event.split('\n')
    for line in lines:
        if line.startswith("banner："):
            banner_path = line.replace("banner：", "").strip()
            # 检查是否是联合作战的sticker图片或恶灵讨伐或邮箱事件的sticker图片
            if (banner_path.startswith("sticker_eas_") or 
                banner_path.startswith("sticker_singleraid_") or 
                banner_path.startswith("sticker_love_")):
                return str(STICKER_DIR / banner_path)
            else:
                return str(BANNER_DIR / banner_path)
    # 如果没有找到banner图片，返回默认图片
    return str(BANNER_DIR / "banner_No_Image.png")


async def generate_ark_level_chart(data: dict, target_level: int) -> MessageSegment:
    """生成主方舟等级与超频等级关系图以及超频等级升级消耗图
    
    Args:
        data: 游戏数据
        target_level: 指定的目标超频等级，如果提供则会在图中标注，并将图表范围限制到该等级
    
    Returns:
        MessageSegment: 包含图表的消息段
    """
    try:
        # 检查数据是否存在
        if "ark_enhance" not in data or "json" not in data["ark_enhance"]:
            logger.error("数据中缺少ark_enhance或其json字段")
            return MessageSegment.text("生成统计图失败: 缺少方舟强化数据")
            
        if "ark_overclock" not in data or "json" not in data["ark_overclock"]:
            logger.error("数据中缺少ark_overclock或其json字段")
            return MessageSegment.text("生成统计图失败: 缺少超频数据")
        
        # 收集超频消耗数据
        all_overclock_costs = []
        all_overclock_levels_cost = []
        
        # 收集魔力粉尘消耗数据
        extra_items_data = {}  # 格式: {item_no: {levels: [], costs: []}}
        
        # 使用字典确保每个超频等级只对应一个消耗值
        level_cost_map = {}
        for overclock in data["ark_overclock"]["json"]:
            level = overclock.get("overclock_level", 0)
            cost = overclock.get("mana_crystal", 0)
            if level is not None and cost is not None:
                level_cost_map[level] = cost
                
                # 收集魔力粉尘消耗数据
                for i in range(10):  # 最多有10个魔力粉尘
                    item_no_key = f"pay_item_no_{i}"
                    item_amount_key = f"pay_amount_{i}"
                    if item_no_key in overclock and item_amount_key in overclock:
                        item_no = overclock[item_no_key]
                        item_amount = overclock[item_amount_key]
                        if item_no and item_amount:
                            if item_no not in extra_items_data:
                                extra_items_data[item_no] = {"levels": [], "costs": []}
                            if level not in [l for l in extra_items_data[item_no]["levels"]]:
                                extra_items_data[item_no]["levels"].append(level)
                                extra_items_data[item_no]["costs"].append(item_amount)
        
        # 将字典转换为有序列表
        sorted_cost_levels = sorted(level_cost_map.keys())
        for level in sorted_cost_levels:
            all_overclock_levels_cost.append(level)
            all_overclock_costs.append(level_cost_map[level])
        
        # 获取数据的最大超频等级
        max_overclock_level = max(all_overclock_levels_cost) if all_overclock_levels_cost else 0
        
        # 如果提供了目标等级，限制图表范围为目标等级
        # 否则使用全范围
        plot_max_level = target_level if target_level else max_overclock_level
        
        # 过滤超频消耗数据
        overclock_levels_cost = []
        overclock_costs = []
        for i, level in enumerate(all_overclock_levels_cost):
            if level <= plot_max_level:
                overclock_levels_cost.append(level)
                overclock_costs.append(all_overclock_costs[i])
                
        
        # 过滤魔力粉尘消耗数据
        filtered_extra_items_data = {}
        for item_no, item_data in extra_items_data.items():
            filtered_levels = []
            filtered_costs = []
            for i, level in enumerate(item_data["levels"]):
                if i < len(item_data["costs"]) and level <= plot_max_level:
                    filtered_levels.append(level)
                    filtered_costs.append(item_data["costs"][i])
            if filtered_levels:  # 只保留有数据的物品
                item_name = (await get_string_item(data, item_no)).get("zh_tw", "")
                if not item_name:
                    item_name = f"{item_no}"
                filtered_extra_items_data[item_no] = {
                    "levels": filtered_levels,
                    "costs": filtered_costs,
                    "name": item_name
                }
        
        # 使用双Y轴
        fig, ax1 = plt.subplots(figsize=(12, 8))
        
        # 设置左侧Y轴 - 魔力水晶
        ax1.set_xlabel('超频等级', fontproperties=CUSTOM_FONT)
        ax1.set_ylabel('魔力水晶消耗', color='red', fontproperties=CUSTOM_FONT)
        ax1.plot(overclock_levels_cost, overclock_costs, 'r-', marker='o', markersize=3, label='魔力水晶')
        ax1.tick_params(axis='y', labelcolor='red')
        ax1.grid(True, linestyle='--', alpha=0.7, axis='both')
        
        # 设置右侧Y轴 - 魔力粉尘
        if filtered_extra_items_data:
            ax2 = ax1.twinx()  # 创建共享X轴的第二个Y轴
            ax2.set_ylabel('魔力粉尘消耗', color='blue', fontproperties=CUSTOM_FONT)
            
            # 设置颜色循环
            colors = ['g', 'c', 'm', 'y', 'k', 'b']
            color_index = 0
            
            # 绘制每种魔力粉尘的消耗曲线
            for item_no, item_data in filtered_extra_items_data.items():
                # 验证数据
                if len(item_data["levels"]) != len(item_data["costs"]):
                    logger.warning(f"物品 {item_no} 数据维度不匹配: levels({len(item_data['levels'])}) != costs({len(item_data['costs'])})")
                    continue
                    
                if len(item_data["levels"]) == 0:
                    continue
                    
                color = colors[color_index % len(colors)]
                ax2.plot(item_data["levels"], item_data["costs"], f'{color}-', marker='o', markersize=3, label=item_data["name"])
                color_index += 1
                
            ax2.tick_params(axis='y', labelcolor='blue')
            
            # 添加图例 - 合并两个轴的图例
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', prop=CUSTOM_FONT)
        else:
            # 如果没有魔力粉尘，只添加魔力水晶的图例
            ax1.legend(loc='upper left', prop=CUSTOM_FONT)
        
        # 设置图表标题
        plt.title(f'超频等级升级消耗图 (1-{plot_max_level}级)', fontproperties=CUSTOM_FONT)
        
        # 设置x轴范围和刻度
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
            ax1.set_xticks(range(0, x_max+1, x_interval))
        
        # 添加网格线
        ax1.grid(True, linestyle='--', alpha=0.7)
        
        # 添加标记线，显示当前等级
        if target_level and target_level <= plot_max_level:
            ax1.axvline(x=target_level, color='purple', linestyle='--', alpha=0.7)
            ax1.text(target_level, ax1.get_ylim()[1] * 0.95, f'当前等级: {target_level}', 
                    color='purple', ha='right', va='top', fontproperties=CUSTOM_FONT)
        
        plt.tight_layout()
        
        buffer = BytesIO()
        plt.savefig(buffer, format='webp', dpi=300, bbox_inches='tight')
        plt.close()
        
        # 获取bytes数据
        buffer.seek(0)
        image_bytes = buffer.getvalue()

        # 返回MessageSegment对象
        return MessageSegment.image(image_bytes)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"生成统计图时发生错误: {str(e)}\n{error_trace}")
        return MessageSegment.text("生成统计图失败")


async def generate_level_cost_chart(data: dict) -> MessageSegment:
    """生成等级升级消耗统计图"""
    try:
        # 收集数据
        levels = []
        gold_costs = []
        mana_dust_costs = []
        mana_crystal_costs = []
        
        sorted_levels = sorted([item for item in data["level"]["json"] if "level" in item], 
                                key=lambda x: x["level"])
        
        for item in sorted_levels:
            level = item.get("level")
            if level is not None:
                levels.append(level)
                gold_costs.append(item.get("gold", 0))
                mana_dust_costs.append(item.get("mana_dust", 0))
                mana_crystal_costs.append(item.get("mana_crystal", 0) if "mana_crystal" in item else 0)
        
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
        
        # 绘制魔力水晶消耗
        ax3.plot(levels, mana_crystal_costs, 'r-', marker='o', markersize=2)
        ax3.set_title('魔力水晶消耗统计', fontproperties=CUSTOM_FONT)
        ax3.set_xlabel('等级', fontproperties=CUSTOM_FONT)
        ax3.set_ylabel('消耗数量', fontproperties=CUSTOM_FONT)
        ax3.grid(True, linestyle='--', alpha=0.7)
        ax3.set_xticks(range(0, max_level+1, x_interval))
        ax3.tick_params(axis='x', rotation=45)
        
        plt.tight_layout(pad=3.0)
        
        buffer = BytesIO()
        plt.savefig(buffer, format='webp', dpi=300, bbox_inches='tight')
        plt.close()
        
        buffer.seek(0)
        image_bytes = buffer.getvalue()
        return MessageSegment.image(image_bytes)
        
    except Exception as e:
        logger.error(f"生成等级消耗统计图时发生错误: {str(e)}")
        return MessageSegment.text("生成统计图失败")


async def get_battle_power_percentage(data: dict, effect_type: int, effect_no: int) -> float:
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
                    option.get("effect_type", 0),
                    option.get("effect_no1", 0),
                    option.get("option", 0)
                ))
        
        # 获取潜能名称
        potential_names = {}  # {tooltip_sno: name}
        for string in data["string_ui"]["json"]:
            if string.get("no") in potentials:
                potential_names[string["no"]] = string.get("zh_tw", "")
        
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
        
        # 等级列
        max_level = max(level for tooltip_sno in potentials for level, _, _, _ in potentials[tooltip_sno])
        for level in range(1, max_level + 1):
            html += f"<th>Lv.{level}</th>"
        
        html += "</tr>"
        
        for tooltip_sno, name in sorted(potential_names.items(), key=lambda x: x[0]):  # 修改排序键为x[0]
            html += f"<tr><td class='potential-name'>{name}</td>"
            level_data = {level: (effect_type, effect_no, option) for level, effect_type, effect_no, option in potentials[tooltip_sno]}
            for level in range(1, max_level + 1):
                if level in level_data:
                    effect_type, effect_no, option = level_data[level]
                    value = await get_potential_value(data, effect_type, effect_no)
                    battle_power_per = await get_battle_power_percentage(data, effect_type, effect_no)

                    if battle_power_per:
                        html += f"<td class='value-cell'>{value}<br><span class='power-value'>+{battle_power_per}</span></td>"
                    else:
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