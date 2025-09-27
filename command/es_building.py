from ..library.utils import *


@es_building.handle()
async def handle(bot: Bot, event: Event):
    """处理建筑信息查询"""
    try:
        group_id = 0
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
        
        data = await load_json_data(group_id)
        
        if not data.get("town_object") or not data["town_object"].get("json"):
            await es_building.finish("未找到建筑数据，请检查数据源配置！")
        
        if not data.get("town_buff") or not data["town_buff"].get("json"):
            await es_building.finish("未找到建筑buff数据，请检查数据源配置！")
        
        html = await generate_building_html(data)
        
        pic = await html_to_pic(html, viewport={"width": 1400, "height": 1000})
        
        await es_building.finish(MessageSegment.image(pic))

    except Exception as e:
        if not isinstance(e, FinishedException):
            import traceback
            error_location = traceback.extract_tb(e.__traceback__)[-1]
            logger.error(
                f"处理建筑信息时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )
            await es_building.finish(f"处理建筑信息时发生错误: {str(e)}")
