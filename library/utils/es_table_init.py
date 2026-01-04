"""
数据表初始化模块
"""

import asyncio
import json
from pathlib import Path
from nonebot.log import logger
from ...config import (
    TABLE_DIR,
    GL_LIVE_TABLE_DIR,
    GL_REVIEW_TABLE_DIR,
    CN_LIVE_TABLE_DIR,
    CN_REVIEW_TABLE_DIR,
    GL_SCHEMA_DIR,
    CN_SCHEMA_DIR,
    JP_SCHEMA_DIR,
)
from ..model import EversoulUser
from .es_table_manager import download_and_setup_table
from .es_update_utils import EversoulUpdateChecker

# 导入下载状态管理
from . import es_update_utils


async def generate_aliases_after_download():
    """在数据表下载完成后生成别名文件"""
    try:
        from .es_data_utils import generate_aliases

        logger.info("开始生成别名文件...")
        await generate_aliases()
        logger.info("别名文件生成完成！")
    except Exception as e:
        logger.error(f"生成别名文件时出错: {e}")


async def check_and_download_tables():
    """检查并下载数据表（不阻塞，后台运行）"""
    try:
        # 创建必要的目录
        TABLE_DIR.mkdir(parents=True, exist_ok=True)

        # 检查Schema是否存在
        missing_schemas = []
        if not GL_SCHEMA_DIR.exists() or not any(GL_SCHEMA_DIR.glob("*.fbs")):
            missing_schemas.append(f"Global Schema: {GL_SCHEMA_DIR}")
        if not CN_SCHEMA_DIR.exists() or not any(CN_SCHEMA_DIR.glob("*.fbs")):
            missing_schemas.append(f"CN Schema: {CN_SCHEMA_DIR}")
        if not JP_SCHEMA_DIR.exists() or not any(JP_SCHEMA_DIR.glob("*.fbs")):
            missing_schemas.append(f"JP Schema: {JP_SCHEMA_DIR}")

        if missing_schemas:
            logger.error("FlatBuffers Schema 文件不存在！")
            for schema in missing_schemas:
                logger.error(f"  缺失: {schema}")
            logger.error("请将Schema文件复制到相应目录")
            return

        # 在后台任务中下载所有数据表
        asyncio.create_task(download_all_tables())

    except Exception as e:
        logger.error(f"检查和下载数据表失败: {e}")


async def download_all_tables():
    """后台下载所有数据表"""
    # 设置下载状态标志
    async with es_update_utils._download_lock:
        es_update_utils._downloading_tables = True
    
    try:
        from rich.console import Console
        from rich.progress import (
            Progress,
            TextColumn,
            BarColumn,
            DownloadColumn,
            TransferSpeedColumn,
            TimeRemainingColumn,
        )

        console = Console()

        # 收集需要下载的服务器
        servers_to_download = []

        # 检查国际服Live
        if not GL_LIVE_TABLE_DIR.exists() or not any(GL_LIVE_TABLE_DIR.glob("*.json")):
            servers_to_download.append("gl_live")

        # 检查国际服Review
        if not GL_REVIEW_TABLE_DIR.exists() or not any(
            GL_REVIEW_TABLE_DIR.glob("*.json")
        ):
            servers_to_download.append("gl_review")

        # 检查国服Live
        if not CN_LIVE_TABLE_DIR.exists() or not any(CN_LIVE_TABLE_DIR.glob("*.json")):
            servers_to_download.append("cn_live")

        # 检查国服Review
        if not CN_REVIEW_TABLE_DIR.exists() or not any(
            CN_REVIEW_TABLE_DIR.glob("*.json")
        ):
            servers_to_download.append("cn_review")

        if not servers_to_download:
            logger.info("所有数据表已存在，无需下载")
            # 即使不需要下载，也要生成别名文件
            await generate_aliases_after_download()
            return

        console.print(
            f"\n[bold cyan]═══════════════════════════════════════[/bold cyan]"
        )
        console.print(
            f"[bold cyan]开始下载 {len(servers_to_download)} 个数据源[/bold cyan]"
        )
        console.print(
            f"[bold cyan]═══════════════════════════════════════[/bold cyan]\n"
        )

        # 创建共享的进度条管理器
        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            # 并发下载所有数据表
            tasks = []
            for server_type in servers_to_download:
                task = asyncio.create_task(
                    check_and_download_server_table(server_type, progress)
                )
                tasks.append(task)

            # 等待所有下载完成
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 检查是否有失败的任务
            failed_servers = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_servers.append(servers_to_download[i])
                    logger.error(f"下载 {servers_to_download[i]} 时出错: {result}")

        if failed_servers:
            console.print(
                f"[bold yellow]部分数据表下载完成，失败: {', '.join(failed_servers)}[/bold yellow]"
            )
        else:
            console.print(f"[bold green]所有数据表下载完成！[/bold green]")

        # 下载完成后生成别名文件
        await generate_aliases_after_download()

    except Exception as e:
        logger.error(f"后台下载数据表失败: {e}")
    finally:
        # 无论成功失败，都要清除下载状态标志
        async with es_update_utils._download_lock:
            es_update_utils._downloading_tables = False


