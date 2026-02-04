from ..library.utils import *


@es_love_level.handle()
async def handle(bot: Bot, event: Event):
    """处理好感等级信息查询"""
    try:
        group_id = get_group_id(event)
        data = await load_json_data(group_id, command_name="es好感等级信息")
        if not data.get("love_level") or not data["love_level"].get("json"):
            await es_love_level.finish("未找到好感等级数据，请检查数据源配置！")
        html = await generate_love_level_html(data)
        pic = await html_to_pic(html, viewport={"width": 1400, "height": 1800})

        await es_love_level.finish(MessageSegment.image(pic))

    except Exception as e:
        if not isinstance(e, FinishedException):
            import traceback

            error_location = traceback.extract_tb(e.__traceback__)[-1]
            logger.error(
                f"处理好感等级信息时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )
            await es_love_level.finish(f"处理好感等级信息时发生错误: {str(e)}")
