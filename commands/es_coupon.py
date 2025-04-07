from ..libraries.utils import *

# 保存当前正在等待绑定的用户
# 键是用户ID，值是绑定过期时间和其他信息
BINDING_USERS = {}


@es_coupon.handle()
async def handle_coupon(bot: Bot, event: Event, args: Message = CommandArg()):
    """处理兑换码指令"""

    user_id = event.get_user_id()
    coupon_input = args.extract_plain_text().strip()
    
    group_id = None
    if isinstance(event, GroupMessageEvent):
        group_id = event.group_id
    
    if not coupon_input:
        await es_coupon.finish("请输入兑换码！用法：es兑换码 [兑换码1] [兑换码2] ...")
    
    # 分割多个兑换码（以空格分隔）
    coupon_codes = coupon_input.split()
    # 是否已绑定
    user_data = await EversoulUser.get_user(int(user_id))
    
    if not user_data:
        # 用户未绑定，发送绑定提示
        bind_msg = (
            f"未绑定游戏账号，无法进行兑换。\n"
            "请按照以下格式绑定账号：\n"
            "【地区+ID】，例如：kr123456789012\n\n"
            "支持的地区代码：\n"
            "asia - 亚服\n"
            "kr - 韩服\n"
            "en - 欧美服\n\n"
            "ID必须是12位纯数字"
        )
        await es_coupon.send(bind_msg)
        
        # 设置超时时间（60秒）
        timeout_seconds = 60
        
        # 获取当前时间并计算过期时间
        import time
        current_time = time.time()
        expire_time = current_time + timeout_seconds
        
        # 记录用户正在绑定状态及过期时间，同时保存群组ID用于响应
        BINDING_USERS[user_id] = {
            "expire_time": expire_time,
            "coupon_codes": coupon_codes,
            "group_id": group_id
        }
        
        # 创建一个任务用于自动清理过期的绑定记录
        async def clean_expired_binding():
            await asyncio.sleep(timeout_seconds)
            if user_id in BINDING_USERS:
                binding_info = BINDING_USERS[user_id]
                del BINDING_USERS[user_id]
                
                # 获取群组ID，确保我们在群聊中回复
                try_group_id = binding_info.get("group_id")
                if try_group_id:
                    try:
                        await bot.send_group_msg(
                            group_id=try_group_id,
                            message=f"绑定超时，请重新绑定",
                            reply=True
                        )
                    except Exception as e:
                        logger.error(f"发送超时消息到群组失败: {e}")
        
        # 启动超时清理任务
        asyncio.create_task(clean_expired_binding())
        
        # 提示用户超时时间
        await es_coupon.send(f"请在{timeout_seconds}秒内回复您的游戏ID信息...")
        return
    
    # 用户已绑定，直接执行兑换流程
    app_id = user_data.get("app_id")
    player_id = user_data.get("player_id")
    
    # 获取服务器名称
    server_name = "未知服务器"
    for code, id_value in SERVER_APP_ID_MAPPING.items():
        if id_value == app_id:
            server_name = SERVER_NAME_MAPPING.get(code, code)
            break
    
    # 显示用户信息
    await es_coupon.send(
        f"使用账号 {server_name}/{player_id} 进行兑换...\n"
        f"共有{len(coupon_codes)}个兑换码需要处理"
    )
    
    # 批量兑换所有码
    results = []
    for i, code in enumerate(coupon_codes):
        success, result = await redeem_coupon(app_id, player_id, code)
        status = "成功" if success else "失败"
        results.append(f"兑换码 {i+1}/{len(coupon_codes)} [{code}]: {status}\n{result}")
    
    # 汇总结果
    summary = "\n\n".join(results)
    
    # 如果结果太长，可能需要分多条消息发送
    if len(summary) > 1000:
        # 分段发送结果
        chunks = []
        current_chunk = ""
        
        for result in results:
            if len(current_chunk) + len(result) + 2 > 1000:
                chunks.append(current_chunk)
                current_chunk = result
            else:
                if current_chunk:
                    current_chunk += "\n\n" + result
                else:
                    current_chunk = result
        
        if current_chunk:
            chunks.append(current_chunk)
        
        # 发送第一部分结果
        if chunks:
            await es_coupon.send(f"兑换结果 (1/{len(chunks)}):\n{chunks[0]}")
            
            # 发送剩余部分
            for i in range(1, len(chunks)):
                await bot.send(event, f"兑换结果 ({i+1}/{len(chunks)}):\n{chunks[i]}")
    else:
        # 一次性发送所有结果
        await es_coupon.finish(f"兑换结果:\n{summary}")


