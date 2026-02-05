from ..library.utils import *


@es_single_raid.handle()
async def handle(bot: Bot, event: Event, args: Message = CommandArg()):
    try:
        # 获取输入参数
        input_text = args.extract_plain_text().strip()
        if not input_text:
            await es_single_raid.finish("请输入恶灵名称！\n示例：es恶灵信息 艾拉")

        group_id = get_group_id(event)
        # 先从角色别名(hero aliases)中查找，如果找到则用kr名去恶灵别名中查找
        hero_alias_map = await load_aliases(group_id)
        raid_alias_map, raid_aliases_data = await load_raid_aliases(group_id)

        # 获取角色别名配置的原始数据（用于获取kr_name）
        config = await get_group_data_source(group_id)
        hero_alias_file = config["hero_alias_file"]
        hero_aliases_data = {"names": []}
        if hero_alias_file.exists():
            with open(hero_alias_file, "r", encoding="utf-8") as f:
                hero_aliases_data = yaml.safe_load(f) or {"names": []}

        hero_ids = None
        # 步骤1：先在角色别名中查找
        matched_hero_id = hero_alias_map.get(input_text)
        if not matched_hero_id and input_text.isascii():
            matched_hero_id = hero_alias_map.get(input_text.lower())

        if matched_hero_id:
            # 找到角色，获取其kr_name
            kr_name = None
            for hero in hero_aliases_data.get("names", []):
                if hero.get("hero_id") == matched_hero_id:
                    kr_name = hero.get("kr_name")
                    break

            if kr_name:
                # 用kr_name在恶灵别名中查找
                hero_ids = raid_alias_map.get(kr_name)
                if hero_ids:
                    search_name = kr_name  # 更新搜索名称
                    logger.info(
                        f"通过角色「{input_text}」的韩文名「{kr_name}」找到恶灵"
                    )

        # 步骤2：如果角色别名中没找到，直接在恶灵别名中查找
        if not hero_ids:
            hero_ids = raid_alias_map.get(input_text)
            if not hero_ids and input_text.isascii():
                hero_ids = raid_alias_map.get(input_text.lower())

        # 步骤3：如果都没找到，尝试模糊匹配
        if not hero_ids:
            # 合并两个别名表的所有名称用于模糊匹配
            all_names = list(
                set(list(hero_alias_map.keys()) + list(raid_alias_map.keys()))
            )
            if input_text.isascii():
                matches = get_close_matches(
                    input_text.lower(),
                    [n.lower() if n.isascii() else n for n in all_names],
                    n=3,
                    cutoff=0.6,
                )
            else:
                matches = get_close_matches(input_text, all_names, n=3, cutoff=0.6)

            if matches:
                await es_single_raid.finish(
                    f"未找到恶灵「{input_text}」\n您是否想查询：{', '.join(matches)}"
                )
            else:
                await es_single_raid.finish(f"未找到恶灵「{input_text}」")

        # 加载数据
        data = await load_json_data(group_id, command_name="es恶灵讨伐信息")
        server = config.get("server", "global")

        # 在所有匹配的hero_id中，找到single_raid_boss中boss_max_level最大的
        best_boss = None
        best_hero_id = None
        max_level = 0

        for hid in hero_ids:
            for boss in data["single_raid_boss"]["json"]:
                if (
                    boss.get("boss_no") == hid
                    and boss.get("boss_max_level", 0) > max_level
                ):
                    max_level = boss.get("boss_max_level", 0)
                    best_boss = boss
                    best_hero_id = hid

        if not best_boss:
            await es_single_raid.finish(f"未找到恶灵「{input_text}」的讨伐信息")

        # 获取level_group
        level_group = best_boss.get("level_group")

        # 在single_raid中找到对应的raid
        raid_data = None
        for raid in data["single_raid"]["json"]:
            if raid.get("level_group") == level_group:
                raid_data = raid
                break

        if not raid_data:
            await es_single_raid.finish(f"未找到恶灵「{input_text}」的讨伐配置")

        raid_no = raid_data.get("no")

        # 在single_raid_schedule中查找所有匹配的赛季
        # 只查找 server_check == 4 的记录（国际服通用）
        schedules = []
        for schedule in data["single_raid_schedule"]["json"]:
            if schedule.get("raid_no") == raid_no and schedule.get("server_check") == 4:
                schedules.append(schedule)

        if not schedules:
            # 没有赛季信息，直接显示
            await _show_raid_info(bot, event, group_id, best_hero_id, None)
            return

        if len(schedules) == 1:
            # 只有一个赛季，直接显示
            await _show_raid_info(
                bot, event, group_id, best_hero_id, schedules[0].get("season_no")
            )
            return

    except Exception as e:
        if not isinstance(e, FinishedException):
            import traceback

            error_location = traceback.extract_tb(e.__traceback__)[-1]
            logger.error(
                f"处理恶灵讨伐信息时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )


async def _show_raid_info(
    bot: Bot, event: Event, group_id, hero_id: int, season_no: int = None
):
    """显示恶灵讨伐详细信息"""
    # 加载数据
    data = await load_json_data(group_id, command_name="es恶灵讨伐信息")
    config = await get_group_data_source(group_id)
    server = config.get("server", "global")

    # 查找角色数据
    hero_data = None
    for hero in data["hero"]["json"]:
        if hero["hero_id"] == hero_id:
            hero_data = hero
            break

    if not hero_data:
        await es_single_raid.finish(f"未找到ID为{hero_id}的恶灵信息")

    # 查找SingleRaidBoss数据，获取boss_max_level最大的那个
    boss_data = None
    max_level = 0
    for boss in data["single_raid_boss"]["json"]:
        if boss.get("boss_no") == hero_id and boss.get("boss_max_level", 0) > max_level:
            max_level = boss.get("boss_max_level", 0)
            boss_data = boss

    if not boss_data:
        await es_single_raid.finish(f"未找到ID为{hero_id}的恶灵讨伐信息")

    level_group = boss_data.get("level_group")
    raid_data = None
    for raid in data["single_raid"]["json"]:
        if raid.get("level_group") == level_group:
            raid_data = raid
            break

    # 基础属性
    name_zh_tw = (await get_string_character(data, hero_data["name_sno"])).get(
        "zh_tw", ""
    )
    race_zh_tw = (await get_string_by_type(data, "system", hero_data["race_sno"])).get(
        "zh_tw", ""
    )
    hero_class_zh_tw = (
        await get_string_by_type(data, "system", hero_data["class_sno"])
    ).get("zh_tw", "")
    sub_class_zh_tw = (
        await get_string_by_type(data, "system", hero_data["sub_class_sno"])
    ).get("zh_tw", "")
    stat_zh_tw = (await get_string_by_type(data, "system", hero_data["stat_sno"])).get(
        "zh_tw", ""
    )

    # 战斗时长
    battle_time = 0
    if raid_data and raid_data.get("stage_no"):
        for stage in data["stage"]["json"]:
            if stage.get("no") == raid_data.get("stage_no"):
                battle_time = stage.get("battle_time", 0)
                break

    # 讨伐攻略
    guide_text = ""
    if raid_data and raid_data.get("guide_sno"):
        guide_data = await get_string_by_type(data, "ui", raid_data.get("guide_sno"))
        guide_text = guide_data.get("zh_tw", "")

    # 血量倍数
    hp_multiplier = 1.0
    for level_grade in data["single_raid_boss_level_grade"]["json"]:
        if level_grade.get("level") == boss_data.get("boss_max_level"):
            hp_multiplier = level_grade.get("value", 1.0)
            break

    # 最终血量
    final_hp = int(
        hero_data.get("max_hp", 0) * hp_multiplier * boss_data.get("boss_max_level", 0)
    )

    # 奖励信息
    reward_items = []
    if boss_data.get("reward_item1_no"):
        item_name = await get_string_item(data, boss_data.get("reward_item1_no"))
        item_amount = boss_data.get("reward_item1_amount", 0)
        reward_items.append(f"{item_name['zh_tw']}x{item_amount}")

    if boss_data.get("reward_item2_no"):
        item_name = await get_string_item(data, boss_data.get("reward_item2_no"))
        item_amount = boss_data.get("reward_item2_amount", 0)
        reward_items.append(f"{item_name['zh_tw']}x{item_amount}")

    # 获取赛季信息
    season_info = ""
    if season_no:
        # 使用指定的赛季
        for season in data["single_raid_season"]["json"]:
            if season.get("no") == season_no:
                season_name = await get_string_by_type(
                    data, "ui", season.get("season_name_no")
                )
                season_info = f"赛季：{season_name.get('zh_tw', '')}"
                break
    elif raid_data and raid_data.get("no"):
        # 查找最新的赛季信息
        latest_schedule = None
        for schedule in data["single_raid_schedule"]["json"]:
            if schedule.get("raid_no") == raid_data.get("no"):
                if not latest_schedule or schedule.get(
                    "season_no", 0
                ) > latest_schedule.get("season_no", 0):
                    latest_schedule = schedule

        if latest_schedule:
            for season in data["single_raid_season"]["json"]:
                if season.get("no") == latest_schedule.get("season_no"):
                    season_name = await get_string_by_type(
                        data, "ui", season.get("season_name_no")
                    )
                    season_info = f"赛季：{season_name.get('zh_tw', '')}"
                    break

    # 获取相互作用之人信息
    interaction_info = []
    special_heroes = {}
    delay_text = None
    delay_seconds = None
    if raid_data and raid_data.get("level_group"):
        for interaction in data["single_raid_boss_interaction_detail"]["json"]:
            if interaction.get("interaction_no") == raid_data.get("level_group"):
                hero_name = await get_string_character(
                    data, interaction.get("hero_no"), special=True
                )
                if hero_name:
                    interaction_info.append(hero_name["zh_tw"])

        if raid_data.get("no"):
            buff_lookup = {
                buff["no"]: buff for buff in data["battle_buff"]["json"] if "no" in buff
            }
            for gimmick in data["single_raid_season_gimmick"]["json"]:
                if gimmick.get("raid_no") == raid_data.get("no"):
                    i = 1
                    while (
                        f"gimmick_type_{i}" in gimmick
                        and f"gimmick_value_{i}" in gimmick
                    ):
                        gimmick_value = gimmick.get(f"gimmick_value_{i}")
                        buff = buff_lookup.get(gimmick_value)

                        if buff:
                            specific_target = buff.get("specific_target")
                            if (
                                specific_target
                                and specific_target not in special_heroes
                            ):
                                hero_name_data = await get_string_character(
                                    data, specific_target, special=True
                                )
                                if hero_name_data and "zh_tw" in hero_name_data:
                                    special_heroes[specific_target] = hero_name_data[
                                        "zh_tw"
                                    ]

                            if not delay_text and buff.get("delay"):
                                delay_seconds = buff.get("delay")
                                delay_text = (
                                    await get_string_by_type(
                                        data, "ui", buff.get("buff_tooltip_sno")
                                    )
                                ).get("zh_tw", "")

                        i += 1

    # 获取护盾削减系数和解除眩晕时间
    groggy_info = []
    recovery_duration = 0
    condition_group_id = None
    if boss_data and boss_data.get("no"):
        if server == "cn":
            for groggy in data["single_raid_boss_groggy_trigger"]["json"]:
                if groggy.get("single_raid_boss_no") == boss_data.get("no"):
                    recovery_duration = groggy.get("recovery_duration", 0)
                    for (
                        buff_type,
                        status_name,
                    ) in SINGLE_RAID_GROGGY_TYPE_MAPPING.items():
                        if (buff_type - 201) & 0xFFFFFFFF <= 6 and (
                            ((0x63 >> ((buff_type + 55) % 32)) & 1) != 0
                        ):
                            groggy_info.append(
                                f"{status_name}类技能：{await format_value(groggy.get(f'value_{SINGLE_RAID_GROGGY_REDUCE_MAPPING[buff_type - 201]}'), True)}"
                            )
        else:
            for groggy_trigger in data["single_raid_boss_groggy_trigger"]["json"]:
                if groggy_trigger.get("single_raid_boss_no") == boss_data.get("no"):
                    condition_group_id = groggy_trigger.get("condition_group")
                    recovery_duration = groggy_trigger.get("recovery_duration", 0)
                    break
            if condition_group_id:
                for condition in data["single_raid_boss_groggy_condition"]["json"]:
                    if condition.get("condition_group") == condition_group_id:
                        buff_type = condition.get("condition_buff")
                        value = condition.get("value", 0)
                        status_name = SINGLE_RAID_GROGGY_TYPE_MAPPING.get(buff_type)

                        if status_name and value != 0:
                            groggy_info.append(
                                f"{status_name}类技能：{await format_value(value, True)}"
                            )

    messages = []
    basic_info = []

    portrait_paths = await get_character_portrait(data, hero_id)
    basic_info.append(f"【恶灵讨伐：{name_zh_tw}】")
    if portrait_paths:
        basic_info.append(MessageSegment.image(f"file:///{portrait_paths[0]}"))

    basic_info_text = f"""类型：{race_zh_tw} {hero_class_zh_tw}
攻击方式：{sub_class_zh_tw}
属性：{stat_zh_tw}
等级：{boss_data.get('boss_max_level', 0)}
护盾量：{await format_value(boss_data.get('groggy_ratio', 0), True)}
生命值：{final_hp}
战斗时长：{battle_time}秒
{season_info if season_info else ""}
击杀奖励：
{chr(10).join(f"- {item}" for item in reward_items)}"""

    if interaction_info:
        basic_info_text += f"\n\n有开场台词的角色：\n{chr(10).join(f'- {name}' for name in interaction_info)}"

    if special_heroes:
        basic_info_text += f"\n\n羁绊角色：\n{chr(10).join(f'- {name}' for name in special_heroes.values())}"

    if delay_text:
        basic_info_text += f"\n\n特殊情况：开场{delay_seconds}秒后{delay_text}"

    if groggy_info:
        basic_info_text += (
            f"\n\n护盾削减系数：\n{chr(10).join(f'- {info}' for info in groggy_info)}"
        )
        if recovery_duration > 0:
            basic_info_text += f"\n解除眩晕时间：{recovery_duration}秒"

    basic_info.append(basic_info_text)

    if guide_text:
        basic_info.append(f"\n【讨伐攻略】\n{await clean_rich_text(guide_text)}")

    messages.append("\n".join(str(x) for x in basic_info))

    await send_forward_messages(bot, event, messages)
