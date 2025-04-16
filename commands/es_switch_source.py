from ..libraries.utils import *


@es_switch_source.handle()
async def handle_switch_source(event: GroupMessageEvent):
    # 获取参数
    msg = str(event.get_message()).strip()
    args = msg.replace("es数据源切换", "").strip().lower()
    
    # 获取群组ID
    group_id = str(event.group_id)
    
    if not args:
        await es_switch_source.finish("请指定数据源类型：live 或 review")
    
    if args not in ["live", "review"]:
        await es_switch_source.finish("参数错误！请使用 'live' 或 'review'")
    
    # 确保CURRENT_DATA_SOURCE包含default配置
    if "default" not in CURRENT_DATA_SOURCE:
        CURRENT_DATA_SOURCE["default"] = DEFAULT_CONFIG.copy()
    
    # 记录原始配置
    logger.info(f"切换前CURRENT_DATA_SOURCE: {CURRENT_DATA_SOURCE}")
    
    # 更新群组配置
    if group_id not in CURRENT_DATA_SOURCE:
        # 如果群组配置不存在，基于默认配置创建一个
        CURRENT_DATA_SOURCE[group_id] = CURRENT_DATA_SOURCE["default"].copy()
    
    # 更新群组的数据源类型
    CURRENT_DATA_SOURCE[group_id]["type"] = args
    CURRENT_DATA_SOURCE[group_id]["json_path"] = Path(f"/home/rikka/Eversoul/{args}_jsons")
    # 使用DATA_DIR中的别名文件
    CURRENT_DATA_SOURCE[group_id]["hero_alias_file"] = DATA_DIR / f"{args}_hero_aliases.yaml"
    
    # 记录更新后的配置
    logger.info(f"切换后CURRENT_DATA_SOURCE: {CURRENT_DATA_SOURCE}")
    
    try:
        # 保存配置到文件
        save_data_source_config(CURRENT_DATA_SOURCE)
        logger.info(f"保存后CURRENT_DATA_SOURCE: {CURRENT_DATA_SOURCE}")
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
            await es_switch_source.finish(f"切换数据源时发生错误: {str(e)}")
    
    await es_switch_source.finish(f"已为当前群组切换到{args}数据源")