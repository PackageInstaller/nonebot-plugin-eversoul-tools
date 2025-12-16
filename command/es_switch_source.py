from ..library.utils import *


@es_switch_source.handle()
async def handle(event: GroupMessageEvent, args: Message = CommandArg()):
    # 获取参数
    args_str = str(args).strip().lower()

    # 获取群组ID
    group_id = str(event.group_id)

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

        if plugin_config.eversoul_cn_live_path:
            CURRENT_DATA_SOURCE[group_id]["json_path"] = Path(
                plugin_config.eversoul_cn_live_path
            )
        else:
            await es_switch_source.finish(
                "未配置国服live数据源路径，请在env中设置eversoul_cn_live_path"
            )
    elif args_str == "cn_review":
        # 国服review
        CURRENT_DATA_SOURCE[group_id]["server"] = "cn"
        CURRENT_DATA_SOURCE[group_id]["type"] = "review"

        if plugin_config.eversoul_cn_review_path:
            CURRENT_DATA_SOURCE[group_id]["json_path"] = Path(
                plugin_config.eversoul_cn_review_path
            )
        else:
            await es_switch_source.finish(
                "未配置国服review数据源路径，请在env中设置eversoul_cn_review_path"
            )
    elif args_str == "jp_live":
        # 日服live
        CURRENT_DATA_SOURCE[group_id]["server"] = "jp"
        CURRENT_DATA_SOURCE[group_id]["type"] = "live"

        if plugin_config.eversoul_jp_live_path:
            CURRENT_DATA_SOURCE[group_id]["json_path"] = Path(
                plugin_config.eversoul_jp_live_path
            )
        else:
            await es_switch_source.finish(
                "未配置日服live数据源路径，请在env中设置eversoul_jp_live_path"
            )
    elif args_str == "jp_review":
        # 日服review
        CURRENT_DATA_SOURCE[group_id]["server"] = "jp"
        CURRENT_DATA_SOURCE[group_id]["type"] = "review"

        if plugin_config.eversoul_jp_review_path:
            CURRENT_DATA_SOURCE[group_id]["json_path"] = Path(
                plugin_config.eversoul_jp_review_path
            )
        else:
            await es_switch_source.finish(
                "未配置日服review数据源路径，请在env中设置eversoul_jp_review_path"
            )
    elif args_str == "gl_live":
        # 国际服live
        CURRENT_DATA_SOURCE[group_id]["server"] = "global"
        CURRENT_DATA_SOURCE[group_id]["type"] = "live"

        if plugin_config.eversoul_gl_live_path:
            CURRENT_DATA_SOURCE[group_id]["json_path"] = Path(
                plugin_config.eversoul_gl_live_path
            )
        else:
            await es_switch_source.finish(
                "未配置国际服live数据源路径，请在env中设置eversoul_gl_live_path"
            )
    else:  # gl_review
        # 国际服review
        CURRENT_DATA_SOURCE[group_id]["server"] = "global"
        CURRENT_DATA_SOURCE[group_id]["type"] = "review"

        if plugin_config.eversoul_gl_review_path:
            CURRENT_DATA_SOURCE[group_id]["json_path"] = Path(
                plugin_config.eversoul_gl_review_path
            )
        else:
            await es_switch_source.finish(
                "未配置国际服review数据源路径，请在env中设置eversoul_gl_review_path"
            )

    # 使用DATA_DIR中的别名文件
    CURRENT_DATA_SOURCE[group_id]["hero_alias_file"] = (
        CONFIG_DIR / f"{CURRENT_DATA_SOURCE[group_id]['type']}_hero_aliases.yaml"
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
