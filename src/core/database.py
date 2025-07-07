import psycopg
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from config.settings import get_settings

settings = get_settings()

class DatabasePool:
    def __init__(self):
        self.pool = None

    async def initialize(self):
        """Initialize connection pool"""
        self.pool = AsyncConnectionPool(
            conninfo = settings.database_url,
            min_size = 5,
            max_size = 20,
            row_factory = dict_row
        )

        await self._ensure_schema()
        self._schema_initialized = True

    async def _ensure_schema(self):
        """Checks if the db schema has been instantiated. If not, creates the db schema."""
        async with self.pool.connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = 'users';
                    )
                    """)
                
                users_table_exists = bool(await cursor.fetchone())[0]

                if not users_table_exists:
                    await self._create_schema(cursor)
                    await conn.commit()

                # Can create a check schema version here too

    async def _create_schema(self, cursor: psycopg.AsyncCursor):
        """Create all tables"""
        user_schema = """
        --users table
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            email TEXT NOT NULL UNIQUE,
            hashed_password TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL
        );
        """

        spotify_token_schema = """
        -- Spotify tokens table
        CREATE TABLE IF NOT EXISTS spotify_tokens (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            last_sync TIMESTAMP WITH TIME ZONE,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(user_id)
        );
        """

        refresh_token_schema = """
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            token_hash VARCHAR(255) NOT NULL,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            is_revoked BOOLEAN DEFAULT FALSE
        );
        """

        index_schema = """
        --user indices
        CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user
        ON refresh_tokens(user_id, expires_at);
        """


        database_schema = "".join(user_schema,
                                  spotify_token_schema,
                                  refresh_token_schema,
                                  index_schema)

        await cursor.execute(user_schema)

    async def close(self):
        """Close the connection pool"""
        if self.pool:
            await self.pool.close()

    async def get_connection(self):
        return self.pool.connection()
    
db_pool = DatabasePool()