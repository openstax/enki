import pytest

from pages.home import Home

from pytest_testrail.plugin import pytestrail


@pytestrail.case("C624695")
@pytest.mark.smoke
@pytest.mark.ui
@pytest.mark.nondestructive
def test_invalid_colid_error(selenium, base_url):
    # GIVEN: Selenium driver and the base url

    # WHEN: The Home page is fully loaded
    home = Home(selenium, base_url).open()

    # AND: The create a new job button is clicked
    modal = home.click_create_new_job_button()

    # AND: Incorrect collection id is typed into the collection id field
    modal.fill_collection_id_field("1col11229")

    # AND: Create button is clicked
    modal.click_create_button()

    split_col_id_incorrect = modal.collection_id_incorrect_field_error.text.splitlines()
    text_col_id_incorrect = split_col_id_incorrect[1]

    # THEN: Correct error message appears in collection id field
    assert "A valid collection ID is required, e.g. col12345" == text_col_id_incorrect

    split_style = modal.style_field_error.text.splitlines()
    text_style = split_style[1]
    assert "Style is required" == text_style

    split_server = modal.content_server_field_error.text.splitlines()
    text_server = split_server[1]
    assert "Please select a server" == text_server

    # THEN: The modal does not close and remains open
    assert home.create_job_modal_is_open

    # WHEN: modal is open and collection id has incorrect colid/slug
    # AND: PDF(git) button is clicked
    modal.click_pdfgit_radio_button()

    # AND: Create button is clicked when data fields are empty and collection ID field has incorrect colid
    modal.click_create_button()

    split_col_id_slug_incorrect = (
        modal.collection_id_slug_incorrect_field_error.text.splitlines()
    )
    text_col_id_slug_incorrect = split_col_id_slug_incorrect[1]

    # THEN: Correct error message appears in collection id and style field
    assert (
        "A valid repo and slug name is required, e.g. repo-name/slug-name"
        == text_col_id_slug_incorrect
    )

    # Test unicode book collection (here Polish)
    modal.fill_collection_id_field("osbooks_fizyka_bundle2/fizyka-dla-szkół-wyższych-tom-1")
    split_col_id_slug_incorrect = (
        modal.collection_id_slug_incorrect_field_error.text.splitlines()
    )
    text_col_id_slug_incorrect = split_col_id_slug_incorrect[1]
    assert (
        "e.g. repo-name/slug-name"
        == text_col_id_slug_incorrect
    )
    # Unallowed characters
    modal.fill_collection_id_field("osbooks_fizyka_bundle1/fizyka=dla-szkół-wyższych-tom-1")
    split_col_id_slug_incorrect = (
        modal.collection_id_slug_incorrect_field_error.text.splitlines()
    )
    text_col_id_slug_incorrect = split_col_id_slug_incorrect[1]
    assert (
        "A valid repo and slug name is required, e.g. repo-name/slug-name"
        == text_col_id_slug_incorrect
    )

    split_style = modal.style_field_error.text.splitlines()
    text_style = split_style[1]
    assert "Style is required" == text_style

    # THEN: No error message appears for Content Server as it is disabled for pdf git
    split_server = modal.content_server_field_error.text.splitlines()
    assert "Please select a server" not in split_server
