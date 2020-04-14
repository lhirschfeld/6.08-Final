import databases
import sqlalchemy
import datetime
from fastapi import FastAPI
from pydantic import BaseModel

DATABASE_URL = "sqlite:///./test.db"

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
    sqlalchemy.Column("timestamp", sqlalchemy.DateTime, default=datetime.datetime.utcnow),
    sqlalchemy.Column("status", sqlalchemy.String, default=STATUS_QUEUED),
    sqlalchemy.Column("container", sqlalchemy.String),
    sqlalchemy.Column("mount", sqlalchemy.String, default=DEFAULT_MOUNT),
    sqlalchemy.Column("robot", sqlalchemy.String, default=""),
    sqlalchemy.Column("code_zip", sqlalchemy.String),
    sqlalchemy.Column("output_zip", sqlalchemy.String, default=""),

)

engine = sqlalchemy.create_engine(DATABASE_URL)
metadata.create_all(engine)

app = FastAPI()

@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# See https://fastapi.tiangolo.com/advanced/async-sql-databases/ for
# SqlAlchemy and FastAPI usage