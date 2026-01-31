from ..library.utils import *


@es_coupon.handle()
async def handle_coupon(bot: Bot, event: Event, args: Message = CommandArg()):
    """处理兑换码指令"""

    user_id = event.get_user_id()
    user_accounts = await EversoulUser.get_all_user_accounts(int(user_id))

    if not user_accounts:
        bind_msg = (
            f"未绑定游戏账号，无法进行兑换。\n" "请使用 es绑定 [地区+ID] 绑定账号"
        )
        await es_coupon.finish(message=bind_msg, reply_message=True)

    # 解析命令参数
    arg_text = args.extract_plain_text().strip()
    custom_codes = []
    use_custom_codes = False
    
    if arg_text:
        # 有参数，使用自定义兑换码
        custom_codes = [code.strip() for code in arg_text.split() if code.strip()]
        use_custom_codes = True
        logger.info(f"使用自定义兑换码: {custom_codes}")
    
    if use_custom_codes:
        # 使用参数中的兑换码
        all_coupons = [{"code": code, "expired": False, "is_custom": True} for code in custom_codes]
        if not all_coupons:
            await es_coupon.finish(message="未提供有效的兑换码", reply_message=True)
    else:
        # 从YAML文件读取兑换码
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

        all_coupons = valid_coupons

        if not all_coupons:
            await es_coupon.finish(message="全部兑换码已过期！", reply_message=True)

    accounts_count = len(user_accounts)
    
    if use_custom_codes:
        reply_text = (
            f"开始为您的{accounts_count}个账号兑换自定义兑换码({len(all_coupons)}个)，请耐心等待..."
        )
    else:
        reply_text = (
            f"开始为您的{accounts_count}个账号兑换{len(all_coupons)}个兑换码，请耐心等待..."
        )

    await es_coupon.send(message=reply_text, reply_message=True)

    forward_messages = []
    successful_custom_codes = set()  # 记录成功的自定义兑换码

    all_coupon_histories = {}
    for account in user_accounts:
        player_id = account.get("player_id")
        history = await EversoulUser.get_coupon_history(int(user_id), str(player_id))
        all_coupon_histories[player_id] = history

    for account_index, account in enumerate(user_accounts):
        app_id = account.get("app_id")
        player_id = account.get("player_id")

        server_code = next(
            (k for k, v in SERVER_APP_ID_MAPPING.items() if v == app_id), "未知"
        )
        server_name = SERVER_NAME_MAPPING.get(server_code, app_id)

        account_info = (
            f"账号{account_index+1}/{accounts_count}: {server_name}, ID: {player_id}"
        )
        forward_messages.append(
            build_forward_message(f"开始为 {account_info} 兑换", event.self_id)
        )
        coupon_history = await EversoulUser.get_coupon_history(
            int(user_id), str(player_id)
        )
        results = await redeem_coupons_concurrently(
            str(app_id),
            str(player_id),
            all_coupons,
            event,
            coupon_history,
            max_workers=100,
        )

        sorted_results = []
        success_results = []
        failed_results = []

        for result_item in results:
            if result_item.get("status") == "成功":
                success_results.append(result_item)
            else:
                failed_results.append(result_item)

        sorted_results = success_results + failed_results

        if success_results:
            success_content = "\n".join(
                [result_item["result"] for result_item in success_results]
            )
            forward_messages.append(
                build_forward_message(success_content, event.self_id)
            )

        if failed_results:
            failed_content = "\n".join(
                [result_item["result"] for result_item in failed_results]
            )
            forward_messages.append(
                build_forward_message(failed_content, event.self_id)
            )

        for result_item in sorted_results:
            code = result_item["code"]
            success = result_item.get("success", False)
            message = result_item.get("message", "")
            is_custom = result_item.get("is_custom", False)
            reward_desc = result_item.get("reward_desc", "")

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status_text = "成功" if success else "失败"

            # 如果是自定义兑换码且兑换成功，记录下来（包括奖励信息）
            if use_custom_codes and is_custom and success:
                successful_custom_codes.add((code, reward_desc))

            # 更新兑换历史
            await EversoulUser.update_coupon_history(
                int(user_id),
                str(player_id),
                code,
                {"status": status_text, "message": message, "time": current_time},
            )

    # 如果有成功的自定义兑换码，保存到YAML
    if use_custom_codes and successful_custom_codes:
        try:
            # 读取现有的YAML文件
            try:
                with open(COUPON_YAML_PATH, "r", encoding="utf-8") as f:
                    coupon_data = yaml.safe_load(f) or {}
            except FileNotFoundError:
                coupon_data = {}
            
            existing_coupons = coupon_data.get("coupons", [])
            
            # 计算过期时间（一个月后）
            from dateutil.relativedelta import relativedelta
            expiry_date = (datetime.now() + relativedelta(months=1)).strftime("%Y-%m-%d")
            
            # 添加或更新成功兑换码
            added_codes = []
            updated_codes = []
            
            for code, reward_desc in successful_custom_codes:
                # 使用奖励描述作为 desc，如果为空则使用默认值
                desc = reward_desc if reward_desc else "未知奖励"
                
                # 查找是否已存在该兑换码
                existing_item = None
                for item in existing_coupons:
                    if item.get("code") == code:
                        existing_item = item
                        break
                
                if existing_item:
                    # 已存在，检查是否需要更新
                    needs_update = False
                    
                    # 如果现有的desc为空或无效，更新它
                    if not existing_item.get("desc") or existing_item.get("desc") in [None, "null", "无描述", "未知奖励"]:
                        if desc and desc != "未知奖励":
                            existing_item["desc"] = desc
                            needs_update = True
                    
                    # 如果现有的date为空或无效，更新它
                    if not existing_item.get("date") or existing_item.get("date") in [None, "null", ""]:
                        existing_item["date"] = expiry_date
                        needs_update = True
                    
                    # 移除旧的note字段（如果存在）
                    if "note" in existing_item:
                        del existing_item["note"]
                        needs_update = True
                    
                    if needs_update:
                        updated_codes.append(code)
                        logger.info(f"更新兑换码 {code}: desc={desc}, date={expiry_date}")
                else:
                    # 不存在，添加新的
                    existing_coupons.append({
                        "code": code,
                        "date": expiry_date,
                        "desc": desc
                    })
                    added_codes.append(code)
                    logger.info(f"添加新兑换码 {code}: desc={desc}, date={expiry_date}")
            
            # 保存回YAML
            if added_codes or updated_codes:
                coupon_data["coupons"] = existing_coupons
                with open(COUPON_YAML_PATH, "w", encoding="utf-8") as f:
                    yaml.dump(coupon_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
                
                # 构建反馈消息
                feedback_parts = []
                if added_codes:
                    feedback_parts.append(f"✅ 新增 {len(added_codes)} 个兑换码")
                    logger.info(f"成功添加 {len(added_codes)} 个自定义兑换码: {added_codes}")
                if updated_codes:
                    feedback_parts.append(f"🔄 更新 {len(updated_codes)} 个兑换码")
                    logger.info(f"成功更新 {len(updated_codes)} 个兑换码信息: {updated_codes}")
                
                feedback_parts.append(f"过期时间: {expiry_date}")
                
                forward_messages.append(
                    build_forward_message("\n".join(feedback_parts), event.self_id)
                )
        except Exception as e:
            logger.error(f"保存自定义兑换码到YAML失败: {e}")
            forward_messages.append(
                build_forward_message(f"⚠️ 保存兑换码到配置文件失败: {str(e)}", event.self_id)
            )

    forward_messages.append(
        build_forward_message(f"共{accounts_count}个账号，{len(all_coupons)}个兑换码", event.self_id)
    )

    # 发送合并转发消息
    await send_forward_messages(bot, event, forward_messages)

    await es_coupon.finish()
