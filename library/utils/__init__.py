"""
Eversoul工具模块 - 功能集合
"""
import re
import os
import yaml
import time
import asyncio
import nonebot
import aiohttp
import requests
from typing import Any, Tuple, Dict
from nonebot.log import logger
from nonebot.permission import SUPERUSER
from nonebot import on_regex, on_command, require, on_message, on_notice, get_bot
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
    NoticeEvent
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

es_help = on_command("es命令列表", aliases={"es帮助", "es指令列表"}, priority=5, block=True)
es_ark_info = on_regex(r"^es方舟等级信息(\d+)$", priority=5, block=True)
es_ark_overclock = on_regex(r"^es超频消耗(\d+)$", priority=5, block=True)
es_cash_pack_info = on_command("es突发礼包信息", priority=5, block=True)
es_single_raid = on_command("es恶灵信息", aliases={"es惡靈資訊"}, priority=5, block=True)
es_gate = on_regex(r"es(自由|人类|野兽|妖精|不死)传送门信息(\d+)", priority=5, block=True)
es_hero_info = on_command("es角色信息", aliases={"es角色資訊"}, priority=5, block=True)
es_hero_list = on_command("es角色列表", priority=5, block=True)
es_level_cost = on_regex(r"^es升级消耗(\d+)$", priority=5, block=True)
es_month = on_regex(r"^es(\d{1,2})月事件$", priority=5, block=True)
es_potential_info = on_command("es潜能信息", priority=5, block=True)
es_stage_info = on_command("es主线信息", priority=5, block=True)
es_stats = on_regex(r"^es(身高|体重)排行$", priority=5, block=True)
es_switch_source = on_command("es数据源", priority=5, permission=\
                            (SUPERUSER | GROUP_ADMIN | GROUP_OWNER), block=True)
es_tier_info = on_command("es礼品信息", priority=5, block=True)
es_coupon = on_command("es兑换码", priority=5, block=True)
es_bind = on_command("es绑定账号", aliases={"es绑定"}, priority=5, block=True)
es_unbind = on_command("es解绑账号", aliases={"es解绑"}, priority=5, block=True)
es_notice = on_command("es公告", priority=5, block=True)


# 数据相关
from .es_data_utils import (
    load_aliases, load_json_data, load_data_source_config, 
    save_data_source_config, get_group_data_source, sync_aliases,
    generate_aliases, process_json_files
)

# 图片相关
from .es_image_utils import (
    apply_color_to_icon, format_event_content,
    generate_event_html, get_event_name, get_event_type_class,
    generate_ark_level_chart, get_character_illustration,
    get_character_portrait, get_character_evertalk_cg,
    get_schedule_event, get_mail_event, get_calendar_event,
    get_character_affection_cg, get_character_evertalk_cg,
    generate_level_cost_chart, generate_timeline_html,
    generate_potential_html
)

# 文本相关
from .es_string_utils import (
    clean_tags, format_number, get_drop_item_rate,
    get_string_character, get_string_system,
    get_character_lost_item, format_character_story, get_cash_pack, get_string_item, 
    get_formation_type, get_character_skill, get_character_skill_value,
    get_character_similar_name, get_character_release_date, get_character_cv,
    get_character_keyword_point, get_character_prefer_gift, get_string_ui,
    get_character_keyword_source, get_character_keyword_location,
    get_character_arbeit, get_character_soullink, get_character_story,
    get_character_keyword, get_character_town_object, get_character_town_object_task,
    get_character_signature, get_character_signature_value, get_character_skill_type,
    get_base_battle_power, calculate_battle_power, get_character_skill_pattern
)

# 兑换码相关
from .es_coupon_utils import (
    parse_server_id, redeem_coupon, redeem_coupons_concurrently
)