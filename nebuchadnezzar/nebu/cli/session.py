import requests
import backoff


class NebSession(requests.Session):
    def __init__(self):
        super(NebSession, self).__init__()

        self.headers.update(
            {
                "User-Agent": "OpenStax Nebuchadnezzar Client"
            }
        )

    @backoff.on_exception(backoff.expo, requests.exceptions.ConnectionError)
    def request(self, *args, **kwargs):
        return super(NebSession, self).request(*args, **kwargs)
