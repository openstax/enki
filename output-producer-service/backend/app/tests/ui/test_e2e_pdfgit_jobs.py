import pytest

from pages.home import Home

from pytest_testrail.plugin import pytestrail


@pytestrail.case("C618754")
@pytest.mark.smoke
@pytest.mark.ui
@pytest.mark.nondestructive
def test_e2e_pdfgit_jobs(selenium, base_url):
    # GIVEN: Selenium driver and the base url

    # WHEN: The Home page is fully loaded
    home = Home(selenium, base_url).open()

    # AND: The 'create a new job' button is clicked
    modal = home.click_create_new_job_button()

    # AND: Clicks the PDF(git) button
    modal.click_pdfgit_radio_button()

    # AND: Correct data are typed into the input fields
    modal.fill_collection_id_field("ce-git-storage-spike/precalculus")
    modal.fill_version_field("latest")
    modal.fill_style_field("precalculus")

    # AND: Create button is clicked
    modal.click_create_button()

    # THEN: The modal closes and job is queued
    assert home.is_create_new_job_button_displayed
    assert modal.status_message.text == "queued"
