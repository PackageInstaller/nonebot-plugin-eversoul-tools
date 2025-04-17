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
        group_id = None
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
            reward_items.append(f"{item_name['zh_tw']} x {item_amount}")
        
        if boss_data.get("reward_item2_no"):
            item_name = get_string_item(data, boss_data.get("reward_item2_no"))
            item_amount = boss_data.get("reward_item2_amount", 0)
            reward_items.append(f"{item_name['zh_tw']} x {item_amount}")
        
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
击杀奖励：
{chr(10).join(f"- {item}" for item in reward_items)}"""
        
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