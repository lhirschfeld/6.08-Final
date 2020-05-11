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
import json

HOST_FILE = os.path.join(Path.home(),".the_hill/host.txt")
CODE_FILE = os.path.join(Path.home(), ".the_hill/code.zip")


app = typer.Typer()
url_name = None
job_app = typer.Typer()
app.add_typer(job_app, name="job")

if os.path.exists(HOST_FILE):
    with open(HOST_FILE) as json_file:
        stored_values = json.load(json_file)
else: 
    stored_values = {"container": None,
                    "mount": None,
                    "robot": None,
                    "run_command": None,
                    "code_zip": None,
                    "url_name": None}

def json_print(js, hide = True):    
    out = pandas.json_normalize(js)
    if out.empty:
        empty = {'id': '', 
                'timestamp': '',
                'status': '',
                'container':'',
                'run_command': '',
                'mount': '',
                'robot': '',
                'logs': ''}
        out = pandas.json_normalize(empty)
    out.set_index('id', inplace = True)
    if hide:
        out.drop(columns = ['logs'], inplace = True)
    typer.echo(out)


@app.command()
def queue(robotname: str = typer.Option(None), 
            url: str = typer.Option(stored_values["url_name"], prompt = True)): 
    set_host(url)
    endpoint = url + '/queue/'
    if robotname is not None:
        endpoint += robotname
    r = requests.get(endpoint)
    json_print(r.json())


@app.command()
def history(robotname: str = typer.Option(None), 
            url: str = typer.Option(stored_values["url_name"], prompt = True)): 
    set_host(url)
    endpoint = url + '/history/'
    if robotname is not None:
        endpoint += robotname
    r = requests.get(endpoint)
    json_print(r.json())

@job_app.command("create")
def job_create(container: str = typer.Option(stored_values["container"], prompt = True),
        mount: str = typer.Option(stored_values["mount"], prompt = True),
        robotname: str = typer.Option(stored_values["robot"], prompt = True),
        codezip: str = typer.Option(stored_values["code_zip"], prompt = True), 
        runcommand: str = typer.Option(stored_values["run_command"], prompt = True),
        url: str = typer.Option(stored_values["url_name"], prompt = True)):
    update(container, mount, robotname, codezip, runcommand, url)
    endpoint = url + '/job/'
    if os.path.isdir(codezip):  
        with ZipFile(CODE_FILE, 'w') as f:
           for folderName, subfolders, filenames in os.walk(codezip):
               for filename in filenames:
                   filePath = os.path.join(folderName, filename)
                   f.write(filePath)
        f = open(CODE_FILE, "rb")
    else :  
        f= open(codezip,"rb")

    r = requests.post(endpoint, params = {
        'container': container,
        'mount': mount,
        'robot': robotname,
        'run_command': runcommand
    }, files = {'code_zip': f})
    json_print(r.json())
    f.close()

def update(container, mount, robot_name, code_zip, run_command, url):
    stored_values["container"] = container
    stored_values["mount"] = mount
    stored_values["robot"] = robot_name
    stored_values["code_zip"] = code_zip
    stored_values["run_command"] = run_command
    stored_values["url_name"] = url
    if not os.path.exists(os.path.dirname(HOST_FILE)):
        os.makedirs(os.path.dirname(HOST_FILE))

    file = open(HOST_FILE,"w+") 
    file.truncate(0)
    json.dump(stored_values, file)
    file.close() 
    

@job_app.command("read") 
def job_read(jobid : int = typer.Option(None, prompt = True),  
            url: str = typer.Option(stored_values["url_name"], prompt = True)):
    set_host(url)
    endpoint = url + '/job/' + str(jobid)
    r = requests.get(endpoint)
    json_print(r.json(), False)
    
@job_app.command("delete") 
def job_delete(jobid : int = typer.Option(None, prompt = True), 
            url: str = typer.Option(stored_values["url_name"], prompt = True)):
    endpoint = url + '/job/'+ str(jobid)
    r = requests.delete(endpoint)
    json_print(r.json())


@job_app.command("update")
def job_update(jobid : int = typer.Option(None, prompt = True), 
                jobstatus : str = typer.Option(None, prompt = True), 
                joblogs : str = typer.Option(None, prompt = True), 
                outputzip : str = typer.Option(None, prompt = True), 
                url: str = typer.Option(stored_values["url_name"], prompt = True)):
    set_host(url)
    endpoint = url + '/job/' + str(jobid) 
    f= open(outputzip,"rb")   
    r = requests.put(endpoint, 
                params= {'job_id': jobid, 'job_status': jobstatus, 'job_logs': joblogs},
                files = {'output_zip': f})
    print(r.text)
    json_print(r.json())


@app.command("daemon") 
def run_daemon(robot_name : str, 
                url: str):    
    set_host(url)
    daemon.run(robot_name, url)

    
@app.command()
def sethost(host_url: str):
    set_host(host_url)
    typer.echo("host url: " + str(host_url))


def set_host(host_url):
    stored_values["url_name"] = host_url
    if not os.path.exists(os.path.dirname(HOST_FILE)):
        os.makedirs(os.path.dirname(HOST_FILE))

    file = open(HOST_FILE,"w+") 
    file.truncate(0)
    json.dump(stored_values, file)
    file.close()

if __name__ == "__main__":
    app()