# 创建一个专门处理绑定消息的matcher
binding_handler = on_message(priority=1, block=False)

@binding_handler.handle()
async def handle_binding_response(bot: Bot, event: MessageEvent):
    user_id = event.get_user_id()
    
    # 检查用户是否在等待绑定状态
    if user_id not in BINDING_USERS:
        return
    
    # 检查是否已过期
    import time
    current_time = time.time()
    binding_info = BINDING_USERS[user_id]
    
    if current_time > binding_info["expire_time"]:
        # 已过期，清理记录
        del BINDING_USERS[user_id]
        return
    
    # 获取绑定信息
    coupon_codes = binding_info["coupon_codes"]
    group_id = binding_info.get("group_id")
    
    # 移除用户的绑定记录，防止下一条消息被误处理
    del BINDING_USERS[user_id]
    
    # 获取用户输入
    input_text = event.get_message().extract_plain_text().strip()
    logger.info(f"收到用户 {user_id} 的绑定响应: {input_text}")
    
    # 解析服务器和ID
    server_code, player_id = parse_server_id(input_text)
    
    # 根据用户是在群聊还是私聊中，选择发送消息的方式
    async def send_response(message: str):
        try:
            if group_id:
                # 在群聊中回复
                await bot.send_group_msg(group_id=group_id, message=message)
            else:
                # 尝试通过事件回复
                await bot.send(event, message)
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            # 如果都失败，尝试直接在当前事件的上下文中回复
            try:
                if isinstance(event, GroupMessageEvent):
                    await bot.send_group_msg(group_id=event.group_id, message=message)
            except Exception as e2:
                logger.error(f"备用发送方式也失败: {e2}")
    
    # 验证输入
    if not server_code or not player_id:
        await send_response(
            f"输入格式错误！请按照格式：【地区+ID】\n"
            "例如：kr123456789012\n"
            "请重新绑定。"
        )
        return
    
    # 获取app_id
    app_id = SERVER_APP_ID_MAPPING.get(server_code)
    if not app_id:
        await send_response(f"不支持的服务器代码：{server_code}")
        return
    
    # 保存用户信息
    success = await EversoulUser.add_user(int(user_id), app_id, player_id)
    if not success:
        await send_response("数据库操作失败，请联系管理员")
        return
    
    # 显示绑定成功信息
    await send_response(
        f"绑定成功！\n"
        f"服务器：{SERVER_NAME_MAPPING.get(server_code, server_code)}\n"
        f"玩家ID：{player_id}\n"
        f"即将兑换{len(coupon_codes)}个兑换码..."
    )
    
    # 批量兑换所有码
    results = []
    for i, code in enumerate(coupon_codes):
        success, result = await redeem_coupon(app_id, player_id, code)
        status = "成功" if success else "失败"
        results.append(f"兑换码 {i+1}/{len(coupon_codes)} [{code}]: {status}\n{result}")
    
    # 汇总结果
    summary = "\n\n".join(results)
    
    # 如果结果太长，可能需要分多条消息发送
    if len(summary) > 1000:
        # 分段发送结果
        chunks = []
        current_chunk = ""
        
        for result in results:
            if len(current_chunk) + len(result) + 2 > 1000:
                chunks.append(current_chunk)
                current_chunk = result
            else:
                if current_chunk:
                    current_chunk += "\n\n" + result
                else:
                    current_chunk = result
        
        if current_chunk:
            chunks.append(current_chunk)
        
        # 发送第一部分结果
        if chunks:
            await send_response(f"兑换结果 (1/{len(chunks)}):\n{chunks[0]}")
            
            # 发送剩余部分
            for i in range(1, len(chunks)):
                try:
                    if group_id:
                        await bot.send_group_msg(group_id=group_id, message=f"兑换结果 ({i+1}/{len(chunks)}):\n{chunks[i]}")
                    else:
                        await bot.send_private_msg(user_id=int(user_id), message=f"兑换结果 ({i+1}/{len(chunks)}):\n{chunks[i]}")
                except Exception as e:
                    logger.error(f"发送分段结果失败: {e}")
    else:
        # 一次性发送所有结果
        await send_response(f"兑换结果:\n{summary}") 