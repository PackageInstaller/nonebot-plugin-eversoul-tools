import yaml
import os
import time
from datetime import datetime, timedelta
from ..libraries.utils import *

# 保存当前正在等待绑定的用户
# 键是用户ID，值是绑定过期时间和其他信息
BINDING_USERS = {}

# 兑换码文件路径
COUPON_YAML_PATH = DATA_DIR / "coupons.yaml"

# 确保兑换码文件存在
def ensure_coupon_file():
    if not os.path.exists(COUPON_YAML_PATH):
        with open(COUPON_YAML_PATH, "w", encoding="utf-8") as f:
            yaml.dump({
                "coupons": [
                    # 示例兑换码数据
                    # {"code": "ABCD1234", "desc": "测试兑换码", "date": "2024-12-31"}
                ]
            }, f, allow_unicode=True)
        logger.info(f"已创建兑换码文件: {COUPON_YAML_PATH}")


@es_coupon.handle()
async def handle_coupon(bot: Bot, event: Event, args: Message = CommandArg()):
    """处理兑换码指令"""

    # 确保兑换码文件存在
    ensure_coupon_file()
    
    user_id = event.get_user_id()
    
    # 获取用户的所有账号
    user_accounts = await EversoulUser.get_all_user_accounts(int(user_id))
    
    if not user_accounts:
        # 用户未绑定，发送绑定提示
        bind_msg = (
            f"未绑定游戏账号，无法进行兑换。\n"
            "请使用 es绑定 [地区+ID] 绑定账号"
        )
        await es_coupon.finish(message=bind_msg, reply_message=True)
    
    # 读取所有兑换码
    try:
        with open(COUPON_YAML_PATH, "r", encoding="utf-8") as f:
            coupon_data = yaml.safe_load(f)
            coupon_items = coupon_data.get("coupons", [])
    except Exception as e:
        logger.error(f"读取兑换码文件失败: {e}")
        await es_coupon.finish(message=f"读取兑换码失败: {str(e)}", reply_message=True)
    
    if not coupon_items:
        await es_coupon.finish(message="当前没有可用的兑换码", reply_message=True)

    # 获取当前时间，用于检查兑换码是否过期
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # 分类兑换码
    valid_coupons = []
    expired_coupons = []
    
    for item in coupon_items:
        code = item.get("code")
        expiry_date = item.get("date")
        
        if not code:
            continue
            
        # 如果日期已过期，标记为过期，但不再尝试兑换
        if expiry_date and expiry_date < current_date:
            item["is_expired"] = True
            expired_coupons.append(item)
        else:
            item["is_expired"] = False
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
    
    # 准备合并转发消息
    forward_messages = []
    
    # 添加兑换开始信息
    forward_messages.append({
        "type": "node",
        "data": {
            "name": "Eversoul Helper",
            "uin": event.self_id,
            "content": f"兑换码兑换结果 ({len(all_coupons)}个兑换码，{accounts_count}个账号)"
        }
    })
    
    # 记录需要更新过期日期的兑换码
    codes_to_update = []
    
    # 用于统计各类型结果数量
    total_success_results = 0
    total_limit_results = 0
    total_failed_results = 0
    total_skipped_results = 0
    
    # 获取所有已兑换历史
    all_coupon_histories = {}
    for account in user_accounts:
        player_id = account.get("player_id")
        history = await EversoulUser.get_coupon_history(int(user_id), player_id)
        all_coupon_histories[player_id] = history
    
    # 寻找已过期但限制兑换的码
    expired_limit_codes = []
    for item in all_coupons:
        if item.get("is_expired", False):
            code = item.get("code")
            # 检查是否在任何账号的历史中有超出限制记录
            for player_id, history in all_coupon_histories.items():
                if code in history and "帐号超出兑换次数限制" in history[code].get("message", ""):
                    if code not in expired_limit_codes:
                        expired_limit_codes.append(code)
    
    # 如果找到这样的兑换码，添加一个提示
    if expired_limit_codes:
        forward_messages.append({
            "type": "node",
            "data": {
                "name": "Eversoul Helper",
                "uin": event.self_id,
                "content": f"发现 {len(expired_limit_codes)} 个已过期但显示为超出兑换限制的兑换码，将尝试更新日期并重新兑换"
            }
        })
        
        for code in expired_limit_codes:
            # 同时更新兑换码列表中的状态
            for item in all_coupons:
                if item.get("code") == code:
                    item["is_expired"] = False

    
    # 为每个账号执行兑换
    for account_index, account in enumerate(user_accounts):
        app_id = account.get("app_id")
        player_id = account.get("player_id")
        
        # 获取服务器名称
        server_code = next((k for k, v in SERVER_APP_ID_MAPPING.items() if v == app_id), "未知")
        server_name = SERVER_NAME_MAPPING.get(server_code, app_id)
        
        # 账号信息
        account_info = f"账号{account_index+1}/{accounts_count}: {server_name}, ID: {player_id}"
        forward_messages.append({
            "type": "node",
            "data": {
                "name": "Eversoul Helper",
                "uin": event.self_id,
                "content": f"开始为 {account_info} 兑换"
            }
        })
        
        # 获取该账号的兑换历史
        coupon_history = await EversoulUser.get_coupon_history(int(user_id), player_id)
        
        # 对于已更新日期的特殊兑换码，从历史记录中移除，确保它们会被重新尝试兑换
        if expired_limit_codes:
            for code in expired_limit_codes:
                if code in coupon_history:
                    del coupon_history[code]
        
        # 使用并发执行兑换
        results, skipped_count = await redeem_coupons_concurrently(
            app_id, player_id, all_coupons, event, coupon_history, max_workers=100
        )
        
        # 对结果进行排序：成功的在前，超出限制的其次，失败的放最后
        sorted_results = []
        success_results = []
        limit_results = []
        failed_results = []
        skipped_results = []
        
        for result_item in results:
            if result_item.get("is_skipped", False):
                skipped_results.append(result_item)
            elif result_item.get("status") == "成功":
                success_results.append(result_item)
            elif result_item.get("status") == "超出限制":
                limit_results.append(result_item)
            else:
                failed_results.append(result_item)
        
        # 更新总计数
        total_success_results += len(success_results)
        total_limit_results += len(limit_results)
        total_failed_results += len(failed_results)
        total_skipped_results += len(skipped_results)
        
        # 按顺序合并结果
        sorted_results = success_results + limit_results + failed_results + skipped_results
        
        # 合并同一类别的结果到一条消息中
        if success_results:
            success_content = f"——— ✅ 兑换成功({len(success_results)}个) ———\n"
            success_content += "\n".join([result_item["result"] for result_item in success_results])
            forward_messages.append({
                "type": "node",
                "data": {
                    "name": "Eversoul Helper",
                    "uin": event.self_id,
                    "content": success_content
                }
            })
        
        if limit_results:
            limit_content = f"——— ⚠️ 超出兑换限制({len(limit_results)}个) ———\n"
            limit_content += "\n".join([result_item["result"] for result_item in limit_results])
            forward_messages.append({
                "type": "node",
                "data": {
                    "name": "Eversoul Helper",
                    "uin": event.self_id,
                    "content": limit_content
                }
            })
        
        if failed_results:
            failed_content = f"——— ❎ 兑换失败({len(failed_results)}个) ———\n"
            failed_content += "\n".join([result_item["result"] for result_item in failed_results])
            forward_messages.append({
                "type": "node",
                "data": {
                    "name": "Eversoul Helper",
                    "uin": event.self_id,
                    "content": failed_content
                }
            })
        
        if skipped_results:
            skipped_content = f"——— ⏭️ 已兑换过({len(skipped_results)}个) ———\n"
            skipped_content += "\n".join([result_item["result"] for result_item in skipped_results])
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
            if not result_item.get("is_skipped", False):
                code = result_item["code"]
                success = result_item.get("success", False)
                message = result_item.get("message", "")
                
                # 记录兑换状态
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                status_text = "成功" if success else "失败"
                
                # 更新兑换历史
                await EversoulUser.update_coupon_history(
                    int(user_id), 
                    player_id, 
                    code, 
                    {
                        "status": status_text,
                        "message": message,
                        "time": current_time
                    }
                )
                
                # 检查是否需要更新过期日期
                for item in all_coupons:
                    if item["code"] == code and item.get("is_expired", False):
                        # 如果是超出兑换次数限制的情况，也需要更新过期日期
                        if success or "帐号超出兑换次数限制" in message:
                            # 如果过期码兑换成功或返回超出限制，需要更新日期
                            if code not in codes_to_update:
                                codes_to_update.append(code)
    
    # 添加兑换完成信息
    forward_messages.append({
        "type": "node",
        "data": {
            "name": "Eversoul Helper",
            "uin": event.self_id,
            "content": f"兑换完成！共{accounts_count}个账号，{len(all_coupons)}个兑换码\n"
                       f"✅成功: {total_success_results}个 | ⚠️超出限制: {total_limit_results}个\n"
                       f"❎失败: {total_failed_results}个 | ⏭️已兑换过: {total_skipped_results}个"
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