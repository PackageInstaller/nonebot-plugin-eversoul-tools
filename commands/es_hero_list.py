import yaml
from nonebot import on_command
from nonebot.exception import FinishedException
from zhenxun.services.log import logger
from nonebot.adapters.onebot.v11 import (
    Bot,
    Event,
    GroupMessageEvent
)
from ..libraries.es_utils import *

es_hero_list = on_command("es角色列表", priority=0, block=True)


@es_hero_list.handle()
async def handle_hero_list(bot: Bot, event: Event):
    """处理角色列表查询"""
    try:
        # 加载数据
        # 获取群组ID
        group_id = None
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
        data = load_json_data(group_id)
        
        # 加载别名配置
        aliases_data = {}
        config = get_group_data_source(group_id)
        with open(config["hero_alias_file"], "r", encoding="utf-8") as f:
            aliases_data = yaml.safe_load(f)
        
        if not aliases_data or "names" not in aliases_data:
            await es_hero_list.finish("角色数据加载失败")
            return
            
        # 使用字典存储不同种族的角色
        hero_categories = {}
        
        # 遍历所有角色
        for hero in aliases_data["names"]:
            hero_id = hero["hero_id"]
            name = hero["zh_tw_name"]
            if not name:  # 跳过未知角色
                continue
            
            # 从Hero.json中获取角色种族信息
            hero_data = next((h for h in data["hero"]["json"] if h["hero_id"] == hero_id), None)
            if not hero_data:
                continue
                
            # 获取种族名称
            race_tw, _, _, _ = get_system_string(data, hero_data["race_sno"])
            if not race_tw:
                continue
                
            # 初始化种族分类
            if race_tw not in hero_categories:
                hero_categories[race_tw] = []
            
            # 添加别名信息
            aliases = hero.get("aliases", [])
            alias_text = f"（{', '.join(aliases)}）" if aliases else ""
            
            # 添加角色信息
            hero_info = f"{name}{alias_text}"
            hero_categories[race_tw].append(hero_info)
        
        # 生成转发消息
        forward_msgs = []
        for category, heroes in hero_categories.items():
            if heroes:  # 只显示有角色的分类
                msg = f"【{category}】\n"
                msg += "\n".join(f"・ {hero}" for hero in sorted(heroes))  # 按名称排序
                
                forward_msgs.append({
                    "type": "node",
                    "data": {
                        "name": "Character List",
                        "uin": bot.self_id,
                        "content": msg
                    }
                })
        
        # 发送合并转发消息
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
                f"处理角色列表时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )
            await es_hero_list.finish(f"处理角色列表时发生错误: {str(e)}")