async def check_and_download_server_table(server_type: str, progress_manager=None):
    """检查并下载指定服务器的数据表

    Args:
        server_type: 服务器类型 ("gl_live", "gl_review", "cn_live", "cn_review")
        progress_manager: 可选的共享进度条管理器
    """
    try:
        # 获取目标目录和Schema目录
        if server_type == "gl_live":
            target_dir = GL_LIVE_TABLE_DIR
            schema_dir = GL_SCHEMA_DIR
            server_name = "国际服Live"
        elif server_type == "gl_review":
            target_dir = GL_REVIEW_TABLE_DIR
            schema_dir = GL_SCHEMA_DIR
            server_name = "国际服Review"
        elif server_type == "cn_live":
            target_dir = CN_LIVE_TABLE_DIR
            schema_dir = CN_SCHEMA_DIR
            server_name = "国服Live"
        elif server_type == "cn_review":
            target_dir = CN_REVIEW_TABLE_DIR
            schema_dir = CN_SCHEMA_DIR
            server_name = "国服Review"
        else:
            logger.error(f"不支持的服务器类型: {server_type}")
            return

        # 检查数据表是否存在
        table_exists = target_dir.exists() and any(target_dir.glob("*.json"))

        if table_exists:
            logger.info(f"{server_name}数据表已存在，跳过下载")
            return

        # 从数据库获取版本信息
        server_info = await EversoulUser.get_server(server_type)

        # 数据表不存在
        if server_info:
            # 数据库中有版本信息，按照该版本下载
            version = server_info.get("version", "")
            table_version = server_info.get("table_version", 0)
            cdn_date = server_info.get("cdn_date", "")

            if version and table_version:
                # 获取下载URL（如果是国服）
                download_urls = None
                if server_type in ["cn_live", "cn_review"]:
                    async with EversoulUpdateChecker() as checker:
                        cn_config = await checker.get_cn_server_config()
                        if server_type == "cn_live":
                            download_urls = (
                                cn_config.download_urls if cn_config.is_valid else None
                            )
                        else:
                            download_urls = (
                                cn_config.review_download_urls
                                if cn_config.review_is_valid
                                else None
                            )

                success = await download_and_setup_table(
                    server_type,
                    version,
                    table_version,
                    target_dir,
                    schema_dir,
                    cdn_date,
                    download_urls,
                    progress_manager,
                    infinite_retry=True,  # 启用无限重试
                )

                if not success:
                    logger.error(f"{server_name}数据表下载失败")
            else:
                logger.warning(f"{server_name}数据库中版本信息不完整，尝试获取最新版本")
                await download_latest_table(
                    server_type, target_dir, schema_dir, server_name, progress_manager
                )
        else:
            # 数据库中没有版本信息，尝试获取最新版本并下载
            await download_latest_table(
                server_type, target_dir, schema_dir, server_name, progress_manager
            )

    except Exception as e:
        server_name = server_type
        logger.error(f"检查和下载{server_name}数据表失败: {e}")


