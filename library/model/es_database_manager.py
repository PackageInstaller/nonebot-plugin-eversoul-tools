"""
Eversoul群组数据模型 - 管理群组通知记录
"""
import os
import json
from typing import Optional, Dict, Any, List, Set
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
                    CREATE TABLE IF NOT EXISTS eversoul_users (
                        user_id INTEGER NOT NULL,
                        app_id TEXT NOT NULL,
                        player_id TEXT NOT NULL,
                        update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        coupon_history TEXT DEFAULT '{}',
                        PRIMARY KEY (user_id, player_id)
                    )
                    """
                )
                await db.commit()
                logger.info("数据库表 eversoul_users 创建成功")
        else:
            # 检查是否需要升级数据库结构
            try:
                async with aiosqlite.connect(cls._db_path) as db:
                    cursor = await db.execute("PRAGMA table_info(eversoul_users)")
                    columns = await cursor.fetchall()
                    column_names = [col[1] for col in columns]
                    
                    # 如果coupon_history列不存在，添加它
                    if "coupon_history" not in column_names:
                        await db.execute(
                            """
                            ALTER TABLE eversoul_users
                            ADD COLUMN coupon_history TEXT DEFAULT '{}'
                            """
                        )
                        await db.commit()
                        logger.info("数据库表 eversoul_users 已更新，添加了 coupon_history 列")
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
                    "SELECT coupon_history FROM eversoul_users WHERE user_id = ? AND player_id = ?",
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
                    UPDATE eversoul_users
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