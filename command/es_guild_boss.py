from ..library.utils import *


@es_guild_boss.handle()
async def handle(bot: Bot, event: Event, args: Message = CommandArg()):
    try:
        # 获取输入
        boss_name = args.extract_plain_text().strip()
        if not boss_name:
            await es_guild_boss.finish("请输入工会BOSS名称！")

        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
        else:
            group_id = None

        config = await get_group_data_source(group_id)
        data = await load_json_data(group_id)

        # 确定使用哪个别名文件
        server = config.get("server", "global")
        data_type = config.get("type", "live")

        if data_type == "review":
            raid_alias_file = CONFIG_DIR / "review_raid_aliases.yaml"
        else:
            raid_alias_file = CONFIG_DIR / "live_raid_aliases.yaml"

        # 加载别名数据
        alias_map = {}
        aliases_data = None

        if raid_alias_file.exists():
            with open(raid_alias_file, "r", encoding="utf-8") as f:
                aliases_data = yaml.safe_load(f)

            if aliases_data and "names" in aliases_data:
                for hero in aliases_data["names"]:
                    if isinstance(hero, dict) and "hero_id" in hero:
                        # 添加所有语言版本的名称
                        name_fields = [
                            "zh_tw_name",
                            "zh_cn_name",
                            "kr_name",
                            "en_name",
                            "ja_name",
                        ]
                        hero_id = hero["hero_id"]

                        def add_alias(name, h_id):
                            if name not in alias_map:
                                alias_map[name] = []
                            if h_id not in alias_map[name]:
                                alias_map[name].append(h_id)

                        for field in name_fields:
                            if hero.get(field):
                                add_alias(hero[field], hero_id)
                                if field == "en_name":
                                    add_alias(hero[field].lower(), hero_id)

                        # 添加别名
                        for alias in hero.get("aliases", []):
                            add_alias(alias, hero_id)
                            if alias.isascii():
                                add_alias(alias.lower(), hero_id)

        # 验证BOSS是否存在的函数
        def get_valid_boss_data(target_hero_id):
            for boss in data["guild_raid"]["json"]:
                if boss.get("boss_no") == target_hero_id:
                    return boss
            return None

        # 查找 hero_id
        hero_ids = alias_map.get(boss_name)
        if not hero_ids and boss_name.isascii():
            hero_ids = alias_map.get(boss_name.lower())

        boss_data = None
        hero_id = None

        if hero_ids:
            for hid in hero_ids:
                if b_data := get_valid_boss_data(hid):
                    boss_data = b_data
                    hero_id = hid
                    break

        if not hero_id:
            # 模糊匹配
            all_names = list(alias_map.keys())
            if boss_name.isascii():
                matches = get_close_matches(
                    boss_name.lower(),
                    [n.lower() if n.isascii() else n for n in all_names],
                    n=1,
                    cutoff=0.6,
                )
            else:
                matches = get_close_matches(boss_name, all_names, n=1, cutoff=0.6)

            if matches:
                matched_name = matches[0]
                matched_hero_ids = alias_map[matched_name]

                # 在模糊匹配中也寻找有效的BOSS ID
                matched_hero_id = None
                for hid in matched_hero_ids:
                    if get_valid_boss_data(hid):
                        matched_hero_id = hid
                        break

                if matched_hero_id:
                    # 构建“是否想查询”的消息 (参考 es_hero.py)
                    response_parts = ["未找到BOSS " + boss_name + "\n您是否想查询："]

                    main_names = {
                        "繁体": None,
                        "简体": None,
                        "韩文": None,
                        "英文": None,
                        "日文": None,
                    }
                    aliases = []

                    if aliases_data:
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
                                aliases = hero.get("aliases", [])
                                break

                    for lang, name in main_names.items():
                        if name:
                            response_parts.append(f"{lang}：{name}")
                    if aliases:
                        response_parts.append(f"别名：{', '.join(aliases)}")

                    await es_guild_boss.finish("\n".join(response_parts))
                else:
                    await es_guild_boss.finish(f"未找到工会BOSS: {boss_name}")
            else:
                await es_guild_boss.finish(f"未找到工会BOSS: {boss_name}")

        if not boss_data:
            await es_guild_boss.finish("未找到该BOSS的公会讨伐数据")

        # 查找 Hero 数据
        hero_data = None
        for hero in data["hero"]["json"]:
            if hero["hero_id"] == hero_id:
                hero_data = hero
                break

        if not hero_data:
            await es_guild_boss.finish("未找到该BOSS的基础信息")

        # 获取各类名称
        name_info = await get_string_character(data, hero_data["name_sno"])
        name_zh_tw = name_info["zh_tw"]

        race_zh_tw = (
            await get_string_by_type(data, "system", hero_data["race_sno"])
        ).get("zh_tw", "")
        class_zh_tw = (
            await get_string_by_type(data, "system", hero_data["class_sno"])
        ).get("zh_tw", "")
        sub_class_zh_tw = (
            await get_string_by_type(data, "system", hero_data["sub_class_sno"])
        ).get("zh_tw", "")
        stat_zh_tw = (
            await get_string_by_type(data, "system", hero_data["stat_sno"])
        ).get("zh_tw", "")
        grade_zh_tw = (
            await get_string_by_type(data, "system", hero_data["grade_sno"])
        ).get("zh_tw", "")

        msgs = []
        basic_msg = []
        basic_msg.append(f"【工会讨伐：{name_zh_tw}】")

        # 尝试获取立绘 (参考 es_hero.py)
        portrait_paths = await get_character_portrait(data, hero_id)
        if portrait_paths:
            # 只取第一张
            if os.path.exists(portrait_paths[0]):
                basic_msg.append(MessageSegment.image(f"file:///{portrait_paths[0]}"))

        info_text = f"""类型：{race_zh_tw} {class_zh_tw}
攻击方式：{sub_class_zh_tw}
属性：{stat_zh_tw}
品质：{grade_zh_tw}
攻击力：{int(hero_data.get('attack', 0))} (+{int(hero_data.get('inc_attack', 0))}/级)
防御力：{int(hero_data.get('defence', 0))} (+{int(hero_data.get('inc_defence', 0))}/级)
生命值：{int(hero_data.get('max_hp', 0))} (+{int(hero_data.get('inc_max_hp', 0))}/级)
暴击率：{hero_data.get('critical_rate', 0) * 100:.1f}% (+{hero_data.get('inc_critical_rate', 0) * 100:.3f}%/级)
暴击威力：{hero_data.get('critical_power', 0) * 100:.1f}% (+{hero_data.get('inc_critical_power', 0) * 100:.3f}%/级)"""

        basic_msg.append(info_text)
        msgs.append(basic_msg)

        # 攻略信息
        guide_sno = boss_data.get("guide_sno")
        if guide_sno:
            guide_info = await get_string_by_type(data, "ui", guide_sno)
            guide_zh_tw = guide_info.get("zh_tw", "")
            if guide_zh_tw:
                cleaned_guide = await clean_rich_text(guide_zh_tw)
                msgs.append(f"【攻略情报】\n{cleaned_guide}")

        # 技能释放顺序
        skill_pattern = await get_character_skill_pattern(
            data, hero_id, server, data_type
        )
        if skill_pattern:
            pattern_text = ["【技能释放顺序】"]
            for i, (skill_name, skill_type) in enumerate(skill_pattern, 1):
                pattern_text.append(f"{i}. [{skill_type}] {skill_name}")
            msgs.append("\n".join(pattern_text))

        skill_types = []
        skill_keys = [
            "skill_no_1",
            "skill_no_2",
            "skill_no_3",
            "skill_no_4",
            "ultimate_skill_no",
        ]

        # 先检查角色有哪些技能
        for skill_key in skill_keys:
            skill_no = hero_data.get(skill_key)
            if skill_no:
                # 在skill表中查找
                found_skill = None
                for skill in data["skill"]["json"]:
                    if skill["no"] == skill_no:
                        found_skill = skill
                        break
                
                if found_skill:
                    skill_type_data = await get_string_by_type(
                        data, "system", found_skill["type"]
                    )
                    skill_type_zh_tw = skill_type_data["zh_tw"]
                    skill_type_zh_cn = skill_type_data["zh_cn"]
                    skill_type_kr = skill_type_data["kr"]
                    skill_type_en = skill_type_data["en"]
                    skill_info = await get_character_skill(
                        data, skill_no, server=server, data_type=data_type
                    )
                    skill_types.append(
                        (
                            skill_type_zh_tw,
                            skill_type_zh_cn,
                            skill_type_kr,
                            skill_type_en,
                            skill_info,
                        )
                    )
        for idx, (
            skill_type_zh_tw,
            skill_type_zh_cn,
            skill_type_kr,
            skill_type_en,
            skill_info,
        ) in enumerate(skill_types):
            
            skill_text = []

            # 只显示文字（带技能图标）
            if skill_info["icon_info"]:
                icon_path = str(ICON_DIR / f"{skill_info['icon_info']['icon']}.png")
                cache_filename = f"{skill_info['icon_info']['icon']}_{skill_info['icon_info']['color'].replace('#', '')}.png"
                cache_path = str(ICON_DIR / cache_filename)

                # 如果存在缓存图标，直接使用
                if os.path.exists(cache_path):
                    with open(cache_path, "rb") as f:
                        colored_icon = f.read()
                else:
                    # 没有缓存，重新生成并保存
                    colored_icon = await apply_color_to_icon(
                        icon_path, skill_info["icon_info"]["color"]
                    )
                    with open(cache_path, "wb") as f:
                        f.write(colored_icon)

                skill_text.append(MessageSegment.image(colored_icon))

            skill_type_text = await select_text_by_priority(
                skill_type_zh_tw,
                skill_type_zh_cn,
                skill_type_kr,
                skill_type_en,  # 使用英文作为备选
                server,
                data_type,
            )
            skill_name_text = await select_text_by_priority(
                skill_info["name"]["zh_tw"],
                skill_info["name"]["zh_cn"],
                skill_info["name"]["kr"],
                skill_info["name"].get("ja", ""),
                server,
                data_type,
            )

            skill_text.append(f"【{skill_type_text}】{skill_name_text}")
            
            for i, desc in enumerate(skill_info["descriptions"]):
                desc_text = await select_text_by_priority(
                    desc["desc_zh_tw"],
                    desc["desc_zh_cn"],
                    desc["desc_kr"],
                    desc.get("desc_ja", ""),
                    server,
                    data_type,
                )
                # 清理颜色代码
                desc_text = await clean_rich_text(desc_text)
                hero_level = desc.get("hero_level", 1)
                unlock_text = f"（等级{hero_level}解锁）" if hero_level >= 1 else ""
                skill_text.append(f"\n{desc_text}{unlock_text}\n")

            # 每个技能单独添加到msgs
            msgs.append(skill_text)

        # 发送合并转发消息
        forward_msgs = []
        for msg in msgs:
            content = msg
            if isinstance(msg, list):
                # 处理列表中可能的图片和文本混合
                content_parts = []
                for part in msg:
                    if isinstance(part, str):
                        content_parts.append(part)
                    else:
                        content_parts.append(str(part))
                content = "\n".join(content_parts)

            forward_msgs.append(
                {
                    "type": "node",
                    "data": {
                        "name": "Eversoul Guild Boss",
                        "uin": bot.self_id,
                        "content": content,
                    },
                }
            )

        if isinstance(event, GroupMessageEvent):
            await bot.call_api(
                "send_group_forward_msg", group_id=event.group_id, messages=forward_msgs
            )
        else:
            await bot.call_api(
                "send_private_forward_msg",
                user_id=event.get_user_id(),
                messages=forward_msgs,
            )

    except Exception as e:
        if not isinstance(e, FinishedException):
            import traceback

            error_location = traceback.extract_tb(e.__traceback__)[-1]
            logger.error(
                f"处理工会BOSS信息时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )
