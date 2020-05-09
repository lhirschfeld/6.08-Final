from datetime import datetime, timedelta
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
from pydantic import BaseModel
from typing import List

from db import activity, database, jobs, STATUS

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

app.mount("/static", StaticFiles(directory="static"), name="static")


class Job(BaseModel):
    id: int
    timestamp: datetime
    status: str
    container: str
    run_command: str
    mount: str
    robot: str
    logs: str


def ensure_storage():
    for storage_folder in ['code_zips', 'output_zips']:
        if not os.path.exists(storage_folder):
            os.makedirs(storage_folder)


@app.on_event('startup')
async def startup():
    await database.connect()


@app.on_event('shutdown')
async def shutdown():
    await database.disconnect()


@app.get("/", response_class=HTMLResponse)
async def main():
    return '\n'.join(open('index.html').readlines())


@app.get('/queue/', response_model=List[Job])
async def read_all_queues():
    query = jobs.select().where(jobs.c.status == STATUS['QUEUED']) \
                         .order_by(jobs.c.timestamp.asc())

    return await database.fetch_all(query)


@app.get('/queue/{robot_name}', response_model=List[Job])
async def read_robot_queue(robot_name: str):
    query = jobs.select().where(jobs.c.status == STATUS['QUEUED']) \
                         .where(jobs.c.robot == robot_name) \
                         .order_by(jobs.c.timestamp.asc())

    return await database.fetch_all(query)


@app.get('/history/', response_model=List[Job])
async def read_all_histories():
    query = jobs.select().where(jobs.c.status != STATUS['QUEUED']) \
                         .order_by(jobs.c.timestamp.desc())

    return await database.fetch_all(query)


@app.get('/history/{robot_name}', response_model=List[Job])
async def read_robot_history(robot_name: str):
    query = jobs.select().where(jobs.c.status != STATUS['QUEUED']) \
                         .where(jobs.c.robot == robot_name) \
                         .order_by(jobs.c.timestamp.desc())

    return await database.fetch_all(query)


@app.post('/job/', response_model=Job)
async def create_job(container: str,
                     mount: str,
                     robot: str,
                     run_command: str,
                     code_zip: UploadFile = File(...)):
    query = jobs.insert(None).values(container=container,
                                     mount=mount,
                                     robot=robot,
                                     run_command=run_command)

    last_job_id = await database.execute(query)

    ensure_storage()
    with open(f'code_zips/{last_job_id}.zip', 'wb+') as f:
        output = await code_zip.read()
        f.write(output)

    new_query = jobs.select().where(jobs.c.id == last_job_id)

    return await database.fetch_one(new_query)


@app.get('/job/{job_id}', response_model=Job)
async def read_job(job_id: int):
    query = jobs.select().where(jobs.c.id == job_id)

    return await database.fetch_one(query)


@app.put('/job/{job_id}', response_model=Job)
async def update_job(job_id: int, job_status: str, job_logs: str,
                     output_zip: UploadFile = File(...)):

    query = jobs.update().values(status=job_status, logs=job_logs) \
                         .where(jobs.c.id == job_id)
    await database.execute(query)

    ensure_storage()
    with open(f'output_zips/{job_id}.zip', 'wb+') as f:
        output = await output_zip.read()
        f.write(output)

    new_query = jobs.select(jobs.c.id == job_id)

    return await database.fetch_one(new_query)


@app.delete('/job/{job_id}', response_model=Job)
async def delete_job(job_id: int):
    query = jobs.select(jobs.c.id == job_id)
    job = await database.fetch_one(query)

    new_query = jobs.delete().where(jobs.c.id == job_id)
    await database.execute(new_query)

    for path in [
        f'code_zips/{job_id}.zip',
        f'output_zips/{job_id}.zip'
    ]:
        if os.path.exists(path):
            os.remove(path)

    return job


@app.get('/code/{job_id}')
async def read_code(job_id: int):
    query = jobs.select(jobs.c.id == job_id)
    job = await database.fetch_one(query)

    path = f'code_zips/{job_id}.zip'

    if job is None or not os.path.exists(path):
        return None

    return FileResponse(path, filename=f'{job_id}.zip')


@app.get('/output/{job_id}')
async def read_output(job_id: int):
    query = jobs.select(jobs.c.id == job_id)
    job = await database.fetch_one(query)

    path = f'output_zips/{job_id}.zip'

    if job is None or not os.path.exists(path):
        return None

    return FileResponse(path, filename=f'{job_id}.zip')


@app.post('/pop/{robot_name}', response_model=Job)
async def pop(robot_name: str):
    # Record this activity.
    query = activity.insert(None).values(robot=robot_name)

    await database.execute(query)

    # Pop the robot from the queue.
    query = jobs.select().where(jobs.c.status == STATUS['QUEUED']) \
                         .where(jobs.c.robot == robot_name) \
                         .order_by(jobs.c.timestamp.asc())

    job = await database.fetch_one(query)

    if job is None:
        return None

    query = jobs.update().values(status=STATUS['RUNNING']) \
                         .where(jobs.c.id == job.id)
    await database.execute(query)

    return await database.fetch_one(jobs.select(jobs.c.id == job.id))


@app.get('/activity/', response_model=List[str])
async def read_active_robots(seconds_since_last_ping: int = 180):
    old_time = datetime.utcnow() - timedelta(seconds=seconds_since_last_ping)
    query = activity.select() \
                    .where(activity.c.timestamp > old_time) \
                    .column(activity.c.robot) \
                    .distinct()

    robot_rows = await database.fetch_all(query)
    return [row.robot for row in robot_rows]
