from ..library.utils import *


@es_update_check.handle()
async def handle():
    """处理手动检查更新的命令"""
    
    result = await check_eversoul_updates()
    message = await format_update_result(result)
    await es_update_check.finish(message)


async def format_update_result(result: dict) -> str:
    """格式化更新结果为消息文本"""
    live_info = result.get("live", {})
    review_info = result.get("review", {})
    
    message_parts = []
    
    message_parts.append("Live服务器状态:")
    if live_info.get("hasUpdate", False):
        message_parts.append(f"🔄 有更新可用")
        message_parts.append(f"📊 当前版本: {live_info.get('currentVersion', '未知')}")
        message_parts.append(f"🆕 更新版本: {live_info.get('updateVersion', '未知')}")
    else:
        message_parts.append(f"✅ 无更新")
        message_parts.append(f"📊 当前版本: {live_info.get('currentVersion', '未知')}")
    

    # 显示Live服务器数据表版本
    current_table_version = live_info.get('currentTableVersion', 0)
    if current_table_version > 0:
        message_parts.append(f"📋 当前数据表版本: {current_table_version}")
        
        # 如果有更新，显示新的数据表版本
        if live_info.get("hasUpdate", False):
            new_table_version = live_info.get("newTableVersion")
            if new_table_version and new_table_version != current_table_version:
                message_parts.append(f"🆕 更新数据表版本: {new_table_version}")
    
    message_parts.append("")
    
    message_parts.append("Review服务器状态:")
    if review_info.get("hasUpdate", False):
        message_parts.append(f"🔄 有更新可用")
        message_parts.append(f"📊 当前版本: {review_info.get('currentVersion', '未知')}")
        message_parts.append(f"🆕 更新版本: {review_info.get('updateVersion', '未知')}")
    else:
        message_parts.append(f"✅ 无更新")
        current_version = review_info.get('currentVersion', '未知')
        if current_version and current_version != '未知':
            message_parts.append(f"📊 当前版本: {current_version}")
        else:
            message_parts.append(f"📊 当前版本: 暂无Review版本")
    

    # 显示Review服务器数据表版本
    current_table_version = review_info.get('currentTableVersion', 0)
    if current_table_version > 0:
        message_parts.append(f"📋 当前数据表版本: {current_table_version}")
        
        # 如果有更新，显示新的数据表版本
        if review_info.get("hasUpdate", False):
            new_table_version = review_info.get("newTableVersion")
            if new_table_version and new_table_version != current_table_version:
                message_parts.append(f"🆕 更新数据表版本: {new_table_version}")

    
    return "\n".join(message_parts)


async def check_and_push_updates():
    """定时检查更新并推送到指定群组"""
    try:
        # 指定推送的群号
        TARGET_GROUP_ID = 645741432
        
        result = await check_eversoul_updates()
        live_info = result.get("live", {})
        review_info = result.get("review", {})
        
        push_messages = []
        
        # 检查Live服务器更新
        if live_info.get("hasUpdate", False):
            live_version = live_info.get("updateVersion", "")
            live_table_version = live_info.get("newTableVersion", 0)
            
            # 检查是否已推送过这个版本
            already_pushed = await EversoulUser.check_push_history(
                "live", live_version, live_table_version, TARGET_GROUP_ID
            )
            
            if not already_pushed:
                push_messages.append("🔥 永恒灵魂Live服务器有新版本更新！")
                push_messages.append(f"📊 当前版本: {live_info.get('currentVersion', '未知')}")
                push_messages.append(f"🆕 更新版本: {live_version}")
                if live_table_version > 0:
                    push_messages.append(f"📋 新数据表版本: {live_table_version}")
                push_messages.append("")
                
                # 记录推送历史
                await EversoulUser.add_push_history(
                    "live", live_version, live_table_version, TARGET_GROUP_ID
                )
        
        # 检查Review服务器更新
        if review_info.get("hasUpdate", False):
            review_version = review_info.get("updateVersion", "")
            review_table_version = review_info.get("newTableVersion", 0)
            
            # 检查是否已推送过这个版本
            already_pushed = await EversoulUser.check_push_history(
                "review", review_version, review_table_version, TARGET_GROUP_ID
            )
            
            if not already_pushed:
                if push_messages:  # 如果前面已有Live更新消息，加个分隔
                    push_messages.append("="*30)
                    
                push_messages.append("🔥 永恒灵魂Review服务器有新版本更新！")
                push_messages.append(f"📊 当前版本: {review_info.get('currentVersion', '未知')}")
                push_messages.append(f"🆕 更新版本: {review_version}")
                if review_table_version > 0:
                    push_messages.append(f"📋 新数据表版本: {review_table_version}")
                
                # 记录推送历史
                await EversoulUser.add_push_history(
                    "review", review_version, review_table_version, TARGET_GROUP_ID
                )
        
        # 如果有需要推送的消息，发送到群组
        if push_messages:
            try:
                bot = get_bot()
                push_message = "\n".join(push_messages)
                await bot.send_group_msg(group_id=TARGET_GROUP_ID, message=push_message)
                logger.info(f"已向群 {TARGET_GROUP_ID} 推送更新消息")
            except Exception as e:
                logger.error(f"推送消息到群 {TARGET_GROUP_ID} 失败: {e}")
    
    except Exception as e:
        logger.error(f"定时检查更新失败: {e}")


# 添加定时任务，每分钟检查一次更新（默认启动）
@scheduler.scheduled_job("interval", minutes=1, id="eversoul_update_check")
async def scheduled_update_check():
    """定时任务：每分钟检查永恒灵魂更新"""
    await check_and_push_updates()