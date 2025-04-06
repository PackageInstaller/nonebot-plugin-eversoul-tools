from ..libraries.utils import *



@es_hero_list.handle()
async def handle_hero_list(bot: Bot, event: Event):
    """处理角色列表查询"""
    # 创建图像资源
    fig = None
    buf = None
    
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
            race_data = get_string_system(data, hero_data["race_sno"])
            race_tw = race_data["zh_tw"]
            if not race_tw:
                continue
                
            # 初始化种族分类
            if race_tw not in hero_categories:
                hero_categories[race_tw] = []
            
            # 添加别名信息
            # aliases = hero.get("aliases", [])
            # alias_text = f"（{', '.join(aliases)}）" if aliases else ""
            
            # 添加角色信息
            hero_info = f"{name}"
            hero_categories[race_tw].append(hero_info)
        
        # 设置字体
        font_prop = CUSTOM_FONT
        
        # 计算布局
        # 对种族类型进行排序 
        sorted_categories = sorted([(category, sorted(heroes)) for category, heroes in hero_categories.items()])
        
        # 设定列数 - 可以根据需要调整
        num_columns = min(4, len(sorted_categories))  # 最多4列，或者更少
        
        # 计算每列应该包含的种族数量
        races_per_column = math.ceil(len(sorted_categories) / num_columns)
        
        # 划分列 - 简单平均分配
        columns = []
        for i in range(0, len(sorted_categories), races_per_column):
            columns.append(sorted_categories[i:i+races_per_column])
        
        # 确保列数正确
        num_columns = len(columns)
        
        # 计算每列最大宽度和高度
        column_widths = []
        column_heights = []
        
        for column in columns:
            # 计算这一列中所有行的最大宽度
            max_width = 0
            total_height = 0
            
            for category, heroes in column:
                # 计算标题和各行的最大宽度
                category_width = len(f"【{category}】")
                hero_widths = [len(f"・ {hero}") for hero in heroes]
                max_width = max(max_width, category_width, *hero_widths if hero_widths else [0])
                
                # 统计该种族的总高度 (标题 + 所有角色)
                total_height += 1 + len(heroes)
            
            column_widths.append(max_width)
            column_heights.append(total_height)
        
        # 计算图像尺寸
        # 宽度 = 所有列宽度和 * 字符宽度系数 + 列间距
        char_width = 0.08  # 每个字符的宽度
        column_spacing = 1.5  # 列间距（图像单位）
        fig_width = sum(w * char_width for w in column_widths) + (num_columns - 1) * column_spacing
        fig_width = max(fig_width, 10)  # 确保最小宽度
        
        # 高度 = 最高列的高度 * 行高
        line_height = 0.35  # 每行高度
        fig_height = max(column_heights) * line_height
        fig_height = max(fig_height, 6)  # 确保最小高度
        
        # 创建图像
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))
        ax.axis('off')  # 隐藏坐标轴
        fig.patch.set_facecolor('white')  # 设置背景颜色为白色
        
        # 添加标题
        ax.text(0.5, 0.98, "永魂灵魂角色列表", fontsize=16, ha='center', va='top', 
                fontproperties=font_prop, transform=ax.transAxes, fontweight='bold')
        
        # 计算每列的起始x位置
        x_positions = []
        x_pos = 0.05  # 初始x位置（左边距）
        
        for width in column_widths:
            x_positions.append(x_pos)
            x_pos += (width * char_width + column_spacing) / fig_width
        
        # 开始渲染每列内容
        for col_idx, column in enumerate(columns):
            y_pos = 0.94  # 初始y位置（顶部空间）
            x_pos = x_positions[col_idx]
            
            for category, heroes in column:
                # 渲染种族标题
                ax.text(x_pos, y_pos, f"【{category}】", fontsize=14, ha='left', va='top', 
                       fontproperties=font_prop, transform=ax.transAxes, fontweight='bold')
                y_pos -= line_height * 0.08  # 标题后的间距
                
                # 渲染角色名称
                for hero in heroes:
                    y_pos -= line_height * 0.05  # 角色之间的间距
                    ax.text(x_pos, y_pos, f"・ {hero}", fontsize=12, ha='left', va='top', 
                           fontproperties=font_prop, transform=ax.transAxes)
                
                # 种族之间的间距
                y_pos -= line_height * 0.12
        
        # 保存图像到内存
        buf = io.BytesIO()
        plt.savefig(buf, format='webp', dpi=100, bbox_inches='tight', transparent=False, 
                   pil_kwargs={'quality': 30})
        buf.seek(0)
        
        # 发送图片
        await es_hero_list.finish(MessageSegment.image(buf))
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