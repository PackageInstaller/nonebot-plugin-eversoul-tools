from ..library.utils import *


@es_notice.handle()
async def handle(bot: Bot, event: Event):
    try:
        # 获取版本号
        try:
            result = playstore_app(app_id="com.kakaogames.eversoul", lang="en", country="kr")
            version = result["version"]
        except Exception as e:
            await es_notice.finish(f"获取版本号失败: {str(e)}")
            return

        # 构建API链接
        api_url = f"https://gc-infodesk-zinny3.kakaogames.com/v2/app?appId=743491&appVer={version}&market=googlePlay&sdkVer=3.19.0&os=android&lang=zh-hant&country=tw&sdkState=INIT"

        # 发送请求获取通知
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status != 200:
                    await es_notice.finish("获取通知失败")
                    return
                
                data = await response.json()
                
                if data["status"] != 200:
                    await es_notice.finish("获取通知失败")
                    return

                notices = data["content"].get("notices", [])
                if not notices:
                    await es_notice.finish("当前没有通知", reply_message=True)
                    return

                # 处理通知信息
                notice_messages = []
                for notice in notices:
                    notice_type = notice.get("noticeType", "未知类型")
                    content = notice.get("msg", "无内容")
                    message = [
                        f"【通知类型】{notice_type}\n",
                        f"【通知内容】\n{content}\n"
                    ]
                    
                    # 如果有链接，添加到消息中
                    if notice.get("link"):
                        message.append(f"【详情链接】{notice['link']}\n")
                    
                    notice_messages.append("\n".join(message))

                try:
                    await bot.send(event, Message(notice_messages), reply_message=True)
                except Exception as e:
                    logger.error(f"发送消息失败: {str(e)}")

    except Exception as e:
        if not isinstance(e, FinishedException):
            import traceback
            error_location = traceback.extract_tb(e.__traceback__)[-1]
            logger.error(
                f"处理通知信息时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )

