import nonebot
from nonebot.plugin import PluginMetadata
from .config import *
from .commands import *

__plugin_meta__ = PluginMetadata(
    name='nonebot-plugin-eversoul-tools',
    description='基于 nonebot2 的 Eversoul 工具合集',
    usage='请使用 es命令列表 指令查看使用方法',
    type='application',
    config=Config,
    homepage='https://github.com/PackageInstaller/nonebot-plugin-eversoul-tools',
    supported_adapters={'~onebot.v11'}
)

sub_plugins = nonebot.load_plugins(
    str(Path(__file__).parent.joinpath('plugins').resolve())
)
