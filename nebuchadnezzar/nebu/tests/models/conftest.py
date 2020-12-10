import pytest


@pytest.fixture
def neb_collection_data(datadir):
    """This data is the result of a ``neb get ...``"""
    return datadir / 'collection_for_bakedpdf_workflow'


@pytest.fixture
def neb_assembled_data(datadir):
    """This data is the results of a ``neb assemble ...``"""
    return datadir / 'assembled_collection_for_bakedpdf_workflow'


@pytest.fixture
def git_collection_data(datadir):
    """This data reflects what is expected from git storage"""
    return datadir / 'collection_for_git_workflow'


@pytest.fixture
def git_assembled_data(datadir):
    """This data is the results of a ``neb assemble ...``"""
    return datadir / 'assembled_collection_for_git_workflow'
