from ..libraries.utils import *

# 保存当前正在等待绑定的用户
# 键是用户ID，值是绑定过期时间和其他信息
BINDING_USERS = {}


@es_coupon.handle()
async def handle_coupon(bot: Bot, event: Event, args: Message = CommandArg()):
    """处理兑换码指令"""

    user_id = event.get_user_id()
    coupon_input = args.extract_plain_text().strip()
    
    
    if not coupon_input:
        await es_coupon.finish("请输入兑换码！用法：es兑换码 [兑换码1] [兑换码2] ...")
    
    # 分割多个兑换码（以空格分隔）
    coupon_codes = coupon_input.split()
    
    # 获取用户的所有账号
    user_accounts = await EversoulUser.get_all_user_accounts(int(user_id))
    
    if not user_accounts:
        # 用户未绑定，发送绑定提示
        bind_msg = (
            f"未绑定游戏账号，无法进行兑换。\n"
            "请使用 es绑定 [地区+ID] 绑定账号"
        )
        await es_coupon.finish(message=bind_msg, reply_message=True)
    
    # 显示用户信息
    accounts_count = len(user_accounts)
    await es_coupon.send(
        message=f"开始兑换，请耐心等待...\n为您的{accounts_count}个账号兑换{len(coupon_codes)}个兑换码",
        reply_message=True
    )
    
    # 准备合并转发消息
    forward_messages = []
    
    # 添加兑换开始信息
    forward_messages.append({
        "type": "node",
        "data": {
            "name": "永恒灵魂助手",
            "uin": event.self_id,
            "content": f"兑换码兑换结果 ({len(coupon_codes)}个兑换码，{accounts_count}个账号)"
        }
    })
    
    # 为每个账号执行兑换
    for account_index, account in enumerate(user_accounts):
        app_id = account.get("app_id")
        player_id = account.get("player_id")
        
        # 获取服务器名称
        server_name = "未知服务器"
        for code, id_value in SERVER_APP_ID_MAPPING.items():
            if id_value == app_id:
                server_name = SERVER_NAME_MAPPING.get(code, code)
                break
        
        # 账号信息
        account_info = f"账号{account_index+1}/{accounts_count}: {server_name}服务器, ID: {player_id}"
        forward_messages.append({
            "type": "node",
            "data": {
                "name": "永恒灵魂助手",
                "uin": event.self_id,
                "content": f"开始为 {account_info} 兑换"
            }
        })
        
        # 批量兑换所有码
        account_results = []
        for i, code in enumerate(coupon_codes):
            success, result = await redeem_coupon(app_id, player_id, code)
            status = "✅成功" if success else "❌失败"
            account_results.append(f"{code}: {status}\n{result}")
        
        # 将每个兑换码的结果加入合并转发
        for i, result in enumerate(account_results):
            forward_messages.append({
                "type": "node",
                "data": {
                    "name": "永恒灵魂助手",
                    "uin": event.self_id,
                    "content": result
                }
            })
    
    # 添加兑换完成信息
    forward_messages.append({
        "type": "node",
        "data": {
            "name": "永恒灵魂助手",
            "uin": event.self_id,
            "content": f"兑换完成！共{accounts_count}个账号，{len(coupon_codes)}个兑换码"
        }
    })
    
    # 发送合并转发消息
    if isinstance(event, GroupMessageEvent):
        await bot.call_api(
            "send_group_forward_msg",
            group_id=event.group_id,
            messages=forward_messages
        )
    else:
        await bot.call_api(
            "send_private_forward_msg",
            user_id=int(user_id),
            messages=forward_messages
        )
    
    await es_coupon.finish()