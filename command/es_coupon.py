from ..library.utils import *


@es_coupon.handle()
async def handle_coupon(bot: Bot, event: Event):
    """处理兑换码指令"""

    user_id = event.get_user_id()
    user_accounts = await EversoulUser.get_all_user_accounts(int(user_id))
    
    if not user_accounts:
        bind_msg = (
            f"未绑定游戏账号，无法进行兑换。\n"
            "请使用 es绑定 [地区+ID] 绑定账号"
        )
        await es_coupon.finish(message=bind_msg, reply_message=True)
    
    try:
        with open(COUPON_YAML_PATH, "r", encoding="utf-8") as f:
            coupon_data = yaml.safe_load(f)
            coupon_items = coupon_data.get("coupons", [])
    except Exception as e:
        logger.error(f"读取兑换码文件失败: {e}")
        await es_coupon.finish(message=f"读取兑换码失败: {str(e)}", reply_message=True)
    
    if not coupon_items:
        await es_coupon.finish(message="当前没有可用的兑换码", reply_message=True)

    current_date = datetime.now().strftime("%Y-%m-%d")
    
    valid_coupons = []
    expired_coupons = []
    
    for item in coupon_items:
        code = item.get("code")
        expiry_date = item.get("date")
        
        if not code:
            continue
            
        if expiry_date and expiry_date < current_date:
            item["expired"] = True
            expired_coupons.append(item)
        else:
            item["expired"] = False
            valid_coupons.append(item)
    
    # 现在只使用有效的兑换码，不再尝试过期的
    all_coupons = valid_coupons
    
    if not all_coupons:
        await es_coupon.finish(message="全部兑换码已过期！", reply_message=True)
    
    # 显示用户信息
    accounts_count = len(user_accounts)
    reply_text = f"开始为您的{accounts_count}个账号兑换{len(all_coupons)}个兑换码，请耐心等待..."
    
    await es_coupon.send(
        message=reply_text,
        reply_message=True
    )
    
    forward_messages = []
    
    all_coupon_histories = {}
    for account in user_accounts:
        player_id = account.get("player_id")
        history = await EversoulUser.get_coupon_history(int(user_id), str(player_id))
        all_coupon_histories[player_id] = history
    
    for account_index, account in enumerate(user_accounts):
        app_id = account.get("app_id")
        player_id = account.get("player_id")
        
        server_code = next((k for k, v in SERVER_APP_ID_MAPPING.items() if v == app_id), "未知")
        server_name = SERVER_NAME_MAPPING.get(server_code, app_id)
        
        account_info = f"账号{account_index+1}/{accounts_count}: {server_name}, ID: {player_id}"
        forward_messages.append({
            "type": "node",
            "data": {
                "name": "Eversoul Helper",
                "uin": event.self_id,
                "content": f"开始为 {account_info} 兑换"
            }
        })
        coupon_history = await EversoulUser.get_coupon_history(int(user_id), str(player_id))
        results, _ = await redeem_coupons_concurrently(
            str(app_id), str(player_id), all_coupons, event, coupon_history, max_workers=100
        )
        
        sorted_results = []
        success_results = []
        limit_results = []
        failed_results = []
        skipped_results = []
        
        for result_item in results:
            if result_item.get("skipped", False):
                skipped_results.append(result_item)
            elif result_item.get("status") == "成功":
                success_results.append(result_item)
            elif result_item.get("status") == "超限":
                limit_results.append(result_item)
            else:
                failed_results.append(result_item)
        
        sorted_results = success_results + limit_results + failed_results + skipped_results
        
        if success_results:
            success_content = "\n".join([result_item["result"] for result_item in success_results])
            forward_messages.append({
                "type": "node",
                "data": {
                    "name": "Eversoul Helper",
                    "uin": event.self_id,
                    "content": success_content
                }
            })
        
        if limit_results:
            limit_content = "\n".join([result_item["result"] for result_item in limit_results])
            forward_messages.append({
                "type": "node",
                "data": {
                    "name": "Eversoul Helper",
                    "uin": event.self_id,
                    "content": limit_content
                }
            })
        
        if failed_results:
            failed_content = "\n".join([result_item["result"] for result_item in failed_results])
            forward_messages.append({
                "type": "node",
                "data": {
                    "name": "Eversoul Helper",
                    "uin": event.self_id,
                    "content": failed_content
                }
            })
        
        if skipped_results:
            skipped_content = "\n".join([result_item["result"] for result_item in skipped_results])
            forward_messages.append({
                "type": "node",
                "data": {
                    "name": "Eversoul Helper",
                    "uin": event.self_id,
                    "content": skipped_content
                }
            })
            
        # 更新兑换历史和检查是否需要更新过期日期
        for result_item in sorted_results:
            # 如果不是跳过的结果，需要更新兑换历史
            if not result_item.get("skipped", False):
                code = result_item["code"]
                success = result_item.get("success", False)
                message = result_item.get("message", "")
                
                # 记录兑换状态
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                status_text = "成功" if success else "失败"
                
                # 更新兑换历史
                await EversoulUser.update_coupon_history(
                    int(user_id), 
                    str(player_id), 
                    code, 
                    {
                        "status": status_text,
                        "message": message,
                        "time": current_time
                    }
                )

    forward_messages.append({
        "type": "node",
        "data": {
            "name": "Eversoul Helper",
            "uin": event.self_id,
            "content": f"共{accounts_count}个账号，{len(all_coupons)}个兑换码"
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