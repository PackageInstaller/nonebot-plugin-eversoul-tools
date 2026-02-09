from ..library.utils import *


@es_update_check.handle()
async def handle():
    """处理手动检查更新的命令"""

    result = await check_eversoul_updates()
    message = await format_update_result(result)
    await es_update_check.finish(message)


async def format_update_result(result: dict) -> str:
    """格式化更新结果为消息文本"""
    live_info = result.get("gl_live", {})
    review_info = result.get("gl_review", {})
    cn_live_info = result.get("cn_live", {})
    cn_review_info = result.get("cn_review", {})

    message_parts = []

    # 国际服Live
    message_parts.append("【国际服】Live服务器状态:")
    if live_info.get("hasUpdate", False):
        message_parts.append(f"🔄 有更新可用")
        message_parts.append(f"📊 当前版本: {live_info.get('currentVersion', '未知')}")
        message_parts.append(f"🆕 更新版本: {live_info.get('updateVersion', '未知')}")
    else:
        message_parts.append(f"✅ 无更新")
        message_parts.append(f"📊 当前版本: {live_info.get('currentVersion', '未知')}")

    # 显示Live服务器数据表版本
    current_table_version = live_info.get("currentTableVersion", 0)
    if current_table_version > 0:
        message_parts.append(f"📋 当前数据表版本: {current_table_version}")

        # 如果有更新，显示新的数据表版本
        if live_info.get("hasUpdate", False):
            new_table_version = live_info.get("newTableVersion")
            if new_table_version and new_table_version != current_table_version:
                message_parts.append(f"🆕 更新数据表版本: {new_table_version}")

    message_parts.append("")

    # 国际服Review
    message_parts.append("【国际服】Review服务器状态:")
    if review_info.get("hasUpdate", False):
        message_parts.append(f"🔄 有更新可用")
        message_parts.append(
            f"📊 当前版本: {review_info.get('currentVersion', '未知')}"
        )
        message_parts.append(f"🆕 更新版本: {review_info.get('updateVersion', '未知')}")
    else:
        message_parts.append(f"✅ 无更新")
        current_version = review_info.get("currentVersion", "未知")
        if current_version and current_version != "未知":
            message_parts.append(f"📊 当前版本: {current_version}")
        else:
            message_parts.append(f"📊 当前版本: 暂无Review版本")

    # 显示Review服务器数据表版本
    current_table_version = review_info.get("currentTableVersion", 0)
    if current_table_version > 0:
        message_parts.append(f"📋 当前数据表版本: {current_table_version}")

        # 如果有更新，显示新的数据表版本
        if review_info.get("hasUpdate", False):
            new_table_version = review_info.get("newTableVersion")
            if new_table_version and new_table_version != current_table_version:
                message_parts.append(f"🆕 更新数据表版本: {new_table_version}")

    message_parts.append("")

    # 国服Live
    message_parts.append("【国服】Live服务器状态:")
    if cn_live_info.get("hasUpdate", False):
        message_parts.append(f"🔄 有更新可用")
        message_parts.append(
            f"📊 当前版本: {cn_live_info.get('currentVersion', '未知')}"
        )
        message_parts.append(
            f"🆕 更新版本: {cn_live_info.get('updateVersion', '未知')}"
        )
    else:
        message_parts.append(f"✅ 无更新")
        current_version = cn_live_info.get("currentVersion", "未知")
        if current_version and current_version != "未知":
            message_parts.append(f"📊 当前版本: {current_version}")
        else:
            message_parts.append(f"📊 当前版本: 暂无版本信息")

    # 显示国服Live服务器数据表版本
    current_table_version = cn_live_info.get("currentTableVersion", 0)
    if current_table_version > 0:
        message_parts.append(f"📋 当前数据表版本: {current_table_version}")

        # 如果有更新，显示新的数据表版本
        if cn_live_info.get("hasUpdate", False):
            new_table_version = cn_live_info.get("newTableVersion")
            if new_table_version and new_table_version != current_table_version:
                message_parts.append(f"🆕 更新数据表版本: {new_table_version}")

    message_parts.append("")

    # 国服Review
    message_parts.append("【国服】Review服务器状态:")
    if cn_review_info.get("hasUpdate", False):
        message_parts.append(f"🔄 有更新可用")
        message_parts.append(
            f"📊 当前版本: {cn_review_info.get('currentVersion', '未知')}"
        )
        message_parts.append(
            f"🆕 更新版本: {cn_review_info.get('updateVersion', '未知')}"
        )
    else:
        message_parts.append(f"✅ 无更新")
        current_version = cn_review_info.get("currentVersion", "未知")
        if current_version and current_version != "未知":
            message_parts.append(f"📊 当前版本: {current_version}")
        else:
            message_parts.append(f"📊 当前版本: 暂无Review版本")

    # 显示国服Review服务器数据表版本
    current_table_version = cn_review_info.get("currentTableVersion", 0)
    if current_table_version > 0:
        message_parts.append(f"📋 当前数据表版本: {current_table_version}")

        # 如果有更新，显示新的数据表版本
        if cn_review_info.get("hasUpdate", False):
            new_table_version = cn_review_info.get("newTableVersion")
            if new_table_version and new_table_version != current_table_version:
                message_parts.append(f"🆕 更新数据表版本: {new_table_version}")

    return "\n".join(message_parts)


