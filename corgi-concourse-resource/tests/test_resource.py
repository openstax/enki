import io
import json
import os
import tempfile

import vcr

from src import check, in_, out

DATA_DIR = os.path.join(os.path.realpath(os.path.dirname(__file__)), "data")


def read_file(filepath):
    with open(filepath, "r") as infile:
        return infile.read()


def write_file(filepath, data):
    with open(filepath, "w") as outfile:
        outfile.write(data)


def make_stream(json_obj):
    stream = io.StringIO()
    json.dump(json_obj, stream)
    stream.seek(0)
    return stream


def make_input(version, **kwargs):
    payload = {"source": {
        "api_root": "http://localhost/api",
    },
        "version": version,
    }
    payload["source"].update(kwargs)

    return payload


def make_input_stream(version, **kwargs):
    return make_stream(make_input(version, **kwargs))


class TestCheck(object):

    @vcr.use_cassette("tests/cassettes/test_check.yaml")
    def test_edge_case_queued_jobs(self):
        version = None

        in_stream = make_input_stream(version, status_id=1)
        result = check.check(in_stream)

        assert result == [{'id': '2'},
                          {'id': '1'}]

    @vcr.use_cassette("tests/cassettes/test_check.yaml")
    def test_edge_case_queued_no_jobs(self):
        version = None

        in_stream = make_input_stream(version, status_id=6)
        result = check.check(in_stream)

        assert result == []

    @vcr.use_cassette("tests/cassettes/test_check.yaml")
    def test_has_newest_job(self):
        version = {"id": 1}

        in_stream = make_input_stream(version, status_id=1)
        result = check.check(in_stream)

        assert result == [{"id": "2"}]

    @vcr.use_cassette("tests/cassettes/test_check.yaml")
    def test_has_newer_jobs(self):
        version = {"id": 0}

        in_stream = make_input_stream(version, status_id=1)
        result = check.check(in_stream)

        assert result == [{'id': '2'}, {'id': '1'}]

    @vcr.use_cassette("tests/cassettes/test_check.yaml")
    def test_check_without_status_id(self):
        version = {"id": 9}

        in_stream = make_input_stream(version)
        result = check.check(in_stream)

        assert result == [version]

    @vcr.use_cassette("tests/cassettes/test_check.yaml")
    def test_check_when_status_id_is_zero(self):
        version = {"id": 2}

        in_stream = make_input_stream(version, status_id=0)
        result = check.check(in_stream)

        assert result == [version]

    @vcr.use_cassette("tests/cassettes/test_check.yaml")
    def test_check_without_version_with_status(self):
        payload = make_input(None, status_id=5)
        del payload["version"]

        in_stream = make_stream(payload)
        result = check.check(in_stream)

        assert result == [{'id': '10'}, {'id': '9'}]

    @vcr.use_cassette("tests/cassettes/test_check.yaml")
    def test_check_without_version_without_status(self):
        payload = make_input(None)
        del payload["version"]

        in_stream = make_stream(payload)
        result = check.check(in_stream)

        assert result == []

    @vcr.use_cassette("tests/cassettes/test_check.yaml")
    def test_check_with_job_type(self):
        version = None

        in_stream = make_input_stream(version, status_id=1, job_type_id=2)
        result = check.check(in_stream)

        assert result == [{'id': '2'}]


class TestIn(object):
    @vcr.use_cassette('tests/cassettes/test_in.yaml')
    def test_resource_files_are_written(self):
        id = "1"
        version = {"version": {"id": id}}
        dest_path = tempfile.mkdtemp()

        in_stream = make_input_stream(version["version"])

        result = in_.in_(dest_path, in_stream)
        assert result == version

        job_id = read_file(os.path.join(dest_path, "id"))
        assert job_id == version["version"]["id"]

        job_json = json.loads(read_file(os.path.join(dest_path, "job.json")))
        expected_json = json.loads(
            read_file(os.path.join(DATA_DIR, "job.json"))
        )
        assert job_json == expected_json

        collection_id = read_file(os.path.join(dest_path, "collection_id"))
        assert collection_id == read_file(os.path.join(DATA_DIR, "collection_id"))

        collection_version = read_file(os.path.join(dest_path, "version"))
        assert collection_version == read_file(os.path.join(DATA_DIR, "version"))

        collection_style = read_file(os.path.join(dest_path, "collection_style"))
        assert collection_style == read_file(os.path.join(DATA_DIR, "collection_style"))

        content_server = read_file(os.path.join(dest_path, "content_server"))
        assert content_server == read_file(os.path.join(DATA_DIR, "content_server"))


class TestOut(object):

    @vcr.use_cassette("tests/cassettes/test_out.yaml")
    def test_update_job_status_and_url(self):
        id = "1"
        pdf_url = "http://dummy.cops.org/col12345-latest.pdf"
        src_path = tempfile.mkdtemp()

        id_filepath = os.path.join(src_path, "id")
        pdf_url_filepath = os.path.join(src_path, "pdf_url")

        write_file(id_filepath, id)
        write_file(pdf_url_filepath, pdf_url)

        params = {
            "id": "id",
            "pdf_url": "pdf_url",
            "status_id": "5"
        }

        payload = make_input(None)
        del payload["version"]
        payload["params"] = params

        in_stream = make_stream(payload)

        result = out.out(src_path, in_stream)

        assert result == {
            "version": {
                "id": "1"
            }
        }
