from ..library.utils import *


@es_month.handle()
async def handle_es_month(bot: Bot, event: Event):
    try:
        # 获取月份
        raw_message = event.get_plaintext() # 获取纯文本消息
        month_match = re.match(r"^es(\d{1,2})月事件$", raw_message)
        if month_match:
            target_month = int(month_match.group(1))
            if not 1 <= target_month <= 12:
                await es_month.finish("请输入正确的月份(1-12)")
        else:
            # 如果是其他别名触发，使用当前月份
            target_month = datetime.now().month
        
        current_year = datetime.now().year
        # 加载数据
        # 获取群组ID
        group_id = 0
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
        data = load_json_data(group_id)
        
        # 收集指定月份的事件
        month_events = []

        main_events = []
        for schedule in data["localization_schedule"]["json"]:
            schedule_key = schedule.get("schedule_key", "")
            if schedule_key.startswith("Calender_") and schedule_key.endswith("_Main"):
                prefix = schedule_key
                main_events.extend(get_schedule_event(data, target_month, current_year,
                                                    prefix, "主要活动"))
        month_events.extend(main_events)
        
        month_events.extend(get_schedule_event(data, target_month, current_year,
                                             "Calender_PickUp_", "Pickup"))

        # 获取一般活动事件
        calendar_events = get_calendar_event(data, target_month, current_year)
        month_events.extend(calendar_events)

        # 获取邮箱事件
        mail_events = get_mail_event(data, target_month, current_year)
        month_events.extend(mail_events)
        
        if month_events:
            html = await generate_timeline_html(target_month, month_events)
            png_pic = await html_to_pic(
                html, 
                device_scale_factor = 0.8,
                viewport={"width": 1800, "height": 1000}
            )
            
            if isinstance(event, GroupMessageEvent):
                await bot.send_group_msg(
                    group_id=event.group_id,
                    message=Message(MessageSegment.image(png_pic))
                )
            else:
                await bot.send_private_msg(
                    user_id=int(event.get_user_id()),
                    message=Message(MessageSegment.image(png_pic))
                )
        else:
            await es_month.finish(f"{target_month}月份没有事件哦~")
            
    except Exception as e:
        if not isinstance(e, FinishedException):
            import traceback
            error_location = traceback.extract_tb(e.__traceback__)[-1]
            logger.error(
                f"处理月度事件查询时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )