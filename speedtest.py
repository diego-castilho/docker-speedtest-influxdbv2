#!/usr/bin/env python3

import datetime
import json
import os
import re
import subprocess  # nosec B404
import time
import socket
import sys
from influxdb_client import InfluxDBClient

# Variables
influxdb_scheme = os.getenv("INFLUXDB_SCHEME", "http")
influxdb_host = os.getenv("INFLUXDB_HOST", "localhost")
influxdb_user = os.getenv("INFLUXDB_USER")
influxdb_pass = os.getenv("INFLUXDB_PASS")
influxdb_token = os.getenv("INFLUXDB_TOKEN")
influxdb_org = os.getenv("INFLUXDB_ORG", "-")
influxdb_db = os.getenv("INFLUXDB_DB")
start_time = datetime.datetime.utcnow().isoformat()
default_hostname = socket.gethostname()
hostname = os.getenv("SPEEDTEST_HOST", default_hostname)
speedtest_server = os.getenv("SPEEDTEST_SERVER")
debug_mode = bool(os.getenv("DEBUG_MODE", False))

# Validate numeric environment variables
try:
    influxdb_port = int(os.getenv("INFLUXDB_PORT", 8086))
except ValueError:
    print("ERROR: INFLUXDB_PORT must be a valid integer")
    sys.exit(1)

try:
    sleepy_time = int(os.getenv("SLEEPY_TIME", 3600))
except ValueError:
    print("ERROR: SLEEPY_TIME must be a valid integer")
    sys.exit(1)

if sleepy_time < 0:
    print("ERROR: SLEEPY_TIME must be a non-negative integer")
    sys.exit(1)

# Validate speedtest server ID is numeric (prevents argument injection)
if speedtest_server and not re.match(r'^\d+$', speedtest_server):
    print("ERROR: SPEEDTEST_SERVER must be a numeric server ID")
    sys.exit(1)


def escape_line_protocol_tag(value):
    """Escape special characters in InfluxDB line protocol tag values."""
    value = str(value)
    value = value.replace(" ", "\\ ")
    value = value.replace(",", "\\,")
    value = value.replace("=", "\\=")
    return value


def escape_line_protocol_field_str(value):
    """Escape special characters in InfluxDB line protocol string field values."""
    value = str(value)
    value = value.replace("\\", "\\\\")
    value = value.replace('"', '\\"')
    return value


def db_check():

    if debug_mode is True:
        print("STATE: Debug mode is enabled, skipping the database check!")
    else:
        print("STATE: Running database check")
        client_health = client.ping()

        if client_health is True:
            print("STATE: Connection", client_health)
        elif client_health is False:
            print("ERROR: Connection", client_health, " - Check scheme, host, port, user, pass, token, org, etc...")
            sys.exit(1)
        else:
            print("ERROR: Something else went wrong")
            sys.exit(1)


