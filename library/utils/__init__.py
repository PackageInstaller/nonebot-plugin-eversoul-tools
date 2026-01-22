import re
import os
import yaml
import time
import asyncio
import nonebot
import aiohttp
import requests
from typing import Any, Tuple, Dict, Set
from nonebot.log import logger
from nonebot.permission import SUPERUSER
from nonebot import (
    on_regex,
    on_command,
    require,
    on_message,
    on_notice,
    get_bot,
    on_fullmatch,
)
from nonebot.exception import FinishedException
from nonebot.params import RegexGroup, CommandArg
from nonebot.adapters.onebot.v11 import (
    Bot,
    Event,
    Message,
    MessageEvent,
    GROUP_ADMIN,
    GROUP_OWNER,
    MessageSegment,
    GroupMessageEvent,
    NoticeEvent,
)

require("nonebot_plugin_htmlrender")
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_htmlrender import html_to_pic
from google_play_scraper import app as playstore_app
from difflib import get_close_matches
from PIL import Image
from io import BytesIO
from bs4 import BeautifulSoup
from datetime import datetime
from ...config import *
from ..model import *

es_help = on_command(
    "es命令列表",
    aliases={"es帮助", "es指令列表", "es功能", "es菜单", "es命令", "es指令"},
    priority=5,
    block=True,
)
es_ark_level = on_command("es方舟等级信息", priority=5, block=True)
es_ark_overclock = on_command("es超频消耗", priority=5, block=True)
es_cash_pack = on_command("es突发礼包信息", priority=5, block=True)
es_single_raid = on_command("es恶灵信息", priority=5, block=True)
es_gate = on_regex(
    r"es(自由|人类|野兽|妖精|不死)传送门信息(\d+)", priority=5, block=True
)
es_hero = on_command("es角色信息", aliases={"es基础信息"}, priority=5, block=True)
es_hero_skill = on_command("es技能信息", priority=5, block=True)
es_hero_list = on_command("es角色列表", priority=5, block=True)
es_level_cost = on_command("es升级消耗", priority=5, block=True)
es_month = on_command("es日程信息", priority=5, block=True)
es_potential = on_command("es潜能信息", priority=5, block=True)
es_stage = on_command("es主线信息", priority=5, block=True)
es_stats = on_regex(r"^es(身高|体重)排行$", priority=5, block=True)
es_range_ranking = on_fullmatch("es攻击范围排行", priority=5, block=True)
es_switch_source = on_command("es数据源", priority=5, block=True)
es_tier = on_command("es礼品信息", priority=5, block=True)
es_coupon = on_command("es兑换码", priority=5, block=True)
es_bind = on_command(
    "es绑定", aliases={"es绑定账号", "es账号绑定"}, priority=5, block=True
)
es_unbind = on_command(
    "es解绑", aliases={"es解绑账号", "es账号解绑"}, priority=5, block=True
)
es_notice = on_fullmatch("es公告", priority=5, block=True)
es_story = on_command("es故事信息", priority=5, block=True)
es_account = on_command(
    "es账号信息", aliases={"es账号列表", "es查看账号"}, priority=5, block=True
)
es_update_check = on_command(
    "es检查更新", aliases={"es更新检查"}, priority=5, block=True
)
emoji_vote = on_notice(priority=1, block=False)
es_zodiac = on_command("es星座信息", priority=5, block=True)
es_love_level = on_command("es好感等级信息", priority=5, block=True)
es_building = on_command("es建筑信息", aliases={"建筑信息"}, priority=5, block=True)


# 数据相关
from .es_data_utils import (
    load_aliases,
    load_json_data,
    load_data_source_config,
    save_data_source_config,
    get_group_data_source,
    sync_aliases,
    generate_aliases,
    process_json_files,
)


# 图片相关
from .es_image_utils import (
    apply_color_to_icon,
    format_event_content,
    generate_event_html,
    get_event_name,
    get_event_type_class,
    generate_ark_level_chart,
    get_character_illustration,
    get_character_portrait,
    get_character_evertalk_cg,
    get_schedule_event,
    get_mail_event,
    get_calendar_event,
    get_character_affection_cg,
    get_character_evertalk_cg,
    generate_level_cost_chart,
    generate_timeline_html,
    generate_potential_html,
    generate_zodiac_html,
    generate_love_level_html,
    generate_building_html,
    generate_skill_description_image,
)

# 更新检查相关
from .es_update_utils import (
    EversoulUpdateChecker,
    check_eversoul_updates,
    TableInfo,
    ReviewServerInfo,
    ServerStatus,
)

# 文本相关
from .es_string_utils import (
    format_value,
    select_text_by_priority,
    clean_rich_text,
    get_drop_item_rate,
    get_string_character,
    get_string_by_type,
    format_character_story,
    get_cash_pack,
    get_string_item,
    get_formation_type,
    get_character_skill,
    get_character_similar_name,
    get_character_release_date,
    get_character_cv,
    get_character_keyword_point,
    get_character_prefer_gift,
    get_character_keyword_source,
    get_character_arbeit,
    get_character_soullink,
    get_character_story,
    get_character_keyword,
    get_character_town_object,
    get_character_town_object_task,
    get_character_signature,
    get_character_signature_value,
    get_base_battle_power,
    calculate_battle_power,
    get_character_skill_pattern,
    get_character_attack_range,
    get_character_birthday,
    get_buff_value_color_text,
    get_zodiac_name,
    get_zodiac_buff_description,
    format_zodiac_nodes,
    get_love_buff_type_name,
    format_love_level_data,
    get_building_tooltip,
    format_building_data,
    get_building_basic_info,
    get_character_stats_ranking,
)

# 兑换码相关
from .es_coupon_utils import parse_server_id, redeem_coupon, redeem_coupons_concurrently
