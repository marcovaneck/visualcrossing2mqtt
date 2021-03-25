# first stage
FROM python:3.9 AS builder
COPY requirements.txt .

# install dependencies to the local user directory (eg. /root/.local)
RUN pip install --user -r requirements.txt

# second unnamed stage
FROM python:3.9-slim
WORKDIR /app
RUN adduser --shell /bin/false --disabled-password --gecos '' user

# copy only the dependencies installation from the 1st stage image
COPY --from=builder /root/.local /home/user/.local
COPY visualcrossing2mqtt visualcrossing2mqtt
RUN chmod go+rX -R /home/user/.local /app

ENV mqtt_host=host.docker.internal
USER user

# update PATH environment variable
ENV PATH=/home/user/.local:$PATH

CMD [ "python", "-u", "visualcrossing2mqtt" ]