def speedtest():
    db_check()

    current_time = datetime.datetime.utcnow().isoformat()
    print("STATE: Loop running at", current_time)

    # Run Speedtest
    # If the user specified a speedtest_server ID number, run a different command vs if they didn't specify an ID
    if speedtest_server:
        print("STATE: User specified speedtest server:", speedtest_server)
        speedtest_server_arg = "--server-id="+speedtest_server
        print("STATE: Speedtest running")
        my_speed = subprocess.run(['/usr/bin/speedtest', '--accept-license', '--accept-gdpr', '--format=json', speedtest_server_arg], stdout=subprocess.PIPE, shell=False, text=True, check=True)  # nosec B603
    else:
        print("STATE: User did not specify speedtest server, using a random server")
        print("STATE: Speedtest running")
        my_speed = subprocess.run(['/usr/bin/speedtest', '--accept-license', '--accept-gdpr', '--format=json'], stdout=subprocess.PIPE, shell=False, text=True, check=True)  # nosec B603

    # Convert the string into JSON, only getting the stdout and stripping the first/last characters
    my_json = json.loads(my_speed.stdout.strip())

    # Get the values from JSON and log them to the Docker logs
    # Basic values
    speed_down = my_json["download"]["bandwidth"]
    speed_up = my_json["upload"]["bandwidth"]
    ping_latency = my_json["ping"]["latency"]
    ping_jitter = my_json["ping"]["jitter"]
    result_url = my_json["result"]["url"]
    # Advanced values
    speedtest_server_id = my_json["server"]["id"]
    speedtest_server_name = my_json["server"]["name"]
    speedtest_server_location = my_json["server"]["location"]
    speedtest_server_country = my_json["server"]["country"]
    speedtest_server_host = my_json["server"]["host"]

    # Print results to Docker logs
    print("STATE: RESULTS ARE SAVED IN BYTES-PER-SECOND NOT MEGABITS-PER-SECOND")
    print("STATE: Your download     ", speed_down, "B/s")
    print("STATE: Your upload       ", speed_up, "B/s")
    print("STATE: Your ping latency ", ping_latency, "ms")
    print("STATE: Your ping jitter  ", ping_jitter, "ms")
    print("STATE: Your server info  ", speedtest_server_id, speedtest_server_name, speedtest_server_location, speedtest_server_country, speedtest_server_host)
    print("STATE: Your URL is       ", result_url)

    # Build InfluxDB line protocol with proper escaping
    # https://docs.influxdata.com/influxdb/v2.0/reference/syntax/line-protocol/
    safe_hostname = escape_line_protocol_tag(hostname)
    p = (
        f"speedtest,service=speedtest.net,host={safe_hostname} "
        f"download={int(speed_down)},"
        f"upload={int(speed_up)},"
        f"ping_latency={float(ping_latency)},"
        f"ping_jitter={float(ping_jitter)},"
        f"speedtest_server_id={int(speedtest_server_id)},"
        f'speedtest_server_name="{escape_line_protocol_field_str(speedtest_server_name)}",'
        f'speedtest_server_location="{escape_line_protocol_field_str(speedtest_server_location)}",'
        f'speedtest_server_country="{escape_line_protocol_field_str(speedtest_server_country)}",'
        f'speedtest_server_host="{escape_line_protocol_field_str(speedtest_server_host)}",'
        f'result_url="{escape_line_protocol_field_str(result_url)}"'
    )
    # For troubleshooting the raw line protocol
    # print(p)

    if debug_mode is True:
        print("STATE: Debug mode is enabled, skipping writing to the database!")
        print(p)
    else:
        try:
            print("STATE: Writing to database")
            write_api = client.write_api()
            write_api.write(bucket=influxdb_db, record=p)
            write_api.close()
        except Exception as err:
            print("ERROR: Error writing to database")
            print(err)

    print("STATE: Sleeping for", sleepy_time, "seconds")
    time.sleep(sleepy_time)


# Some logging
print("#####\nScript starting!\n#####")
print("STATE: Starting at", start_time)
print("STATE: Sleep time between runs set to", sleepy_time, "seconds")

# Check if variables are set
print("STATE: Checking environment variables...")

if debug_mode is True:
    print("STATE: Debug mode is enabled, not checking for any variables!")
else:
    if 'INFLUXDB_DB' in os.environ:
        print("STATE: INFLUXDB_DB is set")
        pass
    else:
        print("ERROR: INFLUXDB_DB is not set")
        sys.exit(1)

    if 'INFLUXDB_TOKEN' in os.environ:
        print("STATE: INFLUXDB_TOKEN is set, so we must be talking to an InfluxDBv2 instance")
        pass
        # If token is set, then we are talking to an InfluxDBv2 instance, so INFLUXDB_ORG must also be set
        if 'INFLUXDB_ORG' in os.environ:
            print("STATE: INFLUXDB_ORG is set")
            pass
        else:
            print("ERROR: INFLUXDB_TOKEN is set, but INFLUXDB_ORG is not set")
            sys.exit(1)
    else:
        print("STATE: INFLUXDB_TOKEN is not set, so we must be talking to an InfluxDBv1 instance")
        # If token is not set, then we are talking an InfluxDBv1 instance, so INFLUXDB_USER and INFLUXDB_PASS must also be set
        if 'INFLUXDB_USER' in os.environ:
            print("STATE: INFLUXDB_USER is set")
            pass
        else:
            print("ERROR: INFLUXDB_USER is not set")
            sys.exit(1)

        if 'INFLUXDB_PASS' in os.environ:
            print("STATE: INFLUXDB_PASS is set")
            pass
        else:
            print("ERROR: INFLUXDB_PASS is not set")
            sys.exit(1)
        # If token is not set, influxdb_token must be a concatenation of influxdb_user:influxdb_pass when talking to an InfluxDBv1 instance
        # https://docs.influxdata.com/influxdb/v1.8/tools/api/#apiv2query-http-endpoint
        influxdb_token = f'{influxdb_user}:{influxdb_pass}'

    # Instantiate the connection
    connection_string = influxdb_scheme + "://" + influxdb_host + ":" + str(influxdb_port)
    if influxdb_scheme == "http":
        print("WARNING: Using HTTP (plaintext). Credentials will be sent unencrypted. Use INFLUXDB_SCHEME=https for production.")
    print("STATE: Database URL is... " + connection_string)
    print("STATE: Connecting to InfluxDB...")
    client = InfluxDBClient(url=connection_string, token=influxdb_token, org=influxdb_org)

while True:
    speedtest()
