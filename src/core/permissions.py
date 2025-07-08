from enum import Enum

class Permission(str, Enum):
    # User management
    USER_READ_OWN_PROFILE = "user:read_own_profile"
    USER_UPDATE_OWN_PROFILE = "user:update_own_profile"
    USER_DELETE_OWN_ACCOUNT = "user:delete_own_account"
    
    # Music data
    MUSIC_READ_OWN_DATA = "user:read_music_data"
    MUSIC_SYNC_OWN_SPOTIFY = "user:sync_own_spotify"
    MUSIC_DELETE_OWN_DATA = "user:delete_music_data"
    
    # AI insights
    AI_GENERATE_OWN_INSIGHTS = "user:gen_insights"
    
    # System operations
    ADMIN_READ_ALL_USERS = "admin:read_all_users"
    ADMIN_DELETE_ANY_USER = "admin:delete_user"
    ADMIN_VIEW_SYSTEM_STATS = "admin:system_stats"
    ADMIN_MANAGE_API_KEYS = "admin:api_keys"
    ADMIN_MANAGE_PERMISSIONS = "admin:permissions"
    ADMIN_MANAGE_SYSTEM = "admin:system"

class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"
    SYSTEM = "system"

# Role to permissions mapping
ROLE_PERMISSIONS = {
    Role.USER: [
        Permission.USER_READ_OWN_PROFILE,
        Permission.USER_UPDATE_OWN_PROFILE,
        Permission.USER_DELETE_OWN_ACCOUNT,
        Permission.MUSIC_READ_OWN_DATA,
        Permission.MUSIC_SYNC_OWN_SPOTIFY,
        Permission.MUSIC_DELETE_OWN_DATA,
        Permission.AI_GENERATE_OWN_INSIGHTS,
    ],
    Role.ADMIN: [
        Permission.USER_READ_OWN_PROFILE,
        Permission.USER_UPDATE_OWN_PROFILE,
        Permission.USER_DELETE_OWN_ACCOUNT,
        Permission.MUSIC_READ_OWN_DATA,
        Permission.MUSIC_SYNC_OWN_SPOTIFY,
        Permission.MUSIC_DELETE_OWN_DATA,
        Permission.AI_GENERATE_OWN_INSIGHTS,
        Permission.ADMIN_READ_ALL_USERS,
        Permission.ADMIN_DELETE_ANY_USER,
        Permission.ADMIN_VIEW_SYSTEM_STATS,
        Permission.ADMIN_MANAGE_API_KEYS,
        Permission.ADMIN_MANAGE_PERMISSIONS,
        Permission.ADMIN_MANAGE_SYSTEM
    ],
}