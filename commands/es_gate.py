from typing import Tuple, Any
from nonebot import on_regex
from nonebot.exception import FinishedException
from zhenxun.services.log import logger
from nonebot.params import RegexGroup
from nonebot.adapters.onebot.v11 import (
    Bot,
    Event,
    GroupMessageEvent
)
from ..libraries.es_utils import *

es_gate = on_regex(r"es(自由|人类|野兽|妖精|不死)传送门信息(\d+)", priority=5, block=True)


@es_gate.handle()
async def handle_gate_info(bot: Bot, event: Event, matched: Tuple[Any, ...] = RegexGroup()):
    try:
        # 获取传送门类型和关卡编号
        gate_type = matched[0]
        stage_no = int(matched[1])
        
        # 加载数据
        # 获取群组ID
        group_id = None
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
        data = load_json_data(group_id)
        
        # 从Barrier.json获取传送门基本信息
        barrier_info = None
        for barrier in data["barrier"]["json"]:
            if barrier.get("stage_type") == GATE_TYPES[gate_type]:
                barrier_info = barrier
                break
        
        if not barrier_info:
            await es_gate.finish(f"未找到{gate_type}型传送门信息")
            return
            
        # 获取传送门名称和限制
        gate_name = next((s.get("zh_tw", "未知") for s in data["string_stage"]["json"] 
                         if s["no"] == barrier_info.get("text_name_sno")), "未知")
        race_restriction = next((s.get("zh_tw", "") for s in data["string_system"]["json"] 
                               if s["no"] == barrier_info.get("restrictions_race_sno")), "")
        
        # 获取开放日期
        open_days = barrier_info.get("open_day", "").split(",")
        day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        open_days_str = "、".join(day_names[int(d)-1] for d in open_days)
        
        # 查找所有对应的传送门信息
        gate_infos = []
        for stage in data["stage"]["json"]:
            if stage.get("stage_type") == GATE_TYPES[gate_type] and stage.get("stage_no") == stage_no:
                gate_infos.append(stage)
        
        if not gate_infos:
            await es_gate.finish(f"未找到编号为 {stage_no} 的{gate_type}传送门")
            return
        
        # 对每个传送门生成信息
        all_messages = []

        # 添加传送门基本信息
        all_messages.append(f"━━━━━━━━━━━━━━━\n{gate_name}\n━━━━━━━━━━━━━━━")
        all_messages.append(f"开放日期：{open_days_str}")
        if race_restriction:
            all_messages.append(f"限制种族：{race_restriction}")
        all_messages.append("━━━━━━━━━━━━━━━\n")
        
        for gate_info in gate_infos:
            messages = []
            
            # 获取关卡名称
            name_sno = gate_info.get("name_sno")
            stage_name = ""
            for string in data["string_stage"]["json"]:
                if string["no"] == name_sno:
                    stage_name = string.get("zh_tw", "未知")
                    stage_name = stage_name.format(stage_no)
                    break
                    
            messages.append(f"━━━━━━━━━━━━━━━\n{stage_name}\n━━━━━━━━━━━━━━━")
            
            # 获取奖励信息
            rewards = []
            for i in range(1, 3):
                item_no = gate_info.get(f"item_no{i}")
                amount = gate_info.get(f"amount{i}")
                if item_no and amount:
                    item_name = get_item_name(data, item_no)
                    rewards.append(f"・ {item_name} x{amount}")
            
            if rewards:
                messages.append("\n【通关奖励】")
                messages.extend(rewards)
            
            # 获取通关礼包信息
            cash_item_messages = get_cash_item_info(data, "barrier", gate_info)
            messages.extend(cash_item_messages)
            
            # 获取敌方队伍信息
            battle_teams = []
            for battle in data["stage_battle"]["json"]:
                if battle["no"] == gate_info["no"]:
                    battle_teams.append(battle)
            
            if battle_teams:
                battle_teams.sort(key=lambda x: x.get("team_no", 0))
                for team in battle_teams:
                    messages.append(f"\n【敌方队伍 {team.get('team_no', '?')}】")
                    messages.append(f"▼ 阵型：{get_formation_type(team.get('formation_type'))}")
                    
                    # 添加每个角色的信息
                    for i in range(1, 6):
                        hero_no = team.get(f"hero_no{i}")
                        if not hero_no:
                            continue
                            
                        hero_name_zh_tw, hero_name_zh_cn, hero_name_kr, hero_name_en = get_hero_name(data, hero_no)
                        grade_name_zh_tw, grade_name_zh_cn, grade_name_kr, grade_name_en = get_grade_name(data, team.get(f"hero_grade{i}"))
                        level = team.get(f"level{i}", 0)
                        
                        messages.append(f"\n位置{i}：{hero_name_zh_tw}")
                        messages.append(f"・ 等级：{level}")
                        messages.append(f"・ 品质：{grade_name_zh_tw}")
                        
                        # 检查装备信息
                        if equip_no := team.get(f"hero_equip{i}"):
                            equip_data = next((e for e in data["stage_equip"]["json"] if e["no"] == equip_no), None)
                            if equip_data:
                                messages.append("・ 装备：")
                                for slot in range(1, 5):
                                    if item_no := equip_data.get(f"slot{slot}"):
                                        item_name = get_item_name(data, item_no)
                                        level = equip_data.get(f"level{slot}", 0)
                                        messages.append(f"  - {item_name} Lv.{level}")
                        
                        # 检查终极技能优先级
                        if ult_priority := team.get(f"ultimate_autosetting{i}"):
                            messages.append(f"・ 终极技能优先级：{ult_priority}")
                    
                    # 检查遗物信息
                    if sig_level := team.get("signature_level"):
                        messages.append(f"\n· 遗物等级：{sig_level}")
                    if sig_skill_level := team.get("signature_skill_level"):
                        messages.append(f"・ 遗物技能等级：{sig_skill_level}")
                    messages.append("-" * 25)
            
            # 添加分隔线
            if gate_info != gate_infos[-1]:
                messages.append("\n" + "=" * 30 + "\n")
            
            all_messages.extend(messages)
        
        # 发送合并转发消息
        forward_msgs = [{
            "type": "node",
            "data": {
                "name": "Gate Info",
                "uin": bot.self_id,
                "content": "\n".join(all_messages)
            }
        }]
        
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
                f"处理传送门信息时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )
            await es_gate.finish(f"处理传送门信息时发生错误: {str(e)}")