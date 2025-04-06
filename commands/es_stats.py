from ..libraries.utils import *
import matplotlib.pyplot as plt
import io


@es_stats.handle()
async def handle_es_stats(bot: Bot, event: Event):
    # 创建图像资源
    fig = None
    buf = None
    
    try:
        # 获取匹配的类型（身高或体重）
        stat_type = event.get_plaintext()[2:4]  # 获取"身高"或"体重"
        
        # 加载数据
        # 获取群组ID
        group_id = None
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
        data = load_json_data(group_id)
        
        # 收集角色信息
        stats_info = []
        unknown_stats = []
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
                char_name_zh_cn = char_name_data["zh_cn"]
                char_name_kr = char_name_data["kr"]
                char_name_en = char_name_data["en"]
                
                # 查找角色描述数据
                hero_desc = None
                for desc in data["hero_desc"]["json"]:
                    if desc["hero_no"] == hero_id:
                        hero_desc = desc
                        break
                
                # 获取身高或体重信息
                stat_key = "height" if stat_type == "身高" else "weight"
                stat_value = hero_desc.get(stat_key, "？？？") if hero_desc else "？？？"
                
                if stat_value != "？？？":
                    stats_info.append((char_name_zh_tw, stat_value))
                else:
                    unknown_stats.append(char_name_zh_tw)
        
        # 按身高/体重从大到小排序
        stats_info.sort(key=lambda x: x[1], reverse=True)
        
        # 构建消息
        text_lines = []
        text_lines.append(f"永魂灵魂角色{stat_type}排行")
        
        # 添加已知数据的角色
        if stats_info:
            text_lines.append(f"【已知{stat_type}】")
            for i, (name, value) in enumerate(stats_info, 1):
                unit = "cm" if stat_type == "身高" else "kg"
                text_lines.append(f"{i}. {name}: {value}{unit}")
        else:
            text_lines.append(f"【已知{stat_type}】")
            text_lines.append("暂无数据")
        
        # 添加未知数据的角色
        if unknown_stats:
            text_lines.append(f"【未知{stat_type}】")
            for i, name in enumerate(unknown_stats, 1):
                text_lines.append(f"{i}. {name}")
        
        # 设置字体
        font_prop = CUSTOM_FONT
        
        # 计算图像大小
        max_length = max(len(line) for line in text_lines)
        fig_width = max(max_length * 0.10, 8)  # 确保最小宽度
        fig_height = max(len(text_lines) * 0.2, 5)  # 确保最小高度
        
        # 创建图像
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))
        ax.axis('off')  # 隐藏坐标轴
        fig.patch.set_facecolor('white')  # 设置背景颜色为白色
        
        # 添加标题
        ax.text(0.5, 0.98, text_lines[0], fontsize=16, ha='center', va='top', 
                fontproperties=font_prop, transform=ax.transAxes, fontweight='bold')
        
        # 逐行渲染文本
        y_position = 0.94
        line_height = 0.02  # 行高
        
        for line in text_lines[1:]:  # 跳过标题
            # 检查是否是分类标题（以【】括起来的）
            if line.startswith('【') and line.endswith('】'):
                # 为标题添加上方空间
                y_position -= line_height * 0.5
                ax.text(0.05, y_position, line, fontsize=14, ha='left', va='top', 
                       fontproperties=font_prop, transform=ax.transAxes, fontweight='bold')
            else:
                ax.text(0.05, y_position, line, fontsize=12, ha='left', va='top', 
                       fontproperties=font_prop, transform=ax.transAxes)
            
            # 更新y位置
            y_position -= line_height * 1.5
        
        # 保存图像到内存
        buf = io.BytesIO()
        plt.savefig(buf, format='webp', dpi=100, bbox_inches='tight', transparent=False, 
                   pil_kwargs={'quality': 70})
        buf.seek(0)
        
        # 发送图片
        await es_stats.finish(MessageSegment.image(buf))
            
    except Exception as e:
        if not isinstance(e, FinishedException):
            import traceback
            error_location = traceback.extract_tb(e.__traceback__)[-1]
            logger.error(
                f"处理{stat_type}排行时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )
            await es_stats.finish(f"处理{stat_type}排行时发生错误: {str(e)}")
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