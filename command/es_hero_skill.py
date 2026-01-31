from ..library.utils import *


@es_hero_skill.handle()
async def handle(bot: Bot, event: Event, args: Message = CommandArg()):
    try:
        raw_text = args.extract_plain_text().strip()
        if not raw_text:
            await es_hero.finish("请输入角色名！")

        # 解析参数：角色名 [图片标志]
        parts = raw_text.rsplit(maxsplit=1)
        hero_name = parts[0]
        generate_image_flag = False

        # 最后一个参数是否是图片标志
        if len(parts) == 2 and parts[1] in ("1", "0"):
            generate_image_flag = parts[1] == "1"
            hero_name = parts[0]
        else:
            hero_name = raw_text
            generate_image_flag = False
        group_id = 0
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id

        config = await get_group_data_source(group_id)
        data = await load_json_data(group_id)

        with open(config["hero_alias_file"], "r", encoding="utf-8") as f:
            aliases_data = yaml.safe_load(f)
        alias_map = await load_aliases(group_id)

        # 获取服务器和数据类型
        server = config.get("server", "global")
        data_type = config.get("type", "live")
        hero_id = alias_map.get(hero_name)
        if not hero_id and hero_name.isascii():
            hero_id = alias_map.get(hero_name.lower())

        if not hero_id:
            all_names = list(alias_map.keys())
            if hero_name.isascii():
                matches = get_close_matches(
                    hero_name.lower(),
                    [n.lower() if n.isascii() else n for n in all_names],
                    n=1,
                    cutoff=0.6,
                )
            else:
                matches = get_close_matches(hero_name, all_names, n=1, cutoff=0.6)
            if matches:
                matched_name = matches[0]
                matched_hero_id = alias_map[matched_name]

                main_names = {
                    "繁体": None,
                    "简体": None,
                    "韩文": None,
                    "英文": None,
                    "日文": None,
                }
                aliases = []
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

                response_parts = ["未找到角色 " + hero_name + "\n您是否想查询："]

                for lang, name in main_names.items():
                    if name:
                        response_parts.append(f"{lang}：{name}")

                if aliases:
                    response_parts.append(f"别名：{', '.join(aliases)}")

                await es_hero.finish("\n".join(response_parts))
            else:
                await es_hero.finish(f"未找到角色 {hero_name}")

        assert hero_id is not None, "hero_id 应该不为空"

        hero_data = None
        for hero in data["hero"]["json"]:
            if hero["hero_id"] == hero_id:
                hero_data = hero
                break

        if not hero_data:
            await es_hero.finish("未找到该角色信息")

        messages = []

        # 获取技能信息（使用通用函数）
        skill_keys = [
            "skill_no_1",
            "skill_no_2",
            "skill_no_3",
            "skill_no_4",
            "ultimate_skill_no",
            "support_skill_no",
        ]

        skills_data = await get_skills_info(
            data,
            hero_data,
            skill_keys,
            server,
            data_type,
            generate_image=generate_image_flag,
        )

        # 技能释放顺序
        if skills_data["skill_pattern"]:
            pattern_text = ["▼ 技能释放顺序"]
            for i, (skill_name, skill_type) in enumerate(
                skills_data["skill_pattern"], 1
            ):
                pattern_text.append(f"{i}. 【{skill_type}】{skill_name} ")
            messages.append("\n".join(pattern_text))

        # 技能详情
        for skill_data in skills_data["skills"]:
            skill_info = skill_data["skill_info"]
            skill_text = []

            # 根据标志决定显示内容
            if generate_image_flag:
                # 只显示图片
                if skill_info.get("image_bytes"):
                    skill_text.append(MessageSegment.image(skill_info["image_bytes"]))
            else:
                # 只显示文字（带技能图标）
                if skill_info["icon_info"]:
                    icon_path = str(ICON_DIR / f"{skill_info['icon_info']['icon']}.png")
                    cache_filename = f"{skill_info['icon_info']['icon']}_{skill_info['icon_info']['color'].replace('#', '')}.png"
                    cache_path = str(ICON_DIR / cache_filename)

                    if os.path.exists(cache_path):
                        with open(cache_path, "rb") as f:
                            colored_icon = f.read()
                    else:
                        colored_icon = await apply_color_to_icon(
                            icon_path, skill_info["icon_info"]["color"]
                        )
                        with open(cache_path, "wb") as f:
                            f.write(colored_icon)

                    skill_text.append(MessageSegment.image(colored_icon))

                # 添加文字描述
                if skill_data["is_support"]:
                    # 支援技能特殊处理
                    descriptions = await format_skill_descriptions(
                        skill_info, server, data_type
                    )
                    main_effects = [
                        desc["text"]
                        for desc in descriptions
                        if desc.get("type") == "support"
                    ]

                    if main_effects:
                        skill_text.append(
                            f"【{skill_data['skill_type']}】{skill_data['skill_name']}\n"
                        )
                        skill_text.extend(main_effects)
                else:
                    skill_text.append(
                        f"【{skill_data['skill_type']}】{skill_data['skill_name']}"
                    )
                    descriptions = await format_skill_descriptions(
                        skill_info, server, data_type
                    )
                    for desc in descriptions:
                        skill_text.append(f"\n{desc['text']}{desc['unlock_text']}\n")

            messages.append(skill_text)

        signature_info = await get_character_signature(
            data,
            hero_id,
            generate_image=generate_image_flag,
            server=server,
            data_type=data_type,
        )
        if signature_info["name"]["kr"] or signature_info["name"]["zh_cn"]:
            signature_stats = signature_info["stats"]
            max_level = signature_info["max_level"]
            max_level_battle_power_per = signature_info["max_level_battle_power_per"]
            signature_bg_path = signature_info["bg_path"]
            signature_img_path = str(SOUL_DIR / signature_bg_path)

            signature_msg = []

            # 根据标志决定显示内容
            if generate_image_flag:
                # 只显示图片
                if signature_info.get("image_bytes"):
                    signature_msg.append(
                        MessageSegment.image(signature_info["image_bytes"])
                    )
            else:
                # 只显示文字
                signature_msg.append(f"【遗物信息】")
                if os.path.exists(signature_img_path):
                    signature_msg.append(
                        MessageSegment.image(f"file:///{signature_img_path}")
                    )

                signature_name_text = await select_text_by_priority(
                    signature_info["name"]["zh_tw"],
                    signature_info["name"]["zh_cn"],
                    signature_info["name"]["kr"],
                    signature_info["name"].get("ja", ""),
                    server,
                    data_type,
                )
                signature_desc_text = await select_text_by_priority(
                    signature_info["description"]["zh_tw"],
                    signature_info["description"]["zh_cn"],
                    signature_info["description"]["kr"],
                    signature_info["description"].get("ja", ""),
                    server,
                    data_type,
                )
                signature_title_text = await select_text_by_priority(
                    signature_info["title"]["zh_tw"],
                    signature_info["title"]["zh_cn"],
                    signature_info["title"]["kr"],
                    signature_info["title"].get("ja", ""),
                    server,
                    data_type,
                )

                # 生成文字描述
                skill_descriptions_text = []
                for i, skill in enumerate(signature_info["skills"]):
                    desc_text = await select_text_by_priority(
                        skill["desc_zh_tw"],
                        skill["desc_zh_cn"],
                        skill["desc_kr"],
                        skill.get("desc_ja", ""),
                        server,
                        data_type,
                    )
                    desc_text = await clean_rich_text(desc_text)
                    unlock_grade = skill.get("unlock_grade", "")
                    unlock_text = f"（等级{unlock_grade}解锁）" if unlock_grade else ""

                    skill_descriptions_text.append(f"\n{desc_text}{unlock_text}")

                signature_info_text = f"""{signature_name_text}
{signature_desc_text}
战力百分比：{max_level_battle_power_per}
{max_level}级属性：
{chr(10).join(signature_stats)}
遗物技能【{signature_title_text}】：
""" + "\n".join(
                    skill_descriptions_text
                )
                signature_msg.append(signature_info_text)

            messages.append(signature_msg)

        await send_forward_messages(bot, event, messages)

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
