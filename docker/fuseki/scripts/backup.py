#!/usr/bin/python3

#
# Trigger the backup of a dataset in Fuseki and wait for it to finish.
#
# Exit codes:
# 0 - backup successful
# 1 - any kind of error
#
# Mechanics:
# This script calls the dataset's backup endpoint
# (https://jena.apache.org/documentation/fuseki2/fuseki-server-protocol.html#backup),
# receives a taskId and polls Fuseki's tasks endpoint
# (https://jena.apache.org/documentation/fuseki2/fuseki-server-protocol.html#tasks)
# until the backup is finished.
#

import inspect
import json
import sys
import time
import urllib.parse
import urllib.request
from typing import Any
from urllib.error import HTTPError, URLError


# Settings for polling Fuseki's tasks endpoint
POLL_INTERVAL = 1  # interval in seconds between HTTP requests
MAX_POLLS = 100  # maximum number of HTTP requests


def print_to_stderr(s: str) -> None:
    print(s, file=sys.stderr)


def print_help(script_path: str) -> None:
    help_str = f"""
        Trigger the backup of a dataset in Fuseki
        Usage: {script_path} <dataset name>
    """
    print_to_stderr(inspect.cleandoc(help_str))


def parse_args(args: list[str]) -> str:
    if len(args) < 2:
        print_help(args[0])
        exit(1)

    return args[1]


def call_http(url: str, post_data: Any = None) -> Any:
    post_data = None if post_data is None else urllib.parse.urlencode(post_data).encode("ascii")

    try:
        response = urllib.request.urlopen(url, data=post_data)
    except HTTPError as e:
        print_to_stderr(f"Call to {url} ended with error code {e.code}.")
        exit(1)
    except URLError as e:
        print_to_stderr(f"Connection to {url} failed. Reason: {e.reason}")
        exit(1)
    else:
        return json.loads(response.read().decode(response.info().get_content_charset("utf-8")))


# JSON returned by backup call:
# {'taskId': '1', 'requestId': 3}
def trigger_backup(dataset_name: str) -> str:
    url = f"http://127.0.0.1:3030/$/backup/{dataset_name}"
    backup_json = call_http(url, {})

    key = "taskId"
    if key not in backup_json:
        print_to_stderr(f"Could not find key '{key}' in JSON '{backup_json}'.")
        exit(1)

    return backup_json[key]


# Unfinished task JSON:
# {'task': 'Backup', 'taskId': '15', 'started': '2023-06-19T13:24:50.969+00:00'}
#
# Finished task JSON:
# {'task': 'Backup', 'taskId': '15', 'started': '2023-06-19T13:24:50.969+00:00',
# 'finished': '2023-06-19T13:24:50.974+00:00', 'success': True}
def poll_task(taskid: str) -> None:
    url = f"http://127.0.0.1:3030/$/tasks/{taskid}"

    for _ in range(MAX_POLLS):
        task_json = call_http(url)

        if "finished" in task_json:
            success = False

            if "success" in task_json:
                success = task_json["success"]

            if success:
                exit(0)
            else:
                print_to_stderr("Backup was unsuccessful.")
                exit(1)

        time.sleep(POLL_INTERVAL)

    print_to_stderr("MAX_POLLS reached, aborting.")
    exit(1)


def main(args: list[str]) -> None:
    dataset_name = parse_args(args)
    taskid = trigger_backup(dataset_name)
    poll_task(taskid)


if __name__ == "__main__":
    main(sys.argv)
