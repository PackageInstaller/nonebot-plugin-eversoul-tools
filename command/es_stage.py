from ..library.utils import *


@es_stage.handle()
async def handle(bot: Bot, event: Event, args: Message = CommandArg()):
    try:
        # 获取参数文本
        stage_text = args.extract_plain_text().strip()
        # 获取群组ID
        group_id = 0
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
        # 检查格式
        match = re.match(r"^(\d+)-(\d+)$", stage_text)
        if not match:
            await es_stage.finish("请输入正确的关卡编号！")

        area_no = int(match.group(1))
        stage_no = int(match.group(2))

        # 加载数据
        data = await load_json_data(group_id)

        # 查找关卡信息
        main_stage = None

        for stage in data["stage"]["json"]:
            if stage.get("area_no") == area_no and stage.get("stage_no") == stage_no:
                if "area_no" in stage:
                    main_stage = stage
                    drop_group_no = stage.get("item_drop_group_no")
                    break  # 找到主线关卡就直接跳出

        if not main_stage:
            await es_stage.finish(f"未找到关卡 {area_no}-{stage_no} 的信息")

        stage_data = main_stage

        messages = []
        basic_info = []
        basic_info.append(f"关卡 {area_no}-{stage_no} 信息：")

        # 获取关卡类型
        level_type = ""
        for system in data["string_system"]["json"]:
            if system["no"] == stage_data.get("level_type"):
                level_type = system.get("zh_tw", "未知类型")
                break
        basic_info.append(f"关卡类型：{level_type}")
        basic_info.append(f"经验值：{stage_data.get('exp', 0)}")
        messages.append("\n".join(basic_info))

        fixed_items = ["固定掉落物品："]
        for i in range(1, 10):
            item_key = f"item_no_{i}"
            amount_key = f"amount_{i}"
            if item_no := stage_data.get(item_key):
                item_name = await get_string_item(data, item_no)
                amount = stage_data.get(amount_key, 0)
                fixed_items.append(f"{item_name['zh_tw']}x{amount}")

        if len(fixed_items) > 1:
            messages.append("\n".join(fixed_items))

        # 获取关卡编号
        stage_no = stage_data["no"]

        # 获取主线突发礼包信息
        cash_item_messages = await get_cash_pack(data, "stage", stage_data)
        messages.extend(cash_item_messages)

        # 查找敌方队伍信息
        battle_teams = []
        for battle in data["stage_battle"]["json"]:
            if battle["no"] == stage_no:
                battle_teams.append(battle)

        # 如果有敌方队伍信息，添加到消息中
        if battle_teams:
            # 按team_no排序
            battle_teams.sort(key=lambda x: x.get("team_no", 0))

            for team in battle_teams:
                team_info = [f"敌方队伍 {team.get('team_no', '?')}："]
                team_info.append(
                    f"阵型：{await get_formation_type(team.get('formation_type'))}"
                )
                hero_positions = []
                first_valid_hero = None

                for i in range(1, 6):
                    hero_key = f"hero_no_{i}"
                    grade_key = f"hero_grade_{i}"
                    level_key = f"level_{i}"

                    if hero_no := team.get(hero_key):
                        hero_positions.append(i)

                        if first_valid_hero is None:
                            first_valid_hero = {
                                "position": i,
                                "hero_no": hero_no,
                                "grade": team.get(grade_key),
                                "level": team.get(level_key, 0),
                            }

                        hero_name_data = await get_string_character(
                            data, hero_no, special=True
                        )
                        hero_name_zh_tw = hero_name_data["zh_tw"]

                        grade_data = await get_string_by_type(
                            data, "system", team.get(grade_key)
                        )
                        grade_name_zh_tw = grade_data["zh_tw"]

                        level = team.get(level_key, 0)

                        team_info.append(
                            f"位置{i}：{hero_name_zh_tw} {grade_name_zh_tw} {level}级"
                        )

                if (
                    first_valid_hero
                    and first_valid_hero["grade"]
                    and first_valid_hero["level"]
                ):
                    level = first_valid_hero["level"]
                    grade = first_valid_hero["grade"]
                    team_battle_power = (
                        await calculate_battle_power(data, 2, level, grade)
                    ) * len(hero_positions)
                    team_info.append(f"队伍战力：{team_battle_power}")

                messages.append("\n".join(team_info))

        # 获取掉落率信息
        drop_items = await get_drop_item_rate(data, drop_group_no)
        if drop_items:
            drop_info = [f"掉落物品概率如下：\n"]
            for item_name, amount, rate in drop_items:
                drop_info.append(f"{item_name["zh_tw"]} ({rate:.3f}%)")
            messages.append("\n".join(drop_info))

        # 发送合并转发消息
        await send_forward_messages(bot, event, messages, name="Stage Info")

    except Exception as e:
        if not isinstance(e, FinishedException):
            import traceback

            error_location = traceback.extract_tb(e.__traceback__)[-1]
            logger.error(
                f"处理关卡信息时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )
