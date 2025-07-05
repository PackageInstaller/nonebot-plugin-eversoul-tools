from ..library.utils import *


@es_range_ranking.handle()
async def handle_es_range_ranking(bot: Bot, event: Event):
    try:
        # 获取群组ID
        group_id = 0
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
        data = load_json_data(group_id)
        
        # 收集角色攻击范围信息
        range_info = []
        unknown_range = []
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
                char_name_data = get_string_character(data, hero_id, special=True)
                char_name_zh_tw = char_name_data["zh_tw"]
                
                # 获取攻击范围
                attack_range = get_character_attack_range(data, hero_id)
                
                if attack_range > 0:
                    range_info.append((char_name_zh_tw, attack_range))
                else:
                    unknown_range.append(char_name_zh_tw)
        
        # 按攻击范围从大到小排序
        range_info.sort(key=lambda x: x[1], reverse=True)
        
        # 构建消息
        messages = [f"EverSoul 角色攻击范围排行：\n"]
        
        # 添加已知攻击范围的角色
        if range_info:
            messages.append(f"【已知攻击范围】")
            for i, (name, range_value) in enumerate(range_info, 1):
                messages.append(f"{i}. {name}: {range_value}")
        else:
            messages.append(f"【已知攻击范围】\n暂无数据")
        
        # 添加未知攻击范围的角色
        if unknown_range:
            messages.append(f"\n【未知攻击范围】")
            for i, name in enumerate(unknown_range, 1):
                messages.append(f"{i}. {name}")
        
        # 发送合并转发消息
        forward_msgs = [{
            "type": "node",
            "data": {
                "name": f"EverSoul 攻击范围 Ranking",
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
                user_id=event.get_user_id(),
                messages=forward_msgs
            )
            
    except Exception as e:
        if not isinstance(e, FinishedException):
            import traceback
            error_location = traceback.extract_tb(e.__traceback__)[-1]
            logger.error(
                f"处理攻击范围排行时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )
            await es_range_ranking.finish(f"处理攻击范围排行时发生错误: {str(e)}") 