import typer
import requests 
from typing import List
from datetime import datetime
from pydantic import BaseModel
from pathlib import Path
import os
import daemon
from zipfile import ZipFile
import pandas
from pandas.io.json import json_normalize
HOST_FILE = os.path.join(Path.home(),".the_hill/host.txt")
CODE_FILE = os.path.join(Path.home(), ".the_hill/code.zip")

app = typer.Typer()
url_name = None
job_app = typer.Typer()
app.add_typer(job_app, name="job")

if os.path.exists(HOST_FILE):
    f = open(HOST_FILE, "r")
    url_name = f.readlines()[0]

def json_print(js, hide = True):    
    out = json_normalize(js)
    if out.empty:
        empty = {'id': '', 
                'timestamp': '',
                'status': '',
                'container':'',
                'run_command': '',
                'mount': '',
                'robot': '',
                'logs': ''}
        out = json_normalize(empty)
    out.set_index('id', inplace = True)
    if hide:
        out.drop(columns = ['logs'], inplace = True)
    typer.echo(out)


@app.command()
def queue(robot_name: str = typer.Argument(None), 
            url: str = typer.Option(url_name, prompt = True)): 
    set_host(url)
    endpoint = url + '/queue/'
    if robot_name is not None:
        endpoint += robot_name
    r = requests.get(endpoint)
    json_print(r.json())


@app.command()
def history(robot_name: str = typer.Argument(None), 
            url: str = typer.Option(url_name, prompt = True)): 
    set_host(url)
    endpoint = url + '/history/'
    if robot_name is not None:
        endpoint += robot_name
    r = requests.get(endpoint)
    json_print(r.json())

@job_app.command("create")
def job_create(container: str,
        mount: str,
        robot: str,
        code_zip: str, 
        run_command: str,
        url: str = typer.Option(url_name, prompt = True)):
    set_host(url)
    endpoint = url + '/job/'
    if os.path.isdir(code_zip):  
        with ZipFile(CODE_FILE, 'w') as f:
           for folderName, subfolders, filenames in os.walk(code_zip):
               for filename in filenames:
                   filePath = os.path.join(folderName, filename)
                   f.write(filePath)
        f = open(CODE_FILE, "rb")
    else :  
        f= open(code_zip,"rb")

    r = requests.post(endpoint, params = {
        'container': container,
        'mount': mount,
        'robot': robot,
        'run_command': run_command
    }, files = {'code_zip': f})
    json_print(r.json())
    f.close()


@job_app.command("read") 
def job_read(job_id : int, 
            url: str = typer.Option(url_name, prompt = True)):
    set_host(url)
    endpoint = url + '/job/' + str(job_id)
    r = requests.get(endpoint)
    json_print(r.json(), False)
    
@job_app.command("delete") 
def job_delete(job_id : int, 
            url: str = typer.Option(url_name, prompt = True)):
    endpoint = url + '/job/'+ str(job_id)
    r = requests.delete(endpoint)
    json_print(r.json())


@job_app.command("update")
def job_update(job_id : int, 
                job_status: str, 
                job_logs: str,
                output_zip: str,
                url: str = typer.Option(url_name, prompt = True)):
    set_host(url)
    endpoint = url + '/job/' + str(job_id) 
    f= open(output_zip,"rb")   
    r = requests.put(endpoint, 
                params= {'job_id': job_id, 'job_status': job_status, 'job_logs': job_logs},
                files = {'output_zip': f})
    print(r.text)
    json_print(r.json())


@app.command("daemon") 
def run_daemon(robot_name : str, 
                url: str = typer.Option(url_name, prompt = True)):
    
    set_host(url)
    daemon.run(robot_name, url)

    
@app.command()
def sethost(host_url: str):
    set_host(host_url)
    typer.echo("host url: " + str(host_url))

def set_host(host_url):
    if not os.path.exists(os.path.dirname(HOST_FILE)):
        os.makedirs(os.path.dirname(HOST_FILE))

    file = open(HOST_FILE,"w+") 
    file.truncate(0)
    file.write(host_url) 
    url_name = host_url
    file.close() #to change file access modes 

if __name__ == "__main__":
    app()
