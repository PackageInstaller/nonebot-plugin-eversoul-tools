from ..library.utils import *


@es_bind.handle()
async def handle(bot: Bot, event: Event, args: Message = CommandArg()):
    """处理绑定账号指令"""

    server_id_text = args.extract_plain_text().strip()

    if not server_id_text:
        help_msg = (
            "请按照以下格式绑定账号：\n"
            "es绑定 [地区+ID]\n"
            "例如：es绑定 kr734521179911(韩服加我!)\n"
            "支持的地区代码：\n"
            "asia - 亚服\n"
            "kr - 韩服\n"
            "en - 欧美服"
        )
        await es_bind.finish(message=help_msg, reply_message=True)

    await handle_bind(bot, event, server_id_text)


async def handle_bind(bot: Bot, event: Event, server_id_text: str):
    """处理实际绑定操作"""
    user_id = event.get_user_id()

    server_code, player_id, error_msg = await parse_server_id(server_id_text)

    if not server_code or not player_id:
        help_msg = f"❌ 绑定失败：{error_msg}"
        await es_bind.finish(message=help_msg, reply_message=True)

    app_id = SERVER_APP_ID_MAPPING.get(server_code)
    if not app_id:
        await es_bind.finish(
            message=f"不支持的服务器代码：{server_code}", reply_message=True
        )

    existing_accounts = await EversoulUser.get_all_user_accounts(int(user_id))

    for account in existing_accounts:
        if account.get("player_id") == player_id:
            await es_bind.finish(
                message=f"此账号已经绑定！\n服务器：{SERVER_NAME_MAPPING.get(server_code, server_code)}\n玩家ID：{player_id}",
                reply_message=True,
            )

    success = await EversoulUser.add_user(int(user_id), app_id, player_id)
    if not success:
        await es_bind.finish(message="数据库操作失败，请联系管理员", reply_message=True)

    server_name = SERVER_NAME_MAPPING.get(server_code, server_code)

    message = f"账号绑定成功！\n" f"服务器：{server_name}\n" f"玩家ID：{player_id}"
    await es_bind.finish(message=message, reply_message=True)
