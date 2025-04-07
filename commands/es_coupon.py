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
    # 是否已绑定
    user_data = await EversoulUser.get_user(int(user_id))
    
    if not user_data:
        # 用户未绑定，发送绑定提示
        bind_msg = (
            f"未绑定游戏账号，无法进行兑换。\n"
            "请使用 es绑定 [地区+ID] 绑定账号"
        )
        await es_coupon.finish(message=bind_msg, reply_message=True)
    else:
        # 用户已绑定，直接执行兑换流程
        app_id = user_data.get("app_id")
        player_id = user_data.get("player_id")
        
        
    # 显示用户信息
    await es_coupon.send(
        message=f"开始兑换，请耐心等待...\n共有{len(coupon_codes)}个兑换码需要处理",
        reply_message=True
    )
    
    # 批量兑换所有码
    results = []
    for i, code in enumerate(coupon_codes):
        success, result = await redeem_coupon(app_id, player_id, code)
        status = "成功" if success else "失败"
        results.append(f"{code}: {status}\n{result}")
    
    # 汇总结果
    summary = "\n\n".join(results)

    await es_coupon.finish(f"{summary}", reply_message=True)