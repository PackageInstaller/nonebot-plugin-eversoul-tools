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

        # 是否为测试模式
        review = config["type"] == "review"
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

        skill_types = []
        skill_keys = [
            "skill_no_1",
            "skill_no_2",
            "skill_no_3",
            "skill_no_4",
            "ultimate_skill_no",
            "support_skill_no",
        ]

        # 技能释放顺序
        skill_pattern = await get_character_skill_pattern(data, hero_id, review)
        if skill_pattern:
            pattern_text = ["▼ 技能释放顺序"]
            for i, (skill_name, skill_type) in enumerate(skill_pattern, 1):
                pattern_text.append(f"{i}. 【{skill_type}】{skill_name} ")
            messages.append("\n".join(pattern_text))

        # 先检查角色有哪些技能
        for skill_key in skill_keys:
            if skill_no := hero_data.get(skill_key):
                for skill in data["skill"]["json"]:
                    if skill["no"] == skill_no:
                        skill_type_data = await get_string_by_type(
                            data, "system", skill["type"]
                        )
                        skill_type_zh_tw = skill_type_data["zh_tw"]
                        skill_type_zh_cn = skill_type_data["zh_cn"]
                        skill_type_kr = skill_type_data["kr"]
                        skill_type_en = skill_type_data["en"]
                        # 判断是否为支援技能
                        support = skill_key == "support_skill_no"
                        # 获取技能信息（根据标志决定是否生成图片）
                        skill_info = await get_character_skill(
                            data, skill_no, support, generate_image=generate_image_flag
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
                        break

        for (
            skill_type_zh_tw,
            skill_type_zh_cn,
            skill_type_kr,
            skill_type_en,
            skill_info,
        ) in skill_types:
            skill_text = []

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
                skill_type_zh_tw, skill_type_zh_cn, skill_type_kr, review
            )
            skill_name_text = await select_text_by_priority(
                skill_info["name"]["zh_tw"],
                skill_info["name"]["zh_cn"],
                skill_info["name"]["kr"],
                review,
            )

            # 添加文字描述（清理颜色代码）
            if skill_info["support"]:
                main_effects = []
                for desc in skill_info["descriptions"]:
                    if desc.get("type") == "support":
                        desc_text = await select_text_by_priority(
                            desc["desc_zh_tw"],
                            desc["desc_zh_cn"],
                            desc["desc_kr"],
                            review,
                        )
                        # 清理颜色代码
                        desc_text = await clean_rich_text(desc_text)
                        main_effects.append(desc_text)

                if main_effects:
                    skill_text.append(f"【{skill_type_text}】{skill_name_text}")
                    skill_text.extend(main_effects)
            else:
                skill_text.append(f"【{skill_type_text}】{skill_name_text}")
                for i, desc in enumerate(skill_info["descriptions"]):
                    desc_text = await select_text_by_priority(
                        desc["desc_zh_tw"], desc["desc_zh_cn"], desc["desc_kr"], review
                    )
                    # 清理颜色代码
                    desc_text = await clean_rich_text(desc_text)
                    hero_level = desc.get("hero_level", 1)
                    unlock_text = f"（等级{hero_level}解锁）" if hero_level >= 1 else ""
                    skill_text.append(f"\n等级{i+1}：{desc_text}{unlock_text}\n")

            # 如果有生成的图片，添加到最后
            if skill_info.get("image_bytes"):
                skill_text.append(MessageSegment.image(skill_info["image_bytes"]))

            messages.append(skill_text)

        signature_info = await get_character_signature(
            data, hero_id, generate_image=generate_image_flag
        )
        if signature_info["name"]["kr"] or signature_info["name"]["zh_cn"]:
            signature_stats = signature_info["stats"]
            max_level = signature_info["max_level"]
            max_level_battle_power_per = signature_info["max_level_battle_power_per"]
            signature_bg_path = signature_info["bg_path"]
            signature_img_path = str(SOUL_DIR / signature_bg_path)

            signature_msg = []
            signature_msg.append(f"【遺物信息】")
            if os.path.exists(signature_img_path):
                signature_msg.append(
                    MessageSegment.image(f"file:///{signature_img_path}")
                )

            signature_name_text = await select_text_by_priority(
                signature_info["name"]["zh_tw"],
                signature_info["name"]["zh_cn"],
                signature_info["name"]["kr"],
                review,
            )
            signature_desc_text = await select_text_by_priority(
                signature_info["description"]["zh_tw"],
                signature_info["description"]["zh_cn"],
                signature_info["description"]["kr"],
                review,
            )
            signature_title_text = await select_text_by_priority(
                signature_info["title"]["zh_tw"],
                signature_info["title"]["zh_cn"],
                signature_info["title"]["kr"],
                review,
            )

            # 生成文字描述（清理颜色代码）
            skill_descriptions_text = []
            for i, skill in enumerate(signature_info["skills"]):
                desc_text = await select_text_by_priority(
                    skill["desc_zh_tw"], skill["desc_zh_cn"], skill["desc_kr"], review
                )
                # 清理颜色代码
                desc_text = await clean_rich_text(desc_text)
                skill_descriptions_text.append(f"\n等級{i+1}：{desc_text}")

            signature_info_text = f"""{signature_name_text}
{signature_desc_text}
战力百分比：{max_level_battle_power_per}
{max_level}級屬性：
{chr(10).join(signature_stats)}
遺物技能【{signature_title_text}】：
""" + "\n".join(
                skill_descriptions_text
            )
            signature_msg.append(signature_info_text)

            # 如果有生成的遗物技能图片，添加到最后
            if signature_info.get("image_bytes"):
                signature_msg.append(
                    MessageSegment.image(signature_info["image_bytes"])
                )

            messages.append(signature_msg)

        forward_msgs = []
        for msg in messages:
            if isinstance(msg, str):
                forward_msgs.append(
                    {
                        "type": "node",
                        "data": {
                            "name": "Eversoul Info",
                            "uin": bot.self_id,
                            "content": msg,
                        },
                    }
                )
            elif isinstance(msg, list):
                # 处理包含MessageSegment的列表
                content_parts = []
                for item in msg:
                    if isinstance(item, MessageSegment):
                        content_parts.append(item)
                    else:
                        content_parts.append(str(item))

                forward_msgs.append(
                    {
                        "type": "node",
                        "data": {
                            "name": "Eversoul Info",
                            "uin": bot.self_id,
                            "content": Message(content_parts),
                        },
                    }
                )
            elif isinstance(msg, MessageSegment):
                forward_msgs.append(
                    {
                        "type": "node",
                        "data": {
                            "name": "Eversoul Info",
                            "uin": bot.self_id,
                            "content": Message([msg]),
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
                f"处理角色信息时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )
