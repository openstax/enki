import pypom


class Region(pypom.Region):
    @property
    def current_url(self):
        return self.driver.current_url
