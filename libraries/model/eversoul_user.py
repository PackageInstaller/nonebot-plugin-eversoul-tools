"""
Eversoul用户数据模型 - 保存用户的游戏数据
"""
import os
from typing import Optional,  Dict, Any, List
import aiosqlite
from nonebot.log import logger
from datetime import datetime, timezone, timedelta

from ...config import DATA_DIR


class EversoulUser:
    """永恒灵魂用户数据模型"""
    
    _db_path = DATA_DIR / "eversoul_user.db"
    
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
                    CREATE TABLE IF NOT EXISTS eversoul_users (
                        user_id INTEGER NOT NULL,
                        app_id TEXT NOT NULL,
                        player_id TEXT NOT NULL,
                        update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_id, player_id)
                    )
                    """
                )
                await db.commit()
                logger.info("数据库表 eversoul_users 创建成功")
    
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
                    INSERT OR REPLACE INTO eversoul_users 
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
                    "SELECT * FROM eversoul_users WHERE user_id = ? LIMIT 1",
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
                    "SELECT * FROM eversoul_users WHERE user_id = ?",
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
                    "DELETE FROM eversoul_users WHERE user_id = ?",
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
                    "DELETE FROM eversoul_users WHERE user_id = ? AND player_id = ?",
                    (user_id, player_id)
                )
                await db.commit()
                logger.info(f"用户特定账号已删除: user_id={user_id}, player_id={player_id}")
            return True
        except Exception as e:
            logger.error(f"删除用户特定账号失败: {e}")
            return False 