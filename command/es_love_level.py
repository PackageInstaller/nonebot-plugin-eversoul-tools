from ..library.utils import *


@es_love_level.handle()
async def handle(bot: Bot, event: Event):
    """处理好感等级信息查询"""
    try:
        # 获取群组ID
        group_id = 0
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
        
        # 加载游戏数据
        data = await load_json_data(group_id)
        
        # 检查是否有好感等级数据
        if not data.get("love_level") or not data["love_level"].get("json"):
            await es_love_level.finish("未找到好感等级数据，请检查数据源配置！")
        
        # 生成好感等级信息HTML
        html = await generate_love_level_html(data)
        
        # 转换为图片
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