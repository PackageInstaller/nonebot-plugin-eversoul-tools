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
                messages = []
                for notice in notices:
                    # 转换时间戳为datetime对象
                    start_time = datetime.fromtimestamp(notice["periodBeginTime"] / 1000)
                    end_time = datetime.fromtimestamp(notice["periodEndTime"] / 1000)
                    
                    # 格式化时间
                    start_time_str = start_time.strftime("%Y-%m-%d %H:%M")
                    end_time_str = end_time.strftime("%Y-%m-%d %H:%M")
                    
                    # 获取通知类型
                    notice_type = notice.get("noticeType", "未知类型")
                    
                    # 获取通知内容
                    content = notice.get("msg", "无内容")
                    
                    # 构建消息
                    message = [
                        f"【通知类型】{notice_type}\n",
                        # f"【开始时间】{start_time_str}\n",
                        # f"【结束时间】{end_time_str}\n",
                        f"【通知内容】\n{content}\n"
                    ]
                    
                    # 如果有链接，添加到消息中
                    if notice.get("link"):
                        message.append(f"【详情链接】{notice['link']}\n")
                    
                    messages.append("\n".join(message))

                try:
                    await bot.send(event, Message(message), reply_message=True)
                except Exception as e:
                    logger.error(f"发送消息失败: {str(e)}")
                    await es_notice.finish(f"发送消息失败: {str(e)}")

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
            await es_notice.finish(f"处理通知信息时发生错误: {str(e)}")

