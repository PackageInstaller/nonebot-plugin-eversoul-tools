from ..library.utils import *


@es_single_raid.handle()
async def handle_single_raid(bot: Bot, event: Event, args: Message = CommandArg()):
    try:
        # 获取hero_id参数
        hero_id_text = args.extract_plain_text().strip()
        if not hero_id_text:
            await es_single_raid.finish("请输入正确的恶灵ID")
        
        try:
            hero_id = int(hero_id_text)
        except ValueError:
            await es_single_raid.finish("恶灵ID必须是数字")
        
        # 获取群组ID
        group_id = 0
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
        
        # 加载数据
        data = load_json_data(group_id)
        
        # 查找角色数据
        hero_data = None
        for hero in data["hero"]["json"]:
            if hero["hero_id"] == hero_id:
                hero_data = hero
                break
        
        if not hero_data:
            await es_single_raid.finish(f"未找到ID为{hero_id}的恶灵信息")
        
        # 查找SingleRaidBoss数据，获取boss_max_level最大的那个
        boss_data = None
        max_level = 0
        for boss in data["single_raid_boss"]["json"]:
            if boss.get("boss_no") == hero_id and boss.get("boss_max_level", 0) > max_level:
                max_level = boss.get("boss_max_level", 0)
                boss_data = boss
        
        if not boss_data:
            await es_single_raid.finish(f"未找到ID为{hero_id}的恶灵讨伐信息")
        
        # 根据level_group找到SingleRaid数据
        level_group = boss_data.get("level_group")
        raid_data = None
        for raid in data["single_raid"]["json"]:
            if raid.get("level_group") == level_group:
                raid_data = raid
                break
        
        # 获取角色名称
        hero_name_zh_tw = ""
        hero_name_zh_cn = ""
        hero_name_kr = ""
        hero_name_en = ""
        if hero_data["name_sno"]:
            name_data = get_string_character(data, hero_data["name_sno"])
            hero_name_zh_tw = name_data["zh_tw"]
            hero_name_zh_cn = name_data["zh_cn"]
            hero_name_kr = name_data["kr"]
            hero_name_en = name_data["en"]

        # 获取基础属性
        race_zh_tw = get_string_system(data, hero_data["race_sno"])["zh_tw"]
        hero_class_zh_tw = get_string_system(data, hero_data["class_sno"])["zh_tw"]
        sub_class_zh_tw = get_string_system(data, hero_data["sub_class_sno"])["zh_tw"]
        stat_zh_tw = get_string_system(data, hero_data["stat_sno"])["zh_tw"]
        
        # 获取战斗时长
        battle_time = 0
        if raid_data and raid_data.get("stage_no"):
            for stage in data["stage"]["json"]:
                if stage.get("no") == raid_data.get("stage_no"):
                    battle_time = stage.get("battle_time", 0)
                    break
        
        # 获取讨伐攻略
        guide_text = ""
        if raid_data and raid_data.get("guide_sno"):
            guide_data = get_string_ui(data, raid_data.get("guide_sno"))
            guide_text = guide_data["zh_tw"]
        
        # 获取血量倍数
        hp_multiplier = 1.0
        for level_grade in data["single_raid_boss_level_grade"]["json"]:
            if level_grade.get("level") == boss_data.get("boss_max_level"):
                hp_multiplier = level_grade.get("value", 1.0)
                break
        
        # 计算最终血量
        final_hp = int(hero_data.get("max_hp", 0) * hp_multiplier * boss_data.get('boss_max_level', 0))
        
        # 获取奖励信息
        reward_items = []
        if boss_data.get("reward_item1_no"):
            item_name = get_string_item(data, boss_data.get("reward_item1_no"))
            item_amount = boss_data.get("reward_item1_amount", 0)
            reward_items.append(f"{item_name['zh_tw']}x{item_amount}")
        
        if boss_data.get("reward_item2_no"):
            item_name = get_string_item(data, boss_data.get("reward_item2_no"))
            item_amount = boss_data.get("reward_item2_amount", 0)
            reward_items.append(f"{item_name['zh_tw']}x{item_amount}")
        
        # 获取赛季信息
        season_info = ""
        if raid_data and raid_data.get("no"):
            # 在single_raid_schedule中查找最新的赛季信息
            latest_schedule = None
            for schedule in data["single_raid_schedule"]["json"]:
                if schedule.get("raid_no") == raid_data.get("no"):
                    if not latest_schedule or schedule.get("season_no", 0) > latest_schedule.get("season_no", 0):
                        latest_schedule = schedule
            
            if latest_schedule:
                # 在single_raid_season中查找赛季名称
                for season in data["single_raid_season"]["json"]:
                    if season.get("no") == latest_schedule.get("season_no"):
                        season_name = get_string_ui(data, season.get("season_name_no"))
                        season_info = f"赛季：{season_name['zh_tw']}"
                        break
        
        # 获取相互作用之人信息
        interaction_info = []
        special_heroes = {}
        delay_text = None
        delay_seconds = None
        if raid_data and raid_data.get("level_group"):
            # 获取有开场台词的角色
            for interaction in data["single_raid_boss_interaction_detail"]["json"]:
                if interaction.get("interaction_no") == raid_data.get("level_group"):
                    # 获取角色名称
                    hero_name = get_string_character(data, interaction.get("hero_no"), special=True)
                    if hero_name:
                        interaction_info.append(hero_name["zh_tw"])
            
            # 获取特殊之人
            if raid_data.get("no"):
                # 在single_raid_season_gimmick中查找所有相关gimmick
                for gimmick in data["single_raid_season_gimmick"]["json"]:
                    if gimmick.get("raid_no") == raid_data.get("no"):
                        # 遍历所有gimmick_type和gimmick_value
                        i = 1
                        while f"gimmick_type{i}" in gimmick and f"gimmick_value{i}" in gimmick:
                            gimmick_value = gimmick.get(f"gimmick_value{i}")
                            # 在battle_buff中查找对应的buff
                            for buff in data["battle_buff"]["json"]:
                                if buff.get("no") == gimmick_value:
                                    # 获取特殊之人ID
                                    specific_target = buff.get("specific_target")
                                    if specific_target:
                                        # 获取角色名称
                                        hero_name = get_string_character(data, specific_target, special=True)
                                        if hero_name:
                                            special_hero = hero_name["zh_tw"]
                                        special_heroes[specific_target] = special_hero
                                    # 检查是否有delay
                                    if buff.get("delay"):
                                        delay_seconds = buff.get("delay")
                                        delay_text = get_string_ui(data, buff.get("buff_tooltip_sno"))['zh_tw']
                            i += 1
        
        # 获取护盾削减系数和解除眩晕时间
        groggy_info = []
        recovery_duration = 0
        if boss_data and boss_data.get("no"):
            for groggy in data["single_raid_boss_groggy_trigger"]["json"]:
                if groggy.get("single_raid_boss_no") == boss_data.get("no"):
                    # 获取解除眩晕时间
                    recovery_duration = groggy.get("recovery_duration", 0)
                    
                    for status_code, status_name in SINGLE_RAID_GROGGY_TRIGGER_MAPPING.items():
                        # 计算数组索引
                        array_index = status_code - 201
                        # 检查该索引位置的值是否在type中
                        type_value = SINGLE_RAID_GROGGY_TRIGGER_ARRAY[array_index]
                        type_key = f"type_{type_value}"
                        value_key = f"value_{type_value}"
                        
                        # 如果type和value都存在
                        if type_key in groggy and value_key in groggy:
                            value = groggy.get(value_key)
                            groggy_info.append(f"{status_name}类技能：{value}")
        
        # 构建消息
        messages = []
        basic_info = []
        
        # 获取立绘
        portrait_path = get_character_portrait(data, hero_id, hero_name_en, raid=True)
        basic_info.append(f"【恶灵讨伐：{hero_name_zh_tw}】")
        if portrait_path:
            basic_info.append(MessageSegment.image(f"file:///{portrait_path}"))
        
        basic_info_text = f"""类型：{race_zh_tw} {hero_class_zh_tw}
攻击方式：{sub_class_zh_tw}
属性：{stat_zh_tw}
等级：{boss_data.get('boss_max_level', 0)}
护盾量：{format_number(boss_data.get('groggy_ratio', 0))}
生命值：{format_number(final_hp)}
战斗时长：{battle_time}秒
{season_info if season_info else ""}
击杀奖励：
{chr(10).join(f"- {item}" for item in reward_items)}"""

        if interaction_info:
            basic_info_text += f"\n\n有开场台词的角色：\n{chr(10).join(f'- {name}' for name in interaction_info)}"
            
        if special_heroes:
            basic_info_text += f"\n\n特殊之人：\n{chr(10).join(f'- {name}' for name in special_heroes.values())}"

        if delay_text:
            basic_info_text += f"\n\n特殊情况：开场{delay_seconds}秒后{delay_text}"
            
        if groggy_info:
            basic_info_text += f"\n\n护盾削减系数：\n{chr(10).join(f'- {info}' for info in groggy_info)}"
            basic_info_text += f"\n护盾削减量为 护盾削减系数 * 技能持续时间"
            if recovery_duration > 0:
                basic_info_text += f"\n解除眩晕时间：{recovery_duration}秒"
        
        basic_info.append(basic_info_text)
        
        # 添加攻略
        if guide_text:
            basic_info.append(f"\n【讨伐攻略】\n{clean_tags(guide_text)}")
        
        messages.append("\n".join(str(x) for x in basic_info))
        
        # 构建转发消息
        forward_msgs = []
        for msg in messages:
            # 如果消息是字符串，直接添加
            if isinstance(msg, str):
                forward_msgs.append({
                    "type": "node",
                    "data": {
                        "name": "EverSoul Evil Raid",
                        "uin": bot.self_id,
                        "content": msg
                    }
                })
            # 如果消息是列表（包含图片），将其合并
            elif isinstance(msg, list):
                forward_msgs.append({
                    "type": "node",
                    "data": {
                        "name": "EverSoul Evil Raid",
                        "uin": bot.self_id,
                        "content": "\n".join(str(x) for x in msg)
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
                f"处理恶灵讨伐信息时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )
            await es_single_raid.finish(f"处理恶灵讨伐信息时发生错误: {str(e)}") 