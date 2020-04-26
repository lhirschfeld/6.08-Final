import typer
import requests 
from typing import List
from datetime import datetime
from db import database, jobs, STATUS
from pydantic import BaseModel
from pathlib import Path
from fastapi import FastAPI, File, UploadFile

import os
import os.path
from os import path
# os.environ['NO_PROXY'] = '127.0.0.1,localhost'



app = typer.Typer()
url_name = None
job_app = typer.Typer()
app.add_typer(job_app, name="job")

if path.exists("host.txt"):
    f = open("host.txt", "r")
    url_name = f.readlines()[0]

@app.command()
def queue(robot_name: str = typer.Argument(None), 
            url: str = typer.Option(url_name, prompt = True)): 
    set_host(url)
    endpoint = url + '/queue'
    if robot_name is not None:
        endpoint += robot_name
    r = requests.get(endpoint)
    typer.echo(r.text)


@app.command()
def history(robot_name: str = typer.Argument(None), 
            url: str = typer.Option(url_name, prompt = True)): 
    set_host(url)
    endpoint = url + '/history/'
    if robot_name is not None:
        endpoint += robot_name
    r = requests.get(endpoint)
    typer.echo(r.text)


@app.command()
def pop(robot_name: str, 
        url: str = typer.Option(url_name, prompt = True)): 
    set_host(url)
    endpoint = url + '/pop/' + robot_name
    r = requests.post(endpoint)
    typer.echo(r.text)

@job_app.command("create")
def job_create(container: str,
        mount: str,
        robot: str,
        code_zip: str, 
        url: str = typer.Option(url_name, prompt = True)):
    set_host(url)
    endpoint = url + '/job/'
    f= open(code_zip,"rb")
    r = requests.post(endpoint, params = {'container': container, 'mount': mount, 'robot': robot}, files = {'code_zip': f})
    typer.echo(r.text)
    f.close()

@app.command()
def printurl():
    typer.echo(url_name)

@job_app.command("read") 
def job_read(job_id : int, 
            url: str = typer.Option(url_name, prompt = True)):
    set_host(url)
    endpoint = url + '/job/' + str(job_id)
    r = requests.get(endpoint)
    typer.echo(r.text)


@job_app.command("update")
def job_update(job_id : int, 
                job_status: str, 
                url: str = typer.Option(url_name, prompt = True)):
    set_host(url)
    endpoint = url + '/job/' + str(job_id)    
    r = requests.put(endpoint, params= {'job_id': job_id, 'job_status': job_status})
    typer.echo(r.text)


@job_app.command("delete") 
def job_delete(job_id : int, 
                url: str = typer.Option(url_name, prompt = True)):
    set_host(url)
    endpoint = url + '/job/'+ str(job_id)
    r = requests.delete(endpoint)
    typer.echo(r.text)


@app.command()
def sethost(host_url: str):
    set_host(host_url)
    typer.echo("host url: " + str(host_url))

def set_host(host_url):
    file = open("host.txt","w+") 
    file.truncate(0)
    file.write(host_url) 
    url_name = host_url
    file.close() #to change file access modes 

if __name__ == "__main__":
    app()
