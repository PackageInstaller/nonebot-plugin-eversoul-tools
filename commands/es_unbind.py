from ..libraries.utils import *


@es_unbind.handle()
async def handle_unbind(bot: Bot, event: Event):
    """处理解绑账号指令"""

    user_id = event.get_user_id()
    
    # 是否已绑定
    user_data = await EversoulUser.get_user(int(user_id))
    
    if not user_data:
        await es_unbind.finish(message="您尚未绑定过账号，请使用 es绑定账号 命令进行绑定", reply_message=True)
    
    success = await EversoulUser.delete_user(int(user_id))
    
    if success:
        await es_unbind.finish(message="解绑成功！您可以使用 es绑定账号 命令重新绑定其他账号", reply_message=True)
    else:
        await es_unbind.finish(message="解绑失败，请联系管理员", reply_message=True )