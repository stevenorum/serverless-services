import base64
import boto3
import copy
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import http.cookies
import json
from math import radians, degrees, cos, sin, asin, sqrt, fabs, log, tan, pi, atan2
import os
import tempfile
import traceback
import urllib
import urllib.parse
import uuid
from sneks.ddb import make_json_safe
from sneks.sam import events
from sneks.sam.response_core import make_response, redirect, ApiException
from sneks.sam.decorators import register_path, returns_json, returns_html
from sneks.sam.exceptions import *
import time

import sqlite3

s3 = boto3.client("s3")

def dumps(obj, *args, **kwargs):
    return json.dumps(make_json_safe(obj), *args, **kwargs)

def _connect(name="shared"):
    prefix = "sqlite3/{}/".format(name)
    conn = sqlite3.connect(':memory:')
    c = conn.cursor()
    objects = s3.list_objects_v2(Bucket=os.environ["DATA_BUCKET"], Prefix=prefix)["Contents"]
    for x in objects:
        if x["Key"].endswith("/dump.sql"):
            f = s3.get_object(Bucket=os.environ["DATA_BUCKET"], Key=x["Key"])
            c.executescript(f["Body"].decode("utf-8"))
    conn.commit()
    return conn, c

def _commit(connection, name):
    connection.commit()
    with tempfile.TemporaryDirectory() as d:
        dumpfile = os.path.join(d, "dump.sql")
        with open(dumpfile, 'w') as f:
            for line in connection.iterdump():
                f.write('%s\n' % line)
        s3.upload_file(Bucket=os.environ["DATA_BUCKET"], Key="sqlite/{}/dump.sql".format(name), Filename=dumpfile)

@register_path("API", r"^/?sqlite/exec$")
@returns_json
def sqlite_exec_api(event, *args, db="shared", command="SHOW TABLES;", **kwargs):
    # This is all hilariously unsafe.  Don't use for anything real.
    connection, cursor = _connect(name=db)
    word = command.split()[0].upper()
    elif word == "SELECT":
        return list(cursor.execute(command))
    elif word == "INSERT":
        cursor.execute(command)
    elif word == "CREATE":
        cursor.execute(command)
    else:
        cursor.execute(command)
    _commit(connection, name)
    return {}

def _add_info_kwargs(info, kwargs):
    if not kwargs:
        return info
    existing_kwargs = list(info.keys())
    for k in kwargs:
        if k not in existing_kwargs:
            info[k] = kwargs[k]
    return info

def add_body_as_kwargs(info, *args, **kwargs):
    if not info["event"].get("body"):
        info["body"] = {}
        return info
    body = json.loads(info["event"]["body"])
    info["body"] = body
    return _add_info_kwargs(info, body)

def add_qs_as_kwargs(info, *args, **kwargs):
    qs_args = info["event"]["queryStringParameters"]
    info["qs_args"] = qs_args
    return _add_info_kwargs(info, qs_args)
