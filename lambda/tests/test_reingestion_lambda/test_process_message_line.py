import json
from dataclasses import asdict
from reingestion_lambda.process_message_line import (
    get_message_metadata,
    package_for_s3,
    process_message_line,
)
from reingestion_lambda.Dataclasses import EventMetadata
from tests.mock_constants import (
    MOCK_BUCKET_NAME,
    MOCK_SOURCE,
    MOCK_SOURCETYPE,
    MOCK_BUCKET_NAME,
)


def test_process_message_line__below_max_ingest():
    mock_metadata = EventMetadata("", {}, "", 10, MOCK_BUCKET_NAME, "")
    mock_message_line = json.dumps(
        {
            "source": MOCK_SOURCE,
            "event": {"key": "value"},
            "sourcetype": MOCK_SOURCETYPE,
            "fields": {"origin_bucket_name": MOCK_BUCKET_NAME, "reingest": 1},
        }
    )
    mock_s3_payload = {}

    expected_reingest_json = {
        "source": MOCK_SOURCE,
        "event": {"key": "value"},
        "sourcetype": MOCK_SOURCETYPE,
        "fields": {"origin_bucket_name": MOCK_BUCKET_NAME, "reingest": 2},
    }
    expected_s3_payload = {}
    expected_count_for_s3 = 0
    expected_sent_to_s3 = False

    processed_message_line = process_message_line(
        mock_message_line,
        mock_s3_payload,
        mock_metadata,
    )

    assert processed_message_line.reingest_json == expected_reingest_json
    assert processed_message_line.s3_payload == expected_s3_payload
    assert processed_message_line.count_for_s3 == expected_count_for_s3
    assert processed_message_line.sent_to_s3 == expected_sent_to_s3


def test_process_message_line__above_max_ingest():
    mock_metadata = EventMetadata("", {}, "", 0, MOCK_BUCKET_NAME, "")
    mock_message_line = json.dumps(
        {
            "source": MOCK_SOURCE,
            "event": {"key": "value"},
            "sourcetype": MOCK_SOURCETYPE,
            "fields": {"origin_bucket_name": MOCK_BUCKET_NAME, "reingest": 1},
        }
    )
    mock_s3_payload = {}

    expected_s3_payload = {MOCK_BUCKET_NAME: '{"key": "value"}\n'}
    expected_reingest_json = {}
    expected_count_for_s3 = 1
    expected_sent_to_s3 = True

    processed_message_line = process_message_line(
        mock_message_line,
        mock_s3_payload,
        mock_metadata,
    )

    assert processed_message_line.reingest_json == expected_reingest_json
    assert processed_message_line.s3_payload == expected_s3_payload
    assert processed_message_line.count_for_s3 == expected_count_for_s3
    assert processed_message_line.sent_to_s3 == expected_sent_to_s3


def test_get_message_metadata():
    mock_data = {
        "source": MOCK_SOURCE,
        "sourcetype": MOCK_SOURCETYPE,
        "fields": {"origin_bucket_name": MOCK_BUCKET_NAME, "reingest": 1},
    }

    expected_fields_to_reingest = {
        "origin_bucket_name": MOCK_BUCKET_NAME,
        "reingest": 2,
    }

    actual_metadata = get_message_metadata(mock_data, MOCK_BUCKET_NAME)

    assert actual_metadata.source == MOCK_SOURCE
    assert actual_metadata.sourcetype == MOCK_SOURCETYPE
    assert asdict(actual_metadata.fields_to_reingest) == expected_fields_to_reingest


def test_get_message_metadata__no_source():
    mock_data = {
        "sourcetype": MOCK_SOURCETYPE,
        "fields": {"origin_bucket_name": MOCK_BUCKET_NAME, "reingest": 1},
    }
    expected_source = "aws:reingested"
    actual_metadata = get_message_metadata(mock_data, MOCK_BUCKET_NAME)
    assert actual_metadata.source == expected_source


def test_get_message_metadata__no_sourcetype():
    mock_data = {
        "source": MOCK_SOURCE,
        "fields": {"origin_bucket_name": MOCK_BUCKET_NAME, "reingest": 1},
    }
    expected_sourcetype = "aws:firehose"
    actual_metadata = get_message_metadata(mock_data, MOCK_BUCKET_NAME)
    assert actual_metadata.sourcetype == expected_sourcetype


def test_get_message_metadata__no_fields():
    mock_data = {
        "source": MOCK_SOURCE,
        "sourcetype": MOCK_SOURCETYPE,
    }
    expected_fields_to_reingest = {
        "origin_bucket_name": MOCK_BUCKET_NAME,
        "reingest": 1,
    }

    actual_metadata = get_message_metadata(mock_data, MOCK_BUCKET_NAME)
    assert asdict(actual_metadata.fields_to_reingest) == expected_fields_to_reingest


def test_package_for_s3__existing_payload():
    mock_s3_payload = {MOCK_BUCKET_NAME: f'{json.dumps({"first": "data"})}\n'}
    mock_data = {"event": {"second": "data"}}
    expected_s3_payload = {
        MOCK_BUCKET_NAME: f'{mock_s3_payload[MOCK_BUCKET_NAME]}{json.dumps({"second": "data"})}\n'
    }

    actual_s3_payload = package_for_s3(mock_s3_payload, MOCK_BUCKET_NAME, mock_data)
    assert actual_s3_payload == expected_s3_payload


def test_package_for_s3__no_payload():
    mock_s3_payload = {}
    mock_data = {"event": {"second": "data"}}
    expected_s3_payload = {MOCK_BUCKET_NAME: f'{json.dumps({"second": "data"})}\n'}

    actual_s3_payload = package_for_s3(mock_s3_payload, MOCK_BUCKET_NAME, mock_data)
    assert actual_s3_payload == expected_s3_payload


def test_package_for_s3__payload_with_different_bucket():
    mock_s3_payload = {MOCK_BUCKET_NAME: f'{json.dumps({"first": "data"})}\n'}
    mock_data = {"event": {"second": "data"}}
    different_bucket_name = "different_bucket"
    expected_s3_payload = {
        MOCK_BUCKET_NAME: mock_s3_payload[MOCK_BUCKET_NAME],
        different_bucket_name: f'{json.dumps({"second": "data"})}\n',
    }

    actual_s3_payload = package_for_s3(
        mock_s3_payload, different_bucket_name, mock_data
    )
    assert actual_s3_payload == expected_s3_payload
