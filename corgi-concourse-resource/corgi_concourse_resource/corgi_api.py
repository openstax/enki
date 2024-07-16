import json
from urllib.parse import urlencode

import requests

from .utils import msg


def build_url(api_root, *args, **kwargs):
    parts = [api_root]
    parts.extend(args)
    url = "/".join(str(p) for p in parts)
    if kwargs:
        return "?".join((url, urlencode(kwargs)))
    return url


def get_jobs(api_root, **kwargs):
    url = build_url(api_root, "jobs", "check", **kwargs)
    response = requests.get(url)
    msg(response.text)
    return response.json()


def get_job(api_root, job_id):
    url = build_url(api_root, "jobs", job_id)
    response = requests.get(url)
    msg(response.text)
    return response.json()


def update_job(api_root, job_id, data):
    url = build_url(api_root, "jobs", job_id)
    response = requests.put(url, data=json.dumps(data))
    msg(response.text)
    return response.json()
