import gzip
import json
from tests.mock_constants import (
    MAX_BATCH_LENGTH_PATH,
    MAX_LAMBDA_RETURN_PATH,
    MOCK_EVENT_STRING,
)
from transformation_lambda.reingest import (
    get_record_to_reingest,
    create_batches_from_record,
    format_record_for_firehose,
    create_batch,
    delete_records_to_be_reingested,
)


def test_get_record_to_reingest(mocker):
    input_data = {"data": "some record", "recordId": "guid1"}
    mocker.patch(
        MAX_LAMBDA_RETURN_PATH,
        5,
    )
    mocker.patch(
        MAX_BATCH_LENGTH_PATH,
        10,
    )

    mocker.patch(
        "transformation_lambda.reingest.create_batches_from_record",
        return_value="successfully called",
    )

    actual_record_to_reingest, actual_record_id_to_delete = get_record_to_reingest(
        input_data
    )

    assert actual_record_id_to_delete == "guid1"
    assert actual_record_to_reingest == "successfully called"


def test_format_record_for_firehose():
    input_record = {"data": MOCK_EVENT_STRING}
    actual_record = format_record_for_firehose(input_record)
    expected_record = {"Data": MOCK_EVENT_STRING}
    assert actual_record == expected_record


def test_create_batch():
    input_batch = [
        {"event1": "event1_data"},
        {"event2": "event2_data"},
        {"event3": "event3_data"},
        {"event4": "event4_data"},
    ]

    max_batch_amount = 2

    expected_data = json.dumps(
        [
            {"event1": "event1_data"},
            {"event2": "event2_data"},
        ]
    )
    expected_zip = gzip.compress(expected_data.encode())
    expected_output = {"Data": expected_zip}

    actual_output = create_batch(input_batch, max_batch_amount)

    assert actual_output == expected_output


def test_create_batches_from_record(mocker):
    mocker.patch(
        MAX_BATCH_LENGTH_PATH,
        2,
    )

    input_data = """{"event1": "event1_data"}\n{"event2": "event2_data"}\n{"event3": "event3_data"}\n"""
    input_records = {"Data": input_data}

    batch_1 = json.dumps(
        [
            {"event1": "event1_data"},
            {"event2": "event2_data"},
        ]
    )
    batch_2 = json.dumps(
        [
            {"event3": "event3_data"},
        ]
    )

    batch_1_zipped = gzip.compress(batch_1.encode())
    batch_2_zipped = gzip.compress(batch_2.encode())

    batch_1_object = {"Data": batch_1_zipped}
    batch_2_object = {"Data": batch_2_zipped}

    expected_output = [batch_1_object, batch_2_object]

    actual_output = create_batches_from_record(input_records)

    assert actual_output == expected_output


def test_create_batches_from_record__with_exactly_max_batch_amount(mocker):
    mocker.patch(
        MAX_BATCH_LENGTH_PATH,
        3,
    )

    input_data = """{"event1": "event1_data"}\n{"event2": "event2_data"}\n{"event3": "event3_data"}\n"""
    input_records = {"Data": input_data}

    expected_batch = json.dumps(
        [
            {"event1": "event1_data"},
            {"event2": "event2_data"},
            {"event3": "event3_data"},
        ]
    )
    expected_batch_zipped = gzip.compress(expected_batch.encode())
    expected_batch_object = {"Data": expected_batch_zipped}

    expected_output = [expected_batch_object]

    actual_output = create_batches_from_record(input_records)
    assert actual_output == expected_output


def test_delete_records_to_be_reingested():
    mock_processed_records = [
        {"data": "test data", "recordId": "guid1", "result": "Ok"},
        {"data": "to be deleted", "recordId": "guid2", "result": "Ok"},
    ]
    mock_record_ids_to_delete = ["guid2"]
    expected_output = [
        {"data": "test data", "recordId": "guid1", "result": "Ok"},
        {"recordId": "guid2", "result": "Dropped"},
    ]

    actual_output = delete_records_to_be_reingested(
        mock_processed_records, mock_record_ids_to_delete
    )

    assert actual_output == expected_output
