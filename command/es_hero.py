from ..library.utils import *


@es_hero.handle()
async def handle(bot: Bot, event: Event, args: Message = CommandArg()):
    try:
        # 获取输入的文本并提取角色名
        hero_name = args.extract_plain_text().strip()
        if not hero_name:
            await es_hero.finish("请输入角色名！")

        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
        
        config = await get_group_data_source(group_id)
        data = await load_json_data(group_id)
        
        # 加载别名配置和原始别名数据
        with open(config["hero_alias_file"], "r", encoding="utf-8") as f:
            aliases_data = yaml.safe_load(f)
        alias_map = await load_aliases(group_id)
        
        # 判断是否为测试模式
        review = config["type"] == "review"

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
        
        # 确保hero_id不为None (类型断言)
        assert hero_id is not None, "hero_id 应该不为空"
        
        # 查找角色数据
        hero_data = None
        hero_desc = None
        for hero in data["hero"]["json"]:
            if hero["hero_id"] == hero_id:
                hero_data = hero
                break
        
        # 查找角色描述数据
        for desc in data["hero_desc"]["json"]:
            if desc["hero_no"] == hero_id:
                hero_desc = desc
                break
        
        if not hero_data:
            await es_hero.finish("未找到该角色信息")     
        # 获取角色名称
        if hero_data["name_sno"]:
            name_data = await get_string_character(data, hero_data["name_sno"])
            hero_name_zh_tw = name_data["zh_tw"]
            hero_name_zh_cn = name_data["zh_cn"]
            hero_name_kr = name_data["kr"]
            hero_name_en = name_data["en"]
            

        # 实装日期
        character_release_date = await get_character_release_date(data, hero_id)
        # 类型
        race_zh_tw = (await get_string_by_type(data, "system", hero_data["race_sno"])).get("zh_tw", "")
        # 职业
        hero_class_zh_tw = (await get_string_by_type(data, "system", hero_data["class_sno"])).get("zh_tw", "")
        # 攻击方式
        sub_class_zh_tw = (await get_string_by_type(data, "system", hero_data["sub_class_sno"])).get("zh_tw", "")
        # 属性
        stat_zh_tw = (await get_string_by_type(data, "system", hero_data["stat_sno"])).get("zh_tw", "")
        # 品质
        grade_zh_tw = (await get_string_by_type(data, "system", hero_data["grade_sno"])).get("zh_tw", "")

        atk_range = await get_character_attack_range(data, hero_id)
        
        # 构建消息列表
        messages = []
        nickname_zh_tw = ""
        nickname_kr = ""
        if hero_desc and isinstance(hero_desc, dict):
            nick_name_sno = hero_desc.get("nick_name_sno")
            nickname_data = await get_string_character(data, nick_name_sno)
            nickname_zh_tw = nickname_data["zh_tw"]
            nickname_kr = nickname_data["kr"]
        
        basic_info_msg = []
        basic_info_msg.append("【基础信息】")
        portrait_paths = await get_character_portrait(data, hero_data.get("prefab_path", "")) 
        if portrait_paths:
            for portrait_path in portrait_paths:
                basic_info_msg.append(MessageSegment.image(f"file:///{portrait_path}"))
                
        # 获取CV信息
        cv_info = await get_character_cv(data, hero_desc)
        cv_kr = cv_info.get("kr")
        cv_jp = cv_info.get("ja")
        
        basic_info_zh_tw = f"""{nickname_zh_tw if nickname_zh_tw != "" else nickname_kr}・{hero_name_zh_tw if hero_name_zh_tw != "" else hero_name_kr}
类型：{race_zh_tw} {hero_class_zh_tw}
攻击方式：{sub_class_zh_tw}
属性：{stat_zh_tw}
品质：{grade_zh_tw}
隶属：{
    (await get_string_character(data, hero_desc.get("union_sno", 0), special=True)).get("zh_tw", "") 
    if hero_desc is not None and hero_desc.get("union_sno") is not None and 
       await get_string_character(data, hero_desc.get("union_sno", 0), special=True) is not None and
       (await get_string_character(data, hero_desc.get("union_sno", 0), special=True)).get("zh_tw", "") != ""
    else "？？？"
}
身高：{hero_desc.get("height", "？？？") if hero_desc else "？？？"}cm
体重：{hero_desc.get("weight", "？？？") if hero_desc else "？？？"}kg
生日：{await get_character_birthday(data, hero_desc.get("birthday", 0)) if hero_desc else "？？？"}
星座：{(await get_string_character(data, hero_desc.get("constellation_sno", 0), special=True)).get("zh_tw", "") if hero_desc else "？？？"}
兴趣：{(await get_string_character(data, hero_desc.get("hobby_sno", 0), special=True)).get("zh_tw", "") if hero_desc else "？？？"}
特殊特长：{(await get_string_character(data, hero_desc.get("speciality_sno", 0), special=True)).get("zh_tw", "") if hero_desc else "？？？"}
喜欢的东西：{(await get_string_character(data, hero_desc.get("like_sno", 0), special=True)).get("zh_tw", "") if hero_desc else "？？？"}
讨厌的东西：{(await get_string_character(data, hero_desc.get("dislike_sno", 0), special=True)).get("zh_tw", "") if hero_desc else "？？？"}
喜好礼物：{await get_character_prefer_gift(data, hero_id)}
初始打工属性：{(await get_character_arbeit(data, hero_id)).get("initial", "？？？")}
满级打工属性：{(await get_character_arbeit(data, hero_id)).get("max", "？？？")}
CV_KR：{cv_kr}"""
        if cv_jp != "？？？":
            basic_info_zh_tw += f"\nCV_JP：{cv_jp}"
        
        basic_info_zh_tw += f"""
实装日期：{character_release_date}
攻击范围：{atk_range if atk_range > 0 else "？？？"}
攻击力：{int(hero_data.get('attack', 0))} + {int(hero_data.get('inc_attack', 0))}/级
防御力：{int(hero_data.get('defence', 0))} + {int(hero_data.get('inc_defence', 0))}/级
生命值：{int(hero_data.get('max_hp', 0))} + {int(hero_data.get('inc_max_hp', 0))}/级
暴击率：{hero_data.get('critical_rate', 0) * 100:.1f}% + {hero_data.get('inc_critical_rate', 0) * 100:.3f}%/级
暴击威力：{hero_data.get('critical_power', 0) * 100:.1f}% + {hero_data.get('inc_critical_power', 0) * 100:.3f}%/级"""
        basic_info_msg.append(basic_info_zh_tw)
        messages.append("".join(str(x) for x in basic_info_msg))

        # 添加立绘
        for char in data["string_character"]["json"]:
            if char["no"] == hero_data["name_sno"]:
                images = await get_character_illustration(data, hero_id)
                if images:
                    image_msg = []
                    image_msg.append("【立绘】")
                    for img_path, display_name_zh_tw, display_name_zh_cn, display_name_kr,\
                        display_name_en, condition_tw, condition_cn, condition_kr, condition_en in images:
                        image_msg.append(f"{display_name_zh_tw}\n解锁条件: {condition_tw}")
                        image_msg.append(MessageSegment.image(f"file:///{img_path}"))
                    messages.append("\n".join(str(x) for x in image_msg))
                break

        # 获取自我介绍
        if hero_desc and isinstance(hero_desc, dict):
            intro_sno = hero_desc.get("introduction_sno")
            if intro_sno:
                intro_data = await get_string_character(data, intro_sno)
                intro_zh_tw = intro_data["zh_tw"]
                intro_kr = intro_data["kr"]
                if intro_zh_tw or intro_kr:
                    intro_text = await select_text_by_priority(intro_zh_tw, intro_kr, review)
                    messages.append("【自我介绍】\n" + intro_text)
        

        # 获取灵魂链接信息，
        soullink_info = await get_character_soullink(data, hero_id, review)
        if soullink_info:
            for link in soullink_info:
                link_msg = ["【灵魂链接】"]
                # 标题可能为空，添加默认值
                title = link['title'] or "未知链接"
                link_msg.append(f"名称：{title}")
                
                # 角色列表可能为空，添加默认处理
                heroes = '、'.join(link['heroes']) if link['heroes'] else "未知角色"
                link_msg.append(f"相关角色：{heroes}")
                
                if link['story']:
                    link_msg.append(f"\n{link['story']}")
                    
                # 效果可能为空
                if link['effects']:
                    link_msg.append("\n收集效果：")
                    for effect in link['effects']:
                        # 条件和效果可能为空
                        condition = effect.get('condition', "未知条件")
                        link_msg.append(f"▶ {condition}")
                        
                        effects_list = effect.get('effects', [])
                        if effects_list:
                            link_msg.append("  " + "\n  ".join(effects_list))
                        else:
                            link_msg.append("  未知效果")
        
                if link['open_date']:
                    link_msg.append(f"\n开启时间：{link['open_date']}")
                    
                messages.append("\n".join(link_msg))

        # 添加好感故事攻略
        has_story, episode_info, endings = await get_character_story(data, hero_id)
        if has_story:
                messages.append(await format_character_story(episode_info, endings, review))
        
        # 好感故事CG
        cg_images = await get_character_affection_cg(data, hero_id)
        if cg_images:
            cg_msg = []
            cg_msg.append("【好感CG】\n")
            current_episode = None
            for img_path, cg_no, episode, episode_title in cg_images:
                # 如果章节号变化，添加章节标题
                if episode != current_episode:
                    cg_msg.append(f"EP{episode}：{episode_title}")
                    current_episode = episode
                cg_msg.append(MessageSegment.image(f"file:///{img_path}"))
            messages.append("".join(str(x) for x in cg_msg))
        
        # 添加角色关键字信息
        keyword_info = await get_character_keyword(data, hero_id, review=False)
        if keyword_info:
            messages.append(keyword_info)

        # EverPhone插图
        evertalk_illusts = await get_character_evertalk_cg(data, hero_id)
        if evertalk_illusts:
            illust_msg = []
            illust_msg.append("【EverPhone插图】")
            for img_path, illust_base in evertalk_illusts:
                illust_msg.append(MessageSegment.image(f"file:///{img_path}"))
            messages.append("".join(str(x) for x in illust_msg))

        # 添加专属领地物品信息
        town_objects = await get_character_town_object(data, hero_id, review)
        if town_objects:
            objects_msg: list = ["【专属领地物品】"]
            for obj_no, name, grade, slot_type, desc, img_path, battle_power_per in town_objects:
                if img_path and os.path.exists(img_path):
                    objects_msg.append(MessageSegment.image(f"file:///{img_path}"))
                objects_msg.append(f"名称：{name}")
                if grade:
                    objects_msg.append(f"品质：{grade}")
                if slot_type:
                    objects_msg.append(f"类型：{slot_type}")
                if desc:
                    objects_msg.append(f"描述：{desc}")
                if battle_power_per:
                    objects_msg.append(f"战力百分比：{battle_power_per}")
                
                # 添加可进行的任务信息
                tasks = await get_character_town_object_task(data, obj_no, review)
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