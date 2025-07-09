from ..library.utils import *


@es_update_check.handle()
async def handle_manual_update_check():
    """处理手动检查更新的命令"""
    
    result = await check_eversoul_updates()
    message = format_update_result(result)
    await es_update_check.finish(message)


def format_update_result(result: dict) -> str:
    """格式化更新结果为消息文本"""
    live_info = result.get("live", {})
    review_info = result.get("review", {})
    
    message_parts = []
    
    message_parts.append("Live服务器状态:")
    if live_info.get("hasUpdate", False):
        message_parts.append(f"  🔄 有更新可用")
        message_parts.append(f"  📊 当前版本: {live_info.get('currentVersion', '未知')}")
        message_parts.append(f"  🆕 更新版本: {live_info.get('updateVersion', '未知')}")
    else:
        message_parts.append(f"  ✅ 无更新")
        message_parts.append(f"  📊 当前版本: {live_info.get('currentVersion', '未知')}")
    
    message_parts.append("")
    
    message_parts.append("Review服务器状态:")
    if review_info.get("hasUpdate", False):
        message_parts.append(f"  🔄 有更新可用")
        message_parts.append(f"  📊 当前版本: {review_info.get('currentVersion', '未知')}")
        message_parts.append(f"  🆕 更新版本: {review_info.get('updateVersion', '未知')}")
    else:
        message_parts.append(f"  ✅ 无更新")
        current_version = review_info.get('currentVersion', '未知')
        if current_version and current_version != '未知':
            message_parts.append(f"  📊 当前版本: {current_version}")
        else:
            message_parts.append(f"  📊 当前版本: 暂无Review版本")
    
    return "\n".join(message_parts)