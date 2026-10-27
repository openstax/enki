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


def update_job(api_root, job_id, data, github_token=None):
    url = build_url(api_root, "jobs", job_id)
    with requests.Session() as session:
        if github_token:
            login_url = build_url(api_root, "auth", "token-login")
            login_response = session.get(
                login_url,
                headers={"Authorization": f"Bearer {github_token}"},
            )
            login_response.raise_for_status()
            if not login_response.cookies.get("session"):
                raise RuntimeError(
                    "CORGI token login did not set a session cookie"
                )

        response = session.put(url, json=data)
        msg(response.text)
        response.raise_for_status()
        return response.json()
