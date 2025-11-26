from ..library.utils import *


@es_check_datasource.handle()
async def handle():
    """处理手动检查数据源的命令"""
    await es_check_datasource.send("正在检查数据源文件变化...")
    
    try:
        result = await check_and_regenerate_aliases(manual_trigger=True)
        
        message_parts = ["【数据源检查结果】\n"]
        
        # 显示监视的目录
        if result["directories_watched"]:
            message_parts.append(f"监视的数据源: {', '.join(result['directories_watched'])}")
        else:
            message_parts.append("⚠️ 未配置任何数据源")
        
        message_parts.append("")
        
        # 显示变化详情
        if result["changes"]:
            message_parts.append("检查详情:")
            for change in result["changes"]:
                message_parts.append(f"• {change}")
        else:
            message_parts.append("✅ 未检测到文件变化")
        
        # 显示错误信息
        if result["error"]:
            message_parts.append(f"\n❌ 错误: {result['error']}")
        elif result["has_changes"]:
            message_parts.append("\n✅ 别名文件已重新生成")
        
        await es_check_datasource.finish("\n".join(message_parts))
    except Exception as e:
        logger.error(f"检查数据源时出错: {e}")
        await es_check_datasource.finish(f"检查数据源时出错: {str(e)}")

