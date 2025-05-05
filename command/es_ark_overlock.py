from ..library.utils import *


@es_ark_overclock.handle()
async def handle_ark_overclock(bot: Bot, event: Event, matched: Tuple[Any, ...] = RegexGroup()):
    try:
        # 获取目标超频等级
        target_level = int(matched[0])
        
        # 加载数据
        # 获取群组ID
        group_id = None
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
        data = load_json_data(group_id)
        
        # 查找超频信息
        current_level_cost = 0
        next_level_cost = 0
        total_cost = 0
        max_level = 0
        last_level_cost = 0
        
        # 找出最大超频等级
        for overclock in data["ark_overclock"]["json"]:
            overclock_level = overclock.get("overclock_level", 0)
            if overclock_level > max_level:
                max_level = overclock_level
        
        # 如果输入的等级超过最大等级，提醒用户并使用最大等级代替
        if target_level > max_level:
            # 发送提醒消息
            await bot.send(event, f"超频等级最大为 {max_level}，已自动为您查询最大等级信息。")
            target_level = max_level
        
        # 计算相关消耗
        for overclock in data["ark_overclock"]["json"]:
            overclock_level = overclock.get("overclock_level", 0)
            mana_crystal = overclock.get("mana_crystal", 0)
            
            # 获取当前等级的消耗
            if overclock_level == target_level:
                current_level_cost = mana_crystal
            
            # 获取下一级的消耗
            if overclock_level == target_level + 1:
                next_level_cost = mana_crystal
            
            # 记录上一级的消耗（用于显示最大等级的消耗）
            if overclock_level == max_level:
                last_level_cost = mana_crystal
            
            # 计算总消耗
            if overclock_level <= target_level:
                total_cost += mana_crystal
        
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
            detail_msg.append(f"当前等级消耗：{format_number(last_level_cost)} 魔力水晶")
        else:
            detail_msg.append(f"当前等级消耗：{format_number(current_level_cost)} 魔力水晶")
        
        # 添加下一级消耗信息（如果有）
        if target_level < max_level:
            detail_msg.append(f"下一级消耗：{format_number(next_level_cost)} 魔力水晶")
        else:
            detail_msg.append("已达到最大超频等级")
        
        # 添加总消耗
        detail_msg.append(f"\n总超频消耗（1-{target_level}级）：{format_number(total_cost)} 魔力水晶")
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
