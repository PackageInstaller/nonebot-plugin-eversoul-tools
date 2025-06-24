from ..library.utils import *


@es_ark_overclock.handle()
async def handle_ark_overclock(bot: Bot, event: Event, args: Message = CommandArg()):
    try:
        # 获取目标超频等级
        target_level = args.extract_plain_text().strip()
        if not target_level:
            await es_ark_overclock.finish("请输入正确的格式：es超频消耗+等级")
        target_level = int(target_level)
        
        # 加载数据
        # 获取群组ID
        group_id = 0
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
        data = load_json_data(group_id)
        
        # 查找超频信息
        current_level_cost = 0
        next_level_cost = 0
        total_cost = 0
        max_level = 0
        last_level_cost = 0
        
        # 魔力粉尘消耗信息
        current_extra_items = {}  # 当前等级的魔力粉尘消耗
        next_extra_items = {}     # 下一等级的魔力粉尘消耗
        total_extra_items = {}    # 总的魔力粉尘消耗
        last_extra_items = {}     # 最大等级的魔力粉尘消耗
        
        # 找出最大超频等级
        for overclock in data["ark_overclock"]["json"]:
            overclock_level = overclock.get("overclock_level", 0)
            if overclock_level > max_level:
                max_level = overclock_level
        
        if target_level > max_level:
            await bot.send(event, f"超频等级最大为 {max_level}，已自动为您查询最大等级信息。")
            target_level = max_level
        
        # 计算相关消耗
        for overclock in data["ark_overclock"]["json"]:
            overclock_level = overclock.get("overclock_level", 0)
            mana_crystal = overclock.get("mana_crystal", 0)
            
            # 获取当前等级的消耗
            if overclock_level == target_level:
                current_level_cost = mana_crystal
                # 收集魔力粉尘消耗
                for i in range(10):  # 最多有10个魔力粉尘
                    item_no_key = f"pay_item_no_{i}"
                    item_amount_key = f"pay_amount_{i}"
                    if item_no_key in overclock and item_amount_key in overclock:
                        item_no = overclock[item_no_key]
                        item_amount = overclock[item_amount_key]
                        if item_no and item_amount:
                            current_extra_items[item_no] = item_amount
            
            # 获取下一级的消耗
            if overclock_level == target_level + 1:
                next_level_cost = mana_crystal
                # 收集魔力粉尘消耗
                for i in range(10):  # 最多有10个魔力粉尘
                    item_no_key = f"pay_item_no_{i}"
                    item_amount_key = f"pay_amount_{i}"
                    if item_no_key in overclock and item_amount_key in overclock:
                        item_no = overclock[item_no_key]
                        item_amount = overclock[item_amount_key]
                        if item_no and item_amount:
                            next_extra_items[item_no] = item_amount
            
            # 记录上一级的消耗（用于显示最大等级的消耗）
            if overclock_level == max_level:
                last_level_cost = mana_crystal
                # 收集魔力粉尘消耗
                for i in range(10):  # 最多有10个魔力粉尘
                    item_no_key = f"pay_item_no_{i}"
                    item_amount_key = f"pay_amount_{i}"
                    if item_no_key in overclock and item_amount_key in overclock:
                        item_no = overclock[item_no_key]
                        item_amount = overclock[item_amount_key]
                        if item_no and item_amount:
                            last_extra_items[item_no] = item_amount
            
            # 计算总消耗
            if overclock_level <= target_level:
                total_cost += mana_crystal
                # 收集魔力粉尘总消耗
                for i in range(10):  # 最多有10个魔力粉尘
                    item_no_key = f"pay_item_no_{i}"
                    item_amount_key = f"pay_amount_{i}"
                    if item_no_key in overclock and item_amount_key in overclock:
                        item_no = overclock[item_no_key]
                        item_amount = overclock[item_amount_key]
                        if item_no and item_amount:
                            if item_no in total_extra_items:
                                total_extra_items[item_no] += item_amount
                            else:
                                total_extra_items[item_no] = item_amount
        
        if total_cost == 0:
            await bot.send(event, f"未找到超频等级 {target_level} 的信息")
            return
        
        # 构建消息
        messages = []
        
        # 添加标题
        title_msg = [f"方舟超频 Lv.{target_level} 信息："]
        messages.append("".join(title_msg))
        
        # 添加详细超频信息
        detail_msg = []
        
        # 对于最大等级，显示最大等级的消耗（而不是升到最大等级+1的消耗，因为没有这个等级）
        if target_level == max_level:
            cost_msg = [f"当前等级消耗：\n{format_number(last_level_cost)} 魔力水晶"]
            # 添加魔力粉尘消耗
            if last_extra_items:
                for item_no, amount in last_extra_items.items():
                    item_name = get_string_item(data, item_no).get("zh_twOffset", "未知物品")
                    cost_msg.append(f"{format_number(amount)} {item_name}")
            detail_msg.append("\n".join(cost_msg))
        else:
            cost_msg = [f"当前等级消耗：\n{format_number(current_level_cost)} 魔力水晶"]
            # 添加魔力粉尘消耗
            if current_extra_items:
                for item_no, amount in current_extra_items.items():
                    item_name = get_string_item(data, item_no).get("zh_twOffset", "未知物品")
                    cost_msg.append(f"{format_number(amount)} {item_name}")
            detail_msg.append("\n".join(cost_msg))
        
        # 添加下一级消耗信息（如果有）
        if target_level < max_level:
            next_cost_msg = [f"下一级消耗：\n{format_number(next_level_cost)} 魔力水晶"]
            # 添加魔力粉尘消耗
            if next_extra_items:
                for item_no, amount in next_extra_items.items():
                    item_name = get_string_item(data, item_no).get("zh_twOffset", "未知物品")
                    next_cost_msg.append(f"{format_number(amount)} {item_name}")
            detail_msg.append("\n".join(next_cost_msg))
        else:
            detail_msg.append("已达到最大超频等级")
        
        # 添加总消耗
        total_cost_msg = [f"\n总超频消耗（1-{target_level}级）：\n{format_number(total_cost)} 魔力水晶"]
        # 添加魔力粉尘总消耗
        if total_extra_items:
            for item_no, amount in total_extra_items.items():
                item_name = get_string_item(data, item_no).get("zh_twOffset", "未知物品")
                total_cost_msg.append(f"{format_number(amount)} {item_name}")
        detail_msg.append("\n".join(total_cost_msg))
        messages.append("\n".join(detail_msg))

        # 添加统计图
        chart_msg = []
        chart_msg.append("\n【等级关系统计图】")
        chart = await generate_ark_level_chart(data, target_level)
        chart_msg.append(chart)
        messages.append("\n".join(str(x) for x in chart_msg))
        
        # 构建转发消息
        forward_msgs = []
        for msg in messages:
            forward_msgs.append({
                "type": "node",
                "data": {
                    "name": "EverSoul Ark Overclock",
                    "uin": bot.self_id,
                    "content": msg
                }
            })
        
        # 发送消息
        if isinstance(event, GroupMessageEvent):
            await bot.call_api(
                "send_group_forward_msg",
                group_id=event.group_id,
                messages=forward_msgs
            )
        else:
            await bot.call_api(
                "send_private_forward_msg",
                user_id=event.user_id,
                messages=forward_msgs
            )
            
    except Exception as e:
        if not isinstance(e, FinishedException):
            import traceback
            error_location = traceback.extract_tb(e.__traceback__)[-1]
            logger.error(
                f"处理方舟超频信息时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )
            await bot.send(event, f"处理方舟超频信息时发生错误: {str(e)}")
