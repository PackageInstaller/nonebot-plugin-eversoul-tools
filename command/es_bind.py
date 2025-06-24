from ..library.utils import *


@es_bind.handle()
async def handle_bind(bot: Bot, event: Event, args: Message = CommandArg()):
    """处理绑定账号指令"""
    
    # 获取输入的账号信息
    server_id_text = args.extract_plain_text().strip()
    
    if not server_id_text:
        # 如果用户未提供参数，显示帮助信息
        help_msg = (
            "请按照以下格式绑定账号：\n"
            "es绑定账号 [地区+ID]\n"
            "例如：es绑定账号 kr734521179911(偷偷夹点私货,我的好友码)\n\n"
            "支持的地区代码：\n"
            "asia - 亚服\n"
            "kr - 韩服\n"
            "en - 欧美服\n"
            "jp - 日服"
        )
        await es_bind.finish(message=help_msg, reply_message=True)
    
    await handle_binding(bot, event, server_id_text)
        

async def handle_binding(bot: Bot, event: Event, server_id_text: str):
    """处理实际绑定操作"""
    user_id = event.get_user_id()
    
    # 解析服务器和ID
    server_code, player_id = parse_server_id(server_id_text)
    
    if not server_code or not player_id:
        await es_bind.finish(
            message="输入格式错误！请按照格式：【地区+ID】\n例如：kr123456789012进行绑定",
            reply_message=True
        )
    
    # 获取app_id
    app_id = SERVER_APP_ID_MAPPING.get(server_code)
    if not app_id:
        await es_bind.finish(message=f"不支持的服务器代码：{server_code}", reply_message=True)
    
    # 检查用户是否已有绑定的账号
    existing_accounts = await EversoulUser.get_all_user_accounts(int(user_id))
    
    # 检查是否绑定了相同playerID的账号
    for account in existing_accounts:
        if account.get("player_id") == player_id:
            await es_bind.finish(
                message=f"此账号已经绑定！\n服务器：{SERVER_NAME_MAPPING.get(server_code, server_code)}\n玩家ID：{player_id}",
                reply_message=True
            )
    
    if server_code == "jp" and datetime.now() > datetime(2025, 8, 20, 0, 0, 0):
        # 日服关服了所以不再支持绑定
        await es_bind.finish(
            message="日服已关服，请使用其他服务器",
            reply_message=True
        )
    
    # 保存用户信息
    success = await EversoulUser.add_user(int(user_id), app_id, player_id)
    if not success:
        await es_bind.finish(message="数据库操作失败，请联系管理员", reply_message=True)
    
    # 绑定成功
    server_name = SERVER_NAME_MAPPING.get(server_code, server_code)
    
    # 添加当前账号列表信息
    total_accounts = len(existing_accounts) + 1
    message = (
        f"账号绑定成功！\n"
        f"服务器：{server_name}\n"
        f"玩家ID：{player_id}\n\n"
    )
    
    if total_accounts > 1:
        message += f"您当前已绑定了{total_accounts}个账号，使用es兑换码将会为所有账号兑换"
    else:
        message += "您可以继续绑定其他服务器账号，兑换码将会为所有账号兑换"
    
    await es_bind.finish(
        message=message,
        reply_message=True
    ) 