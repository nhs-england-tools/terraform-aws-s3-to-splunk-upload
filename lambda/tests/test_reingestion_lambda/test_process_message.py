import json
import gzip
from reingestion_lambda.process_message import (
    process_message,
    process_for_firehose,
)
from reingestion_lambda.Dataclasses import (
    EventMetadata,
    ProcessedBody,
)

from tests.mock_constants import (
    MOCK_BUCKET_NAME,
    MOCK_SOURCE,
    MOCK_SOURCETYPE,
    MOCK_BUCKET_NAME,
)


def test_process_message__processes_each_line():
    input_processed_body = ProcessedBody()
    input_event_metadata = EventMetadata("", {}, "", 10, MOCK_BUCKET_NAME, "")

    mock_message_line1 = json.dumps(
        {
            "source": MOCK_SOURCE,
            "event": {"key": "value1"},
            "sourcetype": MOCK_SOURCETYPE,
            "fields": {"origin_bucket_name": MOCK_BUCKET_NAME, "reingest": 1},
        }
    )
    mock_message_line2 = json.dumps(
        {
            "source": MOCK_SOURCE,
            "event": {"key": "value2"},
            "sourcetype": MOCK_SOURCETYPE,
            "fields": {"origin_bucket_name": MOCK_BUCKET_NAME, "reingest": 1},
        }
    )
    mock_message = f"{mock_message_line1}\n{mock_message_line2}\n"

    expected_message_line1 = json.dumps(
        {
            "sourcetype": MOCK_SOURCETYPE,
            "source": MOCK_SOURCE,
            "event": {"key": "value1"},
            "fields": {"reingest": 2, "origin_bucket_name": MOCK_BUCKET_NAME},
        }
    )
    expected_message_line2 = json.dumps(
        {
            "sourcetype": MOCK_SOURCETYPE,
            "source": MOCK_SOURCE,
            "event": {"key": "value2"},
            "fields": {"reingest": 2, "origin_bucket_name": MOCK_BUCKET_NAME},
        }
    )

    message_bytes1 = gzip.compress(expected_message_line1.encode())
    message_bytes2 = gzip.compress(expected_message_line2.encode())

    expected_record_batch = [{"Data": message_bytes1}, {"Data": message_bytes2}]

    actual_processed_body = process_message(
        input_processed_body, mock_message, input_event_metadata
    )

    assert actual_processed_body.count_for_s3 == 0
    assert actual_processed_body.count_for_firehose == 2
    assert actual_processed_body.s3_payload == {}
    assert actual_processed_body.record_batch == expected_record_batch


def test_process_message__processes_for_firehose(mocker):
    mocker.patch("reingestion_lambda.process_message.MAX_BATCH_SIZE", 1)
    mock_put_to_stream = mocker.patch(
        "reingestion_lambda.process_message.put_records_to_firehose_stream"
    )

    input_processed_body = ProcessedBody()
    input_event_metadata = EventMetadata("", {}, "", 10, MOCK_BUCKET_NAME, "")

    mock_message_line1 = json.dumps(
        {
            "source": MOCK_SOURCE,
            "event": {"key": "value1"},
            "sourcetype": MOCK_SOURCETYPE,
            "fields": {"origin_bucket_name": MOCK_BUCKET_NAME, "reingest": 1},
        }
    )
    mock_message_line2 = json.dumps(
        {
            "source": MOCK_SOURCE,
            "event": {"key": "value2"},
            "sourcetype": MOCK_SOURCETYPE,
            "fields": {"origin_bucket_name": MOCK_BUCKET_NAME, "reingest": 1},
        }
    )
    mock_message = f"{mock_message_line1}\n{mock_message_line2}\n"

    actual_processed_body = process_message(
        input_processed_body, mock_message, input_event_metadata
    )

    mock_put_to_stream.assert_called()
    assert actual_processed_body.count_for_s3 == 0
    assert actual_processed_body.count_for_firehose == 0
    assert actual_processed_body.s3_payload == {}
    assert actual_processed_body.record_batch == []


def test_process_for_firehose():
    mock_processed_body = ProcessedBody()

    mock_object_count = 2
    mock_reingest_json = {
        "sourcetype": "sourcetype",
        "source": "source",
        "event": {"key": "value"},
    }
    mock_record_batch = [{"Data": "encoded_data1"}, {"Data": "encoded_data2"}]
    mock_message = json.dumps(mock_reingest_json)
    mock_message_bytes = gzip.compress(mock_message.encode("utf-8"))

    mock_processed_body.record_batch = mock_record_batch
    mock_processed_body.count_for_firehose = mock_object_count
    mock_processed_body.reingest_json = mock_reingest_json

    expected_record_batch = [*mock_record_batch, {"Data": mock_message_bytes}]
    expected_object_count = 3

    actual_processed_body = process_for_firehose(mock_processed_body)
    assert actual_processed_body.record_batch == expected_record_batch
    assert actual_processed_body.count_for_firehose == expected_object_count
