from ..library.utils import *


@es_story.handle()
async def handle(bot: Bot, event: Event, args: Message = CommandArg()):
    try:
        # 获取用户输入的ID
        story_match = args.extract_plain_text().strip()

        if not story_match:
            await es_story.finish("请输入正确的格式：es故事信息+数字ID")

        target_id = int(story_match)

        group_id = get_group_id(event)
        data = await load_json_data(group_id, command_name="es故事信息")

        # 第一步：在event_info中查找name_sno相符的所有内容
        # first step: find all event_info that match the condition
        calendar_events = []
        for event_item in data["event_info"]["json"]:
            if event_item.get("name_sno") == target_id:
                calendar_events.append(event_item)

        if not calendar_events:
            await es_story.finish(f"未找到ID为 {target_id} 的活动信息")

        # 收集所有相关的故事信息
        all_story_info = []

        # 获取活动名称
        # get the event name
        event_name = await get_string_by_type(data, "ui", target_id).get(
            "zh_tw", f"活动ID {target_id}"
        )

        for calendar_event in calendar_events:
            event_type = calendar_event.get("event_type")
            event_group = calendar_event.get("group")

            # 第二步：根据event_type, group去eventstory寻找符合条件的内容
            # second step: find all event_story that match the condition
            matching_event_stories = []
            for event_story in data["event_story"]["json"]:
                if (
                    event_story.get("event_type") == event_type
                    and event_story.get("event_group") == event_group
                ):
                    matching_event_stories.append(event_story)

            # 第三步：根据story_act去story_info寻找act符合的所有内容
            # third step: find all story_info that match the condition
            for event_story in matching_event_stories:
                story_act = event_story.get("story_act")
                if story_act:
                    episodes = []
                    for story in data["story_info"]["json"]:
                        if story.get("act") == story_act:
                            episodes.append(story)

                    if episodes:
                        # 按episode排序
                        # sort the episodes by episode
                        episodes.sort(key=lambda x: x.get("episode", 0))

                        story_info = {
                            "event_name": event_name,
                            "story_act": story_act,
                            "episodes": episodes,
                            "calendar_event": calendar_event,
                            "event_story": event_story,
                        }
                        all_story_info.append(story_info)

        if not all_story_info:
            await es_story.finish(f"未找到ID为 {target_id} 的故事信息")

        # 生成转发消息
        messages = []

        for story_info in all_story_info:
            event_name = story_info["event_name"]
            episodes = story_info["episodes"]

            # 添加总览消息
            messages.append(event_name)

            # 为每个章节创建单独的消息
            for episode in episodes:
                episode_num = episode.get("episode", 0)
                episode_name_sno = episode.get("episode_name_sno")
                episode_skip_sno = episode.get("episode_skip_no")

                # 获取章节标题
                episode_title = ""
                if episode_name_sno:
                    title_data = await get_string_by_type(
                        data, "talk", episode_name_sno
                    )
                    episode_title = title_data.get("zh_tw", "")

                # 获取章节大意
                episode_summary = ""
                if episode_skip_sno:
                    summary_data = await get_string_by_type(
                        data, "talk", episode_skip_sno
                    )
                    episode_summary = summary_data.get("zh_tw", "")

                episode_parts = [f"第 {episode_num} 章：{episode_title}"]
                if episode_summary:
                    episode_parts.append(f"{episode_summary}")

                messages.append("\n".join(episode_parts))

        # 发送合并转发消息
        await send_forward_messages(bot, event, messages)

    except Exception as e:
        if not isinstance(e, FinishedException):
            import traceback

            error_location = traceback.extract_tb(e.__traceback__)[-1]
            logger.error(
                f"处理故事信息查询时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )
