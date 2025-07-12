from ..library.utils import *


@es_hero_skill.handle()
async def handle(bot: Bot, event: Event, args: Message = CommandArg()):
    try:
        # 获取输入的文本并提取角色名
        hero_name = args.extract_plain_text().strip()
        if not hero_name:
            await es_hero.finish("请输入角色名！")
        
        # 获取群组ID
        group_id = 0
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
                    "英文": None,
                    "日文": None
                }
                aliases = []
                
                # 直接从原始数据中获取各语言名称
                for hero in aliases_data["names"]:
                    if hero["hero_id"] == matched_hero_id:
                        if hero.get("zh_tw_name"):
                            main_names["繁体"] = hero.get("zh_tw_name")
                        if hero.get("zh_cn_name"):
                            main_names["简体"] = hero.get("zh_cn_name")
                        if hero.get("kr_name"):
                            main_names["韩文"] = hero.get("kr_name")
                        if hero.get("en_name"):
                            main_names["英文"] = hero.get("en_name")
                        if hero.get("ja_name"):
                            main_names["日文"] = hero.get("ja_name")
                        # 获取别名
                        aliases = hero.get("aliases", [])
                        break
                
                # 构建响应消息
                response_parts = ["未找到角色 " + hero_name + "\n您是否想查询："]
                
                # 添加各语言名称
                for lang, name in main_names.items():
                    if name:
                        response_parts.append(f"{lang}：{name}")
                
                # 添加别名
                if aliases:
                    response_parts.append(f"别名：{', '.join(aliases)}")
                
                await es_hero.finish("\n".join(response_parts))
            else:
                await es_hero.finish(f"未找到角色 {hero_name}")
        
        assert hero_id is not None, "hero_id 应该不为空"
        
        # 查找角色数据
        hero_data = None
        for hero in data["hero"]["json"]:
            if hero["hero_id"] == hero_id:
                hero_data = hero
                break
        
        
        if not hero_data:
            await es_hero.finish("未找到该角色信息")     
        
        messages = []

        # 技能信息
        skill_types = []
        skill_keys = ["skill_no_1", "skill_no_2", "skill_no_3", "skill_no_4",  "ultimate_skill_no", "support_skill_no"]
        
        # 获取并显示技能释放顺序
        skill_pattern = get_character_skill_pattern(data, hero_id, is_test)
        if skill_pattern:
            pattern_text = ["▼ 技能释放顺序(仅供参考,具体情况以实际为准)"]
            for i, (skill_name, is_normal) in enumerate(skill_pattern, 1):
                pattern_text.append(f"{i}. {skill_name}")
            messages.append("\n".join(pattern_text))
        
        # 先检查角色有哪些技能
        for skill_key in skill_keys:
            if skill_no := hero_data.get(skill_key):
                for skill in data["skill"]["json"]:
                    if skill["no"] == skill_no:
                        skill_type_data = get_string_system(data, skill["type"])
                        skill_type_zh_tw = skill_type_data["zh_tw"]
                        skill_type_zh_cn = skill_type_data["zh_cn"]
                        skill_type_kr = skill_type_data["kr"]
                        skill_type_en = skill_type_data["en"]
                        # 判断是否为支援技能
                        is_support = (skill_key == "support_skill_no")
                        skill_info = get_character_skill(data, skill_no, is_support, hero_data)
                        skill_types.append((skill_type_zh_tw, skill_type_zh_cn, skill_type_kr, skill_type_en, skill_info))
                        break
        
        for skill_type_zh_tw, skill_type_zh_cn, skill_type_kr, skill_type_en, skill_info in skill_types:
            skill_text = []
            # 如果有技能图标，处理并添加
            if skill_info["icon_info"]:
                icon_path = str(ICON_DIR / f"{skill_info['icon_info']['icon']}.png")
                
                # 检查是否存在缓存的着色图标
                cache_filename = f"{skill_info['icon_info']['icon']}_{skill_info['icon_info']['color'].replace('#', '')}.png"
                cache_path = str(ICON_DIR / cache_filename)
                
                # 如果存在缓存图标，直接使用
                if os.path.exists(cache_path):
                    with open(cache_path, "rb") as f:
                        colored_icon = f.read()
                else:
                    # 没有缓存，重新生成并保存
                    colored_icon = apply_color_to_icon(icon_path, skill_info['icon_info']['color'])
                    # 保存到缓存目录
                    with open(cache_path, "wb") as f:
                        f.write(colored_icon)
                
                skill_text.append(MessageSegment.image(colored_icon))
            
            # 适配文本获取逻辑：优先使用zh_tw，如果为空则根据is_test决定
            skill_type_text = skill_type_zh_tw if skill_type_zh_tw else (skill_type_kr if is_test else skill_type_zh_tw)
            skill_name_text = skill_info["name"]["zh_tw"] if skill_info["name"]["zh_tw"] else (skill_info["name"]["kr"] if is_test else skill_info["name"]["zh_tw"])
            
            # 如果是支援技能，使用新的格式
            if skill_info["is_support"]:
                # 分类存储主要和辅助效果
                main_effects = []
                support_effects = []
                
                # 对效果进行分类
                for desc in skill_info["descriptions"]:
                    if desc.get("type") == "main_partner":
                        # 从desc_zh_tw中去除前缀，优先使用zh_tw，为空时根据is_test决定
                        desc_text = desc["desc_zh_tw"].replace("主要夥伴：", "") if desc["desc_zh_tw"] else (desc["desc_kr"].replace("메인 파트너：", "") if is_test else desc["desc_zh_tw"])
                        main_effects.append(desc_text)
                    elif desc.get("type") == "support_partner":
                        # 从desc_zh_tw中去除前缀，优先使用zh_tw，为空时根据is_test决定
                        desc_text = desc["desc_zh_tw"].replace("輔助夥伴：", "") if desc["desc_zh_tw"] else (desc["desc_kr"].replace("서브 파트너：", "") if is_test else desc["desc_zh_tw"])
                        support_effects.append(desc_text)
                
                # 如果有主要效果，添加主要效果部分
                if main_effects:
                    skill_text.append("▼ 主要伙伴效果")
                    skill_text.append(f"【{skill_type_text}】{skill_name_text}")
                    skill_text.extend(main_effects)
                
                # 如果有辅助效果，添加辅助效果部分
                if support_effects:
                    skill_text.append("▼ 辅助伙伴效果")
                    if not main_effects:  # 如果之前没有显示过技能名称，在这里显示
                        skill_text.append(f"【{skill_type_text}】{skill_name_text}")
                    skill_text.extend(support_effects)
            else:
                # 非支援技能保持原有格式
                # 只在第一级显示技能类型和名称
                skill_text.append(f"【{skill_type_text}】{skill_name_text}")
                for i, desc in enumerate(skill_info["descriptions"]):
                    # 适配描述文本获取逻辑：优先使用zh_tw，如果为空则根据is_test决定
                    desc_text = desc["desc_zh_tw"] if desc["desc_zh_tw"] else (desc["desc_kr"] if is_test else desc["desc_zh_tw"])
                    hero_level = desc.get("hero_level", 1)
                    unlock_text = f"（等级{hero_level}解锁）" if hero_level >= 1 else ""
                    skill_text.append(f"等级{i+1}：{desc_text}{unlock_text}\n")
            
            messages.append("\n".join(str(x) for x in skill_text))

        
        # 获取并添加遗物信息
        signature_info = get_character_signature(data, hero_id)
        if signature_info["name"]["kr"]:
            signature_stats = signature_info["stats"]
            max_level = signature_info["max_level"] 
            max_level_battle_power_per = signature_info["max_level_battle_power_per"]
            signature_bg_path = signature_info["bg_path"]
            signature_img_path = str(SOUL_DIR / signature_bg_path)

            # 遗物信息 - 优先使用zh_tw，为空时根据is_test决定
            signature_msg = []
            signature_msg.append(f"【遺物信息】")
            # 检查图片是否存在并添加
            if os.path.exists(signature_img_path):
                signature_msg.append(MessageSegment.image(f"file:///{signature_img_path}"))
            
            # 适配文本获取逻辑：优先使用zh_tw，如果为空则根据is_test决定
            signature_name_text = signature_info["name"]["zh_tw"] if signature_info["name"]["zh_tw"] else (signature_info["name"]["kr"] if is_test else signature_info["name"]["zh_tw"])
            signature_desc_text = signature_info["description"]["zh_tw"] if signature_info["description"]["zh_tw"] else (signature_info["description"]["kr"] if is_test else signature_info["description"]["zh_tw"])
            signature_title_text = signature_info["title"]["zh_tw"] if signature_info["title"]["zh_tw"] else (signature_info["title"]["kr"] if is_test else signature_info["title"]["zh_tw"])
            
            # 组装描述信息
            skill_descriptions_text = []
            for i, skill in enumerate(signature_info["skills"]):
                desc_text = skill["desc_zh_tw"] if skill["desc_zh_tw"] else (skill["desc_kr"] if is_test else skill["desc_zh_tw"])
                skill_descriptions_text.append(f"等級{i+1}：{desc_text}")
            
            signature_info_text = f"""{signature_name_text}
{signature_desc_text}
最大等级战力百分比：{max_level_battle_power_per}
{max_level}級屬性：
{chr(10).join(signature_stats)}
遺物技能【{signature_title_text}】：
""" + "\n".join(skill_descriptions_text)
            
            signature_msg.append(signature_info_text)
            messages.append("\n".join(str(x) for x in signature_msg))

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
                user_id=event.get_user_id(),
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
            await es_hero.finish(f"处理角色信息时发生错误: {str(e)}")