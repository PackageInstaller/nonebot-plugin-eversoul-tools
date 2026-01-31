from ..library.utils import *


@es_range_ranking.handle()
async def handle(bot: Bot, event: Event):
    try:
        if isinstance(event, GroupMessageEvent):
            group_id = event.group_id
        data = await load_json_data(group_id)

        range_info = []
        unknown_range = []
        config = await get_group_data_source(group_id)

        with open(config["hero_alias_file"], "r", encoding="utf-8") as f:
            hero_aliases_data = yaml.safe_load(f)

        char_list = hero_aliases_data.get("names", [])

        for char_data in char_list:
            if isinstance(char_data, dict):
                hero_id = char_data.get("hero_id")
                if not hero_id:
                    continue

                char_name_data = await get_string_character(data, hero_id, special=True)
                char_name_zh_tw = char_name_data["zh_tw"]
                attack_range = await get_character_attack_range(data, hero_id)

                if attack_range > 0:
                    range_info.append((char_name_zh_tw, attack_range))
                else:
                    unknown_range.append(char_name_zh_tw)

        range_info.sort(key=lambda x: x[1], reverse=True)

        if range_info:
            messages = ["【已知攻击范围】"]
            for i, (name, range_value) in enumerate(range_info, 1):
                messages.append(f"{i}. {name}: {range_value}")

        if unknown_range:
            messages.append("\n【未知攻击范围】")
            for i, name in enumerate(unknown_range, 1):
                messages.append(f"{i}. {name}")

        await send_forward_messages(bot, event, ["\n".join(messages)], name="EverSoul Range")

    except Exception as e:
        if not isinstance(e, FinishedException):
            import traceback

            error_location = traceback.extract_tb(e.__traceback__)[-1]
            logger.error(
                f"处理攻击范围排行时发生错误:\n"
                f"错误类型: {type(e).__name__}\n"
                f"错误信息: {str(e)}\n"
                f"函数名称: {error_location.name}\n"
                f"问题代码: {error_location.line}\n"
                f"错误行号: {error_location.lineno}\n"
            )
