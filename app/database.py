import os
import sqlite3
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

DATABASE_URL = os.getenv("LINSPIRER_DB_PATH", "sqlite+aiosqlite:///./data/linspirer.db")
DB_PATH = DATABASE_URL.replace("sqlite+aiosqlite:///", "")

Base = declarative_base()

db_dir = os.path.dirname(DB_PATH)
if db_dir:
    os.makedirs(db_dir, exist_ok=True)

async_engine = create_async_engine(DATABASE_URL, connect_args={"check_same_thread": False}, echo=False)
engine = async_engine
async_session_maker = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)


def init_db_sync():
    from app.auth import get_password_hash
    
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            description TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 更新CHECK约束：添加randomize_app_duration
    try:
        # 1. 禁用外键约束（如果有）
        cursor.execute('PRAGMA foreign_keys = OFF')
        
        # 2. 创建新表，带有正确的CHECK约束
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interception_rules_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                method_name TEXT NOT NULL,
                email TEXT,
                action TEXT NOT NULL CHECK(action IN ('passthrough', 'modify', 'replace', 'randomize_app_duration')),
                custom_response TEXT,
                remark TEXT,
                is_enabled BOOLEAN DEFAULT 1,
                is_global BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 3. 复制数据
        cursor.execute('''
            INSERT INTO interception_rules_new (
                id, method_name, email, action, custom_response, remark, 
                is_enabled, is_global, created_at, updated_at
            ) SELECT 
                id, method_name, email, action, custom_response, remark, 
                is_enabled, is_global, created_at, updated_at
            FROM interception_rules
        ''')
        
        # 4. 删除旧表
        cursor.execute('DROP TABLE interception_rules')
        
        # 5. 重命名新表
        cursor.execute('ALTER TABLE interception_rules_new RENAME TO interception_rules')
        
        # 6. 重建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_interception_rules_method_email ON interception_rules(method_name, email)')
        
        # 7. 启用外键约束
        cursor.execute('PRAGMA foreign_keys = ON')
    except sqlite3.OperationalError:
        # 如果新表已存在或其他错误，忽略并继续
        cursor.execute('''CREATE TABLE IF NOT EXISTS interception_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            method_name TEXT NOT NULL,
            email TEXT,
            action TEXT NOT NULL CHECK(action IN ('passthrough', 'modify', 'replace', 'randomize_app_duration')),
            custom_response TEXT,
            remark TEXT,
            is_enabled BOOLEAN DEFAULT 1,
            is_global BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
    
    # 索引已在表替换过程中创建，无需重复
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            command_json TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('unverified', 'verified', 'rejected')),
            received_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            processed_at DATETIME,
            notes TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS request_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            method TEXT,
            request_body TEXT,
            response_body TEXT,
            intercepted_request TEXT,
            intercepted_response TEXT,
            request_interception_action TEXT,
            response_interception_action TEXT,
            email TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    try:
        cursor.execute('ALTER TABLE request_logs ADD COLUMN email TEXT')
    except sqlite3.OperationalError:
        pass
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tactics_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            template_json TEXT NOT NULL,
            is_default BOOLEAN DEFAULT 0,
            is_applied BOOLEAN DEFAULT 0,
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    try:
        cursor.execute('ALTER TABLE tactics_templates ADD COLUMN is_applied BOOLEAN DEFAULT 0')
    except sqlite3.OperationalError:
        pass
    
    cursor.execute("SELECT value FROM config WHERE `key` = 'admin_password_hash'")
    if cursor.fetchone() is None:
        password_hash = get_password_hash("admin123")
        cursor.execute(
            "INSERT INTO config (`key`, value, description) VALUES (?, ?, ?)",
            ("admin_password_hash", password_hash, "Hashed admin password (default: admin123)")
        )
    
    cursor.execute("SELECT value FROM config WHERE `key` = 'target_url'")
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO config (`key`, value, description) VALUES (?, ?, ?)",
            ("target_url", "https://cloud.linspirer.com:883", "Target server URL for proxying")
        )
    
    conn.commit()
    conn.close()


async def init_db():
    init_db_sync()


async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
