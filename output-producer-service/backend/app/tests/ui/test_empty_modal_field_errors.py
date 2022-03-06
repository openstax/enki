import pytest

from pages.home import Home

from pytest_testrail.plugin import pytestrail


@pytestrail.case("C624691")
@pytest.mark.smoke
@pytest.mark.ui
@pytest.mark.nondestructive
def test_empty_modal_field_errors(selenium, base_url):
    # GIVEN: Selenium driver and the base url

    # WHEN: The Home page is fully loaded
    home = Home(selenium, base_url).open()

    # AND: The create a new job button is clicked
    modal = home.click_create_new_job_button()

    # AND: Create button is clicked when data fields are empty
    modal.click_create_button()

    # THEN: The correct error messages are shown for each applicable
    # input field (colid, style and server)
    split_col_id = modal.collection_id_field_error.text.splitlines()
    text_col_id = split_col_id[1]
    assert "Collection ID is required" == text_col_id

    split_style = modal.style_field_error.text.splitlines()
    text_style = split_style[1]
    assert "Style is required" == text_style

    split_server = modal.content_server_field_error.text.splitlines()
    text_server = split_server[1]
    assert "Please select a server" == text_server

    # AND: The modal does not close and remains open
    assert home.create_job_modal_is_open

    # WHEN: modal is open
    # AND: PDF(git) button is clicked
    modal.click_pdfgit_radio_button()

    # AND: Create button is clicked when data fields are empty
    modal.click_create_button()

    # THEN: The correct error messages are shown for each applicable
    # input field (colid and style)
    split_col_id_slug = modal.collection_id_slug_field_error.text.splitlines()
    text_col_id_slug = split_col_id_slug[1]
    assert "Repo and slug are required" == text_col_id_slug

    split_style = modal.style_field_error.text.splitlines()
    text_style = split_style[1]
    assert "Style is required" == text_style


@pytestrail.case("C624692")
@pytest.mark.smoke
@pytest.mark.ui
@pytest.mark.nondestructive
def test_empty_modal_field_errors_preview(selenium, base_url):
    # GIVEN: Selenium driver and the base url

    # WHEN: The Home page is fully loaded
    home = Home(selenium, base_url).open()

    # AND: The create a new job button is clicked
    modal = home.click_create_new_job_button()

    # AND: Web preview button is clicked
    modal.click_web_preview_radio_button()

    # AND: Create button is clicked when data fields are empty
    modal.click_create_button()

    # THEN: The correct error messages are shown for each applicable
    # input field (colid, style and server)
    split_col_id = modal.collection_id_field_error.text.splitlines()
    text_col_id = split_col_id[1]
    assert "Collection ID is required" == text_col_id

    split_style = modal.style_field_error.text.splitlines()
    text_style = split_style[1]
    assert "Style is required" == text_style

    split_server = modal.content_server_field_error.text.splitlines()
    text_server = split_server[1]
    assert "Please select a server" == text_server

    # AND: The modal does not close and remains open
    assert home.create_job_modal_is_open

    # AND: Web preview (git) button is clicked
    modal.click_web_preview_git_radio_button()

    # AND: Create button is clicked when data fields are empty
    modal.click_create_button()

    # THEN: The correct error messages are shown for each applicable
    # input field (colid and style)
    split_col_id_slug = modal.collection_id_slug_field_error.text.splitlines()
    text_col_id_slug = split_col_id_slug[1]
    assert "Repo and slug are required" == text_col_id_slug

    split_style = modal.style_field_error.text.splitlines()
    text_style = split_style[1]
    assert "Style is required" == text_style
