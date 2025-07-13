from ..library.utils import *


emoji_vote = on_notice(priority=1, block=False)
unbind_votes: Dict[str, Dict] = {}



@es_unbind.handle()
async def handle_unbind(bot: Bot, event: Event):
    """处理解绑账号指令"""

    user_id = event.get_user_id()
    
    # 获取用户所有账号
    user_accounts = await EversoulUser.get_all_user_accounts(int(user_id))
    
    if not user_accounts:
        await es_unbind.finish(message="您尚未绑定过账号，请使用 es绑定账号 命令进行绑定", reply_message=True)
    
    # 多个账号，显示账号列表并等待用户选择
    emoji_list = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    emoji_ids = ["394", "417", "421", "432", "364", "366", "362", "397", "361", "382"]  # 表情ID序列
    account_list = []
    
    for i, account in enumerate(user_accounts):
        if i < len(emoji_list):
            # 获取服务器名称
            server_name = SERVER_NAME_MAPPING.get(APP_ID_TO_SERVER_NAME.get(account["app_id"], "未知"), account["app_id"])
            account_list.append(f"{emoji_list[i]} {server_name} {account['player_id']}")
    
    account_list.append("✨ 确认解绑")
    account_list.append("❎ 取消操作")
    
    msg = "请选择要解绑的账号：\n\n"
    msg += "\n".join(account_list)
    
    # 发送消息并记录投票状态
    message = await es_unbind.send(message=msg, reply_message=True)
    message_id = message["message_id"]
    
    # 初始化投票状态
    unbind_votes[message_id] = {
        "user_id": user_id,
        "accounts": user_accounts,
        "selected": set(),  # 已选择的账号索引
        "confirmed": False,
        "cancelled": False,
        "message_id": message_id,
        "emoji_to_index": {emoji_ids[i]: i for i in range(min(len(user_accounts), len(emoji_ids)))}  # 表情ID到索引的映射
    }
    
    for i in range(min(len(user_accounts), len(emoji_ids))):
        await asyncio.sleep(0.2)
        await bot.call_api("set_msg_emoji_like", message_id=message_id, emoji_id=emoji_ids[i])
    
    # 添加确认和取消表情
    await asyncio.sleep(0.2)
    await bot.call_api("set_msg_emoji_like", message_id=message_id, emoji_id="10024")  # 确认
    await asyncio.sleep(0.2)
    await bot.call_api("set_msg_emoji_like", message_id=message_id, emoji_id="10060")  # 取消
    
    asyncio.create_task(unbind_timer(bot, event, message_id, 60))

async def unbind_timer(bot: Bot, event: Event, message_id: str, timeout: int):
    """解绑投票定时器"""
    await asyncio.sleep(timeout)
    
    if message_id in unbind_votes:
        vote_data = unbind_votes[message_id]
        
        # 如果已经确认或取消，不执行任何操作
        if vote_data["confirmed"] or vote_data["cancelled"]:
            return
        
        # 超时，自动取消
        await bot.send(event, "解绑操作超时，已自动取消。", reply_message=True)
        unbind_votes.pop(message_id, None)

@emoji_vote.handle()
async def handle_unbind_emoji(bot: Bot, event: NoticeEvent):
    """处理解绑表情响应"""
    try:
        if event.notice_type == "group_msg_emoji_like":
            message_id = event.dict().get('message_id')
            user_id = str(event.dict().get('user_id'))
            likes = event.dict().get('likes')
            if not likes:
                return
            emoji_id = likes[0].get('emoji_id')
            
            # 检查是否是解绑投票
            if message_id in unbind_votes:
                vote_data = unbind_votes[message_id]
                
                # 检查是否是投票发起人
                if user_id != vote_data["user_id"]:
                    return
                
                # 处理表情选择
                if emoji_id == "10024":  # 确认
                    if not vote_data["selected"]:
                        await bot.send(event, "您尚未选择任何账号，请先选择要解绑的账号。", reply_message=True)
                        return
                    
                    # 确认解绑
                    vote_data["confirmed"] = True
                    await finalize_unbind(bot, event, vote_data)
                    
                elif emoji_id == "10060":  # 取消
                    vote_data["cancelled"] = True
                    await bot.send(event, "已取消解绑操作。", reply_message=True)
                    unbind_votes.pop(message_id, None)
                    
                elif emoji_id in vote_data["emoji_to_index"]:  # 数字选择
                    # 使用emoji_to_index映射获取选择的索引
                    index = vote_data["emoji_to_index"][emoji_id]
                    accounts = vote_data["accounts"]
                    
                    if index < len(accounts):
                        if index in vote_data["selected"]:
                            vote_data["selected"].remove(index)
                        else:
                            vote_data["selected"].add(index)
    except Exception as e:
        logger.error(f"处理解绑表情响应时发生错误: {e}")

async def finalize_unbind(bot: Bot, event: Event, vote_data: Dict):
    """完成解绑操作"""
    try:
        user_id = vote_data["user_id"]
        selected_indices = vote_data["selected"]
        accounts = vote_data["accounts"]
        
        # 解绑选中的账号
        success_count = 0
        fail_count = 0
        unbind_results = []
        
        for index in selected_indices:
            account = accounts[index]
            success = await EversoulUser.delete_specific_account(int(user_id), account["player_id"])
            
            if success:
                success_count += 1
                server_name = SERVER_NAME_MAPPING.get(APP_ID_TO_SERVER_NAME.get(account["app_id"], "未知"), account["app_id"])
                unbind_results.append(f"✅ {server_name} {account['player_id']}")
            else:
                fail_count += 1
                server_name = SERVER_NAME_MAPPING.get(APP_ID_TO_SERVER_NAME.get(account["app_id"], "未知"), account["app_id"])
                unbind_results.append(f"❎ {server_name} {account['player_id']}")
        
        # 构建结果消息
        result_msg = f"解绑结果：\n"
        result_msg += "\n".join(unbind_results)
        
        await bot.send(event, result_msg, reply_message=True)
        
        # 清理投票状态
        unbind_votes.pop(vote_data["message_id"], None)
        
    except Exception as e:
        logger.error(f"完成解绑操作时发生错误: {e}")
        await bot.send(event, "解绑过程中发生错误，请联系管理员", reply_message=True)