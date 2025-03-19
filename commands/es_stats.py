import yaml
from nonebot import on_regex
from nonebot.exception import FinishedException
from zhenxun.services.log import logger
from nonebot.adapters.onebot.v11 import (
    Bot,
    Event,
    GroupMessageEvent
)
from ..libraries.es_utils import *

es_stats = on_regex(r"^es(身高|体重)排行$", priority=5, block=True)


@es_stats.handle()
async def handle_es_stats(bot: Bot, event: Event):
    try:
        # 获取匹配的类型（身高或体重）
        stat_type = event.get_plaintext()[2:4]  # 获取"身高"或"体重"
        
        # 加载数据
        # 获取群组ID
        group_id = None
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
        data = load_json_data(group_id)
        logger.info("数据加载完成")
        
        # 收集角色信息
        stats_info = []
        unknown_stats = []
        config = get_group_data_source(group_id)
        # 读取hero_aliases.yaml获取角色信息
        with open(config["hero_alias_file"], "r", encoding="utf-8") as f:
            hero_aliases_data = yaml.safe_load(f)
            
        # 获取names列表
        char_list = hero_aliases_data.get('names', [])
        
        # 遍历角色列表
        for char_data in char_list:
            if isinstance(char_data, dict):  # 确保是字典类型
                hero_id = char_data.get('hero_id')
                if not hero_id:
                    continue
                
                # 获取角色名称
                char_name_tw, char_name_cn, char_name_kr, char_name_en = get_hero_name_by_id(data, hero_id)
                
                # 查找英雄描述数据
                hero_desc = None
                for desc in data["hero_desc"]["json"]:
                    if desc["hero_no"] == hero_id:
                        hero_desc = desc
                        break
                
                # 获取身高或体重信息
                stat_key = "height" if stat_type == "身高" else "weight"
                stat_value = hero_desc.get(stat_key, "???") if hero_desc else "???"
                
                if stat_value != "???":
                    stats_info.append((char_name_tw, stat_value))
                else:
                    unknown_stats.append(char_name_tw)
        
        # 按身高/体重从大到小排序
        stats_info.sort(key=lambda x: x[1], reverse=True)
        
        # 构建消息
        messages = [f"EverSoul 角色{stat_type}排行：\n"]
        
        # 添加已知数据的角色
        if stats_info:
            messages.append(f"【已知{stat_type}】")
            for i, (name, value) in enumerate(stats_info, 1):
                unit = "cm" if stat_type == "身高" else "kg"
                messages.append(f"{i}. {name}: {value}{unit}")
        else:
            messages.append(f"【已知{stat_type}】\n暂无数据")
        
        # 添加未知数据的角色
        if unknown_stats:
            messages.append(f"\n【未知{stat_type}】")
            for i, name in enumerate(unknown_stats, 1):
                messages.append(f"{i}. {name}")
        
        # 发送合并转发消息
        forward_msgs = [{
            "type": "node",
            "data": {
                "name": f"EverSoul {stat_type} Ranking",
                "uin": bot.self_id,
                "content": "\n".join(messages)
            }
        }]
        
        # 发送消息
        if isinstance(event, GroupMessageEvent):
            await bot.call_api(
                "send_group_forward_msg",
                group_id=event.group_id,
                messages=forward_msgs
            )
        else:
            await bot.call_api(
                "send_private_forward_msg",
                user_id=event.user_id,
                messages=forward_msgs
            )
            
    except Exception as e:
        if not isinstance(e, FinishedException):
            import traceback
            error_location = traceback.extract_tb(e.__traceback__)[-1]
            logger.error(
                f"处理{stat_type}排行时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )
            await es_stats.finish(f"处理{stat_type}排行时发生错误: {str(e)}")