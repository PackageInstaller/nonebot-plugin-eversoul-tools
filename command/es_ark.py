from ..library.utils import *


@es_ark_info.handle()
async def handle_ark_info(bot: Bot, event: Event, args: Message = CommandArg()):
    try:
        # 获取目标等级
        target_level = args.extract_plain_text().strip()
        if not target_level:
            await es_ark_info.finish("请输入正确的格式：es方舟等级信息+等级")
        target_level = int(target_level)
        
        # 加载数据
        # 获取群组ID
        group_id = 0
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
        data = load_json_data(group_id)
        
        # 存储不同类型的方舟信息
        ark_types = {
            110051: [],  # 主方舟
            110101: [],  # 战士
            110102: [],  # 游侠
            110103: [],  # 斗士
            110104: [],  # 魔法师
            110105: [],  # 辅助
            110106: []   # 捍卫者
        }
        
        # 收集所有符合等级的方舟信息
        for ark in data["ark_enhance"]["json"]:
            if ark.get("core_level") == target_level:
                core_type = ark.get("core_type_02")
                if core_type in ark_types:
                    ark_types[core_type].append(ark)
        
        messages = []
        # 添加标题信息
        title_msg = [f"方舟等级 {target_level} 信息："]
        messages.append("".join(title_msg))
        
        # 处理每种类型的方舟
        for core_type, arks in ark_types.items():
            if not arks:
                continue
                
            # 获取方舟类型名称
            type_name = next((s.get("zh_tw", "未知类型") for s in data["string_system"]["json"] 
                            if s["no"] == core_type), "未知类型")
            
            # 主方舟名称适配
            if type_name == "所有":
                type_name = "主要"
            ark_msg = []
            ark_msg.append(f"【{type_name}】")
            
            for ark in arks:
                # 获取升级材料信息
                item_name = "未知材料"
                for item in data["item"]["json"]:
                    if item["no"] == ark.get("pay_item_no"):
                        item_name = next((s.get("zh_tw", "未知材料") for s in data["string_item"]["json"] 
                                       if s["no"] == item.get("name_sno")), "未知材料")
                        break
                
                ark_msg.append(f"升级消耗：{item_name}x{ark.get('pay_amount', 0)}")
                
                # 获取基础属性加成
                if buff_no := ark.get("contents_buff_no"):
                    found_buff = False
                    for buff in data["contents_buff"]["json"]:
                        if buff.get("no") == buff_no:
                            found_buff = True
                            ark_msg.append("基础属性加成：")
                            if buff.get("battle_power"):
                                ark_msg.append(f"・ 战斗力加成：{buff.get('battle_power')}")
                            if buff.get("battle_power_per"):
                                ark_msg.append(f"・ 每级战斗力加成：{buff.get('battle_power_per')}")
                            for key, value in buff.items():
                                if key in STAT_NAME_MAPPING and value != 0:
                                    if key.endswith('_rate'):
                                        ark_msg.append(f"・ {STAT_NAME_MAPPING[key]}：{value*100:.2f}%")
                                    else:
                                        ark_msg.append(f"・ {STAT_NAME_MAPPING[key]}：{format_number(value)}")
                    if not found_buff:
                        ark_msg.append("基础属性加成：数据未找到")
                
                # 获取特殊属性加成
                if sp_buff_value := ark.get("sp_buff_value02"):
                    found_buff = False
                    for buff in data["contents_buff"]["json"]:
                        if buff.get("no") == int(sp_buff_value):
                            found_buff = True
                            ark_msg.append("特殊属性加成：")
                            if buff.get("battle_power"):
                                ark_msg.append(f"・ 战斗力加成：{buff.get('battle_power')}")
                            if buff.get("battle_power_per"):
                                ark_msg.append(f"・ 每级战斗力加成：{buff.get('battle_power_per')}")
                            for key, value in buff.items():
                                if key in STAT_NAME_MAPPING and value != 0:
                                    ark_msg.append(f"・ {STAT_NAME_MAPPING[key]}：{value*100:.2f}%")
                    if not found_buff:
                        ark_msg.append("特殊属性加成：数据未找到")
            
            messages.append("\n".join(ark_msg))
            
        # 构建转发消息
        forward_msgs = []
        for msg in messages:
            forward_msgs.append({
                "type": "node",
                "data": {
                    "name": "EverSoul Ark Info",
                    "uin": bot.self_id,
                    "content": msg
                }
            })
        
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
                f"处理方舟等级信息时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )
            await es_ark_info.finish(f"处理方舟等级信息时发生错误: {str(e)}")