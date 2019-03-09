import pytest


@pytest.fixture
def collection_data(datadir):
    """This data is the result of a ``neb get ...``"""
    return datadir / 'collection_for_bakedpdf_workflow'


@pytest.fixture
def assembled_data(datadir):
    """This data is the results of a ``neb assemble ...``"""
    return datadir / 'assembled_collection_for_bakedpdf_workflow'
