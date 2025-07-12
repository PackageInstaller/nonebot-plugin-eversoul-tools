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