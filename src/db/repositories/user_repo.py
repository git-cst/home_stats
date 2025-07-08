from typing import Optional, TYPE_CHECKING
from datetime import datetime, timedelta
from uuid import UUID

from core.database import DatabasePool
from core.security import hash_password

if TYPE_CHECKING:
    from core.permissions import Permission

class UserRepository:
    def __init__(self, pool: DatabasePool):
        self.pool = pool
    
    async def create_user(self, email: str, password: str) -> UUID:
        """Create a new user and return the user ID"""
        hashed_password = hash_password(password)
        
        async with self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO users (email, hashed_password, created_at, is_active)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id;
                """, (email, hashed_password.decode('utf-8'), datetime.now(), True))
                
                result = await cursor.fetchone()
                await conn.commit()
                return result['id']

    async def deactivate_user(self, user_id: UUID, status: bool) -> Optional[dict]:
        """Deactivate a user"""        
        async with self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    UPDATE users SET is_active = %s WHERE id = %s
                    RETURNING id, is_active;
                """, (user_id, status))
                await conn.commit()
                return await cursor.fetchone()

    async def recover_user(self, user_id: UUID) -> bool:
        """Recover a user. E.g. remove deleted_at and deletion_reason"""        
        async with self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    UPDATE users SET deleted_at = NULL, deletion_reason = NULL, is_active = %s WHERE id = %s
                    RETURNING id, is_active;
                """, (True, user_id))
                result = await cursor.fetchone()
                await conn.commit()
                return result is not None

    async def soft_delete_user(self, user_id: UUID, deletion_reason: str = "user_request") -> bool:
        """Soft delete a user"""        
        async with self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    UPDATE users SET deleted_at = %s, deletion_reason = %s, is_active = %s WHERE id = %s
                """, (datetime.now(), deletion_reason, False, user_id))
                await conn.commit()
                return cursor.rowcount > 0

    async def hard_delete_user(self, user_id: UUID) -> None:
        """Hard delete a user"""        
        async with self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                try:

                    await cursor.execute("DELETE FROM user_permissions WHERE user_id = %s", (user_id,))
                    await cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
                    await conn.commit()
                    return cursor.rowcount > 0

                except Exception as e:
                    await conn.rollback()
                    raise e

    async def get_user_by_id(self, user_id: UUID, include_deleted: bool = False) -> Optional[dict]:
        """Get user by ID"""
        async with self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                if include_deleted:
                    await cursor.execute("""
                        SELECT id, email, hashed_password, created_at, last_login, 
                            is_active, deleted_at, deletion_reason, role
                        FROM users
                        WHERE id = %s
                    """, (user_id,))
                else:
                    await cursor.execute("""
                        SELECT id, email, hashed_password, created_at, last_login, 
                            is_active, role
                        FROM users
                        WHERE id = %s AND is_active = true AND deleted_at IS NULL
                    """, (user_id,))
                
                return await cursor.fetchone()

    async def get_user_by_email(self, email: str) -> Optional[dict]:
        """Retrieve user by email"""
        async with self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, email, hashed_password, created_at, is_active
                    FROM users
                    WHERE email = %s;
                """, (email,))
                
                return await cursor.fetchone()
            
    async def get_user_permissions(self, user_id: UUID) -> Optional[list[dict]]:
        """Retrieve user by email"""
        async with self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, user_id, permission, granted_at, granted_by
                    FROM user_permissions
                    WHERE user_id = %s;
                """, (user_id,))
                
                return await cursor.fetchall()
            
    async def grant_user_permission(self, user_id: UUID, permission: Permission, granted_by: UUID) -> Optional[dict]:
        """Retrieve user by email"""
        async with self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO user_permissions(
                        user_id,
                        permission,
                        granted_at,
                        granted_by
                    ) VALUES (%s, %s, %s, %s)
                    RETURNING id, user_id, permission, granted_at, granted_by;
                """, (user_id, permission.value, datetime.now(), granted_by))
                result = await cursor.fetchone()
                await conn.commit()
                return result
            
    async def revoke_user_permission(self, user_id: UUID, permission: Permission) -> bool:
        """Revoke a permission from a user"""
        async with self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    DELETE FROM user_permissions
                    WHERE user_id = %s AND permission = %s
                """, (user_id, permission.value))
                
                await conn.commit()
                return cursor.rowcount > 0
            
    async def user_has_permission(self, user_id: UUID, permission: Permission) -> bool:
        """Check if user has a specific permission"""
        async with self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT 1 FROM user_permissions
                    WHERE user_id = %s AND permission = %s
                    LIMIT 1;
                """, (user_id, permission.value))
                
                result = await cursor.fetchone()
                return result is not None
            

    async def get_expired_soft_deleted_users(self, cutoff_date: datetime) -> list[dict]:
        """Get users soft-deleted before the cutoff date (for cleanup job)"""
        async with self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, email, deleted_at, deletion_reason
                    FROM users
                    WHERE deleted_at IS NOT NULL 
                    AND deleted_at < %s 
                    AND is_active = false
                """, (cutoff_date,))
                
                return await cursor.fetchall()

    async def is_user_within_grace_period(self, user_id: UUID, grace_days: int = 30) -> bool:
        """Check if a soft-deleted user is still within the recovery grace period"""
        user = await self.get_user_by_id(user_id, include_deleted=True)
        
        if not user or user.get("is_active", True):
            return False  # User not deleted or not found
        
        deleted_at = user.get("deleted_at")
        if not deleted_at:
            return False  # Not soft-deleted
        
        grace_period = timedelta(days=grace_days)
        return datetime.now() - deleted_at <= grace_period