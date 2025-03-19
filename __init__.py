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
    
    # 强制将配置文件中的所有键转换为字符串
    if DATA_SOURCE_CONFIG.exists():
        try:
            with open(DATA_SOURCE_CONFIG, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            if config:  # 确保配置不为空
                # 确保所有键都是字符串
                new_config = {}
                for k, v in config.items():
                    new_config[str(k)] = v
                
                # 重新保存标准化的配置
                with open(DATA_SOURCE_CONFIG, "w", encoding="utf-8") as f:
                    yaml.dump(new_config, f, allow_unicode=True)
                
                logger.info(f"已标准化配置文件键，配置内容: {new_config}")
            else:
                logger.warning("配置文件存在但内容为空")
        except Exception as e:
            logger.error(f"初始化配置文件出错: {e}")
    else:
        logger.info("配置文件不存在，将创建默认配置")
    
    # 确保加载配置
    from .libraries.es_utils import load_data_source_config
    load_data_source_config()
    
    # 验证配置是否正确加载
    from .config import CURRENT_DATA_SOURCE
    logger.info(f"插件初始化完成，当前配置: {list(CURRENT_DATA_SOURCE.keys())}")

# 导入命令
from .commands import *