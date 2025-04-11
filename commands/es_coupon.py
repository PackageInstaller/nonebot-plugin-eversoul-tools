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


# 更新兑换码的过期日期
async def update_coupon_expiry_date(code: str, new_date: str = None):
    """更新兑换码的过期日期
    
    Args:
        code: 兑换码
        new_date: 新的过期日期，如果为None则自动设置为当前日期+30天
    """
    try:
        # 读取当前文件
        with open(COUPON_YAML_PATH, "r", encoding="utf-8") as f:
            coupon_data = yaml.safe_load(f)
            
        # 如果文件为空或格式不正确，初始化结构
        if not coupon_data or not isinstance(coupon_data, dict):
            coupon_data = {"coupons": []}
        
        # 查找并更新对应的兑换码
        updated = False
        for item in coupon_data.get("coupons", []):
            if item.get("code") == code:
                # 如果没有提供新日期，则默认设置为当前日期+30天
                if new_date is None:
                    future_date = datetime.now() + timedelta(days=30)
                    new_date = future_date.strftime("%Y-%m-%d")
                
                # 更新日期
                item["date"] = new_date
                updated = True
                logger.info(f"已更新兑换码 {code} 的过期日期为 {new_date}")
                break
        
        # 如果找到并更新了兑换码，保存文件
        if updated:
            with open(COUPON_YAML_PATH, "w", encoding="utf-8") as f:
                yaml.dump(coupon_data, f, allow_unicode=True)
            
            return True
        
        return False
    except Exception as e:
        logger.error(f"更新兑换码过期日期失败: {e}")
        return False


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
            
        # 尽管日期已过期，我们仍然尝试兑换，但在UI中标记为过期
        # 这样如果官方延长了兑换期限，我们仍然能够兑换成功
        if expiry_date and expiry_date < current_date:
            item["is_expired"] = True
            expired_coupons.append(item)
        else:
            item["is_expired"] = False
            valid_coupons.append(item)
    
    # 合并有效和过期的兑换码，我们都会尝试兑换
    all_coupons = valid_coupons + expired_coupons
    valid_count = len(valid_coupons)
    expired_count = len(expired_coupons)
    
    if not all_coupons:
        await es_coupon.finish(message="没有找到有效的兑换码", reply_message=True)
    
    # 显示用户信息
    accounts_count = len(user_accounts)
    message_text = f"开始为您的{accounts_count}个账号兑换{len(all_coupons)}个兑换码，请耐心等待..."
    
    await es_coupon.send(
        message=message_text,
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
    
    # 如果有过期的兑换码，添加提示
    if expired_count > 0:
        forward_messages.append({
            "type": "node",
            "data": {
                "name": "Eversoul Helper",
                "uin": event.self_id,
                "content": f"注意: {expired_count}个已过期的兑换码将被尝试兑换，如果成功则自动更新过期时间"
            }
        })
    
    # 记录需要更新过期日期的兑换码
    codes_to_update = []
    
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
        
        # 使用并发执行兑换
        results, skipped_count = await redeem_coupons_concurrently(
            app_id, player_id, all_coupons, event, coupon_history, max_workers=100
        )
        
        # 将每个兑换码的结果加入合并转发
        for result_item in results:
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
                    if item["code"] == code and item.get("is_expired", False) and success:
                        # 如果过期码兑换成功，需要更新日期
                        if code not in codes_to_update:
                            codes_to_update.append(code)
            
            # 添加结果到消息中
            forward_messages.append({
                "type": "node",
                "data": {
                    "name": "Eversoul Helper",
                    "uin": event.self_id,
                    "content": result_item["result"]
                }
            })
        
        # 添加跳过统计信息
        if skipped_count > 0:
            forward_messages.append({
                "type": "node",
                "data": {
                    "name": "Eversoul Helper",
                    "uin": event.self_id,
                    "content": f"账号 {account_info} 共跳过了 {skipped_count} 个已兑换过的兑换码"
                }
            })
    
    # 更新过期码的日期
    updated_codes = []
    if codes_to_update:
        for code in codes_to_update:
            # 设置为当前日期
            future_date = (datetime.now()).strftime("%Y-%m-%d")
            if await update_coupon_expiry_date(code, future_date):
                updated_codes.append(code)
    
    # 添加过期码更新信息
    if updated_codes:
        forward_messages.append({
            "type": "node",
            "data": {
                "name": "Eversoul Helper",
                "uin": event.self_id,
                "content": f"已更新 {len(updated_codes)} 个过期码的有效期：\n" + "\n".join(updated_codes)
            }
        })
    
    # 添加兑换完成信息
    forward_messages.append({
        "type": "node",
        "data": {
            "name": "Eversoul Helper",
            "uin": event.self_id,
            "content": f"兑换完成！共{accounts_count}个账号，{len(all_coupons)}个兑换码"
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