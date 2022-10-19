import json
import requests

from src.utils import msg


def build_url(api_root, *args):
    parts = [api_root]
    parts.extend(args)
    parts = [str(p) for p in parts]
    return "/".join(parts)


def get_jobs(api_root):
    url = build_url(api_root, "jobs")
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
