"""
Eversoul兑换码相关工具函数
"""
import re
import json
import aiohttp
from typing import Tuple, Optional
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


async def redeem_coupon(app_id: str, player_id: str, coupon_code: str, event: Event) -> Tuple[bool, str]:
    """兑换礼包码
    
    Args:
        app_id: 游戏服务器对应的appId
        player_id: 玩家ID
        coupon_code: 兑换码
        
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
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
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
                    return False, f"服务器返回错误 (状态码: {status_code}): {response_text}"
                
    except aiohttp.ClientError as e:
        logger.error(f"兑换请求发生网络错误: {e}")
        return False, f"网络请求错误: {str(e)}"
    except Exception as e:
        logger.error(f"兑换过程中发生未知错误: {e}")
        return False, f"处理兑换请求时发生错误: {str(e)}" 