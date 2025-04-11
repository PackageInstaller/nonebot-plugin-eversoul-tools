"""
Eversoul兑换码相关工具函数
"""
import re
import json
import aiohttp
import asyncio
from typing import Tuple, Optional, List, Dict, Any
from nonebot.log import logger
from . import *


def parse_server_id(text: str) -> Tuple[Optional[str], Optional[str]]:
    """解析用户输入的服务器和ID
    
    Args:
        text: 用户输入的文本，格式为"服务器ID"，例如"kr123456789012"
        
    Returns:
        Tuple[Optional[str], Optional[str]]: (服务器代码, 玩家ID)，如果解析失败则返回(None, None)
    """
    if not text:
        return None, None
    
    # 尝试匹配格式: asia/kr/en + 12位数字ID
    pattern = r"^(asia|kr|en|jp)\s*(\d{12})$"
    match = re.match(pattern, text.lower().strip())
    
    if not match:
        return None, None
    
    server_code = match.group(1)
    player_id = match.group(2)
    
    # 确保ID正好是12位数字
    if not player_id.isdigit() or len(player_id) != 12:
        return None, None
    
    return server_code, player_id


async def redeem_coupon(app_id: str, player_id: str, coupon_code: str, event: Event, max_retries: int = 3, retry_delay: float = 1.0) -> Tuple[bool, str]:
    """兑换礼包码
    
    Args:
        app_id: 游戏服务器对应的appId
        player_id: 玩家ID
        coupon_code: 兑换码
        event: 事件对象
        max_retries: 最大重试次数（默认为3次）
        retry_delay: 重试间隔时间（秒，默认为1秒）
        
    Returns:
        Tuple[bool, str]: (是否成功, 结果信息)
    """
    url = "https://openapi-zinny3.game.kakao.com/service/v3/coupon/useFromWeb"
    
    headers = {
        "appId": app_id,
        "playerId": player_id
    }
    
    payload = {
        "couponCode": coupon_code
    }
    
    # 初始化重试计数器
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            async with aiohttp.ClientSession() as session:
                # 设置超时时间
                timeout = aiohttp.ClientTimeout(total=10)
                async with session.post(url, headers=headers, json=payload, timeout=timeout) as response:
                    response_text = await response.text()
                    status_code = response.status
                    
                    # 处理各种可能的结果
                    if status_code == 200:
                        # 尝试解析JSON响应
                        try:
                            group_id = None
                            if isinstance(event, GroupMessageEvent):
                                group_id = event.group_id
                            
                            # 解析响应JSON
                            response_data = json.loads(response_text)
                            
                            # 构建奖励信息
                            reward_info = []
                            
                            # 加载物品数据
                            data = load_json_data(group_id)
                            # 处理主要物品
                            if "item" in response_data:
                                item = response_data["item"]
                                item_code = item.get("itemCode")
                                # 确保item_code是整数
                                if isinstance(item_code, str):
                                    item_code = int(item_code)
                                quantity = item.get("quantity", 1)
                                if item_code:
                                    # 获取物品名称
                                    try:
                                        item_name = get_string_item(data, item_code).get("zh_tw", "未知物品")
                                        reward_info.append(f"{item_name} x{quantity}")
                                    except Exception as e:
                                        logger.error(f"获取物品名称失败: {e}")
                                        reward_info.append(f"未知物品(itemCode:{item_code}) x{quantity}")
                            
                            # 处理其他物品
                            if "others" in response_data and isinstance(response_data["others"], list):
                                for other_item in response_data["others"]:
                                    item_code = other_item.get("itemCode")
                                    # 确保item_code是整数
                                    if isinstance(item_code, str):
                                        item_code = int(item_code)
                                    quantity = other_item.get("quantity", 1)

                                    if item_code:
                                        # 获取物品名称
                                        try:
                                            item_name = get_string_item(data, item_code).get("zh_tw", "未知物品")
                                            reward_info.append(f"{item_name} x{quantity}")
                                        except Exception as e:
                                            logger.error(f"获取物品名称失败: {e}")
                                            reward_info.append(f"未知物品(itemCode:{item_code}) x{quantity}")
                            
                            # 构建成功消息
                            if reward_info:
                                rewards = "、".join(reward_info)
                                return True, f"兑换成功! 获得: {rewards}"
                            return True, f"兑换成功!"
                        except Exception as e:
                            logger.error(f"解析奖励信息失败: {e}")
                            return True, f"兑换成功! 服务器响应: {response_text}"
                    elif status_code == 403:
                        return False, f"兑换码无效。"
                    elif status_code == 462:
                        return False, f"兑换码已过期。"
                    elif status_code == 463:
                        return False, f"帐号超出兑换次数限制。"
                    elif status_code == 466:
                        return False, f"账号不存在。"
                    else:
                        # 可能需要重试的错误
                        if status_code >= 500 or status_code == 429:
                            retry_count += 1
                            if retry_count <= max_retries:
                                logger.warning(f"兑换请求失败 (状态码: {status_code})，将在 {retry_delay} 秒后重试 (第 {retry_count}/{max_retries} 次)")
                                await asyncio.sleep(retry_delay)
                                # 每次重试增加延迟时间
                                retry_delay *= 1.5
                                continue
                        return False, f"服务器返回错误 (状态码: {status_code}): {response_text}"
                
        except aiohttp.ClientError as e:
            retry_count += 1
            if retry_count <= max_retries:
                logger.warning(f"兑换请求发生网络错误: {e}，将在 {retry_delay} 秒后重试 (第 {retry_count}/{max_retries} 次)")
                await asyncio.sleep(retry_delay)
                # 每次重试增加延迟时间
                retry_delay *= 1.5
                continue
            logger.error(f"兑换请求发生网络错误 (最终尝试): {e}")
            return False, f"网络请求错误: {str(e)}"
        except asyncio.TimeoutError:
            retry_count += 1
            if retry_count <= max_retries:
                logger.warning(f"兑换请求超时，将在 {retry_delay} 秒后重试 (第 {retry_count}/{max_retries} 次)")
                await asyncio.sleep(retry_delay)
                # 每次重试增加延迟时间
                retry_delay *= 1.5
                continue
            logger.error("兑换请求超时 (最终尝试)")
            return False, "请求超时，服务器未响应"
        except Exception as e:
            logger.error(f"兑换过程中发生未知错误: {e}")
            return False, f"处理兑换请求时发生错误: {str(e)}"
            
    # 如果到达这里，说明已经重试了最大次数但仍然失败
    return False, f"经过 {max_retries} 次重试后仍然失败"


