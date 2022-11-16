import json
from urllib.parse import quote

import requests
from .utils import msg


def build_url(api_root, *args, **kwargs):
    parts = [api_root]
    query = []
    parts.extend(args)
    parts = [str(p) for p in parts]
    url = "/".join(parts)
    for item in kwargs.items():
        query.append("=".join(map(quote, map(str, item))))
    if query:
        return "?".join((url, "&".join(query)))
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
