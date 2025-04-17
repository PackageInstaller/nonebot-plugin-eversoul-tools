import nonebot
from nonebot.plugin import PluginMetadata
from nonebot.log import logger
from nonebot import get_driver
from pathlib import Path
import os
from .config import *
from .command import *
from .library.utils import *
__plugin_meta__ = PluginMetadata(
    name='永恒灵魂工具合集',
    description='基于 nonebot2 的 Eversoul 工具合集',
    usage='请使用 es命令列表 指令查看使用方法',
    type='application',
    config=Config,
    homepage='https://github.com/PackageInstaller/nonebot-plugin-eversoul-tools',
    supported_adapters={'~onebot.v11'}
)

driver = get_driver()

@driver.on_startup
async def init_database():
    """初始化数据库"""
    try:
        # 确保数据目录存在
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # 检查数据库文件是否存在
        db_path = EversoulUser._db_path
        if not os.path.exists(db_path):
            logger.info("正在初始化 Eversoul 用户数据库...")
            # 初始化用户数据库
            await EversoulUser.init_db()
    except Exception as e:
        logger.error(f"初始化 Eversoul 用户数据库时发生错误: {e}")

sub_plugins = nonebot.load_plugins(
    str(Path(__file__).parent.joinpath('plugins').resolve())
)
