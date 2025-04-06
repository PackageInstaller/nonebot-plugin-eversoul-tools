from ..libraries.utils import *


@es_stage_info.handle()
async def handle_stage_info(bot: Bot, event: Event, args: Message = CommandArg()):
    # 创建图像资源
    fig = None
    buf = None
    
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
            await es_stage_info.finish(f"未找到对应的关卡信息")
        
        # 构建消息
        messages = []

        # 基础信息
        basic_info = []
        basic_info.append(f"关卡 {area_no}-{stage_no} 信息：")
        
        # 获取关卡类型
        level_type = ""
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
                item_name = get_string_item(data, item_no)
                amount = stage_data.get(amount_key, 0)
                messages.append(f"固定掉落物品{i}：\n{item_name['zh_tw']} x{amount}")

        # 获取关卡编号
        stage_no = stage_data["no"]

        # 查找敌方队伍信息
        battle_teams = []
        for battle in data["stage_battle"]["json"]:
            if battle["no"] == stage_no:
                battle_teams.append(battle)
        
        # 如果有敌方队伍信息，添加到消息中
        if battle_teams:
            # 按team_no排序
            battle_teams.sort(key=lambda x: x.get("team_no", 0))
            
            # 首先收集所有队伍中所有角色的名称，找出最长的名称长度
            max_name_length = 0
            hero_infos = []
            
            # 计算字符串的显示宽度，中文字符算两个宽度
            def get_display_width(s):
                width = 0
                for char in s:
                    if '\u4e00' <= char <= '\u9fff':  # 中文字符范围
                        width += 2
                    else:
                        width += 1
                return width
            
            # 使用显示宽度填充字符串到指定宽度
            def pad_string(s, width):
                current_width = get_display_width(s)
                if current_width < width:
                    return s + ' ' * (width - current_width)
                return s
            
            # 收集所有角色信息
            for team in battle_teams:
                team_heroes = []
                for i in range(1, 6):  # 检查5个角色位置
                    hero_key = f"hero_no{i}"
                    grade_key = f"hero_grade{i}"
                    level_key = f"level{i}"
                    
                    if hero_no := team.get(hero_key):
                        hero_name_data = get_string_character(data, hero_no, special=True)
                        hero_name_zh_tw = hero_name_data["zh_tw"]
                        
                        grade_data = get_string_system(data, team.get(grade_key))
                        grade_name_zh_tw = grade_data["zh_tw"]
                        
                        level = team.get(level_key, 0)
                        
                        # 获取显示宽度
                        display_width = get_display_width(hero_name_zh_tw)
                        
                        # 更新最长名称显示宽度
                        max_name_length = max(max_name_length, display_width)
                        
                        # 保存角色信息
                        team_heroes.append({
                            "position": i,
                            "name": hero_name_zh_tw,
                            "grade": grade_name_zh_tw,
                            "level": level,
                            "name_width": display_width
                        })
                hero_infos.append({"team_no": team.get("team_no", "?"), "formation": get_formation_type(team.get("formation_type")), "heroes": team_heroes})
            
            for team_info in hero_infos:
                team_text = [f"敌方队伍 {team_info['team_no']}："]
                team_text.append(f"阵型：{team_info['formation']}")
                
                for hero in team_info["heroes"]:
                    # 使用固定宽度的角色名栏位
                    pos_text = f"位置{hero['position']}："
                    name_column_width = max_name_length + 2  # 额外添加空间确保对齐
                    
                    # 计算需要的空格数
                    spaces_needed = name_column_width - hero["name_width"]
                    spacer = " " * spaces_needed
                    
                    # 构建对齐的文本行
                    team_text.append(f"{pos_text}{hero['name']}{spacer}{hero['grade']}  Lv.{hero['level']}")
                
                messages.append("\n".join(team_text))

        # 使用matplotlib绘制图片
        all_text = "\n\n".join(messages)
        
        # 设置字体
        font_prop = CUSTOM_FONT
        
        # 计算图像大小
        text_lines = all_text.split('\n')
        max_length = max(len(line) for line in text_lines)
        fig_width = max(max_length * 0.12, 8)  # 确保最小宽度
        fig_height = max(len(text_lines) * 0.25, 5)  # 确保最小高度
        
        # 创建图像
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))
        ax.axis('off')  # 隐藏坐标轴
        fig.patch.set_facecolor('white')  # 设置背景颜色为白色
        
        # 尝试渲染每行文本，确保对齐
        y_position = 0.95
        line_height = 0.025  # 行高
        
        # 找出每队中的最大位置文本长度
        for message in messages:
            lines = message.split('\n')
            ax.text(0.05, y_position, lines[0], fontsize=14, ha='left', va='top', 
                   fontproperties=font_prop, transform=ax.transAxes)
            y_position -= line_height
            
            if len(lines) > 1:
                ax.text(0.05, y_position, lines[1], fontsize=14, ha='left', va='top', 
                       fontproperties=font_prop, transform=ax.transAxes)
                y_position -= line_height
            
            # 处理位置行，确保对齐
            position_x = 0.05   # 初始位置
            name_x = 0.15       # 名称开始位置
            attr_x = 0.35       # 属性开始位置 - 减少与名称的距离
            
            for i in range(2, len(lines)):
                line = lines[i]
                parts = line.split('：', 1)
                
                if len(parts) == 2 and parts[0].startswith('位置'):
                    # 绘制位置标签
                    ax.text(position_x, y_position, parts[0] + '：', fontsize=14, ha='left', va='top', 
                           fontproperties=font_prop, transform=ax.transAxes)
                    
                    # 分解名称和属性
                    name_attr = parts[1].strip()
                    name_end_idx = 0
                    # 找出名称结束的位置（连续空格开始的地方）
                    for j in range(len(name_attr)):
                        if name_attr[j] == ' ' and j < len(name_attr)-1 and name_attr[j+1] == ' ':
                            name_end_idx = j
                            break
                    
                    if name_end_idx > 0:
                        name = name_attr[:name_end_idx].strip()
                        attr = name_attr[name_end_idx:].strip()
                        
                        # 绘制名称和属性，分开放置以确保对齐
                        ax.text(name_x, y_position, name, fontsize=14, ha='left', va='top', 
                               fontproperties=font_prop, transform=ax.transAxes)
                        ax.text(attr_x, y_position, attr, fontsize=14, ha='left', va='top', 
                               fontproperties=font_prop, transform=ax.transAxes)
                    else:
                        # 如果无法分解，则直接放置整行
                        ax.text(name_x, y_position, name_attr, fontsize=14, ha='left', va='top', 
                               fontproperties=font_prop, transform=ax.transAxes)
                else:
                    # 非位置行，直接放置
                    ax.text(position_x, y_position, line, fontsize=14, ha='left', va='top', 
                           fontproperties=font_prop, transform=ax.transAxes)
                
                y_position -= line_height
            
            # 每个队伍之间增加额外间距
            y_position -= line_height
        
        # 保存图像到内存
        buf = io.BytesIO()
        plt.savefig(buf, format='webp', dpi=100, bbox_inches='tight', transparent=False, 
                   pil_kwargs={'quality': 30})
        buf.seek(0)
        
        # 发送图片
        await es_stage_info.finish(MessageSegment.image(buf))

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
            await es_stage_info.finish(f"处理关卡信息时发生错误: {str(e)}\n请联系机器人开发者反馈")
    finally:
        # 在finally块中安全释放资源
        if buf:
            try:
                buf.close()
            except:
                pass
        if fig:
            try:
                plt.close(fig)
            except:
                pass
        try:
            plt.close('all')
        except:
            pass