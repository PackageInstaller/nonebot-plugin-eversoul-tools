from ..library.utils import *


@es_switch_source.handle()
@require_group("私聊无法切换数据源，请在群聊中使用此命令。")
async def handle(bot: Bot, event: Event, args: Message = CommandArg()):
    # 获取参数
    args_str = str(args).strip().lower()

    # 获取群组ID（装饰器已确保是群聊）
    group_id = str(get_group_id(event))

    # 权限检查：只有超级用户能切到 review 数据源
    if args_str.endswith("_review"):
        if not await SUPERUSER(bot, event):
            await es_switch_source.finish("仅超级用户允许切换到 review 数据源。")

    if not args_str:
        config = await get_group_data_source(group_id)
        server = config.get("server", "global")
        data_type = config.get("type", "live")
        server_name = {"global": "国际服", "cn": "国服", "jp": "日服"}.get(server, server)
        await es_switch_source.finish(f"当前群组数据源为: {server_name} - {data_type}")

    # 支持的参数：cn_live, cn_review, gl_live, gl_review, jp_live, jp_review
    if args_str not in ["cn_live", "cn_review", "gl_live", "gl_review", "jp_live", "jp_review"]:
        await es_switch_source.finish(
            "参数错误！\n"
            "可用选项:\n"
            "  cn_live - 国服live\n"
            "  cn_review - 国服review\n"
            "  gl_live - 国际服live\n"
            "  gl_review - 国际服review\n"
            "  下面两个没用，不要切过去\n"
            "  jp_live - 日服live\n"
            "  jp_review - 日服review"
        )

    # 确保CURRENT_DATA_SOURCE包含default配置
    if "default" not in CURRENT_DATA_SOURCE:
        CURRENT_DATA_SOURCE["default"] = DEFAULT_CONFIG.copy()

    # 更新群组配置
    if group_id not in CURRENT_DATA_SOURCE:
        # 如果群组配置不存在，基于默认配置创建一个
        CURRENT_DATA_SOURCE[group_id] = CURRENT_DATA_SOURCE["default"].copy()

    # 根据参数设置server和type
    if args_str == "cn_live":
        # 国服live
        CURRENT_DATA_SOURCE[group_id]["server"] = "cn"
        CURRENT_DATA_SOURCE[group_id]["type"] = "live"
        CURRENT_DATA_SOURCE[group_id]["json_path"] = CN_LIVE_TABLE_DIR
        
        # 检查数据表是否存在
        if not CN_LIVE_TABLE_DIR.exists() or not any(CN_LIVE_TABLE_DIR.glob("*.json")):
            await es_switch_source.finish(
                "国服live数据表不存在，请等待自动下载完成或手动触发更新检查"
            )
    elif args_str == "cn_review":
        # 国服review
        CURRENT_DATA_SOURCE[group_id]["server"] = "cn"
        CURRENT_DATA_SOURCE[group_id]["type"] = "review"
        CURRENT_DATA_SOURCE[group_id]["json_path"] = CN_REVIEW_TABLE_DIR
        
        # 检查数据表是否存在
        if not CN_REVIEW_TABLE_DIR.exists() or not any(CN_REVIEW_TABLE_DIR.glob("*.json")):
            await es_switch_source.finish(
                "国服review数据表不存在，请等待自动下载完成或手动触发更新检查"
            )
    elif args_str == "jp_live":
        # 日服live
        CURRENT_DATA_SOURCE[group_id]["server"] = "jp"
        CURRENT_DATA_SOURCE[group_id]["type"] = "live"
        CURRENT_DATA_SOURCE[group_id]["json_path"] = JP_LIVE_TABLE_DIR
        
        # 检查数据表是否存在
        if not JP_LIVE_TABLE_DIR.exists() or not any(JP_LIVE_TABLE_DIR.glob("*.json")):
            await es_switch_source.finish(
                "日服live数据表不存在，请等待自动下载完成或手动触发更新检查"
            )
    elif args_str == "jp_review":
        # 日服review
        CURRENT_DATA_SOURCE[group_id]["server"] = "jp"
        CURRENT_DATA_SOURCE[group_id]["type"] = "review"
        CURRENT_DATA_SOURCE[group_id]["json_path"] = JP_REVIEW_TABLE_DIR
        
        # 检查数据表是否存在
        if not JP_REVIEW_TABLE_DIR.exists() or not any(JP_REVIEW_TABLE_DIR.glob("*.json")):
            await es_switch_source.finish(
                "日服review数据表不存在，请等待自动下载完成或手动触发更新检查"
            )
    elif args_str == "gl_live":
        # 国际服live
        CURRENT_DATA_SOURCE[group_id]["server"] = "global"
        CURRENT_DATA_SOURCE[group_id]["type"] = "live"
        CURRENT_DATA_SOURCE[group_id]["json_path"] = GL_LIVE_TABLE_DIR
        
        # 检查数据表是否存在
        if not GL_LIVE_TABLE_DIR.exists() or not any(GL_LIVE_TABLE_DIR.glob("*.json")):
            await es_switch_source.finish(
                "国际服live数据表不存在，请等待自动下载完成或手动触发更新检查"
            )
    else:  # gl_review
        # 国际服review
        CURRENT_DATA_SOURCE[group_id]["server"] = "global"
        CURRENT_DATA_SOURCE[group_id]["type"] = "review"
        CURRENT_DATA_SOURCE[group_id]["json_path"] = GL_REVIEW_TABLE_DIR
        
        # 检查数据表是否存在
        if not GL_REVIEW_TABLE_DIR.exists() or not any(GL_REVIEW_TABLE_DIR.glob("*.json")):
            await es_switch_source.finish(
                "国际服review数据表不存在，请等待自动下载完成或手动触发更新检查"
            )

    # 使用DATA_DIR中的别名文件
    CURRENT_DATA_SOURCE[group_id]["hero_alias_file"] = (
        CONFIG_DIR / f"{CURRENT_DATA_SOURCE[group_id]['type']}_hero_alias.yaml"
    )

    try:
        # 保存配置到文件
        await save_data_source_config(CURRENT_DATA_SOURCE)
    except Exception as e:
        if not isinstance(e, FinishedException):
            import traceback

            error_location = traceback.extract_tb(e.__traceback__)[-1]
            logger.error(
                f"切换数据源时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )

    server_name = {"global": "国际服", "cn": "国服", "jp": "日服"}.get(
        CURRENT_DATA_SOURCE[group_id]["server"], CURRENT_DATA_SOURCE[group_id]["server"]
    )
    await es_switch_source.finish(
        f"已为当前群组切换到 {server_name} - {CURRENT_DATA_SOURCE[group_id]['type']} 数据源"
    )
