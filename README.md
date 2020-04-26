# The Hill

Install prerequisites with `python3 -m pip install -r requirements.txt`.  If you add a new package, please add it to the requirements file as well.

### Web API

The API (in `api.py`) is written in FastAPI using SQLAlchemy to talk to SQLite.  See [this page](https://fastapi.tiangolo.com/advanced/async-sql-databases/) for details.  To run the API, from `webserver` run `python3 -m uvicorn api:app --reload`.

### Command Line Interace

The CLI (in `cli.py`) is written in Typer, and provides the entrypoint for researchers to queue/monitor jobs and to start the robot daemon.

### Robot Library

The simulation and Arduino communications library lives in `env.py`.  This supports talking to the physical robot, but we still need to fill in the simulation dynamics.  We also should investigate finding simulation dynamics parameters that allows the best matching between hardware and simulation.

### Mechaduino firmware

The Arduino firmware for the cartpole robot lives in the `Mechaduino` directory.  This is forked from [jcchurch13/Mechaduino-Firmware](https://github.com/jcchurch13/Mechaduino-Firmware). Current thoughts:

1. There might be delays in the serial communication, but I'm not sure where from.  Could be useful to profile.
2. We should build a real current->force map, because it's certainly not linear (doesn't move from 0-20, caps out at 50).  I think this would make linear control methods like PID a lot easier.