import os
import yaml
from pathlib import Path
from nonebot import on_command
from nonebot.exception import FinishedException
from difflib import get_close_matches
from zhenxun.services.log import logger
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import (
    Bot,
    Event,
    Message,
    MessageSegment,
    GroupMessageEvent
)
from ..libraries.es_utils import *
from ..config import *

es_hero_info = on_command("es角色信息", priority=5, block=True)


@es_hero_info.handle()
async def handle_hero_info(bot: Bot, event: Event, args: Message = CommandArg()):
    try:
        # 获取输入的文本并提取角色名
        hero_name = args.extract_plain_text().strip()
        if not hero_name:
            return
        
        # 获取群组ID
        group_id = None
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
        
        # 加载数据
        config = get_group_data_source(group_id)
        
        # 加载数据
        data = load_json_data(group_id)
        
        # 加载别名配置和原始别名数据
        with open(config["hero_alias_file"], "r", encoding="utf-8") as f:
            aliases_data = yaml.safe_load(f)
        alias_map = load_aliases(group_id)
        
        # 判断是否为测试模式
        is_test = config["type"] == "review"

        # 尝试从别名映射中获取hero_id
        hero_id = alias_map.get(hero_name)
        if not hero_id and hero_name.isascii():  # 如果是英文名称,尝试小写匹配
            hero_id = alias_map.get(hero_name.lower())
            
        if not hero_id:
            # 如果没有直接匹配,尝试模糊匹配
            all_names = list(alias_map.keys())
            # 对于英文输入,同时在小写版本中搜索
            if hero_name.isascii():
                matches = get_close_matches(hero_name.lower(), [n.lower() if n.isascii() else n for n in all_names], n=1, cutoff=0.6)
            else:
                matches = get_close_matches(hero_name, all_names, n=1, cutoff=0.6)
            if matches:
                # 找到匹配的主名称和别名
                matched_name = matches[0]
                matched_hero_id = alias_map[matched_name]
                
                main_names = {
                    "繁体": None,
                    "简体": None,
                    "韩文": None,
                    "英文": None
                }
                aliases = []
                
                for name, hid in alias_map.items():
                    if hid == matched_hero_id:
                        # 在原始数据中查找这个名称属于哪种语言
                        for hero in aliases_data["names"]:
                            if hero["hero_id"] == matched_hero_id:
                                if name == hero.get("zh_tw_name"):
                                    main_names["繁体"] = name
                                elif name == hero.get("zh_cn_name"):
                                    main_names["简体"] = name
                                elif name == hero.get("kr_name"):
                                    main_names["韩文"] = name
                                elif name == hero.get("en_name"):
                                    main_names["英文"] = name
                                elif name in hero.get("aliases", []):
                                    aliases.append(name)
                
                # 构建响应消息
                response_parts = ["未找到角色 " + hero_name + "\n您是否想查询："]
                
                # 添加各语言名称
                for lang, name in main_names.items():
                    if name:
                        response_parts.append(f"{lang}：{name}")
                
                # 添加别名
                if aliases:
                    response_parts.append(f"别名：{', '.join(aliases)}")
                
                await es_hero_info.finish("\n".join(response_parts))
                return
            else:
                await es_hero_info.finish(f"未找到角色 {hero_name}")
                return
        
        # 查找英雄数据
        hero_data = None
        hero_desc = None
        for hero in data["hero"]["json"]:
            if hero["hero_id"] == hero_id:
                hero_data = hero
                break
        
        # 查找英雄描述数据
        for desc in data["hero_desc"]["json"]:
            if desc["hero_no"] == hero_id:
                hero_desc = desc
                break
        
        if not hero_data:
            await es_hero_info.finish("未找到该角色信息")
            return
            
        # 获取英雄名称
        hero_name_tw = ""
        hero_name_cn = ""
        hero_name_kr = ""
        hero_name_en = ""
        for char in data["string_character"]["json"]:
            if char["no"] == hero_data["name_sno"]:
                hero_name_tw = char.get("zh_tw", "")
                hero_name_cn = char.get("zh_cn", "")
                hero_name_kr = char.get("kr", "")
                hero_name_en = char.get("en", "")
                break

        # 获取实装信息
        release_date = get_character_release_date(data, hero_id)
        date_info = format_date_info(release_date)
        
        # 获取双语版本的基础信息
        race_tw, race_cn, race_kr, race_en = get_system_string(data, hero_data["race_sno"])
        hero_class_tw, hero_class_cn, hero_class_kr, hero_class_en = get_system_string(data, hero_data["class_sno"])
        sub_class_tw, sub_class_cn, sub_class_kr, sub_class_en = get_system_string(data, hero_data["sub_class_sno"])
        stat_tw, stat_cn, stat_kr, stat_en = get_system_string(data, hero_data["stat_sno"])
        grade_tw, grade_cn, grade_kr, grade_en = get_system_string(data, hero_data["grade_sno"])
        
        # 构建消息列表
        messages = []
        nickname_tw = ""
        nickname_cn = ""
        nickname_kr = ""
        nickname_en = ""
        if hero_desc and isinstance(hero_desc, dict):
            nick_name_sno = hero_desc.get("nick_name_sno")
            nickname_tw, nickname_cn, nickname_kr, nickname_en = get_string_character(data, nick_name_sno)
        
        # 繁体中文版本
        basic_info_msg = []
        portrait_path = get_character_portrait(data, hero_id, hero_name_en) # 获取立绘路径
        basic_info_msg.append("【基础信息】")
        if portrait_path:
            basic_info_msg.append(MessageSegment.image(f"file:///{portrait_path}"))
        basic_info_tw = f"""{nickname_tw if nickname_tw else nickname_kr}・{hero_name_tw if hero_name_tw else hero_name_kr}
類型：{race_tw} {hero_class_tw}
攻擊方式：{sub_class_tw}
屬性：{stat_tw}
品質：{grade_tw}
隸屬：{get_string_character(data, hero_desc.get("union_sno", 0))[0] if hero_desc else "???"}
身高：{hero_desc.get("height", "???") if hero_desc else "???"}cm
體重：{hero_desc.get("weight", "???") if hero_desc else "???"}kg
生日：{str(hero_desc.get("birthday", "???")).zfill(4)[:2] 
if hero_desc else "???"}.{str(hero_desc.get("birthday", "???")).zfill(4)[2:]
if hero_desc and hero_desc.get("birthday") else "???"}
星座：{get_string_character(data, hero_desc.get("constellation_sno", 0))[0] if hero_desc else "???"}
興趣：{get_string_character(data, hero_desc.get("hobby_sno", 0))[0] if hero_desc else "???"}
特殊專長：{get_string_character(data, hero_desc.get("speciality_sno", 0))[0] if hero_desc else "???"}
喜歡的東西：{get_string_character(data, hero_desc.get("like_sno", 0))[0] if hero_desc else "???"}
討厭的東西：{get_string_character(data, hero_desc.get("dislike_sno", 0))[0] if hero_desc else "???"}
CV：{get_string_character(data, hero_desc.get("cv_sno", 0))[0] if hero_desc else "???"}
CV_JP：{get_string_character(data, hero_desc.get("cv_jp_sno", 0))[0] if hero_desc else "???"}
{date_info}
攻击力：{int(hero_data.get('attack', 0))}+{int(hero_data.get('inc_attack', 0))}/级
防御力：{int(hero_data.get('defence', 0))}+{int(hero_data.get('inc_defence', 0))}/级
生命值：{int(hero_data.get('max_hp', 0))}+{int(hero_data.get('inc_max_hp', 0))}/级
暴击率：{hero_data.get('critical_rate', 0)*100:.1f}%+{hero_data.get('inc_critical_rate', 0)*100:.3f}%/级
暴击威力：{hero_data.get('critical_power', 0)*100:.1f}%+{hero_data.get('inc_critical_power', 0)*100:.3f}%/级"""
        basic_info_msg.append(basic_info_tw)
        messages.append("\n".join(str(x) for x in basic_info_msg))

        # 添加立绘
        for char in data["string_character"]["json"]:
            if char["no"] == hero_data["name_sno"]:
                images = get_character_illustration(data, hero_id)
                if images:
                    image_msg = []
                    image_msg.append("【立绘】")
                    for img_path, display_name_zh_tw, display_name_zh_cn, display_name_kr,\
                        display_name_en, condition_tw, condition_cn, condition_kr, condition_en in images:
                        image_msg.append(f"{display_name_zh_tw}\n解锁条件: {condition_tw}")
                        image_msg.append(MessageSegment.image(f"file:///{str(img_path.absolute())}"))
                    messages.append("\n".join(str(x) for x in image_msg))
                break

        # 获取灵魂链接信息，
        soullink_info = get_soullink_info(data, hero_id, is_test=False)
        if soullink_info:
            for link in soullink_info:
                link_msg = ["【灵魂链接】"]
                link_msg.append(f"名称：{link['title']}")
                link_msg.append(f"相关角色：{'、'.join(link['heroes'])}")
                if link['story']:
                    link_msg.append(f"\n故事：{link['story']}")
                if link['effects']:
                    link_msg.append("\n收集效果：")
                    for effect in link['effects']:
                        link_msg.append(f"▶ {effect['condition']}")
                        link_msg.append("  " + "\n  ".join(effect['effects']))
                if link['open_date']:
                    link_msg.append(f"\n开启时间：{link['open_date']}")
                messages.append("\n".join(link_msg))

        # 获取自我介绍
        if hero_desc and isinstance(hero_desc, dict):
            intro_sno = hero_desc.get("introduction_sno")
            if intro_sno:
                intro_zh_tw, intro_zh_cn, intro_kr, intro_en = get_string_character(data, intro_sno)
                if intro_zh_tw or intro_kr:
                    if is_test:
                        messages.append("【自我介绍】\n" + intro_kr)
                    else:
                        messages.append("【自我介绍】\n" + intro_zh_tw)
        
        # 添加好感故事信息
        has_story, episode_info, endings = get_story_info(data, hero_id)
        if has_story:
                messages.append(format_story_info(episode_info, endings, is_test))
        
        # 添加角色关键字信息
        keyword_info = format_character_keywords(data, hero_id, is_test=False)
        if keyword_info:
            messages.append(keyword_info)
        
        # 好感故事CG
        cg_images = get_affection_cgs(data, hero_id)
        if cg_images:
            cg_msg = []
            cg_msg.append("【好感CG】")
            current_episode = None
            for img_path, cg_no, episode, episode_title in cg_images:
                # 如果章节号变化，添加章节标题
                if episode != current_episode:
                    cg_msg.append(f"\nEP{episode}：{episode_title}")
                    current_episode = episode
                cg_msg.append(MessageSegment.image(f"file:///{img_path}"))
            messages.append("\n".join(str(x) for x in cg_msg))

        # EverPhone插图
        evertalk_illusts = get_evertalk_illustrations(data, hero_id)
        if evertalk_illusts:
            illust_msg = []
            illust_msg.append("【EverPhone插图】")
            for img_path, illust_base in evertalk_illusts:
                illust_msg.append(MessageSegment.image(f"file:///{img_path}"))
            messages.append("".join(str(x) for x in illust_msg))

        # 添加专属领地物品信息
        town_objects = get_town_object_info(data, hero_id, is_test)
        if town_objects:
            objects_msg = ["【专属领地物品】"]
            for obj_no, name, grade, slot_type, desc, img_path in town_objects:
                if img_path and os.path.exists(img_path):
                    objects_msg.append(MessageSegment.image(f"file:///{img_path}"))
                objects_msg.append(f"名称：{name}")
                if grade:
                    objects_msg.append(f"品质：{grade}")
                if slot_type:
                    objects_msg.append(f"类型：{slot_type}")
                if desc:
                    objects_msg.append(f"描述：{desc}")
                
                # 添加可进行的任务信息
                tasks = get_town_object_tasks(data, obj_no, is_test)
                if tasks:
                    objects_msg.append("\n可进行的打工：")
                    for task in tasks:
                        objects_msg.append(f"▼ {task['name']}（{task['rarity']}）")
                        objects_msg.append(f"所需时间：{task['time']}小时")
                        if task['traits']:
                            objects_msg.append(f"要求特性：{' '.join(task['traits'])}")
                        objects_msg.append(f"疲劳度：{task['stress']}")
                        objects_msg.append(f"打工经验：{task['exp']}")
                        if task['rewards']:
                            objects_msg.append("奖励：")
                            objects_msg.extend(f"・{reward}" for reward in task['rewards'])
                
                objects_msg.append("")  # 添加空行分隔不同物品
            messages.append("\n".join(str(x) for x in objects_msg))
        
        # review版本下，技能信息只显示韩文
        if is_test:
            # 技能信息
            skill_types = []
            skill_keys = ["skill_no1", "skill_no2", "skill_no3", "skill_no4",  "ultimate_skill_no", "support_skill_no"]
            # 先检查角色有哪些技能
            for skill_key in skill_keys:
                if skill_no := hero_data.get(skill_key):
                    for skill in data["skill"]["json"]:
                        if skill["no"] == skill_no:
                            skill_type_zh_tw, skill_type_zh_cn, skill_type_kr, skill_type_en = get_skill_type(data, skill["type"])
                            # 判断是否为支援技能
                            is_support = (skill_key == "support_skill_no")
                            skill_name_zh_tw, skill_name_zh_cn, skill_name_kr, skill_name_en, skill_descriptions, skill_icon_info, is_support = get_skill_info(data, skill_no, is_support, hero_data)
                            skill_types.append((skill_type_zh_tw, skill_type_zh_cn, skill_type_kr, skill_type_en, skill_name_zh_tw, skill_name_zh_cn, skill_name_kr, skill_name_en, skill_descriptions, skill_icon_info, is_support))
                            break
            
            for skill_type_zh_tw, skill_type_zh_cn, skill_type_kr, skill_type_en, skill_name_zh_tw, skill_name_zh_cn, skill_name_kr, skill_name_en, skill_descriptions, skill_icon_info, is_support in skill_types:
                skill_text = []
                
                # 如果有技能图标，处理并添加
                if skill_icon_info:
                    icon_path = str(ICON_DIR / f"{skill_icon_info['icon']}.png")
                    
                    # 检查是否存在缓存的着色图标
                    cache_filename = f"{skill_icon_info['icon']}_{skill_icon_info['color'].replace('#', '')}.png"
                    cache_path = str(ICON_DIR / cache_filename)
                    
                    # 如果存在缓存图标，直接使用
                    if os.path.exists(cache_path):
                        with open(cache_path, "rb") as f:
                            colored_icon = f.read()
                    else:
                        # 没有缓存，重新生成并保存
                        colored_icon = apply_color_to_icon(icon_path, skill_icon_info['color'])
                        # 保存到缓存目录
                        with open(cache_path, "wb") as f:
                            f.write(colored_icon)
                    
                    skill_text.append(MessageSegment.image(colored_icon))
                
                # 如果是支援技能，使用新的格式
                if is_support:
                    # 分类存储主要和辅助效果
                    main_effects = []
                    support_effects = []
                    
                    # 对效果进行分类
                    for desc_zh_tw, desc_zh_cn, desc_kr, desc_en in skill_descriptions:
                        if "메인 파트너" in desc_kr:
                            main_effects.append(desc_kr.replace("메인 파트너：", ""))
                        elif "서브 파트너" in desc_kr:
                            support_effects.append(desc_kr.replace("서브 파트너：", ""))
                    
                    # 如果有主要效果，添加主要效果部分
                    if main_effects:
                        skill_text.append("▼ 主要伙伴效果")
                        skill_text.append(f"【{skill_type_kr}】{skill_name_kr}")
                        skill_text.extend(main_effects)
                    
                    # 如果有辅助效果，添加辅助效果部分
                    if support_effects:
                        skill_text.append("▼ 辅助伙伴效果")
                        if not main_effects:  # 如果之前没有显示过技能名称，在这里显示
                            skill_text.append(f"【{skill_type_kr}】{skill_name_kr}")
                        skill_text.extend(support_effects)
                else:
                    # 非支援技能保持原有格式
                    # 只在第一级显示技能类型和名称
                    skill_text.append(f"【{skill_type_kr}】{skill_name_kr}")
                    for i, (desc_zh_tw, desc_zh_cn, desc_kr, desc_en, hero_level) in enumerate(skill_descriptions):
                        unlock_text = f"（等级{hero_level}解锁）" if hero_level >= 1 else ""
                        skill_text.append(f"等级{i+1}：{desc_kr}{unlock_text}\n")
                
                messages.append("\n".join(str(x) for x in skill_text))
        else:
            # 技能信息
            skill_types = []
            skill_keys = ["skill_no1", "skill_no2", "skill_no3", "skill_no4",  "ultimate_skill_no", "support_skill_no"]
            # 先检查角色有哪些技能
            for skill_key in skill_keys:
                if skill_no := hero_data.get(skill_key):
                    for skill in data["skill"]["json"]:
                        if skill["no"] == skill_no:
                            skill_type_zh_tw, skill_type_zh_cn, skill_type_kr, skill_type_en = get_skill_type(data, skill["type"])
                            # 判断是否为支援技能
                            is_support = (skill_key == "support_skill_no")
                            skill_name_zh_tw, skill_name_zh_cn, skill_name_kr,\
                            skill_name_en, skill_descriptions, skill_icon_info, is_support = get_skill_info(data, skill_no, is_support, hero_data)
                            skill_types.append((skill_type_zh_tw, skill_type_zh_cn, skill_type_kr, skill_type_en, skill_name_zh_tw,\
                                                skill_name_zh_cn, skill_name_kr, skill_name_en, skill_descriptions, skill_icon_info, is_support))
                            break
            
            for skill_type_zh_tw, skill_type_zh_cn, skill_type_kr, skill_type_en, skill_name_zh_tw,\
                skill_name_zh_cn, skill_name_kr, skill_name_en, skill_descriptions, skill_icon_info, is_support in skill_types:
                skill_text = []
                # 如果有技能图标，处理并添加
                if skill_icon_info:
                    icon_path = str(ICON_DIR / f"{skill_icon_info['icon']}.png")
                    
                    # 检查是否存在缓存的着色图标
                    cache_filename = f"{skill_icon_info['icon']}_{skill_icon_info['color'].replace('#', '')}.png"
                    cache_path = str(ICON_DIR / cache_filename)
                    
                    # 如果存在缓存图标，直接使用
                    if os.path.exists(cache_path):
                        with open(cache_path, "rb") as f:
                            colored_icon = f.read()
                    else:
                        # 没有缓存，重新生成并保存
                        colored_icon = apply_color_to_icon(icon_path, skill_icon_info['color'])
                        # 保存到缓存目录
                        with open(cache_path, "wb") as f:
                            f.write(colored_icon)
                    
                    skill_text.append(MessageSegment.image(colored_icon))
                
                # 如果是支援技能，使用新的格式
                if is_support:
                    # 分类存储主要和辅助效果
                    main_effects = []
                    support_effects = []
                    
                    # 对效果进行分类
                    for desc_tw, desc_cn, desc_kr, desc_en in skill_descriptions:
                        if "主要伙伴" in desc_cn:
                            main_effects.append(desc_tw.replace("主要夥伴：", ""))
                        elif "辅助伙伴" in desc_cn:
                            support_effects.append(desc_tw.replace("輔助夥伴：", ""))
                    
                    # 如果有主要效果，添加主要效果部分
                    if main_effects:
                        skill_text.append("▼ 主要伙伴效果")
                        skill_text.append(f"【{skill_type_zh_tw}】{skill_name_zh_tw}")
                        skill_text.extend(main_effects)
                    
                    # 如果有辅助效果，添加辅助效果部分
                    if support_effects:
                        skill_text.append("▼ 辅助伙伴效果")
                        if not main_effects:  # 如果之前没有显示过技能名称，在这里显示
                            skill_text.append(f"【{skill_type_zh_tw}】{skill_name_zh_tw}")
                        skill_text.extend(support_effects)
                else:
                    # 非支援技能保持原有格式
                    # 只在第一级显示技能类型和名称
                    skill_text.append(f"【{skill_type_zh_tw}】{skill_name_zh_tw}")
                    for i, (desc_zh_tw, desc_zh_cn, desc_kr, desc_en, hero_level) in enumerate(skill_descriptions):
                        unlock_text = f"（等级{hero_level}解锁）" if hero_level >= 1 else ""
                        skill_text.append(f"等级{i+1}：{desc_zh_tw}{unlock_text}\n")
                
                messages.append("\n".join(str(x) for x in skill_text))

        
        # 获取并添加遗物信息
        signature_name_zh_tw, signature_name_zh_cn, signature_name_kr, signature_name_en,\
        signature_title_zh_tw, signature_title_zh_cn, signature_title_kr, signature_title_en, \
        signature_desc_tw, signature_desc_cn, signature_desc_kr, signature_desc_en, signature_descriptions,\
        signature_stats, signature_bg_path = get_signature_info(data, hero_id)
        if signature_name_kr:
            signature_stats, max_level = signature_stats
            signature_img_path = str(SIGNATURE_DIR / signature_bg_path)

            if is_test:
                # 遗物信息 - 韩文版本
                signature_msg_kr = []
                signature_msg_kr.append(f"【遺物信息】")
                # 检查图片是否存在并添加
                if os.path.exists(signature_img_path):
                    signature_msg_kr.append(MessageSegment.image(f"file:///{signature_img_path}"))
                
                signature_info_kr = f"""{signature_name_kr}
{signature_desc_kr}

{max_level}級屬性：
{chr(10).join(signature_stats)}

遺物技能【{signature_title_kr}】：
""" + "\n".join(f"等級{i+1}：{desc_kr}" for i, (desc_tw, desc_cn, desc_kr, desc_en) in enumerate(signature_descriptions))
                signature_msg_kr.append(signature_info_kr)
                messages.append("\n".join(str(x) for x in signature_msg_kr))
        
            else:
                # 遗物信息 - 繁中版本
                signature_msg_tw = []
                signature_msg_tw.append(f"【遺物信息】")
                # 检查图片是否存在并添加
                if os.path.exists(signature_img_path):
                    signature_msg_tw.append(MessageSegment.image(f"file:///{signature_img_path}"))
                
                signature_info_tw = f"""{signature_name_zh_tw}
{signature_desc_tw}

{max_level}級屬性：
{chr(10).join(signature_stats)}

遺物技能【{signature_title_zh_tw}】：
""" + "\n".join(f"等級{i+1}：{desc_tw}" for i, (desc_tw, desc_cn, desc_kr, desc_en) in enumerate(signature_descriptions))
                signature_msg_tw.append(signature_info_tw)
                messages.append("\n".join(str(x) for x in signature_msg_tw))

        # 构建转发消息
        forward_msgs = []
        for msg in messages:
            # 如果消息是字符串，直接添加
            if isinstance(msg, str):
                forward_msgs.append({
                    "type": "node",
                    "data": {
                        "name": "Eversoul Info",
                        "uin": bot.self_id,
                        "content": msg
                    }
                })

        # 如果消息是列表（包含图片），将其合并
            elif isinstance(msg, list):
                forward_msgs.append({
                    "type": "node",
                    "data": {
                        "name": "Eversoul Info",
                        "uin": bot.self_id,
                        "content": "\n".join(str(x) for x in msg)
                    }
                })

        # 发送合并转发消息
        if isinstance(event, GroupMessageEvent):
            await bot.call_api(
                "send_group_forward_msg",
                group_id=event.group_id,
                messages=forward_msgs
            )
        else:
            await bot.call_api(
                "send_private_forward_msg",
                user_id=event.user_id,
                messages=forward_msgs
            )
    except Exception as e:
        if not isinstance(e, FinishedException):
            import traceback
            error_location = traceback.extract_tb(e.__traceback__)[-1]
            logger.error(
                f"处理角色信息时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )
            await es_hero_info.finish(f"处理角色信息时发生错误: {str(e)}")