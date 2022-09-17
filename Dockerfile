# syntax=docker/dockerfile:1
FROM python:3.9-slim-bullseye
WORKDIR /kooppy
RUN apt-get update
# Install GDAL dependencies
RUN apt-get install -y libgdal-dev g++ --no-install-recommends && \
    apt-get clean -y
# Update C env vars so compiler can find gdal
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get -yqq install libkrb5-dev
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
EXPOSE 80
COPY . .
CMD ["uvicorn", "main:app","--host", "0.0.0.0", "--port", "80"] 
