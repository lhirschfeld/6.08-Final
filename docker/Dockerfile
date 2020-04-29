FROM resin/raspberrypi3-python:3.6

# Needed to build on x64
COPY ./qemu-system-arm /usr/bin/qemu-system-arm

RUN apt-get update -y

RUN pip install --upgrade pip

# numpy/scipy dependencies
RUN apt-get install -y libblas-dev gfortran libopenblas-base libatlas-base-dev

RUN pip install numpy gym tqdm pyserial