# 用于并发执行兑换操作的函数
async def redeem_coupons_concurrently(app_id: str, player_id: str, coupon_items: List[Dict[str, Any]], 
            event: Event, coupon_history: Dict[str, Any], max_workers: int = 100) -> List[Dict[str, Any]]:
    """并发兑换多个礼包码
    
    Args:
        app_id: 游戏服务器对应的appId
        player_id: 玩家ID
        coupon_items: 兑换码列表
        event: 事件对象
        coupon_history: 兑换历史
        max_workers: 最大并发数
        
    Returns:
        List[Dict[str, Any]]: 兑换结果列表
    """
    results = []
    skipped_count = 0
    
    # 创建任务队列
    queue = asyncio.Queue()
    
    # 填充队列
    for item in coupon_items:
        await queue.put(item)
    
    # 定义工作函数
    async def worker():
        nonlocal skipped_count
        while not queue.empty():
            try:
                item = await queue.get()
                code = item["code"]
                desc = item.get("desc", "无描述")
                
                # 检查是否已经兑换过
                if code in coupon_history:
                    skipped_count += 1
                    status = coupon_history[code]["status"]
                    result = coupon_history[code]["message"]
                    results.append({
                        "code": code,
                        "desc": desc,
                        "status": "已兑换",
                        "result": f"{code} ({desc}): ⏭️已兑换\n{result}",
                        "is_skipped": True
                    })
                    queue.task_done()
                    continue
                
                # 执行兑换
                success, result = await redeem_coupon(app_id, player_id, code, event)
                status = "成功" if success else "失败"
                status_emoji = "✅成功" if success else "❎失败"
                
                results.append({
                    "code": code,
                    "desc": desc,
                    "status": status,
                    "result": f"{code} ({desc}): {status_emoji}\n{result}",
                    "is_skipped": False,
                    "success": success,
                    "message": result
                })
                
                queue.task_done()
            except Exception as e:
                logger.error(f"处理兑换码时发生错误: {e}")
                if "item" in locals():
                    results.append({
                        "code": item.get("code", "未知"),
                        "desc": item.get("desc", "无描述"),
                        "status": "错误",
                        "result": f"{item.get('code', '未知')} ({item.get('desc', '无描述')}): ❌错误\n处理兑换时发生错误: {str(e)}",
                        "is_skipped": False,
                        "success": False,
                        "message": f"处理兑换时发生错误: {str(e)}"
                    })
                queue.task_done()
    
    # 创建并启动工作任务
    tasks = []
    for _ in range(min(max_workers, len(coupon_items))):
        task = asyncio.create_task(worker())
        tasks.append(task)
    
    # 等待队列处理完成
    await queue.join()
    
    # 取消工作任务
    for task in tasks:
        task.cancel()
    
    # 等待所有任务完成
    await asyncio.gather(*tasks, return_exceptions=True)
    
    return results, skipped_count 