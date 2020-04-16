import databases
import sqlalchemy

DATABASE_URL = "sqlite:///./hill.db"

database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

# Use strings for status
STATUS_QUEUED    = "queued"
STATUS_RUNNING   = "running" 
STATUS_FINISHED  = "finished"
STATUS_CANCELLED = "cancelled"

DEFAULT_MOUNT    = "/output"

jobs = sqlalchemy.Table(
    "jobs",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("timestamp", sqlalchemy.DateTime, server_default=sqlalchemy.sql.func.now()),
    sqlalchemy.Column("status", sqlalchemy.String, server_default=STATUS_QUEUED),
    sqlalchemy.Column("container", sqlalchemy.String),
    sqlalchemy.Column("mount", sqlalchemy.String, server_default=DEFAULT_MOUNT),
    sqlalchemy.Column("robot", sqlalchemy.String, server_default=""),
    sqlalchemy.Column("code_zip", sqlalchemy.String),
    sqlalchemy.Column("output_zip", sqlalchemy.String, server_default=""),

)

engine = sqlalchemy.create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
metadata.create_all(engine)
