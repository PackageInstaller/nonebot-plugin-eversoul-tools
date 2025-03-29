from pathlib import Path
from nonebot import on_command
from nonebot.exception import FinishedException
from nonebot.permission import SUPERUSER
from zhenxun.services.log import logger
from nonebot.adapters.onebot.v11 import (
    GROUP_ADMIN,
    GROUP_OWNER,
    GroupMessageEvent
)
from ..libraries.es_utils import *
from ..config import *

es_switch_source = on_command("es数据源切换", priority=0, permission=(SUPERUSER | GROUP_ADMIN | GROUP_OWNER), block=True)


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
    
    # 更新群组配置
    if group_id not in CURRENT_DATA_SOURCE:
        # 如果群组配置不存在，基于默认配置创建一个
        CURRENT_DATA_SOURCE[group_id] = CURRENT_DATA_SOURCE["default"].copy()
    
    # 更新群组的数据源类型
    CURRENT_DATA_SOURCE[group_id]["type"] = args
    CURRENT_DATA_SOURCE[group_id]["json_path"] = Path(f"/home/rikka/Eversoul/{args}_jsons")
    # 使用DATA_DIR中的别名文件
    CURRENT_DATA_SOURCE[group_id]["hero_alias_file"] = DATA_DIR / f"{args}_hero_aliases.yaml"
    
    try:
        # 保存配置到文件
        save_data_source_config(CURRENT_DATA_SOURCE)
        current_keys = list(CURRENT_DATA_SOURCE.keys())
        # 重新加载配置
        load_data_source_config()
        # 验证配置是否正确加载
        new_keys = list(CURRENT_DATA_SOURCE.keys())
        
        # 确保群组配置被加载
        if group_id not in CURRENT_DATA_SOURCE:
            # 手动添加回配置
            if group_id in current_keys:
                with open(DATA_SOURCE_CONFIG, "r", encoding="utf-8") as f:
                    saved_config = yaml.safe_load(f)
                if saved_config and group_id in saved_config:
                    group_config = saved_config[group_id]
                    if "json_path" in group_config:
                        group_config["json_path"] = Path(group_config["json_path"])
                    if "hero_alias_file" in group_config:
                        group_config["hero_alias_file"] = Path(group_config["hero_alias_file"])
                    CURRENT_DATA_SOURCE[group_id] = group_config
        
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