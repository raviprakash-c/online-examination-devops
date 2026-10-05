import os

import pymysql
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3307")),
        user=os.getenv("DB_USER", "examuser"),
        password=os.getenv("DB_PASSWORD", "exampassword"),
        database=os.getenv("DB_NAME", "online_exam"),
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=int(os.getenv("DB_CONNECT_TIMEOUT", "5")),
        read_timeout=int(os.getenv("DB_READ_TIMEOUT", "10")),
        write_timeout=int(os.getenv("DB_WRITE_TIMEOUT", "10")),
        autocommit=False,
    )
