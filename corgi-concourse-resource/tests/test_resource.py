import io
import json
import os
import tempfile

import vcr
import pytest

from corgi_concourse_resource import check, in_, out

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

    # This edge case is testing behavior when no previous version exists
    @vcr.use_cassette("tests/cassettes/test_check.yaml", record_mode="new_episode")
    def test_edge_case_queued_jobs(self):
        version = None

        in_stream = make_input_stream(version, status_id=1)
        result = check.check(in_stream)

        assert result == [{"id": "3"},
                          {"id": "2"},
                          {"id": "1"}]

    @vcr.use_cassette("tests/cassettes/test_check.yaml", record_mode="new_episode")
    def test_edge_case_queued_no_jobs(self):
        version = None

        in_stream = make_input_stream(version, status_id=999)
        result = check.check(in_stream)

        assert result == []

    @vcr.use_cassette("tests/cassettes/test_check.yaml", record_mode="new_episode")
    @pytest.mark.parametrize(
        "id,result", [
            ("1", [{"id": "3"}, {"id": "2"}]),
            ("2", [{"id": "3"}]),
            ("3", [])
        ]
    )
    def test_has_newer_job(self, id, result):
        version = {"id": id}

        in_stream = make_input_stream(version, status_id=1)
        assert check.check(in_stream) == result

    @vcr.use_cassette("tests/cassettes/test_check.yaml", record_mode="new_episode")
    def test_check_without_status_id(self):
        version = {"id": 9}

        in_stream = make_input_stream(version)
        result = check.check(in_stream)

        assert result == [version]

    @vcr.use_cassette("tests/cassettes/test_check.yaml", record_mode="new_episode")
    def test_check_when_status_id_is_zero(self):
        version = {"id": 2}

        in_stream = make_input_stream(version, status_id=0)
        result = check.check(in_stream)

        assert result == [version]

    @vcr.use_cassette("tests/cassettes/test_check.yaml", record_mode="new_episode")
    def test_check_without_version_without_status(self):
        payload = make_input(None)
        del payload["version"]

        in_stream = make_stream(payload)
        result = check.check(in_stream)

        assert result == []

    @vcr.use_cassette("tests/cassettes/test_check.yaml", record_mode="new_episode")
    @pytest.mark.parametrize(
        "job_type_id,result", [
            (1, []),
            (2, []),
            (3, [{"id": "1"}]),
            (4, [{"id": "2"}]),
            (5, [{"id": "3"}])
        ]
    )
    def test_check_with_job_type(self, job_type_id, result):
        version = None

        in_stream = make_input_stream(version, status_id=1, job_type_id=job_type_id)
        assert result == check.check(in_stream)


    @vcr.use_cassette("tests/cassettes/test_check.yaml", record_mode="new_episode")
    @pytest.mark.parametrize(
        "status_id,result", [
            (1, [{"id": "3"}, {"id": "2"}, {"id": "1"}],),
            (2, [{"id": "6"}, {"id": "5"}, {"id": "4"}]),
            (3, [{"id": "9"}, {"id": "8"}, {"id": "7"}]),
            (4, [{"id": "12"}, {"id": "11"}, {"id": "10"}]),
            (5, [{"id": "15"}, {"id": "14"}, {"id": "13"}]),
        ]
    )
    def test_check_with_status(self, status_id, result):
        version = None

        in_stream = make_input_stream(version, status_id=status_id)
        assert result == check.check(in_stream)


class TestIn(object):
    @vcr.use_cassette("tests/cassettes/test_in.yaml")
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
        # Ignore information that is expected to change
        for key in ("created_at", "updated_at", "user", "version", "books",
                    "artifact_urls"):
            job_json[key] = None
        assert job_json == expected_json

        collection_id = read_file(os.path.join(dest_path, "collection_id"))
        assert collection_id == read_file(os.path.join(DATA_DIR, "collection_id"))

        slugs = read_file(os.path.join(dest_path, "slugs"))
        assert slugs == read_file(os.path.join(DATA_DIR, "slugs"))

        collection_version = read_file(os.path.join(dest_path, "version"))
        assert collection_version == read_file(os.path.join(DATA_DIR, "version"))



class TestOut(object):

    @pytest.mark.parametrize(
            "output,result", [
                ("http://dummy.cops.org/col12345-latest.pdf", None),
                (
                    [
                        {"slug": "test1", "url": "something"},
                        {"slug": "test2", "url": "other"}
                    ],
                    None
                ),
                (
                    [
                        {"text": "View - Rex Web", "href": "Something"},
                        {"text": "View - Rex Web Prod", "href": "Something else"}
                    ],
                    "Something else"
                )
            ]
    )
    @vcr.use_cassette("tests/cassettes/test_out.yaml", record_mode="new_episode")
    def test_update_job_status_and_url(self, output, result, monkeypatch):
        id = "1"
        src_path = tempfile.mkdtemp()
        
        if result is None:
            result = output

        id_filepath = os.path.join(src_path, "id")
        pdf_url_filepath = os.path.join(src_path, "pdf_url")

        write_file(id_filepath, id)
        write_file(
            pdf_url_filepath,
            output
            if isinstance(output, str)
            else json.dumps(output))

        params = {
            "id": "id",
            "pdf_url": "pdf_url",
            "status_id": "5"
        }

        payload = make_input(None)
        del payload["version"]
        payload["params"] = params

        in_stream = make_stream(payload)
 
        from corgi_concourse_resource.corgi_api import update_job
        def test_data(api_root, id, data):
            assert data
            assert id
            assert "status_id" in data
            assert "artifact_urls" in data
            assert data["artifact_urls"] == result
            return update_job(api_root, id, data)
        
        monkeypatch.setattr("corgi_concourse_resource.out.update_job", test_data)

        result = out.out(src_path, in_stream)

        assert result == {
            "version": {
                "id": "1"
            }
        }
