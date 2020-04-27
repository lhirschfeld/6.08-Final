import docker
from docker.types import Mount

import requests
import time, os, shutil
from pathlib import Path
import urllib.request
import zipfile

WORKSPACE_DIR = os.path.join(Path.home(),".the_hill/workspace")

def pop_job(robot_name, url): 
    endpoint = url + '/pop/' + robot_name    
    return requests.post(endpoint).json()

def get_job(job, url):
    endpoint = url + '/job/' + str(job['id'])   
    return requests.get(endpoint).json()

def prepare_workspace(job, url):
    # Delete workspace folder to clear
    if os.path.exists(WORKSPACE_DIR):
        shutil.rmtree(WORKSPACE_DIR)

    # Then create it, along with directories for output and code
    os.makedirs(WORKSPACE_DIR)
    os.makedirs(os.path.join(WORKSPACE_DIR,"code"))
    os.makedirs(os.path.join(WORKSPACE_DIR,"output"))

    # Now, we download the code zip.
    zipfile_path = os.path.join(WORKSPACE_DIR,'code.zip')
    urllib.request.urlretrieve(
        url + '/code/' + str(job['id']), 
        zipfile_path
    )
    
    # And extract it into the code directory.
    with zipfile.ZipFile(zipfile_path, 'r') as f:
        f.extractall(os.path.join(WORKSPACE_DIR,"code"))

def run_job(client, job, url):
    c = client.containers.run(
        job['container'],
        job['run_command'],
        detach=True,
        working_dir='/code',
        volumes={
            os.path.join(WORKSPACE_DIR,'code'):{'bind':'/code', 'mode': 'rw'},
            os.path.join(WORKSPACE_DIR,'output'):{'bind':'/out', 'mode': 'rw'},
            '/dev':{'bind':'/dev', 'mode': 'rw'} # for USB serial
        }
    )
    
    c.reload()
    while c.status != 'exited':
        time.sleep(1)
        job = get_job(job, url)
        if job['status'] == 'cancelled':
            c.stop()
        
        c.reload()

    job['logs'] = c.logs(timestamps=True)
    c.remove()
    
    return job
       
def push_job(job, url):
    # First, we zip the contents of the output directory.
    zip_dir = os.path.join(WORKSPACE_DIR,'output')
    shutil.make_archive(
        zip_dir, 'zip', zip_dir
    )
    
    # Now, we push it to the server.
    endpoint = url + '/job/' + str(job['id'])
    if job['status'] != 'cancelled':
        job['status']  = 'finished'

    requests.put(endpoint, params = {
        'job_id': job['id'],
        'job_logs': job['logs'],
        'job_status': job['status']
    }, files = {'output_zip': open(zip_dir+'.zip', "rb")})
    
def run(robot_name, url):
    client = docker.from_env()
    
    while True:
        time.sleep(1)
        
        job = pop_job(robot_name, url)
        if job is None:
            continue
        
        print(f'Running job {job["id"]}...')
        prepare_workspace(job, url) # setup workspace
        completed_job = run_job(client, job, url) # run job
        push_job(completed_job, url) # push job to server
        print(f'Finished job {job["id"]}!')    