from ..library.utils import *


es_account_info = on_command("es账号信息", aliases={"es账号列表", "es查看账号"}, priority=5, block=True)

@es_account_info.handle()
async def handle_account_info(bot: Bot, event: Event):
    """
    处理查询账号信息命令
    参数:
        bot: Bot 机器人对象
        event: Event 事件对象
    返回:
        None
    异常:
        None

    handle account info command
    args:
        bot
        event
    return:
        None
    exception:
        None
    """
    user_id = event.get_user_id()
    
    # 获取用户所有账号
    user_accounts = await EversoulUser.get_all_user_accounts(int(user_id))
    
    if not user_accounts:
        await es_account_info.finish(message="您尚未绑定过账号，请使用 es绑定账号 命令进行绑定", reply_message=True)
    
    
    # 构建账号信息列表
    account_info_list = []
    for i, account in enumerate(user_accounts):
        server_name = SERVER_NAME_MAPPING.get(APP_ID_TO_SERVER_NAME.get(account["app_id"], "未知"), account["app_id"])
        
        account_info = f"{i+1}. {server_name} - {account['player_id']}"
        account_info_list.append(account_info)
    
    # 构建回复消息
    reply_msg = f"您绑定的账号如下 (共{len(user_accounts)}个):\n\n"
    reply_msg += "\n".join(account_info_list)
    
    await es_account_info.finish(message=reply_msg, reply_message=True)
