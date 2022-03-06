from locust import HttpLocust, TaskSet, task, between

class UserBehavior(TaskSet):

    def on_start(self):
        """ on_start is called when a Locust start before any task is scheduled """
        # login(self)

    def on_stop(self):
        pass

    def login(self):
        """ login user """
        pass

    @task(1)
    def get_jobs(self):
        self.client.get("/api/jobs/")

    @task(1)
    def get_status(self):
        self.client.get("/api/status/")

    @task(1)
    def get_content_servers(self):
        self.client.get("/api/content-servers/")

class WebsiteUser(HttpLocust):
    task_set = UserBehavior
    wait_time = between(5.0, 9.0)
