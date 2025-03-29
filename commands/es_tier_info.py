import re
from pathlib import Path
from nonebot import on_command
from nonebot.exception import FinishedException
from zhenxun.services.log import logger
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import (
    Bot,
    Event,
    Message,
    MessageSegment,
    GroupMessageEvent
)
from ..libraries.es_utils import *

es_tier_info = on_command("es礼品信息", priority=0, block=True)


@es_tier_info.handle()
async def handle_tier_info(bot: Bot, event: Event, args: Message = CommandArg()):
    try:
        # 解析参数
        args_text = args.extract_plain_text().strip()
        match = re.match(r'^(粉|红\+?)(\d*)(智力|敏捷|力量|共用)(加速|暴击率|防御力|体力|攻击力|回避|暴击威力)$', args_text)
        if not match:
            await es_tier_info.finish("格式错误！请使用如：es礼品信息粉1智力加速")
            return
            
        # 获取参数
        grade, level, stat_type, set_type = match.groups()
        
        # 加载数据
        # 获取群组ID
        group_id = None
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
        data = load_json_data(group_id)

        # 获取品质对应的grade_sno
        grade_map = {"粉": "不朽", "红+": "永恆＋"}
        if grade == "红+":
            grade_name = "永恆＋"  # 红+装备直接使用永恆＋
        elif grade == "粉" and not level:  # 如果是白色且没有等级
            grade_name = "不朽"
        elif grade == "粉" and level:  # 如果是白色且有等级
            grade_name = f"不朽+{level}"
        else:
            grade_name = f"{grade_map[grade]}+{level}"  # 其他装备加上等级
            
        grade_sno = next((s["no"] for s in data["string_system"]["json"] 
                         if s.get("zh_tw") == grade_name), None)
        
        # 获取属性限制对应的stat_limit_sno
        stat_sno = STAT_TYPE_MAPPING.get(stat_type)
        
        # 获取套装效果对应的set_effect_no
        set_no = EFFECT_TYPE_MAPPING.get(set_type)
        set_effect = next((e for e in data["item_set_effect"]["json"] 
                          if e.get("name") == set_no), None)
        
        if not all([grade_sno, stat_sno, set_effect]):
            await es_tier_info.finish("未找到对应的礼品信息")
            return
            
        # 查找符合条件的礼品
        items = []
        for item in data["item"]["json"]:
            if ((item.get("category_sno") == 110002 or item.get("category_sno") == 110078) and 
                item.get("grade_sno") == grade_sno and
                item.get("stat_limit_sno") == stat_sno and
                item.get("set_effect_no") == set_effect["no"]):
                items.append(item)
        
        if not items:
            await es_tier_info.finish("未找到符合条件的礼品")
            return
            
        messages = []
        for item in items:
            try:
                # 获取礼品基本信息
                name = next((s.get("zh_tw", "未知") for s in data["string_item"]["json"] 
                           if s["no"] == item.get("name_sno")), "未知")
                desc = next((s.get("zh_tw", "") for s in data["string_item"]["json"] 
                           if s["no"] == item.get("desc_sno")), "")
                
                # 获取图标路径
                icon_base = item.get("icon_path", "")
                if icon_base:
                    # 构建完整的图片路径
                    icon_path = str(TIER_DIR / f"{icon_base}.png")
                    # 检查文件是否存在
                    if Path(icon_path).exists():
                        img_msg = MessageSegment.image(f"file:///{icon_path}")
                    else:
                        img_msg = "[图片未找到]"
                else:
                    img_msg = "[无图片信息]"
                
                 # 获取最高等级的属性信息
                max_stat = max((s for s in data["item_stat"]["json"] 
                              if s.get("no") == item.get("no")), 
                             key=lambda x: x.get("level", 0))
                
                # 获取套装效果
                set2_buff_no = set_effect.get("set2_contentsbuff")
                set4_buff_no = set_effect.get("set4_contentsbuff")
                
                set2_buff = {}
                set4_buff = {}
                
                if set2_buff_no:
                    set2_buff = next((buff for buff in data["contents_buff"]["json"] 
                                    if buff.get("no") == set2_buff_no), {})
                if set4_buff_no:
                    set4_buff = next((buff for buff in data["contents_buff"]["json"] 
                                    if buff.get("no") == set4_buff_no), {})
                
                 # 构建消息
                msg = [
                    f"━━━━━━━━━━━━━━━",
                    str(img_msg),
                    f"【{name}】",
                    f"品质：{grade_name}",
                    f"描述：{desc}",
                    f"\n【最大属性】(等级{max_stat.get('level')})",
                    f"・ 满级所需经验：{format_number(max_stat.get('sum_exp', 0))}",
                    f"・ 满级战斗力：{format_number(max_stat.get('battle_power', 0))}"
                ]

                # 添加基础属性和额外属性
                base_stats = []
                extra_stats = []

                # 获取所有属性（排除特定键）
                exclude_keys = {"index", "no", "level", "exp", "sum_exp", "battle_power", "battle_power_per"}
                stat_items = [(k, v) for k, v in max_stat.items() 
                             if k not in exclude_keys and v and k in STAT_NAME_MAPPING]
                
                # 前三个是基础属性，之后的是额外属性
                for i, (stat, value) in enumerate(stat_items):
                    stat_display = STAT_NAME_MAPPING[stat]
                    if isinstance(value, float):
                        value_str = f"{value*100:.1f}%"
                    else:
                        value_str = format_number(value)
                        
                    if i < 3:  # 基础属性
                        base_stats.append(f"・ {stat_display}：{value_str}")
                    else:  # 额外属性
                        extra_stats.append(f"・ {stat_display}：{value_str}")
                
                # 添加基础属性
                if base_stats:
                    msg.append("\n基础属性：")
                    msg.extend(base_stats)
                
                # 添加额外属性
                if extra_stats:
                    msg.append("\n额外增益：")
                    msg.extend(extra_stats)
                
                
                
                # 添加套装效果
                msg.extend([
                    f"\n【套装效果】",
                    f"2件套效果："
                ])
                
                # 添加2件套效果
                has_2set = False
                for stat, value in set2_buff.items():
                    if stat in STAT_NAME_MAPPING and value:
                        has_2set = True
                        stat_display = STAT_NAME_MAPPING[stat]
                        msg.append(f"・ {stat_display}：{value*100:.1f}%")
                if not has_2set:
                    msg.append("・ 无效果")
                
                # 添加4件套效果
                msg.append(f"4件套效果：")
                has_4set = False
                for stat, value in set4_buff.items():
                    if stat in STAT_NAME_MAPPING and value:
                        has_4set = True
                        stat_display = STAT_NAME_MAPPING[stat]
                        msg.append(f"・ {stat_display}：{value*100:.1f}%")
                if not has_4set:
                    msg.append("・ 无效果")
                
                msg.append("━━━━━━━━━━━━━━━")
                messages.append("\n".join(msg))
            
            except Exception as e:
                logger.error(f"处理礼品图片时发生错误: {e}")
                continue
        
        # 发送合并转发消息
        forward_msgs = []
        for msg in messages:
            forward_msgs.append({
                "type": "node",
                "data": {
                    "name": "Tier Info",
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
                f"处理礼品信息时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )
            await es_tier_info.finish(f"处理礼品信息时发生错误: {str(e)}")

