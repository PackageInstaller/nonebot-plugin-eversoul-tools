"""
Eversoul兑换码相关工具函数
"""
import re
import aiohttp
from typing import Tuple, Optional
from nonebot.log import logger


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
    pattern = r"^(asia|kr|en)\s*(\d{12})$"
    match = re.match(pattern, text.lower().strip())
    
    if not match:
        return None, None
    
    server_code = match.group(1)
    player_id = match.group(2)
    
    # 确保ID正好是12位数字
    if not player_id.isdigit() or len(player_id) != 12:
        return None, None
    
    return server_code, player_id


async def redeem_coupon(app_id: str, player_id: str, coupon_code: str) -> Tuple[bool, str]:
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
                    if "success" in response_text.lower():
                        return True, f"兑换成功! 服务器响应: {response_text}"
                    else:
                        return False, f"兑换请求成功，但服务器返回未知响应: {response_text}"
                elif status_code == 400:
                    return False, f"请求错误: {response_text}"
                elif status_code == 463:
                    return False, f"此帐号已超出兑换码的使用次数限制。"
                elif status_code == 466:
                    return False, f"兑换码无效。请重新检查。"
                else:
                    return False, f"服务器返回错误 (状态码: {status_code}): {response_text}"
                
    except aiohttp.ClientError as e:
        logger.error(f"兑换请求发生网络错误: {e}")
        return False, f"网络请求错误: {str(e)}"
    except Exception as e:
        logger.error(f"兑换过程中发生未知错误: {e}")
        return False, f"处理兑换请求时发生错误: {str(e)}" 