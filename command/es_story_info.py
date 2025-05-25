from ..library.utils import *


@es_story_info.handle()
async def handle_es_story_info(bot: Bot, event: Event, args: Message = CommandArg()):
    try:
        # 获取用户输入的ID
        story_match = args.extract_plain_text().strip()
        
        if not story_match:
            await es_story_info.finish("请输入正确的格式：es故事信息+数字ID")
        
        target_id = int(story_match)
        
        # 获取群组ID
        group_id = None
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
        
        # 加载数据
        data = load_json_data(group_id)
        
        # 第一步：在event_calender中查找name_sno相符的所有内容
        calendar_events = []
        for event_item in data["event_calender"]["json"]:
            if event_item.get("name_sno") == target_id:
                calendar_events.append(event_item)
        
        if not calendar_events:
            await es_story_info.finish(f"未找到ID为 {target_id} 的活动信息")
        
        # 收集所有相关的故事信息
        all_story_info = []
        
        # 获取活动名称
        event_name = get_string_ui(data, target_id).get("zh_tw", f"活动ID {target_id}")
        
        for calendar_event in calendar_events:
            event_no = calendar_event.get("no")
            event_type = calendar_event.get("event_type")
            event_group = calendar_event.get("group")
            
            # 第二步：根据no, event_type, group去eventstory寻找符合条件的内容
            matching_event_stories = []
            for event_story in data["event_story"]["json"]:
                if (event_story.get("no") == event_no and 
                    event_story.get("event_type") == event_type and 
                    event_story.get("event_group") == event_group):
                    matching_event_stories.append(event_story)
            
            # 第三步：根据story_act去story_info寻找act符合的所有内容
            for event_story in matching_event_stories:
                story_act = event_story.get("story_act")
                if story_act:
                    episodes = []
                    for story in data["story_info"]["json"]:
                        if story.get("act") == story_act:
                            episodes.append(story)
                    
                    if episodes:
                        # 按episode排序
                        episodes.sort(key=lambda x: x.get("episode", 0))
                        
                        story_info = {
                            "event_name": event_name,
                            "story_act": story_act,
                            "episodes": episodes,
                            "calendar_event": calendar_event,
                            "event_story": event_story
                        }
                        all_story_info.append(story_info)
        
        if not all_story_info:
            await es_story_info.finish(f"未找到ID为 {target_id} 的故事信息")
        
        # 生成合并转发消息
        forward_msgs = []
        
        for story_info in all_story_info:
            event_name = story_info["event_name"]
            story_act = story_info["story_act"]
            episodes = story_info["episodes"]
            
            # 添加总览消息
            overview_msg = [f"{event_name}"]
            
            forward_msgs.append({
                "type": "node",
                "data": {
                    "name": "Eversoul Story",
                    "uin": bot.self_id,
                    "content": "\n".join(overview_msg)
                }
            })
            
            # 为每个章节创建单独的消息
            for episode in episodes:
                episode_num = episode.get("episode", 0)
                episode_name_sno = episode.get("episode_name_sno")
                episode_skip_sno = episode.get("episode_skip_no")
                
                # 获取章节标题
                episode_title = ""
                if episode_name_sno:
                    title_data = get_string_talk(data, episode_name_sno)
                    episode_title = title_data.get("zh_tw", "")
                
                # 获取章节大意
                episode_summary = ""
                if episode_skip_sno:
                    summary_data = get_string_talk(data, episode_skip_sno)
                    episode_summary = summary_data.get("zh_tw", "")
                
                episode_parts = [f"第 {episode_num} 章：{episode_title}"]
                if episode_summary:
                    episode_parts.append(f"{episode_summary}")
                
                forward_msgs.append({
                    "type": "node",
                    "data": {
                        "name": "Eversoul Story",
                        "uin": bot.self_id,
                        "content": "\n".join(episode_parts)
                    }
                })
        
        # 发送合并转发消息
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
                f"处理故事信息查询时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )
            await es_story_info.finish(f"处理故事信息查询时发生错误: {str(e)}") 