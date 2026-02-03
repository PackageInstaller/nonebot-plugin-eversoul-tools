from ..library.utils import *


@es_cash_pack.handle()
async def handle(bot: Bot, event: Event, args: Message = CommandArg()):
    try:
        group_id = get_group_id(event)
        config = await get_group_data_source(group_id)
        server = config.get("server", "global")

        if server == "cn":
            await es_cash_pack.finish("国服暂不支持突发礼包信息查询")
        args_text = args.extract_plain_text().strip()

        match_main = re.match(r"^主线(\d+)$", args_text)
        match_gate = re.match(r"^(自由|人类|野兽|妖精|不死)传送门$", args_text)

        if match_main:
            item_type = "主线"
            chapter = match_main.group(1)
        elif match_gate:
            item_type = "传送门"
            gate_type = match_gate.group(1)
        else:
            if args_text == "主线":
                await es_cash_pack.finish(
                    "请带上主线章节参数！例如：es突发礼包信息主线21"
                )
            elif args_text == "传送门":
                await es_cash_pack.finish(
                    "请带上传送门类型参数！例如：es突发礼包信息自由传送门"
                )
            item_type = args_text
            chapter = None
            gate_type = ""

        group_id = 0
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
        data = await load_json_data(group_id)
        messages = []

        if item_type == "主线":
            for stage in data["stage"]["json"]:
                if "area_no" in stage:  # 确认是主线关卡
                    area_no = stage.get("area_no")
                    # 如果指定了章节，只处理对应章节的关卡
                    if chapter and str(area_no) != chapter:
                        continue

                    stage_no = stage.get("stage_no")
                    stage_no_id = stage.get("no")
                    if stage_no_id:
                        stage_info = {"no": stage_no_id}
                        package_msgs = await get_cash_pack(data, "stage", stage_info)
                        if package_msgs:
                            messages.append(f"主线关卡 {area_no}-{stage_no}:")
                            messages.extend(package_msgs)

            if not messages:
                chapter_text = f"第{chapter}章" if chapter else "所有章节"
                await es_cash_pack.finish(f"当前{chapter_text}没有主线相关的突发礼包")

        elif item_type == "传送门":
            stage_type = GATE_TYPE_MAPPING.get(gate_type)
            if not stage_type:
                await es_cash_pack.finish(f"未知的传送门类型：{gate_type}")

            # 从Barrier.json获取传送门基本信息
            barrier_info = None
            for barrier in data["barrier"]["json"]:
                if barrier.get("stage_type") == stage_type:
                    barrier_info = barrier
                    break

            if barrier_info:
                gate_name = next(
                    (
                        s.get("zh_tw", "未知")
                        for s in data["string_stage"]["json"]
                        if s["no"] == barrier_info.get("text_name_sno")
                    ),
                    "未知",
                )
                messages.append(f"{gate_name}:")
                for stage in data["stage"]["json"]:
                    if stage.get("stage_type") == stage_type:
                        stage_no = stage.get("stage_no")
                        name_sno = stage.get("name_sno")
                        stage_name = ""
                        for string in data["string_stage"]["json"]:
                            if string["no"] == name_sno:
                                stage_name = string.get("zh_tw", "未知")
                                stage_name = stage_name.format(stage_no)
                                break
                        package_msgs = await get_cash_pack(data, "barrier", stage)
                        if package_msgs:
                            messages.append(f"{stage_name}:")
                            messages.extend(package_msgs)

            if len(messages) <= 1:
                await es_cash_pack.finish(f"当前没有{gate_type}型传送门相关的突发礼包")

        elif item_type == "起源塔":  # 起源塔
            for tower in data["tower"]["json"]:
                hero_id = tower.get("req_hero")
                tower_no = tower.get("no")
                hero_name = ""
                for hero in data["hero"]["json"]:
                    if hero["hero_id"] == hero_id:
                        for char in data["string_character"]["json"]:
                            if char["no"] == hero["name_sno"]:
                                hero_name = char.get("zh_tw", "")
                                break
                        break

                tower_name = f"{hero_name}的起源之塔"
                tower_packages = []
                for shop_item in data["cash_shop_item"]["json"]:
                    if shop_item.get("type") == "tower":
                        type_values = shop_item.get("type_value", "").split(",")
                        type_values = [v.strip() for v in type_values]
                        if str(tower_no) in type_values:
                            tower_packages.append(shop_item)

                if tower_packages:
                    messages.append(f"{tower_name}:")
                    for package in tower_packages:
                        dummy_info = {"no": tower_no}
                        original_type_value = package["type_value"]
                        package["type_value"] = str(tower_no)
                        package_msgs = await get_cash_pack(data, "tower", dummy_info)
                        package["type_value"] = original_type_value
                        messages.extend(package_msgs)

        elif item_type == "升阶":
            for shop_item in data["cash_shop_item"]["json"]:
                if shop_item.get("type") == "grade_eternal":
                    dummy_info = {"no": shop_item.get("type_value")}
                    package_msgs = await get_cash_pack(
                        data, "grade_eternal", dummy_info
                    )
                    if package_msgs:
                        messages.extend(package_msgs)

        else:
            await es_cash_pack.finish(
                "请输入正确的类型：主线/传送门/起源塔/升阶"
            ) 

        if not messages:
            await es_cash_pack.finish(
                f"当前没有{item_type}相关的突发礼包"
            )

        # 发送合并转发消息（合并成一条）
        await send_forward_messages(bot, event, ["\n".join(messages)])

    except Exception as e:
        if not isinstance(e, FinishedException):
            import traceback

            error_location = traceback.extract_tb(e.__traceback__)[-1]
            logger.error(
                f"处理突发礼包信息时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )
