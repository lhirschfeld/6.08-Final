from datetime import datetime
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
import os
from pydantic import BaseModel
from typing import List

from db import database, jobs, STATUS

app = FastAPI()


class JobIn(BaseModel):
    container: str
    mount: str
    robot: str
    output_zip_path: str


class Job(BaseModel):
    id: int
    timestamp: datetime
    status: str
    container: str
    mount: str
    robot: str
    output_zip_path: str


@app.on_event('startup')
async def startup():
    await database.connect()


@app.on_event('shutdown')
async def shutdown():
    await database.disconnect()


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
                     output_zip_path: str,
                     code_zip: UploadFile = File(...)):
    query = jobs.insert(None).values(container=container,
                                     mount=mount,
                                     robot=robot,
                                     output_zip_path=output_zip_path)

    last_job_id = await database.execute(query)

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
async def update_job(job_id: int, job_status: str):
    query = jobs.update().values(status=job_status) \
                         .where(jobs.c.id == job_id)
    await database.execute(query)

    new_query = jobs.select(jobs.c.id == job_id)

    return await database.fetch_one(new_query)


@app.delete('/job/{job_id}', response_model=Job)
async def delete_job(job_id: int):
    query = jobs.select(jobs.c.id == job_id)
    job = await database.fetch_one(query)

    new_query = jobs.delete().where(jobs.c.id == job_id)
    await database.execute(new_query)

    path = f'code_zips/{job_id}.zip'
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


@app.post('/pop/{robot_name}', response_model=Job)
async def pop(robot_name: str):
    query = jobs.select().where(jobs.c.status == STATUS['QUEUED']) \
                         .where(jobs.c.robot == robot_name) \
                         .order_by(jobs.c.timestamp.asc())

    job = await database.fetch_one(query)

    if job is None:
        return None

    updated_job = await update_job(job.id, STATUS['RUNNING'])

    return updated_job
