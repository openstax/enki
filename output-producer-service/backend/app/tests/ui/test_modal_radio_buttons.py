import pytest

from pages.home import Home

from pytest_testrail.plugin import pytestrail


@pytestrail.case("C624697")
@pytest.mark.smoke
@pytest.mark.ui
@pytest.mark.nondestructive
def test_modal_radio_buttons(selenium, base_url):
    # GIVEN: Selenium driver and the base url

    # WHEN: The Home page is fully loaded
    home = Home(selenium, base_url).open()

    # AND: The create a new job button is clicked
    modal = home.click_create_new_job_button()

    # THEN: The pdf, web preview, pdf(git) and web preview (git) radio buttons are displayed
    assert modal.is_pdf_radio_button_displayed
    assert modal.is_web_preview_radio_button_displayed
    assert modal.is_pdfgit_radio_button_displayed
    assert modal.is_git_preview_radio_button_displayed
