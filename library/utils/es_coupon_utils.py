import re
import json
import aiohttp
import asyncio
from typing import Tuple, Optional, List, Dict, Any
from . import *


async def parse_server_id(
    text: str,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """解析用户输入的服务器和ID

    Args:
        text: 用户输入的文本，格式为"服务器ID"，例如"kr123456789012"

    Returns:
        Tuple[Optional[str], Optional[str], Optional[str]]: (服务器代码, 玩家ID, 错误信息)
        如果解析成功返回(server_code, player_id, None)
        如果解析失败返回(None, None, error_message)
    """
    if not text:
        return None, None, "输入不能为空"

    # 清理输入文本
    text = text.strip()

    # 尝试匹配格式: asia/kr/en + 12或15位数字ID
    pattern = r"^(asia|kr|en)\s*(\d{12}|\d{15})$"
    match = re.match(pattern, text.lower())

    if not match:
        # 检查是否有地区代码
        if not any(text.lower().startswith(prefix) for prefix in ["asia", "kr", "en"]):
            return None, None, "缺少地区代码（asia/kr/en）"

        # 检查地区代码后是否有数字
        server_match = re.match(r"^(asia|kr|en)\s*(.*)$", text.lower())
        if server_match:
            server_code = server_match.group(1)
            id_part = server_match.group(2).strip()

            if not id_part:
                return None, None, f"缺少玩家ID（地区代码：{server_code}）"

            if not id_part.isdigit():
                return None, None, f"玩家ID必须是纯数字（当前输入：{id_part}）"

            id_len = len(id_part)
            if id_len != 12 and id_len != 15:
                return None, None, f"玩家ID长度必须是12位或15位（当前长度：{id_len}位）"

        return None, None, "格式错误，请使用格式：地区代码+玩家ID"

    server_code = match.group(1)
    player_id = match.group(2)

    # 确保ID是纯数字且长度为12或15位
    if not player_id.isdigit():
        return None, None, f"玩家ID必须是纯数字（当前输入：{player_id}）"

    if len(player_id) not in [12, 15]:
        return None, None, f"玩家ID长度必须是12位或15位（当前长度：{len(player_id)}位）"

    return server_code, player_id, None


async def redeem_coupon(
    app_id: str,
    player_id: str,
    coupon_code: str,
    event: Event,
    max_retries: int = 3,
    retry_delay: float = 1.0,
) -> Tuple[bool, str]:
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

    headers = {"appId": app_id, "playerId": player_id}

    payload = {"couponCode": coupon_code}

    retry_count = 0

    while retry_count <= max_retries:
        try:
            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=5)
                async with session.post(
                    url, headers=headers, json=payload, timeout=timeout
                ) as response:
                    response_text = await response.text()
                    status_code = response.status

                    if status_code == 200:
                        if isinstance(event, GroupMessageEvent):
                            group_id = event.group_id

                        response_data = json.loads(response_text)
                        reward_info = []

                        data = await load_json_data(group_id)
                        if "item" in response_data:
                            item = response_data["item"]
                            item_code = item.get("itemCode")
                            if isinstance(item_code, str):
                                item_code = int(item_code)
                            quantity = item.get("quantity", 1)
                            if item_code:
                                item_name = (
                                    await get_string_item(data, item_code)
                                ).get("zh_tw", "")
                                reward_info.append(f"{item_name}x{quantity}")

                        if "others" in response_data and isinstance(
                            response_data["others"], list
                        ):
                            for other_item in response_data["others"]:
                                item_code = other_item.get("itemCode")
                                if isinstance(item_code, str):
                                    item_code = int(item_code)
                                quantity = other_item.get("quantity", 1)

                                if item_code:
                                    item_name = (
                                        await get_string_item(data, item_code)
                                    ).get("zh_tw", "")
                                    reward_info.append(f"{item_name}x{quantity}")

                        if reward_info:
                            rewards = "、".join(reward_info)
                            return True, f"✅获得: {rewards}"

                    elif status_code == 403:
                        return False, "❎兑换码无效\n"
                    elif status_code == 461:
                        return False, "❎兑换码售罄\n"
                    elif status_code == 462:
                        return False, "❎兑换码过期\n"
                    elif status_code == 463:
                        return False, "❎兑换码超限\n"
                    elif status_code == 466:
                        return False, "❎账号不存在\n"
                    elif status_code == 503:
                        return False, "❎服务器错误\n"

        except aiohttp.ClientError as e:
            retry_count += 1
            if retry_count <= max_retries:
                await asyncio.sleep(retry_delay)
                continue
            return False, f"网络请求错误: {str(e)}"
        except asyncio.TimeoutError:
            retry_count += 1
            if retry_count <= max_retries:
                await asyncio.sleep(retry_delay)
                continue
            return False, "请求超时，服务器未响应"


async def redeem_coupons_concurrently(
    app_id: str,
    player_id: str,
    coupon_items: List[Dict[str, Any]],
    event: Event,
    coupon_history: Dict[str, Any],
    max_workers: int = 100,
) -> Tuple[List[Dict[str, Any]], int]:
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
    queue = asyncio.Queue()
    for item in coupon_items:
        await queue.put(item)

    async def worker():
        while not queue.empty():
            item = await queue.get()
            code = item["code"]
            desc = item.get("desc", "无描述")

            success, result = await redeem_coupon(app_id, player_id, code, event)

            status = "成功" if success else "失败"

            results.append(
                {
                    "code": code,
                    "desc": desc,
                    "status": status,
                    "result": f"{code}\n({desc})\n{result}",
                    "success": success,
                    "message": result,
                }
            )

            queue.task_done()

    tasks = []
    for _ in range(min(max_workers, len(coupon_items))):
        task = asyncio.create_task(worker())
        tasks.append(task)

    await queue.join()
    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)

    return results
