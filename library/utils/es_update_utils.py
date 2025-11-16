import json
import asyncio
import aiohttp
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from nonebot.log import logger
from ..model import EversoulUser


@dataclass
class TableInfo:
    """数据表信息"""

    version: int = 0
    action: int = 0


class ReviewServerInfo:
    """Review服务器信息"""

    def __init__(self, exists: bool = False, version: str = "", cdn_date: str = ""):
        self.exists = exists
        self.version = version
        self.cdn_date = cdn_date
        self.table_info = TableInfo()


@dataclass
class ServerStatus:
    """服务器状态信息"""

    current_version: str = ""
    live_has_update: bool = False
    live_new_version: str = ""
    review_has_update: bool = False
    review_new_version: str = ""
    review_cdn_date: str = ""


class EversoulUpdateChecker:
    """永恒灵魂更新检查器"""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        self.timeout = aiohttp.ClientTimeout(total=10, connect=5)

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(headers=self.headers, timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()

    async def http_get(self, url: str, retries: int = 5) -> str:
        """执行HTTP GET请求

        Args:
            url: 请求URL
            retries: 重试次数

        Returns:
            str: 响应内容，失败返回空字符串
        """
        if not self.session:
            return ""

        for attempt in range(retries):
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        logger.warning(
                            f"HTTP请求失败，状态码: {response.status}, URL: {url}"
                        )

            except Exception as e:
                logger.warning(f"HTTP请求异常 (尝试 {attempt + 1}/{retries}): {e}")

            if attempt < retries - 1:
                await asyncio.sleep(1)

        return ""

    async def get_table_info(self, version: str) -> TableInfo:
        """获取指定版本的数据表信息

        Args:
            version: 游戏版本号

        Returns:
            TableInfo: 数据表信息
        """
        url = f"https://patch.esoul.kakaogames.com/Live/{version}/Table/const_data_version.json"
        response = await self.http_get(url)

        info = TableInfo()
        if response:
            try:
                data = json.loads(response)
                info.version = data.get("version", 0)
                info.action = data.get("action", 0)
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析错误: {e}")

        return info

    async def check_live_table_update(self, version: str) -> bool:
        """检查Live服务器数据表是否有更新

        Args:
            version: 游戏版本号

        Returns:
            bool: 是否需要更新
        """
        table_info = await self.get_table_info(version)
        if table_info.version == 0:
            return False

        # 从数据库获取当前状态
        current_status = await self.get_server_from_db("live")

        # 检查版本和表版本是否相同
        if (
            current_status
            and current_status.get("version") == version
            and current_status.get("table_version") == table_info.version
        ):
            return False

        return True

    def generate_versions(self, base_version: str) -> List[str]:
        """生成一系列可能的版本号

        Args:
            base_version: 基础版本号

        Returns:
            List[str]: 可能的版本号列表
        """
        versions = []

        # 解析基础版本号
        version_pattern = r"(\d+)\.(\d+)\.(\d+)"
        match = re.match(version_pattern, base_version)
        if not match:
            return versions

        major, minor, patch = map(int, match.groups())

        # 当前minor版本，从当前patch开始，向上检查到200
        for p in range(patch, 201):
            versions.append(f"{major}.{minor}.{p}")

        # 下一个minor版本，从0开始，向上检查到200
        for p in range(0, 201):
            versions.append(f"{major}.{minor + 1}.{p}")

        # major递增，minor从0开始，patch从0开始，向上检查到200
        for p in range(0, 201):
            versions.append(f"{major + 1}.0.{p}")

        return versions

    async def check_version(self, version: str) -> Tuple[bool, str]:
        """检查指定版本是否为可用的Review服务器版本

        Args:
            version: 要检查的版本号

        Returns:
            Tuple[bool, str]: (是否可用, CDN日期)
        """
        url = (
            f"https://gc-infodesk-zinny3.kakaogames.com/v2/app?"
            f"appId=743491&appVer={version}&market=googlePlay&"
            f"sdkVer=1&os=android&lang=en"
        )

        try:
            response = await self.http_get(url)
            if not response:
                return False, ""

            data = json.loads(response)

            # 检查是否是review版本
            content = data.get("content", {})
            app_option = content.get("appOption", {})

            if app_option.get("appVerSvcStatus") == "review":
                cdn_addr = app_option.get("cdnAddr")
                if cdn_addr:
                    date_match = re.search(r"/Review/(\d{4})", cdn_addr)
                    if date_match:
                        return True, date_match.group(1)

        except Exception as e:
            logger.debug(f"检查版本 {version} 时出错: {e}")

        return False, ""

    async def check_review_server(self, base_version: str) -> ReviewServerInfo:
        """检查Review服务器并获取相关信息

        Args:
            base_version: 基础版本号

        Returns:
            ReviewServerInfo: Review服务器信息
        """
        info = ReviewServerInfo()
        versions = self.generate_versions(base_version)
        max_concurrent = min(64, len(versions))

        async def check_single_version(version: str) -> Optional[Tuple[str, str]]:
            """检查单个版本"""
            is_valid, cdn_date = await self.check_version(version)
            if is_valid:
                return version, cdn_date
            return None

        # 分批处理版本检查
        for i in range(0, len(versions), max_concurrent):
            batch = versions[i : i + max_concurrent]
            tasks = [check_single_version(ver) for ver in batch]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if (
                    result
                    and not isinstance(result, Exception)
                    and isinstance(result, tuple)
                ):
                    info.exists = True
                    info.version = result[0]
                    info.cdn_date = result[1]
                    break

            if info.exists:
                break

        # 如果没有找到新版本，检查数据库中的版本
        if not info.exists:
            current_status = await self.get_server_from_db("review")
            if current_status:
                info.exists = True
                info.version = current_status.get("version", "")
                info.cdn_date = current_status.get("cdn_date", "")
                info.table_info.version = current_status.get("table_version", 0)

        # 如果找到了版本，获取table信息
        if info.exists and info.version and info.cdn_date:
            url = (
                f"https://patch.esoul.kakaogames.com/Review/"
                f"{info.cdn_date}/{info.version}/Table/const_data_version.json"
            )

            response = await self.http_get(url)
            if response:
                try:
                    data = json.loads(response)
                    info.table_info.version = data.get("version", 0)
                    info.table_info.action = data.get("action", 0)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析错误: {e}")

        return info

    async def check_review_table_update(self, review_info: ReviewServerInfo) -> bool:
        """检查Review服务器数据表是否有更新

        Args:
            review_info: Review服务器信息

        Returns:
            bool: 是否需要更新
        """
        if not review_info.exists:
            return False

        # 从数据库获取当前状态
        current_status = await self.get_server_from_db("review")

        # 检查版本、CDN日期和表版本是否相同
        if (
            current_status
            and current_status.get("version") == review_info.version
            and current_status.get("cdn_date") == review_info.cdn_date
            and current_status.get("table_version") == review_info.table_info.version
        ):
            return False

        return True

    async def get_version_with_google_play(self) -> str:
        """使用Google Play获取最新的应用版本号

        Returns:
            str: 版本号，失败返回空字符串
        """
        try:
            # 检查是否安装了google-play-scraper
            try:
                import google_play_scraper
            except ImportError:
                logger.error(
                    "未安装google-play-scraper，请运行: pip install google-play-scraper"
                )
                return ""

            # 在线程池中执行同步操作
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                future = executor.submit(
                    google_play_scraper.app,
                    app_id="com.kakaogames.eversoul",
                    lang="en",
                    country="kr",
                )
                result = await loop.run_in_executor(None, future.result)
                return result.get("version", "")

        except Exception as e:
            logger.error(f"获取Google Play版本号失败: {e}")
            return ""

    async def get_server_from_db(self, server_type: str) -> Optional[Dict[str, Any]]:
        """从数据库获取服务器状态

        Args:
            server_type: 服务器类型 ("live" 或 "review")

        Returns:
            Optional[Dict[str, Any]]: 服务器状态信息
        """
        return await EversoulUser.get_server(server_type)

    async def update_server_in_db(
        self, server_type: str, version: str, cdn_date: str = "", table_version: int = 0
    ):
        """更新数据库中的服务器状态

        Args:
            server_type: 服务器类型 ("live" 或 "review")
            version: 版本号
            cdn_date: CDN日期（仅Review服务器需要）
            table_version: 表版本号
        """
        await EversoulUser.update_server(server_type, version, cdn_date, table_version)

    async def check_all_servers(self) -> Dict[str, Any]:
        """检查所有服务器状态

        Returns:
            Dict[str, Any]: 包含所有服务器状态的JSON格式结果
        """
        # 获取当前版本号
        current_version = await self.get_version_with_google_play()
        if not current_version:
            return {
                "live": {"hasUpdate": False, "currentVersion": "", "updateVersion": ""},
                "review": {
                    "hasUpdate": False,
                    "currentVersion": "",
                    "updateVersion": "",
                },
            }

        # 检查Live服务器
        live_has_update = await self.check_live_table_update(current_version)
        live_current_version = ""
        live_update_version = ""
        live_current_table_version = 0

        # 始终先从数据库获取当前版本
        live_status = await self.get_server_from_db("live")
        if live_status:
            live_current_version = live_status.get("version", "")
            live_current_table_version = live_status.get("table_version", 0)

        if live_has_update:
            live_update_version = current_version
            # 获取Live服务器的tableVersion并更新数据库
            live_table_info = await self.get_table_info(current_version)
            await self.update_server_in_db(
                "live", current_version, "", live_table_info.version
            )

        # 检查Review服务器
        review_info = await self.check_review_server(current_version)
        review_has_update = False
        review_current_version = ""
        review_update_version = ""
        review_current_table_version = 0

        if review_info.exists:
            review_has_update = await self.check_review_table_update(review_info)
            review_update_version = review_info.version if review_has_update else ""

            # 始终先从数据库获取当前版本
            review_status = await self.get_server_from_db("review")
            if review_status:
                review_current_version = review_status.get("version", "")
                review_current_table_version = review_status.get("table_version", 0)

            if review_has_update:
                # 更新数据库
                await self.update_server_in_db(
                    "review",
                    review_info.version,
                    review_info.cdn_date,
                    review_info.table_info.version,
                )

        # 构建结果
        result = {
            "live": {
                "hasUpdate": live_has_update,
                "currentVersion": live_current_version,
                "updateVersion": live_update_version,
                "currentTableVersion": live_current_table_version,
            },
            "review": {
                "hasUpdate": review_has_update,
                "currentVersion": review_current_version,
                "updateVersion": review_update_version,
                "currentTableVersion": review_current_table_version,
            },
        }

        # 添加数据表版本信息
        if live_has_update:
            live_table_info = await self.get_table_info(current_version)
            result["live"]["newTableVersion"] = live_table_info.version

        if review_has_update and review_info.exists:
            result["review"]["newTableVersion"] = review_info.table_info.version

        return result


async def check_eversoul_updates() -> Dict[str, Any]:
    """检查永恒灵魂更新状态

    Returns:
        Dict[str, Any]: 服务器状态信息
    """
    async with EversoulUpdateChecker() as checker:
        return await checker.check_all_servers()
