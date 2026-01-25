from ..library.utils import *


@es_alias_add.handle()
async def handle(bot: Bot, event: Event, args: Message = CommandArg()):
    """处理添加别名指令"""
    text = args.extract_plain_text().strip()
    
    if not text:
        help_msg = (
            "请按照以下格式添加别名：\n"
            "es别名添加 <角色名> <别名1> [别名2] ...\n\n"
            "参数说明：\n"
            "- 角色名：现有角色的名字（可以是别名或任意语言的名字）\n"
            "- 别名：要添加的别名，至少需要1个\n\n"
            "示例：es别名添加 界克劳 牢大 坠机王"
        )
        await es_alias_add.finish(message=help_msg, reply_message=True)
    
    # 解析参数
    parts = text.split()
    if len(parts) < 2:
        await es_alias_add.finish(
            message="参数不足！需要至少2个参数：角色名 + 要添加的别名\n示例：es别名添加 界克劳 牢大",
            reply_message=True
        )
    
    hero_name = parts[0]
    new_aliases = parts[1:]
    
    # 获取群组ID（如果是群消息）
    group_id = None
    if isinstance(event, GroupMessageEvent):
        group_id = event.group_id
    
    # 加载别名映射，查找hero_id
    alias_map = await load_aliases(group_id)
    hero_id = alias_map.get(hero_name)
    
    # 如果是英文名称，尝试小写匹配
    if not hero_id and hero_name.isascii():
        hero_id = alias_map.get(hero_name.lower())
    
    if not hero_id:
        await es_alias_add.finish(
            message=f"未找到角色：{hero_name}\n请确认角色名称是否正确",
            reply_message=True
        )
    
    # 读取live别名文件并添加别名
    live_alias_file = CONFIG_DIR / "live_hero_aliases.yaml"
    review_alias_file = CONFIG_DIR / "review_hero_aliases.yaml"
    
    if not live_alias_file.exists():
        await es_alias_add.finish(
            message="别名配置文件不存在，请先初始化数据",
            reply_message=True
        )
    
    try:
        with open(live_alias_file, "r", encoding="utf-8") as f:
            aliases_data = yaml.safe_load(f)
        
        if not aliases_data or "names" not in aliases_data:
            await es_alias_add.finish(
                message="别名配置文件格式错误",
                reply_message=True
            )
        
        # 查找对应角色并添加别名
        hero_found = False
        hero_info = None
        added_aliases = []
        existing_aliases = []
        
        for hero in aliases_data["names"]:
            if hero.get("hero_id") == hero_id:
                hero_found = True
                hero_info = hero
                current_aliases = hero.get("aliases", [])
                
                for new_alias in new_aliases:
                    if new_alias not in current_aliases:
                        current_aliases.append(new_alias)
                        added_aliases.append(new_alias)
                    else:
                        existing_aliases.append(new_alias)
                
                hero["aliases"] = current_aliases
                break
        
        if not hero_found:
            await es_alias_add.finish(
                message=f"在别名文件中未找到hero_id={hero_id}的角色",
                reply_message=True
            )
        
        # 保存文件
        class CustomDumper(yaml.SafeDumper):
            def increase_indent(self, flow=False, indentless=False):
                return super().increase_indent(flow, False)

            def represent_scalar(self, tag, value, style=None):
                if isinstance(value, str):
                    style = None
                return super().represent_scalar(tag, value, style)

            def represent_sequence(self, tag, sequence, flow_style=None):
                if (
                    isinstance(sequence, (list, tuple))
                    and len(sequence) > 0
                    and isinstance(sequence[0], str)
                ):
                    flow_style = True
                return super().represent_sequence(tag, sequence, flow_style=flow_style)
        
        with open(live_alias_file, "w", encoding="utf-8") as f:
            yaml.dump(
                aliases_data,
                f,
                Dumper=CustomDumper,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
                indent=2,
            )
        
        # 同步到review文件
        await sync_aliases(live_alias_file, review_alias_file)
        
        # 构建响应消息
        hero_display_name = hero_info.get("zh_cn_name") or hero_info.get("zh_tw_name") or hero_info.get("en_name")
        response_parts = [f"角色：{hero_display_name} (ID: {hero_id})"]
        
        if added_aliases:
            response_parts.append(f"✅ 成功添加别名：{', '.join(added_aliases)}")
        
        if existing_aliases:
            response_parts.append(f"⚠️ 以下别名已存在：{', '.join(existing_aliases)}")
        
        if added_aliases:
            response_parts.append("📝 已同步到review版本")
        
        await es_alias_add.finish(
            message="\n".join(response_parts),
            reply_message=True
        )
        
    except FinishedException:
        raise  # Re-raise FinishedException as it's normal control flow
    except Exception as e:
        logger.error(f"添加别名时发生错误: {e}")
        await es_alias_add.finish(
            message=f"添加别名失败：{str(e)}",
            reply_message=True
        )
