from ..library.utils import *


@es_ark_level.handle()
async def handle(bot: Bot, event: Event, args: Message = CommandArg()):
    try:
        level_params = args.extract_plain_text().strip()
        if not level_params:
            await es_ark_level.finish(
                "请输入正确的格式：es方舟等级信息+等级\n可输入1-7个等级，分别对应：主方舟 战士 游侠 斗士 魔法师 辅助 捍卫者\n例如：es方舟等级信息500 或 es方舟等级信息500 450 400 350 300 250 200"
            )
        level_list = level_params.split()
        try:
            levels = [int(l) for l in level_list]
        except ValueError:
            await es_ark_level.finish("等级必须是数字！")

        if len(levels) > 7:
            await es_ark_level.finish("最多只能输入7个等级参数！")

        # 如果只有一个参数，所有类型都使用这个等级
        if len(levels) == 1:
            levels = levels * 7
        # 如果参数不足7个，用第一个参数补齐
        elif len(levels) < 7:
            levels.extend([levels[0]] * (7 - len(levels)))

        group_id = get_group_id(event)
        data = await load_json_data(group_id)

        ark_types = {
            110051: {"level": levels[0], "arks": []},  # 主方舟
            110101: {"level": levels[1], "arks": []},  # 战士
            110102: {"level": levels[2], "arks": []},  # 游侠
            110103: {"level": levels[3], "arks": []},  # 斗士
            110104: {"level": levels[4], "arks": []},  # 魔法师
            110105: {"level": levels[5], "arks": []},  # 辅助
            110106: {"level": levels[6], "arks": []},  # 捍卫者
        }
        for ark in data["ark_enhance"]["json"]:
            core_type = ark.get("core_type_02")
            if core_type in ark_types:
                target_level = ark_types[core_type]["level"]
                if ark.get("core_level") == target_level:
                    ark_types[core_type]["arks"].append(ark)

        messages = []
        title_parts = []
        for idx, (core_type, info) in enumerate(ark_types.items()):
            type_name = (await get_string_by_type(data, "system", core_type)).get(
                "zh_tw", ""
            )
            if type_name == "所有":
                type_name = "主要"
            title_parts.append(f"{type_name}Lv.{info['level']}")
        title_msg = f"方舟等级信息：\n{'\n'.join(title_parts)}"
        messages.append(title_msg)

        # 每种类型的方舟
        for core_type, info in ark_types.items():
            arks = info["arks"]
            target_level = info["level"]
            if not arks:
                continue

            # 方舟类型名称
            type_name = (await get_string_by_type(data, "system", core_type)).get(
                "zh_tw", ""
            )

            # 主方舟名称适配
            if type_name == "所有":
                type_name = "主要"
            ark_msg = []
            ark_msg.append(f"【{type_name} Lv.{target_level}】")

            # 计算该类型方舟从1级到目标等级的累计消耗
            type_total_cost = {}
            for ark in data["ark_enhance"]["json"]:
                if (
                    ark.get("core_type_02") == core_type
                    and ark.get("core_level", 0) <= target_level
                ):
                    # 获取材料名称
                    item_name = None
                    for item in data["item"]["json"]:
                        if item["no"] == ark.get("pay_item_no"):
                            item_name = (
                                await get_string_by_type(
                                    data, "item", item.get("name_sno")
                                )
                            ).get("zh_tw", "")
                            break

                    if item_name:
                        pay_amount = ark.get("pay_amount", 0)
                        type_total_cost[item_name] = (
                            type_total_cost.get(item_name, 0) + pay_amount
                        )

            # 累计消耗
            if type_total_cost:
                ark_msg.append(f"总消耗：")
                for item_name, amount in type_total_cost.items():
                    ark_msg.append(f"{item_name}：{amount}")
            for ark in arks:
                # 升级材料信息
                item_name = "未知材料"
                for item in data["item"]["json"]:
                    if item["no"] == ark.get("pay_item_no"):
                        item_name = (
                            await get_string_by_type(data, "item", item.get("name_sno"))
                        ).get("zh_tw", "")
                        break

                pay_amount = ark.get("pay_amount", 0)
                ark_msg.append(f"升级消耗：{item_name}x{pay_amount}")

                # 基础属性加成
                if buff_no := ark.get("contents_buff_no"):
                    found_buff = False
                    for buff in data["contents_buff"]["json"]:
                        if buff.get("no") == buff_no:
                            found_buff = True
                            ark_msg.append("基础属性加成：")
                            if buff.get("battle_power"):
                                ark_msg.append(
                                    f"・ 战斗力加成：{buff.get('battle_power')}"
                                )
                            if buff.get("battle_power_per"):
                                ark_msg.append(
                                    f"・ 每级战斗力加成：{buff.get('battle_power_per')}"
                                )
                            for key, value in buff.items():
                                if key in STAT_NAME_MAPPING and value != 0:
                                    if key.endswith("_rate"):
                                        ark_msg.append(
                                            f"・ {STAT_NAME_MAPPING[key]}：{await format_value(value, False)}"
                                        )
                                    else:
                                        ark_msg.append(
                                            f"・ {STAT_NAME_MAPPING[key]}：{await format_value(value, True)}"
                                        )
                    if not found_buff:
                        ark_msg.append("基础属性加成：数据未找到")

                # 特殊属性加成
                if sp_buff_value := ark.get("sp_buff_value02"):
                    found_buff = False
                    for buff in data["contents_buff"]["json"]:
                        if buff.get("no") == int(sp_buff_value):
                            found_buff = True
                            ark_msg.append("特殊属性加成：")
                            if buff.get("battle_power"):
                                ark_msg.append(
                                    f"・ 战斗力加成：{buff.get('battle_power')}"
                                )
                            if buff.get("battle_power_per"):
                                ark_msg.append(
                                    f"・ 每级战斗力加成：{buff.get('battle_power_per')}"
                                )
                            for key, value in buff.items():
                                if key in STAT_NAME_MAPPING and value != 0:
                                    ark_msg.append(
                                        f"・ {STAT_NAME_MAPPING[key]}：{await format_value(value, True)}"
                                    )
                    if not found_buff:
                        ark_msg.append("特殊属性加成：数据未找到")

            messages.append("\n".join(ark_msg))

        # 发送合并转发消息
        await send_forward_messages(bot, event, messages)

    except Exception as e:
        if not isinstance(e, FinishedException):
            import traceback

            error_location = traceback.extract_tb(e.__traceback__)[-1]
            logger.error(
                f"处理方舟等级信息时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )
