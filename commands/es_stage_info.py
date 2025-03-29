import re
from nonebot import on_command
from nonebot.exception import FinishedException
from zhenxun.services.log import logger
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import (
    Bot,
    Event,
    Message,
    GroupMessageEvent
)
from ..libraries.es_utils import *

es_stage_info = on_command("es主线信息", priority=0, block=True)


@es_stage_info.handle()
async def handle_stage_info(bot: Bot, event: Event, args: Message = CommandArg()):
    try:
        # 获取参数文本
        stage_text = args.extract_plain_text().strip()
        # 获取群组ID
        group_id = None
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
        # 检查格式
        match = re.match(r'^(\d+)-(\d+)$', stage_text)
        if not match:
            return
        
        area_no = int(match.group(1))
        stage_no = int(match.group(2))
        
        # 加载数据
        data = load_json_data(group_id)
        
        # 查找关卡信息
        main_stage = None
        
        for stage in data["stage"]["json"]:
            if stage.get("area_no") == area_no and stage.get("stage_no") == stage_no:
                if "exp" in stage:
                    main_stage = stage
                    break  # 找到主线关卡就直接跳出
        
        # 优先使用主线关卡，如果没有则使用其他关卡
        stage_data = main_stage
        
        if not main_stage:
            await es_stage_info.finish(f"未找到关卡 {area_no}-{stage_no} 的信息")
            return
        
        # 构建消息
        messages = []

        # 基础信息
        basic_info = []
        basic_info.append(f"关卡 {area_no}-{stage_no} 信息：")
        
        # 获取关卡类型
        level_type = "未知类型"
        for system in data["string_system"]["json"]:
            if system["no"] == stage_data.get("level_type"):
                level_type = system.get("zh_tw", "未知类型")
                break
        basic_info.append(f"关卡类型：{level_type}")
        basic_info.append(f"经验值：{stage_data.get('exp', 0)}")
        messages.append("\n".join(basic_info))
        
        # 固定掉落物品，按组分类
        for i in range(1, 5):  # 检查item_no1到item_no4
            item_key = f"item_no{i}"
            amount_key = f"amount{i}"
            if item_no := stage_data.get(item_key):
                item_name = get_item_name(data, item_no)
                amount = stage_data.get(amount_key, 0)
                messages.append(f"固定掉落物品{i}：\n{item_name} x{amount}")

        # 获取关卡编号
        stage_no = stage_data["no"]

        # 获取主线突发礼包信息
        cash_item_messages = get_cash_item_info(data, "stage", stage_data)
        messages.extend(cash_item_messages)

        # 查找敌方队伍信息
        battle_teams = []
        for battle in data["stage_battle"]["json"]:
            if battle["no"] == stage_no:
                battle_teams.append(battle)
        
        # 如果有敌方队伍信息，添加到消息中
        if battle_teams:
            # 按team_no排序
            battle_teams.sort(key=lambda x: x.get("team_no", 0))
            
            for team in battle_teams:
                team_info = [f"\n敌方队伍 {team.get('team_no', '?')}："]
                team_info.append(f"阵型：{get_formation_type(team.get('formation_type'))}")
                
                # 添加每个角色的信息
                for i in range(1, 6):  # 检查5个角色位置
                    hero_key = f"hero_no{i}"
                    grade_key = f"hero_grade{i}"
                    level_key = f"level{i}"
                    
                    if hero_no := team.get(hero_key):
                        hero_name_zh_tw, hero_name_zh_cn, hero_name_kr, hero_name_en = get_hero_name(data, hero_no)
                        grade_name_zh_tw, grade_name_zh_cn, grade_name_kr, grade_name_en = get_grade_name(data, team.get(grade_key))
                        level = team.get(level_key, 0)
                        
                        team_info.append(f"位置{i}：{hero_name_zh_tw} {grade_name_zh_tw} {level}级")
                
                messages.append("\n".join(team_info))

        # 发送合并转发消息
        forward_msgs = []
        for msg in messages:
            forward_msgs.append({
                "type": "node",
                "data": {
                    "name": "Stage Info",
                    "uin": bot.self_id,
                    "content": msg
                }
            })
        
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
                f"处理关卡信息时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )
            await es_stage_info.finish(f"处理关卡信息时发生错误: {str(e)}")