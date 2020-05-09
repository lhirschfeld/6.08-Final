import databases
import sqlalchemy

DATABASE_URL = 'sqlite:///./hill.db'

database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

# Use strings for status
STATUS = {'QUEUED': 'queued',
          'RUNNING': 'running',
          'FINISHED': 'finished',
          'CANCELLED': 'cancelled'}

DEFAULT_MOUNT = '/output'

jobs = sqlalchemy.Table(
    'jobs',
    metadata,
    sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column('timestamp',
                      sqlalchemy.DateTime,
                      server_default=sqlalchemy.sql.func.now()),
    sqlalchemy.Column('status',
                      sqlalchemy.String,
                      server_default=STATUS['QUEUED']),
    sqlalchemy.Column('container', sqlalchemy.String),
    sqlalchemy.Column('run_command', sqlalchemy.String),
    sqlalchemy.Column('logs', sqlalchemy.String, server_default=''),
    sqlalchemy.Column('mount',
                      sqlalchemy.String,
                      server_default=DEFAULT_MOUNT),
    sqlalchemy.Column('robot', sqlalchemy.String, server_default='')
)

activity = sqlalchemy.Table(
    'activity',
    metadata,
    sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column('timestamp',
                      sqlalchemy.DateTime,
                      server_default=sqlalchemy.sql.func.now()),
    sqlalchemy.Column('robot', sqlalchemy.String)
)

engine = sqlalchemy.create_engine(DATABASE_URL,
                                  connect_args={'check_same_thread': False})
metadata.create_all(engine)