async def download_latest_table(
    server_type: str,
    target_dir: Path,
    schema_dir: Path,
    server_name: str,
    progress_manager=None,
):
    """下载最新的数据表

    Args:
        server_type: 服务器类型
        target_dir: 目标目录
        schema_dir: Schema目录
        server_name: 服务器名称
        progress_manager: 可选的共享进度条管理器
    """
    try:
        async with EversoulUpdateChecker() as checker:
            if server_type == "gl_live":
                # 获取国际服Live最新版本
                version = await checker.get_version_with_google_play()
                if not version:
                    logger.error(f"无法获取{server_name}最新版本")
                    return

                table_info = await checker.get_table_info(version, "global")
                if table_info.version == 0:
                    logger.error(f"无法获取{server_name}数据表版本信息")
                    return

                success = await download_and_setup_table(
                    server_type,
                    version,
                    table_info.version,
                    target_dir,
                    schema_dir,
                    "",
                    None,
                    progress_manager,
                    infinite_retry=True,  # 启用无限重试
                )

                if success:
                    # 更新数据库
                    await checker.update_server_in_db(
                        "gl_live", version, "", table_info.version
                    )
                    logger.info(f"{server_name}最新数据表下载完成")
                else:
                    logger.error(f"{server_name}最新数据表下载失败")

            elif server_type == "gl_review":
                # 获取国际服Review最新版本
                version = await checker.get_version_with_google_play()
                if not version:
                    logger.error(f"无法获取{server_name}最新版本")
                    return

                review_info = await checker.check_review_server(version)
                if not review_info.exists:
                    logger.warning(f"{server_name}当前没有可用版本")
                    return

                # 获取表版本
                url = f"https://patch.esoul.kakaogames.com/Review/{review_info.cdn_date}/{review_info.version}/Table/const_data_version.json"
                response = await checker.http_get(url)
                if not response:
                    logger.error(f"无法获取{server_name}数据表版本信息")
                    return

                data = json.loads(response)
                table_version = data.get("version", 0)

                success = await download_and_setup_table(
                    server_type,
                    review_info.version,
                    table_version,
                    target_dir,
                    schema_dir,
                    review_info.cdn_date,
                    None,
                    progress_manager,
                    infinite_retry=True,  # 启用无限重试
                )

                if success:
                    # 更新数据库
                    await checker.update_server_in_db(
                        "gl_review",
                        review_info.version,
                        review_info.cdn_date,
                        table_version,
                    )
                    logger.info(f"{server_name}最新数据表下载完成")
                else:
                    logger.error(f"{server_name}最新数据表下载失败")

            elif server_type in ["cn_live", "cn_review"]:
                # 获取国服配置
                cn_config = await checker.get_cn_server_config()

                if server_type == "cn_live":
                    if not cn_config.is_valid:
                        logger.error(f"无法获取{server_name}配置")
                        return

                    version = cn_config.version
                    download_urls = cn_config.download_urls
                else:
                    if not cn_config.review_is_valid:
                        logger.error(f"无法获取{server_name}配置")
                        return

                    version = cn_config.review_version
                    download_urls = cn_config.review_download_urls

                # 获取表版本
                table_version = 0
                for base_url in download_urls:
                    try:
                        version_url = (
                            f"{base_url}/{version}/Table/const_data_version.json"
                        )
                        response = await checker.http_get(version_url)
                        if response:
                            data = json.loads(response)
                            table_version = data.get("version", 0)
                            if table_version > 0:
                                break
                    except:
                        continue

                if table_version == 0:
                    logger.error(f"无法获取{server_name}数据表版本信息")
                    return

                success = await download_and_setup_table(
                    server_type,
                    version,
                    table_version,
                    target_dir,
                    schema_dir,
                    "",
                    download_urls,
                    progress_manager,
                    infinite_retry=True,  # 启用无限重试
                )

                if success:
                    # 更新数据库
                    await checker.update_server_in_db(
                        server_type, version, "", table_version
                    )
                    logger.info(f"{server_name}最新数据表下载完成")
                else:
                    logger.error(f"{server_name}最新数据表下载失败")

    except Exception as e:
        logger.error(f"下载{server_name}最新数据表失败: {e}")
