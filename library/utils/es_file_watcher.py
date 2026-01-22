import asyncio
from pathlib import Path
from typing import Dict, Callable
from nonebot.log import logger
import time


class FileWatcher:
    """文件监控器，用于监控文件变化并执行回调"""
    
    def __init__(self):
        self.watched_files: Dict[Path, float] = {}  # 文件路径 -> 最后修改时间
        self.callbacks: Dict[Path, Callable] = {}  # 文件路径 -> 回调函数
        self.running = False
        self.check_interval = 2.0  # 检查间隔（秒）
        
    def watch(self, file_path: Path, callback: Callable):
        """添加要监控的文件
        
        Args:
            file_path: 要监控的文件路径
            callback: 文件变化时的回调函数
        """
        if file_path.exists():
            self.watched_files[file_path] = file_path.stat().st_mtime
            self.callbacks[file_path] = callback
            logger.info(f"开始监控文件: {file_path}")
        else:
            logger.warning(f"文件不存在，无法监控: {file_path}")
    
    def unwatch(self, file_path: Path):
        """停止监控文件
        
        Args:
            file_path: 要停止监控的文件路径
        """
        if file_path in self.watched_files:
            del self.watched_files[file_path]
            del self.callbacks[file_path]
            logger.info(f"停止监控文件: {file_path}")
    
    async def start(self):
        """启动文件监控"""
        if self.running:
            logger.warning("文件监控已在运行中")
            return
        
        self.running = True
        logger.info("文件监控已启动")
        
        while self.running:
            try:
                await self._check_files()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"文件监控出错: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _check_files(self):
        """检查所有监控的文件是否有变化"""
        for file_path, last_mtime in list(self.watched_files.items()):
            try:
                if not file_path.exists():
                    logger.warning(f"监控的文件不存在: {file_path}")
                    continue
                
                current_mtime = file_path.stat().st_mtime
                
                # 如果文件被修改了
                if current_mtime > last_mtime:
                    logger.info(f"检测到文件变化: {file_path}")
                    self.watched_files[file_path] = current_mtime
                    
                    # 执行回调函数
                    callback = self.callbacks.get(file_path)
                    if callback:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(file_path)
                            else:
                                callback(file_path)
                        except Exception as e:
                            logger.error(f"执行文件变化回调时出错: {e}")
            except Exception as e:
                logger.error(f"检查文件 {file_path} 时出错: {e}")
    
    def stop(self):
        """停止文件监控"""
        self.running = False
        logger.info("文件监控已停止")


# 全局文件监控器实例
file_watcher = FileWatcher()
