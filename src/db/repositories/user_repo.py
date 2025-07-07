from typing import Optional
from datetime import datetime
from core.database import DatabasePool

from core.security import hash_password

class UserRepository:
    def __init__(self, pool: DatabasePool):
        self.pool = pool
    
    async def create_user(self, email: str, password: str) -> int:
        """Create a new user and return the user ID"""
        hashed_password = hash_password(password)
        
        async with self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO users (email, hashed_password, created_at, is_active)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (email, hashed_password.decode('utf-8'), datetime.now(), True))
                
                result = await cursor.fetchone()
                await conn.commit()
                return result['id']
            
    async def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """Get user by ID"""
        async with self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, email, created_at, is_active
                    FROM users 
                    WHERE id = %s AND is_active = true
                """, (user_id,))
                
                return await cursor.fetchone()

    async def get_user_by_email(self, email: str) -> Optional[dict]:
        """Retrieve user by email"""
        async with self.pool.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, email, hashed_password, created_at, is_active
                    FROM users
                    WHERE email = %s
                """, (email,))
                
                return await cursor.fetchone()