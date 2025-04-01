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
    CG_DIR, HERO_DIR, CUSTOM_FONT
)
from .es_string_utils import (
    get_string_item, get_string_character
)
from nonebot.adapters.onebot.v11 import (
    MessageSegment
)
from typing import List, Tuple
from nonebot.log import logger
import matplotlib.pyplot as plt



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
    

def get_character_portrait(data, hero_id, hero_name_en, raid=False):
    """获取角色头像
    
    Args:
        data: JSON数据字典
        hero_id: 角色ID
        hero_name_en: 角色英文名称
        raid: 是否为恶灵讨伐
    Returns:
        Path: 头像图片路径或None
    """
    # 头像路径
    if raid:
        portrait_path = str(HERO_DIR / f"{HERO_NAME_MAPPING.get(hero_name_en, hero_name_en)}_Raid_512.png")
    else:
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
            costume_name_zh_tw, costume_name_zh_cn, costume_name_kr, costume_name_en, condition_tw,\
            condition_cn, condition_kr, condition_en = costume_info[base_name]
            display_name_tw = f"{costume_name_zh_tw}"
            display_name_cn = f"{costume_name_zh_cn}"
            display_name_kr = f"{costume_name_kr}"
            display_name_en = f"{costume_name_en}"
            images.append((file, display_name_tw, display_name_cn, display_name_kr, display_name_en,\
                            condition_tw, condition_cn, condition_kr, condition_en))
    
    return sorted(images)  # 排序以保持顺序一致


def get_character_affection_cg(data, hero_id):
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


def get_character_evertalk_cg(data: dict, hero_id: int) -> List[Tuple[Path, str]]:
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


def get_schedule_event(data, target_month, current_year, schedule_prefix, event_type):
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
        # 恶灵讨伐类型，从schedule_key提取角色名生成贴纸路径                        
        elif schedule_key.startswith("Calender_SingleRaid_"):
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


def get_mail_event(data, target_month, current_year):
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
            sender_data = get_string_character(data, sender_sno, special=True)
            sender_name_tw = sender_data["zh_tw"]
            sender_name_en = sender_data["en"]
        
        # 获取标题和描述
        title_data = get_string_character(data, mail.get("title_sno", 0)) or "无标题"
        title_tw = title_data["zh_tw"] if isinstance(title_data, dict) else "无标题"
        
        desc_data = get_string_character(data, mail.get("desc_sno", 0)) or "无描述"
        desc_tw = desc_data["zh_tw"] if isinstance(desc_data, dict) else "无描述"
        
        # 处理奖励信息
        rewards = []
        for i in range(1, 5):
            reward_no_key = f"reward_no{i}"
            reward_amount_key = f"reward_amount{i}"
            
            if reward_no := mail.get(reward_no_key):
                amount = mail.get(reward_amount_key, 0)
                item_name = get_string_item(data, reward_no)
                if item_name and amount:
                    rewards.append(f"{item_name['zh_tw']} x{amount}")
        
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


def get_calendar_event(data, target_month, current_year):
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