async def check_and_push_updates():
    """定时检查更新并推送到管理员"""
    try:
        # 获取管理员ID列表
        superusers = getattr(driver.config, "superusers", set())
        
        if not superusers:
            logger.info("未配置管理员ID，跳过更新推送")
            return
        
        result = await check_eversoul_updates()
        live_info = result.get("gl_live", {})
        review_info = result.get("gl_review", {})
        cn_live_info = result.get("cn_live", {})
        cn_review_info = result.get("cn_review", {})

        # 收集所有更新消息
        update_messages = []

        # 检查国际服Live更新
        if live_info.get("hasUpdate", False):
            live_version = live_info.get("updateVersion", "")
            live_table_version = live_info.get("newTableVersion", 0)
            
            # 检查是否已推送过（使用 user_id=0 表示管理员推送）
            already_pushed = await EversoulUser.check_push_history(
                "gl_live", live_version, live_table_version, 0
            )
            
            if not already_pushed:
                message_parts = []
                message_parts.append("🔥 永恒灵魂【国际服】Live服务器有新版本更新！")
                message_parts.append(f"📊 当前版本: {live_info.get('currentVersion', '未知')}")
                message_parts.append(f"🆕 更新版本: {live_version}")
                current_table_version = live_info.get("currentTableVersion", 0)
                if current_table_version > 0:
                    message_parts.append(f"📋 当前数据表版本: {current_table_version}")
                if live_table_version > 0:
                    message_parts.append(f"📋 新数据表版本: {live_table_version}")
                update_messages.append("\n".join(message_parts))
                
                await EversoulUser.add_push_history("gl_live", live_version, live_table_version, 0)

        # 检查国际服Review更新
        if review_info.get("hasUpdate", False):
            review_version = review_info.get("updateVersion", "")
            review_table_version = review_info.get("newTableVersion", 0)
            
            already_pushed = await EversoulUser.check_push_history(
                "gl_review", review_version, review_table_version, 0
            )
            
            if not already_pushed:
                message_parts = []
                message_parts.append("🔥 永恒灵魂【国际服】Review服务器有新版本更新！")
                message_parts.append(f"📊 当前版本: {review_info.get('currentVersion', '未知')}")
                message_parts.append(f"🆕 更新版本: {review_version}")
                current_table_version = review_info.get("currentTableVersion", 0)
                if current_table_version > 0:
                    message_parts.append(f"📋 当前数据表版本: {current_table_version}")
                if review_table_version > 0:
                    message_parts.append(f"📋 新数据表版本: {review_table_version}")
                update_messages.append("\n".join(message_parts))
                
                await EversoulUser.add_push_history("gl_review", review_version, review_table_version, 0)

        # 检查国服Live更新
        if cn_live_info.get("hasUpdate", False):
            cn_live_version = cn_live_info.get("updateVersion", "")
            cn_live_table_version = cn_live_info.get("newTableVersion", 0)
            
            already_pushed = await EversoulUser.check_push_history(
                "cn_live", cn_live_version, cn_live_table_version, 0
            )
            
            if not already_pushed:
                message_parts = []
                message_parts.append("🔥 永恒灵魂【国服】Live服务器有新版本更新！")
                message_parts.append(f"📊 当前版本: {cn_live_info.get('currentVersion', '未知')}")
                message_parts.append(f"🆕 更新版本: {cn_live_version}")
                current_table_version = cn_live_info.get("currentTableVersion", 0)
                if current_table_version > 0:
                    message_parts.append(f"📋 当前数据表版本: {current_table_version}")
                if cn_live_table_version > 0:
                    message_parts.append(f"📋 新数据表版本: {cn_live_table_version}")
                update_messages.append("\n".join(message_parts))
                
                await EversoulUser.add_push_history("cn_live", cn_live_version, cn_live_table_version, 0)

        # 检查国服Review更新
        if cn_review_info.get("hasUpdate", False):
            cn_review_version = cn_review_info.get("updateVersion", "")
            cn_review_table_version = cn_review_info.get("newTableVersion", 0)
            
            already_pushed = await EversoulUser.check_push_history(
                "cn_review", cn_review_version, cn_review_table_version, 0
            )
            
            if not already_pushed:
                message_parts = []
                message_parts.append("🔥 永恒灵魂【国服】Review服务器有新版本更新！")
                message_parts.append(f"📊 当前版本: {cn_review_info.get('currentVersion', '未知')}")
                message_parts.append(f"🆕 更新版本: {cn_review_version}")
                current_table_version = cn_review_info.get("currentTableVersion", 0)
                if current_table_version > 0:
                    message_parts.append(f"📋 当前数据表版本: {current_table_version}")
                if cn_review_table_version > 0:
                    message_parts.append(f"📋 新数据表版本: {cn_review_table_version}")
                update_messages.append("\n".join(message_parts))
                
                await EversoulUser.add_push_history("cn_review", cn_review_version, cn_review_table_version, 0)

        # 向管理员推送消息
        if update_messages:
            bot = get_bot()
            push_message = "\n\n" + ("=" * 30) + "\n\n"
            push_message = push_message.join(update_messages)
            
            for admin_id in superusers:
                try:
                    await bot.send_private_msg(user_id=int(admin_id), message=push_message)
                    logger.info(f"已向管理员 {admin_id} 推送更新消息")
                except Exception as e:
                    logger.error(f"推送消息到管理员 {admin_id} 失败: {e}")

        # 推送消息后，下载更新
        if (
            live_info.get("hasUpdate", False)
            or review_info.get("hasUpdate", False)
            or cn_live_info.get("hasUpdate", False)
            or cn_review_info.get("hasUpdate", False)
        ):
            logger.info("检测到更新，开始下载数据表...")
            async with EversoulUpdateChecker() as checker:
                await checker.download_updates_from_result(result)

    except Exception as e:
        logger.error(f"定时检查更新失败: {e}")


@scheduler.scheduled_job("interval", minutes=60, id="eversoul_update_check")
async def scheduled_update_check():
    """定时任务：每60分钟检查永恒灵魂更新"""
    await check_and_push_updates()

