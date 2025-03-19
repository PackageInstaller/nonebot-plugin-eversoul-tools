from pathlib import Path
import nonebot
from nonebot.plugin import PluginMetadata
from nonebot import require, get_driver
from nonebot.log import logger
require("nonebot_plugin_htmlrender")
from zhenxun.utils.enum import PluginType
from zhenxun.configs.utils import PluginExtraData
from zhenxun.utils.enum import BlockType, PluginType
from zhenxun.configs.utils import BaseBlock, PluginExtraData
from .config import *
from .commands import *
import yaml

__plugin_meta__ = PluginMetadata(
    name="Eversoul工具合集",
    description="Eversoul相关信息查询",
    usage="""
    使用 es 命令列表 指令获取相关信息
    """.strip(),
    extra=PluginExtraData(
        author="少姜",
        version="1.0",
        plugin_type=PluginType.NORMAL,
        limits=[BaseBlock(check_type=BlockType.GROUP)],
        menu_type="功能"
    ).dict(),
    config=Config,
    homepage='https://github.com/PackageInstaller/nonebot-plugin-eversoul-tools',
    supported_adapters={'~onebot.v11'}
)

sub_plugins = nonebot.load_plugins(
    str(Path(__file__).parent.joinpath('plugins').resolve())
)

driver = get_driver()

@driver.on_startup
async def init_plugin():
    """插件启动时初始化"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    if DATA_SOURCE_CONFIG.exists():
        try:
            with open(DATA_SOURCE_CONFIG, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            if config:
                new_config = {}
                for k, v in config.items():
                    new_config[str(k)] = v
                
                with open(DATA_SOURCE_CONFIG, "w", encoding="utf-8") as f:
                    yaml.dump(new_config, f, allow_unicode=True)
            else:
                logger.warning("配置文件存在但内容为空")
        except Exception as e:
            logger.error(f"初始化配置文件出错: {e}")
    else:
        logger.info("配置文件不存在，将创建默认配置")
    
    from .libraries.es_utils import load_data_source_config
    load_data_source_config()
    try:
        generate_aliases()
    except Exception as e:
        logger.error(f"生成别名文件时出错: {e}")

# 导入命令
from .commands import *