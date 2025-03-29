from nonebot import require, on_command
from nonebot.exception import FinishedException
from zhenxun.services.log import logger
from nonebot.adapters.onebot.v11 import (
    Bot,
    Event,
    MessageSegment,
    GroupMessageEvent
)
require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import html_to_pic
from ..libraries.es_utils import *

es_potential_info = on_command("es潜能信息", priority=0, block=True)


@es_potential_info.handle()
async def handle_potential_info(bot: Bot, event: Event):
    """处理潜能信息查询"""
    try:
        # 获取群组ID
        group_id = None
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
        data = load_json_data(group_id)
        # 生成潜能信息HTML
        html = await generate_potential_html(data)
        # 转换为图片
        pic = await html_to_pic(html, viewport={"width": 1000, "height": 10})
        await es_potential_info.finish(MessageSegment.image(pic))

    except Exception as e:
        if not isinstance(e, FinishedException):
            import traceback
            error_location = traceback.extract_tb(e.__traceback__)[-1]
            logger.error(
                f"处理潜能信息时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )
            await es_potential_info.finish(f"处理潜能信息时发生错误: {str(e)}")