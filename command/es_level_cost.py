from ..library.utils import *


@es_level_cost.handle()
async def handle(bot: Bot, event: Event, args: Message = CommandArg()):
    try:
        # 获取目标等级
        target_level = args.extract_plain_text().strip()
        if not target_level:
            await es_level_cost.finish("请输入正确的格式：es升级消耗+等级")
        target_level = int(target_level)

        # 加载数据
        # 获取群组ID
        group_id = 0
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
        data = await load_json_data(group_id)

        # 找出最大等级
        max_level = 0
        for item in data["level"]["json"]:
            if level := item.get("level"):
                max_level = max(max_level, level)

        # 如果目标等级超过最大等级，使用最大等级
        if target_level > max_level:
            target_level = max_level

        # 查找目标等级的数据
        level_data = None
        next_level_data = None
        for item in data["level"]["json"]:
            if item.get("level") == target_level:
                level_data = item
            elif item.get("level") == target_level + 1:
                next_level_data = item
            if level_data and next_level_data:
                break

        if not level_data:
            await es_level_cost.finish(f"未找到等级 {target_level} 的数据")

        # 构建消息列表
        messages = []

        # 添加文字信息
        text_msg = [
            (
                f"等级 {target_level} (最大等级) 升级消耗统计：\n"
                if target_level == max_level
                else f"等级 {target_level} 升级消耗统计：\n"
            )
        ]

        # 添加累计消耗信息
        text_msg.append("【累计消耗】")
        text_msg.append(f"金币：{level_data.get('sum_gold', 0)}")
        text_msg.append(f"魔力粉尘：{level_data.get('sum_mana_dust', 0)}")
        if "sum_mana_crystal" in level_data:
            text_msg.append(f"魔力水晶：{level_data.get('sum_mana_crystal', 0)}")

        # 如果有下一级数据，添加升级消耗信息
        if next_level_data:
            text_msg.append(f"\n【升级到 {target_level + 1} 级需要】")
            text_msg.append(f"金币：{next_level_data.get('gold', 0)}")
            text_msg.append(f"魔力粉尘：{next_level_data.get('mana_dust', 0)}")
            if "mana_crystal" in next_level_data:
                text_msg.append(f"魔力水晶：{next_level_data.get('mana_crystal', 0)}")

        messages.append("\n".join(text_msg))

        # 添加统计图
        chart = await generate_level_cost_chart(data)
        messages.append(chart)

        # 发送消息
        await send_forward_messages(bot, event, messages)

    except Exception as e:
        if not isinstance(e, FinishedException):
            import traceback

            error_location = traceback.extract_tb(e.__traceback__)[-1]
            logger.error(
                f"处理升级消耗查询时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )
