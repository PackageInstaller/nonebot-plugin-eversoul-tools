from ..library.utils import *


def load_push_config() -> dict:
    """加载推送配置文件"""
    try:
        if PUSH_CONFIG_PATH.exists():
            with open(PUSH_CONFIG_PATH, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                return config.get("push_groups", {})
        else:
            logger.warning(f"推送配置文件不存在: {PUSH_CONFIG_PATH}")
            return {}
    except Exception as e:
        logger.error(f"加载推送配置文件失败: {e}")
        return {}


def get_target_groups(server_type: str) -> Set[int]:
    """获取指定服务器类型应该推送的群组列表

    Args:
        server_type: 服务器类型 (gl_live, gl_review, cn_live, cn_review)

    Returns:
        Set[int]: 群号集合
    """
    config = load_push_config()
    target_groups = set()

    # 添加 all 类型的群
    all_groups = config.get("all", [])
    if all_groups:
        target_groups.update(all_groups)

    # 添加服务器大类的群 (gl 或 cn)
    if server_type.startswith("gl_"):
        gl_groups = config.get("gl", [])
        if gl_groups:
            target_groups.update(gl_groups)
    elif server_type.startswith("cn_"):
        cn_groups = config.get("cn", [])
        if cn_groups:
            target_groups.update(cn_groups)

    return target_groups


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
    """定时检查更新并推送到指定群组"""
    try:
        result = await check_eversoul_updates()
        live_info = result.get("gl_live", {})
        review_info = result.get("gl_review", {})
        cn_live_info = result.get("cn_live", {})
        cn_review_info = result.get("cn_review", {})

        # 收集每个服务器类型的更新信息和目标群组
        updates_to_push = {}

        # 检查国际服Live更新
        if live_info.get("hasUpdate", False):
            live_version = live_info.get("updateVersion", "")
            live_table_version = live_info.get("newTableVersion", 0)
            target_groups = get_target_groups("gl_live")

            if target_groups:
                message_parts = []
                message_parts.append("🔥 永恒灵魂【国际服】Live服务器有新版本更新！")
                message_parts.append(
                    f"📊 当前版本: {live_info.get('currentVersion', '未知')}"
                )
                message_parts.append(f"🆕 更新版本: {live_version}")
                current_table_version = live_info.get("currentTableVersion", 0)
                if current_table_version > 0:
                    message_parts.append(f"📋 当前数据表版本: {current_table_version}")
                if live_table_version > 0:
                    message_parts.append(f"📋 新数据表版本: {live_table_version}")

                updates_to_push["gl_live"] = {
                    "version": live_version,
                    "table_version": live_table_version,
                    "message": "\n".join(message_parts),
                    "target_groups": target_groups,
                }

        # 检查国际服Review更新
        if review_info.get("hasUpdate", False):
            review_version = review_info.get("updateVersion", "")
            review_table_version = review_info.get("newTableVersion", 0)
            target_groups = get_target_groups("gl_review")

            if target_groups:
                message_parts = []
                message_parts.append("🔥 永恒灵魂【国际服】Review服务器有新版本更新！")
                message_parts.append(
                    f"📊 当前版本: {review_info.get('currentVersion', '未知')}"
                )
                message_parts.append(f"🆕 更新版本: {review_version}")
                current_table_version = review_info.get("currentTableVersion", 0)
                if current_table_version > 0:
                    message_parts.append(f"📋 当前数据表版本: {current_table_version}")
                if review_table_version > 0:
                    message_parts.append(f"📋 新数据表版本: {review_table_version}")

                updates_to_push["gl_review"] = {
                    "version": review_version,
                    "table_version": review_table_version,
                    "message": "\n".join(message_parts),
                    "target_groups": target_groups,
                }

        # 检查国服Live更新
        if cn_live_info.get("hasUpdate", False):
            cn_live_version = cn_live_info.get("updateVersion", "")
            cn_live_table_version = cn_live_info.get("newTableVersion", 0)
            target_groups = get_target_groups("cn_live")

            if target_groups:
                message_parts = []
                message_parts.append("🔥 永恒灵魂【国服】Live服务器有新版本更新！")
                message_parts.append(
                    f"📊 当前版本: {cn_live_info.get('currentVersion', '未知')}"
                )
                message_parts.append(f"🆕 更新版本: {cn_live_version}")
                current_table_version = cn_live_info.get("currentTableVersion", 0)
                if current_table_version > 0:
                    message_parts.append(f"📋 当前数据表版本: {current_table_version}")
                if cn_live_table_version > 0:
                    message_parts.append(f"📋 新数据表版本: {cn_live_table_version}")

                updates_to_push["cn_live"] = {
                    "version": cn_live_version,
                    "table_version": cn_live_table_version,
                    "message": "\n".join(message_parts),
                    "target_groups": target_groups,
                }

        # 检查国服Review更新
        if cn_review_info.get("hasUpdate", False):
            cn_review_version = cn_review_info.get("updateVersion", "")
            cn_review_table_version = cn_review_info.get("newTableVersion", 0)
            target_groups = get_target_groups("cn_review")

            if target_groups:
                message_parts = []
                message_parts.append("🔥 永恒灵魂【国服】Review服务器有新版本更新！")
                message_parts.append(
                    f"📊 当前版本: {cn_review_info.get('currentVersion', '未知')}"
                )
                message_parts.append(f"🆕 更新版本: {cn_review_version}")
                current_table_version = cn_review_info.get("currentTableVersion", 0)
                if current_table_version > 0:
                    message_parts.append(f"📋 当前数据表版本: {current_table_version}")
                if cn_review_table_version > 0:
                    message_parts.append(f"📋 新数据表版本: {cn_review_table_version}")

                updates_to_push["cn_review"] = {
                    "version": cn_review_version,
                    "table_version": cn_review_table_version,
                    "message": "\n".join(message_parts),
                    "target_groups": target_groups,
                }

        # 按群组组织消息并推送
        if updates_to_push:
            # 收集每个群组需要接收的消息
            group_messages = {}

            for server_type, update_info in updates_to_push.items():
                for group_id in update_info["target_groups"]:
                    # 检查是否已经推送过
                    already_pushed = await EversoulUser.check_push_history(
                        server_type,
                        update_info["version"],
                        update_info["table_version"],
                        group_id,
                    )

                    if not already_pushed:
                        if group_id not in group_messages:
                            group_messages[group_id] = []
                        group_messages[group_id].append(update_info["message"])

                        # 记录推送历史
                        await EversoulUser.add_push_history(
                            server_type,
                            update_info["version"],
                            update_info["table_version"],
                            group_id,
                        )

            # 向每个群组推送消息
            bot = get_bot()
            for group_id, messages in group_messages.items():
                try:
                    push_message = "\n\n" + ("=" * 30) + "\n\n"
                    push_message = push_message.join(messages)
                    await bot.send_group_msg(group_id=group_id, message=push_message)
                    logger.info(f"已向群 {group_id} 推送更新消息")
                except Exception as e:
                    logger.error(f"推送消息到群 {group_id} 失败: {e}")

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


@scheduler.scheduled_job("interval", minutes=10, id="eversoul_update_check")
async def scheduled_update_check():
    """定时任务：每10分钟检查永恒灵魂更新"""
    await check_and_push_updates()
