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

es_cash_pack_info = on_command("es突发礼包信息", priority=5, block=True)


@es_cash_pack_info.handle()
async def handle_cash_pack_info(bot: Bot, event: Event, args: Message = CommandArg()):
    try:
        # 获取参数文本
        args_text = args.extract_plain_text().strip()
        
        # 检查是否是主线章节
        match_main = re.match(r'^主线(\d+)$', args_text)
        # 检查是否是传送门类型
        match_gate = re.match(r'^(自由|人类|野兽|妖精|不死)传送门$', args_text)
        
        if match_main:
            item_type = "主线"
            chapter = match_main.group(1)
        elif match_gate:
            item_type = "传送门"
            gate_type = match_gate.group(1)
        else:
            if args_text == "主线":
                await es_cash_pack_info.finish("请带上主线章节参数！例如：es突发礼包信息主线21")
                return
            elif args_text == "传送门":
                await es_cash_pack_info.finish("请带上传送门类型参数！例如：es突发礼包信息自由传送门")
                return
            item_type = args_text
            chapter = None
            gate_type = None
        
        # 加载数据
        # 获取群组ID
        group_id = None
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
        data = load_json_data(group_id)
        messages = []
        
        if item_type == "主线":
            # 获取所有主线关卡信息
            for stage in data["stage"]["json"]:
                if "exp" in stage:  # 确认是主线关卡
                    area_no = stage.get("area_no")
                    # 如果指定了章节，只处理对应章节的关卡
                    if chapter and str(area_no) != chapter:
                        continue
                        
                    stage_no = stage.get("stage_no")
                    # 获取关卡编号
                    stage_no_id = stage.get("no")
                    if stage_no_id:
                        # 构建一个包含no的字典
                        stage_info = {"no": stage_no_id}
                        package_msgs = get_cash_item_info(data, "stage", stage_info)
                        if package_msgs:
                            messages.append(f"\n主线关卡 {area_no}-{stage_no}:")
                            messages.extend(package_msgs)
            
            if not messages:
                chapter_text = f"第{chapter}章" if chapter else "所有章节"
                await es_cash_pack_info.finish(f"当前{chapter_text}没有主线相关的突发礼包")
                return
        
        elif item_type == "传送门":
            # 获取传送门类型对应的stage_type
            stage_type = GATE_TYPES.get(gate_type)
            if not stage_type:
                await es_cash_pack_info.finish(f"未知的传送门类型：{gate_type}")
                return
            
            # 从Barrier.json获取传送门基本信息
            barrier_info = None
            for barrier in data["barrier"]["json"]:
                if barrier.get("stage_type") == stage_type:
                    barrier_info = barrier
                    break
            
            if barrier_info:
                # 获取传送门名称
                gate_name = next((s.get("zh_tw", "未知") for s in data["string_stage"]["json"] 
                                if s["no"] == barrier_info.get("text_name_sno")), "未知")
                messages.append(f"\n{gate_name}:")
                
                # 获取所有对应类型的关卡
                for stage in data["stage"]["json"]:
                    if stage.get("stage_type") == stage_type:
                        stage_no = stage.get("stage_no")
                        # 获取关卡名称
                        name_sno = stage.get("name_sno")
                        stage_name = ""
                        for string in data["string_stage"]["json"]:
                            if string["no"] == name_sno:
                                stage_name = string.get("zh_tw", "未知")
                                stage_name = stage_name.format(stage_no)
                                break
                        
                        # 获取通关礼包信息
                        package_msgs = get_cash_item_info(data, "barrier", stage)  # 直接传入stage对象
                        if package_msgs:
                            messages.append(f"\n{stage_name}:")
                            messages.extend(package_msgs)
            
            if len(messages) <= 1:  # 只有标题没有实际内容
                await es_cash_pack_info.finish(f"当前没有{gate_type}型传送门相关的突发礼包")
                return
        
        elif item_type == "起源塔":
            # 获取所有起源之塔信息
            for tower in data["tower"]["json"]:
                hero_id = tower.get("req_hero")
                tower_no = tower.get("no")
                
                # 获取角色名称
                hero_name = ""
                for hero in data["hero"]["json"]:
                    if hero["hero_id"] == hero_id:
                        for char in data["string_character"]["json"]:
                            if char["no"] == hero["name_sno"]:
                                hero_name = char.get("zh_tw", "")
                                break
                        break
                
                tower_name = f"{hero_name}的起源之塔"
                
                # 查找对应的礼包信息
                tower_packages = []
                for shop_item in data["cash_shop_item"]["json"]:
                    if shop_item.get("type") == "tower":
                        type_values = shop_item.get("type_value", "").split(",")
                        type_values = [v.strip() for v in type_values]
                        if str(tower_no) in type_values:
                            tower_packages.append(shop_item)
                
                if tower_packages:
                    messages.append(f"{tower_name}:")
                    for package in tower_packages:
                        # 构建一个简单的字典来匹配get_cash_item_info的参数要求
                        dummy_info = {"no": tower_no}
                        # 临时保存原始type_value
                        original_type_value = package["type_value"]
                        # 修改type_value以匹配get_cash_item_info的处理逻辑
                        package["type_value"] = str(tower_no)
                        package_msgs = get_cash_item_info(data, "tower", dummy_info)
                        # 还原原始type_value
                        package["type_value"] = original_type_value
                        messages.extend(package_msgs)
                    
        elif item_type == "升阶":
            # 获取所有角色升阶礼包信息
            for shop_item in data["cash_shop_item"]["json"]:
                if shop_item.get("type") == "grade_eternal":
                    # 构建一个简单的字典来匹配get_cash_item_info的参数要求
                    dummy_info = {"no": shop_item.get("type_value")}
                    package_msgs = get_cash_item_info(data, "grade_eternal", dummy_info)
                    if package_msgs:
                        messages.extend(package_msgs)
        
        else:
            await es_cash_pack_info.finish("请输入正确的类型：主线/传送门/起源塔/升阶")
            return
        
        if not messages:
            await es_cash_pack_info.finish(f"当前没有{item_type}相关的突发礼包")
            return
        
        # 发送合并转发消息
        forward_msgs = [{
            "type": "node",
            "data": {
                "name": "EverSoul Overclock Cost",
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
                f"处理突发礼包信息时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )
            await es_cash_pack_info.finish(f"处理突发礼包信息时发生错误: {str(e)}")