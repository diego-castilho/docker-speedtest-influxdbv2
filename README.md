# ⚠️ WARNING ⚠️

Telegraf now has an official Internet Speed Monitor plugin. I recommend using that instead.

https://github.com/influxdata/telegraf/tree/master/plugins/inputs/internet_speed

# docker-speedtest-influxdbv2

[![CI/CD](https://github.com/loganmarchione/docker-speedtest-influxdbv2/actions/workflows/main.yml/badge.svg)](https://github.com/loganmarchione/docker-speedtest-influxdbv2/actions/workflows/main.yml)
[![Docker Image Size (latest semver)](https://img.shields.io/docker/image-size/loganmarchione/docker-speedtest-influxdbv2)](https://hub.docker.com/r/loganmarchione/docker-speedtest-influxdbv2)

Runs Ookla's [Speedtest CLI](https://www.speedtest.net/apps/cli) program in Docker, sends the results to InfluxDB
  - Source code: [GitHub](https://github.com/loganmarchione/docker-speedtest-influxdbv2)
  - Docker container: [Docker Hub](https://hub.docker.com/r/loganmarchione/docker-speedtest-influxdbv2)
  - Image base: [Python (slim Buster)](https://hub.docker.com/_/python)
  - Init system: N/A
  - Application: [Speedtest CLI](https://www.speedtest.net/apps/cli)
  - Architecture: `linux/amd64`


## Explanation

  - This runs Ooka's Speedtest CLI program on an interval, then writes the data to an InfluxDB database (you can later graph this data with Grafana or Chronograf)
  - This does **NOT** use the open-source [speedtest-cli](https://github.com/sivel/speedtest-cli). That program uses the Speedtest.net HTTP API. This program uses Ookla's official CLI application.
  - ⚠️ Ookla's speedtest application is closed-source (the binary applications are [here](https://www.speedtest.net/apps/cli)) and Ookla's reasoning for this decision is [here](https://www.reddit.com/r/HomeNetworking/comments/dpalqu/speedtestnet_just_launched_an_official_c_cli/f5tm9up/) ⚠️
  - ⚠️ Ookla's speedtest application reports all data back to Ookla ⚠️
  - ⚠️ This application uses Ookla's recommendation to install by piping curl to bash  ⚠️
  - The default output unit of measurement is **bytes-per-second**. You will most likely want to convert to megabits-per-second by dividing your output by 125000.

```
For example, if your download speed is 11702913 bytes-per-second:
11702913 / 125000 = 93.623304 megabits-per-second
```

## Requirements

  - This only works with InfluxDB v1.8 and v2, because I'm using [this](https://github.com/influxdata/influxdb-client-python) client library.
  - You must already have an InfluxDB database created, along with a user that has `WRITE` and `READ` permissions on that database.
  - This Docker container needs to be able to reach that InfluxDB instance by hostname, IP address, or Docker service name (I run this container on the same Docker network as my InfluxDB instance).
  - ⚠️ Depending on how often you run this, you may need to monitor your internet connection's usage. If you have a data cap, you could exceed it. The standard speedtest uses about 750MB of data per run. See below for an example. ⚠️

```
CONTAINER: NET I/O
speedtest: 225MB / 495MB
```

## Docker image information

### Docker image tags
  - `latest`: Latest version
  - `X.X.X`: [Semantic version](https://semver.org/) (use if you want to stick on a specific version)

### Environment variables
| Variable         | Required?                  | Definition                                     | Example                                     | Comments                                                                                            |
|------------------|----------------------------|------------------------------------------------|---------------------------------------------|-----------------------------------------------------------------------------------------------------|
| INFLUXDB_SCHEME  | No (default: http)         | Connect to InfluxDB using http or https        | 'https'                                     | Useful if InfluxDB is behind a reverse proxy and you need to use https                              |
| INFLUXDB_HOST    | No (default: localhost)    | Server hosting the InfluxDB                    | 'localhost' or your Docker service name     |                                                                                                     |
| INFLUXDB_PORT    | No (default: 8086)         | InfluxDB port                                  | 8086                                        |                                                                                                     |
| INFLUXDB_USER    | Yes (only for v1)          | Database username                              | test1                                       | Needs to have the correct permissions                                                               |
| INFLUXDB_PASS    | Yes (only for v1)          | Database password                              | test1234                                    |                                                                                                     |
| INFLUXDB_TOKEN   | Yes (only for v2)          | Token to connect to bucket                     | asdfghjkl                                   | Needs to have the correct permissions. Setting this assumes we're talking to an InfluxDBv2 instance |
| INFLUXDB_ORG     | Yes (only for v2)          | Organization                                   | my_test_org                                 |                                                                                                     |
| INFLUXDB_DB      | Yes                        | Database name                                  | SpeedtestStats                              | Must already be created. In InfluxDBv2, this is the "bucket".                                       |
| SLEEPY_TIME      | No (default: 3600)         | Seconds to sleep between runs                  | 3600                                        | The loop takes about 15-30 seconds to run, so I wouldn't set this value any lower than 60 (1min)    |
| SPEEDTEST_HOST   | No (default: container ID) | Hostname of service where Speedtest is running | server04                                    | Useful if you're running Speedtest on multiple servers                                              |
| SPEEDTEST_SERVER | No (default: random)       | ID number of Speedtest server                  | 41817                                       | See a list of servers and IDs [here](https://c.speedtest.net/speedtest-servers-static.php)          |

### Ports
N/A

### Volumes
N/A

### Example usage
Below is an example docker-compose.yml file for connecting to InfluxDB v2.
```
version: '3'
services:
  speedtest2:
    container_name: docker-speedtest-influxdbv2
    restart: unless-stopped
    environment:
      - INFLUXDB_SCHEME=http
      - INFLUXDB_HOST=influxdbv2
      - INFLUXDB_PORT=8086
      - INFLUXDB_TOKEN=asdfghjkl
      - INFLUXDB_ORG=my_test_org
      - INFLUXDB_DB=SpeedtestStats
      - SLEEPY_TIME=3600
      - SPEEDTEST_HOST=server04
      - SPEEDTEST_SERVER=41817
    networks:
      - speedtest2
    image: loganmarchione/docker-speedtest-influxdbv2:latest

networks:
  speedtest2:
```

Below is an example docker-compose.yml file for connecting to InfluxDB v1.8.
```
version: '3'
services:
  speedtest1:
    container_name: docker-speedtest-influxdbv1
    restart: unless-stopped
    environment:
      - INFLUXDB_SCHEME=http
      - INFLUXDB_HOST=influxdbv1
      - INFLUXDB_PORT=8086
      - INFLUXDB_USER=test1
      - INFLUXDB_PASS=test1234
      - INFLUXDB_DB=SpeedtestStats
      - SLEEPY_TIME=3600
      - SPEEDTEST_HOST=server04
      - SPEEDTEST_SERVER=41817
    networks:
      - speedtest1
    image: loganmarchione/docker-speedtest-influxdbv2:latest

networks:
  speedtest1:
```

Below is an example of running locally (used to edit/test/debug).
```
# Build the Dockerfile
docker compose -f docker-compose-dev.yml up -d

# View logs
docker compose -f docker-compose-dev.yml logs -f

# Destroy when done
docker compose -f docker-compose-dev.yml down
```

## TODO
- [ ] Learn Python
- [x] ~~Run the processes inside the container as a non-root user~~
- [ ] Add a [healthcheck](https://docs.docker.com/engine/reference/builder/#healthcheck)
- [x] ~~Move the database connection check to a function~~
- [x] ~~Add logic to check if variables are set~~
- [x] ~~Add defaults for HOST and PORT~~
- [ ] Update CI/CD with tests
- [x] ~~Add warning about bandwidth~~
- [ ] Implement an authentication check when [this PR](https://github.com/influxdata/influxdb-client-python/pull/269) is merged
