from pages.base import Page
from regions.base import Region

from selenium.webdriver.common.by import By

from time import sleep


class Home(Page):
    _create_new_job_button_locator = (By.CLASS_NAME, "create-job-button")
    _pdf_job_form_modal_locator = (By.CLASS_NAME, "job-modal")

    @property
    def loaded(self):
        return self.is_create_new_job_button_displayed

    @property
    def is_create_new_job_button_displayed(self):
        return self.is_element_displayed(*self._create_new_job_button_locator)

    @property
    def create_job_modal_is_open(self):
        return self.is_element_displayed(*self._pdf_job_form_modal_locator)

    def click_create_new_job_button(self):
        self.find_element(*self._create_new_job_button_locator).click()
        self.wait.until(lambda _: self.create_job_modal_is_open)
        return self.CreateJobModal(
            self, self.find_element(*self._pdf_job_form_modal_locator)
        )

    class CreateJobModal(Region):
        _modal_cancel_button_locator = (By.CLASS_NAME, "job-cancel-button")

        _modal_create_button_locator = (By.CLASS_NAME, "create-button-start-job")

        _modal_pdf_radio_button_locator = (By.CLASS_NAME, "pdf-radio-button")

        _modal_web_preview_radio_button_locator = (
            By.CLASS_NAME,
            "preview-radio-button",
        )

        _modal_pdfgit_radio_button_locator = (By.CLASS_NAME, "git-pdf-radio-button")

        _modal_git_preview_radio_button_locator = (
            By.CLASS_NAME,
            "git-preview-radio-button",
        )

        _modal_collection_id_field_locator = (
            By.CSS_SELECTOR,
            ".collection-id-field input",
        )

        _modal_version_field_locator = (
            By.CSS_SELECTOR,
            ".version-field input",
        )

        _modal_style_field_locator = (
            By.CSS_SELECTOR,
            ".style-field input",
        )

        _modal_server_field_locator = (
            By.CSS_SELECTOR,
            ".server-field input",
        )

        _modal_collection_id_field_error_locator = (
            By.CLASS_NAME,
            "collection-id-error-text",
        )

        _modal_collection_id_slug_field_error_locator = (
            By.CLASS_NAME,
            "collection-id-field",
        )

        _modal_collection_id_incorrect_field_error_locator = (
            By.CLASS_NAME,
            "collection-id-incorrect-error-text",
        )

        _modal_collection_id_slug_incorrect_field_error_locator = (
            By.CLASS_NAME,
            "collection-id-field",
        )

        _modal_style_field_error_locator = (By.CLASS_NAME, "style-error-text")

        _modal_content_server_field_error_locator = (By.CLASS_NAME, "server-error-text")

        _modal_status_message_locator = (
            By.XPATH,
            "//div[contains(@class,'jobs-table')]/div/table/tbody/tr[1]/td[9]/span/span/span",
        )

        @property
        def cancel_button(self):
            return self.find_element(*self._modal_cancel_button_locator)

        def click_cancel_button(self):
            self.cancel_button.click()
            self.wait.until(lambda _: not self.page.create_job_modal_is_open)

        @property
        def create_button(self):
            return self.find_element(*self._modal_create_button_locator)

        def click_create_button(self):
            self.create_button.click()
            self.wait.until(lambda _: self.page.create_job_modal_is_open)
            sleep(2)

        @property
        def pdfgit_radio_button(self):
            return self.find_element(*self._modal_pdfgit_radio_button_locator)

        def click_pdfgit_radio_button(self):
            self.pdfgit_radio_button.click()

        @property
        def web_preview_radio_button(self):
            return self.find_element(*self._modal_web_preview_radio_button_locator)

        def click_web_preview_radio_button(self):
            self.web_preview_radio_button.click()

        @property
        def web_preview_git_radio_button(self):
            return self.find_element(*self._modal_pdfgit_radio_button_locator)

        def click_web_preview_git_radio_button(self):
            self.web_preview_git_radio_button.click()

        @property
        def collection_id_field_error(self):
            return self.find_element(*self._modal_collection_id_field_error_locator)

        @property
        def collection_id_slug_field_error(self):
            return self.find_element(
                *self._modal_collection_id_slug_field_error_locator
            )

        @property
        def collection_id_incorrect_field_error(self):
            return self.find_element(
                *self._modal_collection_id_incorrect_field_error_locator
            )

        @property
        def collection_id_slug_incorrect_field_error(self):
            return self.find_element(
                *self._modal_collection_id_slug_incorrect_field_error_locator
            )

        @property
        def style_field_error(self):
            return self.find_element(*self._modal_style_field_error_locator)

        @property
        def content_server_field_error(self):
            return self.find_element(*self._modal_content_server_field_error_locator)

        @property
        def collection_id_field(self):
            return self.find_element(*self._modal_collection_id_field_locator)

        def fill_collection_id_field(self, value):
            self.collection_id_field.send_keys(value)

        @property
        def version_field(self):
            return self.find_element(*self._modal_version_field_locator)

        def fill_version_field(self, value):
            self.version_field.send_keys(value)

        @property
        def style_field(self):
            return self.find_element(*self._modal_style_field_locator)

        def fill_style_field(self, value):
            self.style_field.send_keys(value)

        @property
        def server_field(self):
            return self.find_element(*self._modal_server_field_locator)

        def fill_server_field(self, value):
            self.server_field.send_keys(value)

        @property
        def status_message(self):
            return self.find_element(*self._modal_status_message_locator)

        @property
        def is_pdf_radio_button_displayed(self):
            return self.is_element_displayed(*self._modal_pdf_radio_button_locator)

        @property
        def is_web_preview_radio_button_displayed(self):
            return self.is_element_displayed(
                *self._modal_web_preview_radio_button_locator
            )

        @property
        def is_pdfgit_radio_button_displayed(self):
            return self.is_element_displayed(*self._modal_pdfgit_radio_button_locator)

        @property
        def is_git_preview_radio_button_displayed(self):
            return self.is_element_displayed(
                *self._modal_git_preview_radio_button_locator
            )
