from ..library.utils import *


@es_zodiac.handle()
async def handle(bot: Bot, event: Event):
    """处理星座信息查询"""
    try:
        # 获取群组ID
        group_id = 0
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
        
        # 加载游戏数据
        data = await load_json_data(group_id)
        # 生成星座信息HTML
        html = await generate_zodiac_html(data)
        
        # 转换为图片
        pic = await html_to_pic(html, viewport={"width": 1200, "height": 1600})
        
        await es_zodiac.finish(MessageSegment.image(pic))

    except Exception as e:
        if not isinstance(e, FinishedException):
            import traceback
            error_location = traceback.extract_tb(e.__traceback__)[-1]
            logger.error(
                f"处理星座信息时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )
            await es_zodiac.finish(f"处理星座信息时发生错误: {str(e)}")