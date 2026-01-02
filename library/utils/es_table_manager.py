"""
数据表下载和管理模块
"""

import json
import asyncio
import aiohttp
import subprocess
import shutil
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any
from nonebot.log import logger
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from rich.progress import Progress, DownloadColumn, BarColumn, TextColumn, TransferSpeedColumn, TimeRemainingColumn
from rich.console import Console

# 全局常量
TABLE_VERSION = 0  # 从cdn直接下载的表版本为0
KEY_MAGIC = "!@UmWlXo"

# Rich console
console = Console()


class TableDownloader:
    """数据表下载器"""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        self.timeout = aiohttp.ClientTimeout(total=600, connect=60)

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(headers=self.headers, timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self.session:
            await self.session.close()

    async def download_file(self, url: str, filepath: Path, description: str = "下载", retries: int = 3, progress_manager=None) -> bool:
        """下载文件（带进度条）
        
        Args:
            url: 下载URL
            filepath: 保存路径
            description: 下载描述
            retries: 重试次数
            progress_manager: 可选的共享进度条管理器
            
        Returns:
            bool: 是否成功
        """
        if not self.session:
            return False

        for attempt in range(retries):
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        filepath.parent.mkdir(parents=True, exist_ok=True)
                        total_size = int(response.headers.get('content-length', 0))
                        
                        # 如果提供了共享的进度条管理器，使用它；否则创建新的
                        if progress_manager:
                            task = progress_manager.add_task(description, total=total_size)
                            
                            with open(filepath, 'wb') as f:
                                async for chunk in response.content.iter_chunked(8192):
                                    f.write(chunk)
                                    progress_manager.update(task, advance=len(chunk))
                            
                            progress_manager.remove_task(task)
                        else:
                            with Progress(
                                TextColumn("[bold blue]{task.description}"),
                                BarColumn(),
                                DownloadColumn(),
                                TransferSpeedColumn(),
                                TimeRemainingColumn(),
                                console=console,
                            ) as progress:
                                task = progress.add_task(description, total=total_size)
                                
                                with open(filepath, 'wb') as f:
                                    async for chunk in response.content.iter_chunked(8192):
                                        f.write(chunk)
                                        progress.update(task, advance=len(chunk))
                        
                        logger.info(f"下载完成: {filepath.name}")
                        return True
                    else:
                        logger.warning(f"下载失败，状态码: {response.status}")
            except Exception as e:
                logger.warning(f"下载异常 (尝试 {attempt + 1}/{retries}): {e}")
                
            if attempt < retries - 1:
                await asyncio.sleep(2)

        return False

    @staticmethod
    def derive_key_and_iv() -> tuple[bytes, bytes]:
        """密钥派生函数
        
        Returns:
            (解密密钥, 初始化向量)的元组
        """
        try:
            # 计算 (tableVersion ^ 0x80000000) 并作为有符号整数
            xor_result = TABLE_VERSION ^ 0x80000000
            # 转换为有符号32位整数
            if xor_result >= 0x80000000:
                xor_result = xor_result - 0x100000000

            unhash_key = str(xor_result) + KEY_MAGIC

            # SHA256处理
            hash_obj = hashlib.sha256(unhash_key.encode("utf-8"))
            hash_bytes = hash_obj.digest()

            # 前16个字节作为密钥
            key = hash_bytes[:16]
            # IV与密钥相同
            iv = key

            return key, iv
        except Exception as e:
            raise RuntimeError(f"密钥派生失败: {e}")

    @staticmethod
    def decrypt_aes128_cbc(ciphertext: bytes, key: bytes, iv: bytes) -> Optional[bytes]:
        """使用AES-128-CBC模式解密数据
        
        Args:
            ciphertext: 待解密的密文数据
            key: 解密密钥
            iv: 初始化向量
            
        Returns:
            解密后的明文数据，失败时返回None
        """
        try:
            cipher = AES.new(key, AES.MODE_CBC, iv)
            plaintext = cipher.decrypt(ciphertext)
            # 移除填充
            plaintext = unpad(plaintext, AES.block_size)
            return plaintext
        except Exception as e:
            logger.error(f"AES解密失败: {e}")
            return None

    @staticmethod
    def is_file_decrypted(file_path: Path) -> bool:
        """检查文件是否已经被解密
        
        Args:
            file_path: 要检查的文件路径
            
        Returns:
            如果文件已解密返回True，否则返回False
        """
        try:
            with open(file_path, "rb") as f:
                header = f.read(32)
                if len(header) < 32:
                    return False

                # 检查是否有统一的偏移量模式
                has_uniform_offsets = False
                for i in range(16, 28, 4):
                    curr = int.from_bytes(header[i : i + 4], byteorder="little")
                    next_val = int.from_bytes(header[i + 4 : i + 8], byteorder="little")
                    # 检查相邻的两个4字节整数是否形成递减序列
                    if curr > next_val and (curr - next_val) < 0x1000:
                        has_uniform_offsets = True
                        break

                return has_uniform_offsets
        except Exception:
            return False

    @staticmethod
    def decrypt_file_in_place(file_path: Path, key: bytes, iv: bytes) -> bool:
        """在文件原位解密数据
        
        Args:
            file_path: 要解密的文件路径
            key: 解密密钥
            iv: 初始化向量
            
        Returns:
            解密成功返回True，失败返回False
        """
        try:
            # 读取文件内容
            with open(file_path, "rb") as f:
                ciphertext = f.read()

            # 解密
            plaintext = TableDownloader.decrypt_aes128_cbc(ciphertext, key, iv)
            if plaintext is None:
                return False

            # 写回文件
            with open(file_path, "wb") as f:
                f.write(plaintext)

            return True
        except Exception as e:
            logger.error(f"解密失败 {file_path}: {e}")
            return False

    @staticmethod
    def decrypt_files(files: list[Path], key: bytes, iv: bytes) -> bool:
        """解密多个文件
        
        Args:
            files: 需要解密的文件路径列表
            key: 解密密钥
            iv: 初始化向量
            
        Returns:
            所有文件解密成功返回True，任一文件解密失败返回False
        """
        failed_count = 0
        failed_files = []

        for file_path in files:
            if not TableDownloader.decrypt_file_in_place(file_path, key, iv):
                failed_count += 1
                failed_files.append(file_path.name)

        if failed_count:
            logger.error(f"解密失败文件: {', '.join(failed_files)}")
            return False

        return True

    @staticmethod
    def convert_tables_to_json(schema_dir: Path, table_dir: Path, output_dir: Path) -> bool:
        """将数据表转换为JSON格式
        
        Args:
            schema_dir: FlatBuffers schema文件所在的目录路径
            table_dir: 二进制数据表文件所在的目录路径
            output_dir: 输出JSON文件的目录路径
            
        Returns:
            转换成功返回True，失败返回False
        """
        try:
            if not output_dir.exists():
                output_dir.mkdir(parents=True, exist_ok=True)

            # 统计需要转换的文件数量
            total_files = 0
            files_to_convert = []
            for fbs_file in schema_dir.glob("*.fbs"):
                tbl_file = table_dir / f"{fbs_file.stem}.tbl"
                if tbl_file.exists():
                    total_files += 1
                    files_to_convert.append((fbs_file, tbl_file))

            logger.info(f"开始转换 {total_files} 个数据表文件")
            
            result = 0
            for fbs_file, tbl_file in files_to_convert:
                schema_name = fbs_file.stem

                command = [
                    "flatc",
                    "--json",
                    "--raw-binary",
                    "--strict-json",
                    "--natural-utf8",
                    "-o",
                    str(output_dir),
                    str(fbs_file),
                    "--",
                    str(tbl_file),
                ]

                result = subprocess.run(
                    command, capture_output=True, text=True
                ).returncode

                if result != 0:
                    logger.warning(f"转换 {schema_name} 失败")
                    continue

            if result == 0:
                logger.info("数据表转换完成")
                return True
            return False
        except Exception as e:
            logger.error(f"转换过程出错: {e}")
            return False


async def download_and_setup_table(
    server_type: str,
    version: str,
    table_version: int,
    target_dir: Path,
    schema_dir: Path,
    cdn_date: str = "",
    download_urls: list = None,
    progress_manager=None,
) -> bool:
    """下载并设置数据表
    
    Args:
        server_type: 服务器类型 ("gl_live", "gl_review", "cn_live", "cn_review")
        version: 版本号
        table_version: 表版本号
        target_dir: 目标目录
        schema_dir: Schema目录
        cdn_date: CDN日期（仅Review服务器需要）
        download_urls: 下载URL列表（仅国服需要）
        progress_manager: 可选的共享进度条管理器
        
    Returns:
        bool: 是否成功
    """
    try:
        from ...config import TABLE_DIR
        
        # 服务器名称映射
        server_names = {
            "gl_live": "国际服Live",
            "gl_review": "国际服Review",
            "cn_live": "国服Live",
            "cn_review": "国服Review",
            "jp_live": "日服Live",
            "jp_review": "日服Review",
        }
        server_name = server_names.get(server_type, server_type)
        
        # 构建下载URL
        if server_type == "gl_live":
            zip_url = f"https://patch.esoul.kakaogames.com/Live/{version}/Table/data_{table_version}.zip"
        elif server_type == "gl_review":
            zip_url = f"https://patch.esoul.kakaogames.com/Review/{cdn_date}/{version}/Table/data_{table_version}.zip"
        elif server_type in ["cn_live", "cn_review"]:
            if not download_urls:
                logger.error("国服下载需要提供download_urls")
                return False
            # 使用第一个可用的URL
            zip_url = f"{download_urls[0]}/{version}/Table/data_{table_version}.zip"
        else:
            logger.error(f"不支持的服务器类型: {server_type}")
            return False

        # 下载文件
        zip_filename = f"data_{server_type}_{table_version}.zip"
        zip_path = TABLE_DIR / zip_filename
        
        if not progress_manager:
            console.print(f"[bold cyan]正在下载 {server_name} 数据表...[/bold cyan]")
        
        async with TableDownloader() as downloader:
            if not await downloader.download_file(zip_url, zip_path, f"下载 {server_name}", progress_manager=progress_manager):
                logger.error(f"{server_name} 数据表下载失败")
                return False

        # 清理旧目录并解压
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        unzip_command = ["unzip", "-qq", "-o", str(zip_path), "-d", str(target_dir) + "/"]
        result = subprocess.run(unzip_command, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"解压失败: {result.stderr}")
            return False
        
        # 删除zip文件
        zip_path.unlink()

        # 解密
        key, iv = TableDownloader.derive_key_and_iv()

        files_to_decrypt = []
        for file_path in target_dir.iterdir():
            if file_path.is_file() and not TableDownloader.is_file_decrypted(file_path):
                files_to_decrypt.append(file_path)

        if not TableDownloader.decrypt_files(files_to_decrypt, key, iv):
            logger.error(f"{server_name} 数据表解密失败")
            return False

        # 转换
        console.print(f"[bold green]正在转换 {server_name} 数据表...[/bold green]")
        if not TableDownloader.convert_tables_to_json(schema_dir, target_dir, target_dir):
            logger.error(f"{server_name} 数据表转换失败")
            return False

        # 清理 .tbl
        for file_path in target_dir.iterdir():
            if file_path.is_file() and file_path.suffix == ".tbl":
                file_path.unlink()

        console.print(f"[bold green]✓ {server_name} 数据表下载完成[/bold green]")
        return True

    except Exception as e:
        logger.error(f"下载和设置数据表失败: {e}")
        return False
