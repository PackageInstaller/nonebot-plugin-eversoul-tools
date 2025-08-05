"""
Eversoul群组数据模型 - 管理群组通知记录
"""
import os
import json
from typing import Optional, Dict, Any, List
import aiosqlite
from nonebot.log import logger
from datetime import datetime, timezone, timedelta

from ..utils import *


class EversoulUser:
    """永恒灵魂用户数据模型"""
    
    _db_path = DATABASE_DIR / "eversoul.db"
    
    @classmethod
    async def init_db(cls):
        """初始化数据库"""
        # 确保目录存在
        db_dir = os.path.dirname(cls._db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        # 检查数据库文件是否已存在
        db_exists = os.path.exists(cls._db_path)
        
        if not db_exists:
            async with aiosqlite.connect(cls._db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS _user (
                        user_id INTEGER NOT NULL,
                        app_id INTEGER NOT NULL,
                        player_id INTEGER NOT NULL,
                        update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        coupon_history TEXT DEFAULT '{}',
                        PRIMARY KEY (user_id, player_id)
                    )
                    """
                )
                
                # 创建服务器状态表
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS server (
                        server_type TEXT PRIMARY KEY,
                        version TEXT,
                        cdn_date TEXT,
                        table_version INTEGER,
                        last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                await db.commit()
        else:
            # 检查是否需要升级数据库结构
            try:
                async with aiosqlite.connect(cls._db_path) as db:
                    cursor = await db.execute("PRAGMA table_info(user)")
                    columns = await cursor.fetchall()
                    column_names = [col[1] for col in columns]
                    
                    # 如果coupon_history列不存在，添加它
                    if "coupon_history" not in column_names:
                        await db.execute(
                            """
                            ALTER TABLE user
                            ADD COLUMN coupon_history TEXT DEFAULT '{}'
                            """
                        )
                        await db.commit()
                    
                    # 检查server表是否存在
                    cursor = await db.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='server'"
                    )
                    table_exists = await cursor.fetchone()
                    
                    if not table_exists:
                        await db.execute(
                            """
                            CREATE TABLE server (
                                server_type TEXT PRIMARY KEY,
                                version TEXT,
                                cdn_date TEXT,
                                table_version INTEGER,
                                last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            )
                            """
                        )
                        await db.commit()
                        logger.info("数据库表 server 创建成功")
                    
                    # 检查push_history表是否存在
                    cursor = await db.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='push_history'"
                    )
                    push_table_exists = await cursor.fetchone()
                    
                    if not push_table_exists:
                        await db.execute(
                            """
                            CREATE TABLE push_history (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                server_type TEXT NOT NULL,
                                version TEXT NOT NULL,
                                table_version INTEGER DEFAULT 0,
                                group_id INTEGER NOT NULL,
                                push_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                UNIQUE(server_type, version, table_version, group_id)
                            )
                            """
                        )
                        await db.commit()
                        logger.info("数据库表 push_history 创建成功")
            except Exception as e:
                logger.error(f"升级数据库结构失败: {e}")
    
    @classmethod
    async def add_user(cls, user_id: int, app_id: str, player_id: str) -> bool:
        """添加或更新用户数据
        
        Args:
            user_id: 用户QQ号
            app_id: 游戏服务器对应的appId
            player_id: 用户游戏ID
            
        Returns:
            bool: 是否成功
        """
        try:
            await cls.init_db()
            
            beijing_time = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
            
            async with aiosqlite.connect(cls._db_path) as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO user
                    (user_id, app_id, player_id, update_time) 
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, app_id, player_id, beijing_time)
                )
                await db.commit()
                logger.info(f"用户数据已保存: user_id={user_id}, app_id={app_id}, player_id={player_id}")
            return True
        except Exception as e:
            logger.error(f"添加用户数据失败: {e}")
            return False
    
    @classmethod
    async def get_user(cls, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户数据，返回第一个找到的账号数据
        
        Args:
            user_id: 用户QQ号
            
        Returns:
            Optional[Dict[str, Any]]: 用户数据，如果不存在则返回None
        """
        try:
            await cls.init_db()
            async with aiosqlite.connect(cls._db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM user WHERE user_id = ? LIMIT 1",
                    (user_id,)
                )
                row = await cursor.fetchone()
                if row:
                    result = dict(row)
                    return result
                return None
        except Exception as e:
            logger.error(f"获取用户数据失败: {e}")
            return None
    
    @classmethod
    async def get_all_user_accounts(cls, user_id: int) -> List[Dict[str, Any]]:
        """获取用户的所有账号数据
        
        Args:
            user_id: 用户QQ号
            
        Returns:
            List[Dict[str, Any]]: 用户的所有账号数据，如果不存在则返回空列表
        """
        try:
            await cls.init_db()
            async with aiosqlite.connect(cls._db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM user WHERE user_id = ?",
                    (user_id,)
                )
                rows = await cursor.fetchall()
                if rows:
                    return [dict(row) for row in rows]
                return []
        except Exception as e:
            logger.error(f"获取用户所有账号数据失败: {e}")
            return []
    
    @classmethod
    async def delete_user(cls, user_id: int) -> bool:
        """删除用户所有账号数据
        
        Args:
            user_id: 用户QQ号
            
        Returns:
            bool: 是否成功
        """
        try:
            await cls.init_db()
            async with aiosqlite.connect(cls._db_path) as db:
                await db.execute(
                    "DELETE FROM user WHERE user_id = ?",
                    (user_id,)
                )
                await db.commit()
                logger.info(f"用户数据已删除: user_id={user_id}")
            return True
        except Exception as e:
            logger.error(f"删除用户数据失败: {e}")
            return False
            
    @classmethod
    async def delete_specific_account(cls, user_id: int, player_id: str) -> bool:
        """删除用户的特定账号
        
        Args:
            user_id: 用户QQ号
            player_id: 游戏ID
            
        Returns:
            bool: 是否成功
        """
        try:
            await cls.init_db()
            async with aiosqlite.connect(cls._db_path) as db:
                await db.execute(
                    "DELETE FROM user WHERE user_id = ? AND player_id = ?",
                    (user_id, player_id)
                )
                await db.commit()
                logger.info(f"用户特定账号已删除: user_id={user_id}, player_id={player_id}")
            return True
        except Exception as e:
            logger.error(f"删除用户特定账号失败: {e}")
            return False
    
    @classmethod
    async def get_coupon_history(cls, user_id: int, player_id: str) -> Dict[str, Any]:
        """获取用户的兑换码历史
        
        Args:
            user_id: 用户QQ号
            player_id: 游戏ID
            
        Returns:
            Dict[str, Any]: 兑换码历史，格式为 {coupon_code: status}
        """
        try:
            await cls.init_db()
            async with aiosqlite.connect(cls._db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT coupon_history FROM user WHERE user_id = ? AND player_id = ?",
                    (user_id, player_id)
                )
                row = await cursor.fetchone()
                if row and row["coupon_history"]:
                    try:
                        # 确保正确解析JSON，不论其编码方式
                        return json.loads(row["coupon_history"])
                    except json.JSONDecodeError:
                        logger.error(f"解析兑换码历史JSON失败: {row['coupon_history']}")
                        return {}
                return {}
        except Exception as e:
            logger.error(f"获取兑换码历史失败: {e}")
            return {}
    
    @classmethod
    async def update_coupon_history(cls, user_id: int, player_id: str, coupon_code: str, status: Dict[str, Any]) -> bool:
        """更新用户的兑换码历史
        
        Args:
            user_id: 用户QQ号
            player_id: 游戏ID
            coupon_code: 兑换码
            status: 兑换状态，包含兑换结果和时间
            
        Returns:
            bool: 是否成功
        """
        try:
            await cls.init_db()
            
            # 先获取当前的历史记录
            history = await cls.get_coupon_history(user_id, player_id)
            
            # 更新历史记录
            history[coupon_code] = status
            
            # 保存更新后的历史记录
            # 使用ensure_ascii=False确保中文字符不会被转义为Unicode编码
            json_str = json.dumps(history, ensure_ascii=False)
            
            async with aiosqlite.connect(cls._db_path) as db:
                await db.execute(
                    """
                    UPDATE user
                    SET coupon_history = ?
                    WHERE user_id = ? AND player_id = ?
                    """,
                    (json_str, user_id, player_id)
                )
                await db.commit()
                logger.info(f"兑换码历史已更新: user_id={user_id}, player_id={player_id}, code={coupon_code}")
            return True
        except Exception as e:
            logger.error(f"更新兑换码历史失败: {e}")
            return False
    
    @classmethod
    async def get_server(cls, server_type: str) -> Optional[Dict[str, Any]]:
        """获取服务器状态
        
        Args:
            server_type: 服务器类型 ("live" 或 "review")
            
        Returns:
            Optional[Dict[str, Any]]: 服务器状态信息
        """
        try:
            await cls.init_db()
            async with aiosqlite.connect(cls._db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT version, cdn_date, table_version FROM server WHERE server_type = ?",
                    (server_type,)
                )
                row = await cursor.fetchone()
                
                if row:
                    return {
                        "version": row["version"],
                        "cdn_date": row["cdn_date"],
                        "table_version": row["table_version"]
                    }
                    
        except Exception as e:
            logger.error(f"获取服务器状态失败: {e}")
            
        return None
    
    @classmethod
    async def update_server(cls, server_type: str, version: str, 
                                 cdn_date: str = "", table_version: int = 0) -> bool:
        """更新服务器状态
        
        Args:
            server_type: 服务器类型 ("live" 或 "review")
            version: 版本号
            cdn_date: CDN日期（仅Review服务器需要）
            table_version: 表版本号
            
        Returns:
            bool: 是否成功
        """
        try:
            await cls.init_db()
            
            beijing_time = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
            
            async with aiosqlite.connect(cls._db_path) as db:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO server 
                    (server_type, version, cdn_date, table_version, last_checked)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (server_type, version, cdn_date, table_version, beijing_time)
                )
                await db.commit()
                logger.info(f"服务器状态已更新: {server_type} - {version}")
            return True
        except Exception as e:
            logger.error(f"更新服务器状态失败: {e}")
            return False
    
    @classmethod
    async def check_push_history(cls, server_type: str, version: str, 
                                table_version: int, group_id: int) -> bool:
        """检查是否已经推送过指定版本
        
        Args:
            server_type: 服务器类型 ("live" 或 "review")
            version: 版本号
            table_version: 表版本号
            group_id: 群号
            
        Returns:
            bool: True表示已推送过，False表示未推送过
        """
        try:
            await cls.init_db()
            
            async with aiosqlite.connect(cls._db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT id FROM push_history 
                    WHERE server_type = ? AND version = ? AND table_version = ? AND group_id = ?
                    """,
                    (server_type, version, table_version, group_id)
                )
                result = await cursor.fetchone()
                return result is not None
                
        except Exception as e:
            logger.error(f"检查推送历史失败: {e}")
            return True  # 出错时返回True，避免重复推送
    
    @classmethod
    async def add_push_history(cls, server_type: str, version: str, 
                              table_version: int, group_id: int) -> bool:
        """添加推送历史记录
        
        Args:
            server_type: 服务器类型 ("live" 或 "review")
            version: 版本号
            table_version: 表版本号
            group_id: 群号
            
        Returns:
            bool: 是否成功
        """
        try:
            await cls.init_db()
            
            beijing_time = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
            
            async with aiosqlite.connect(cls._db_path) as db:
                await db.execute(
                    """
                    INSERT OR IGNORE INTO push_history 
                    (server_type, version, table_version, group_id, push_time)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (server_type, version, table_version, group_id, beijing_time)
                )
                await db.commit()
                logger.info(f"推送历史已记录: {server_type} - {version} - 表版本{table_version} -> 群{group_id}")
            return True
        except Exception as e:
            logger.error(f"添加推送历史失败: {e}")
            return False 