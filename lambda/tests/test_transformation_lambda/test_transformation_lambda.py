import base64
import gzip
import json
import os
import boto3
from moto import mock_firehose, mock_s3
from transformation_lambda.transformation_lambda import (
    lambda_handler,
    process_event,
    process_records,
    transform_log_event,
    get_region_from_arn,
    get_stream_name_from_arn,
    encode_record_data,
)


from tests.mock_constants import (
    MOCK_EVENT_STRING,
    MOCK_EVENT_OBJECT,
    MOCK_STREAM_ARN,
    PUT_RECORDS_TO_FIREHOSE_PATH,
    MOCK_STREAM_NAME,
    MAX_LAMBDA_RETURN_PATH,
    FILEPATH_FOR_TEST_FOLDER,
    MOCK_EVENT_NAME,
    EXPECTED_OUTPUT_FILE_NAME,
)

os.environ["splunk_host"] = "GitHub_Enterprise"
os.environ["splunk_index"] = "github_engineering_audit"
os.environ["splunk_source"] = "GitHub_Audit_Log_Stream"
os.environ["splunk_sourcetype"] = "github:enterprise:audit"
os.environ["timestamp_key"] = "@timestamp"

FILEPATH_FOR_TEST_DATA = f"{FILEPATH_FOR_TEST_FOLDER}/test_transformation_lambda"


def test_transform_log_event():
    expected_event = {
        "event": MOCK_EVENT_OBJECT,
        "host": "GitHub_Enterprise",
        "index": "github_engineering_audit",
        "source": "GitHub_Audit_Log_Stream",
        "sourcetype": "github:enterprise:audit",
        "time": 1234567890,
    }
    actual_event = json.loads(transform_log_event(MOCK_EVENT_OBJECT))

    assert actual_event == expected_event


def test_encode_record_data():
    input_record = {"data": MOCK_EVENT_STRING, "recordId": "guid", "result": "Ok"}
    encoded_mock_event = base64.b64encode(MOCK_EVENT_STRING.encode()).decode()
    expected_record = {"data": encoded_mock_event, "recordId": "guid", "result": "Ok"}
    actual_record = encode_record_data(input_record)
    assert actual_record == expected_record


def test_encode_record_data__no_data():
    input_record = {"recordId": "guid", "result": "Ok"}
    actual_record = encode_record_data(input_record)
    assert actual_record == input_record


def test_process_event():
    expected_event = transform_log_event(MOCK_EVENT_OBJECT)
    actual_event = process_event(MOCK_EVENT_OBJECT)
    assert actual_event == expected_event


def test_process_event__contains_sourcetype():
    test_event = {
        "sourcetype": "some sourcetype",
        "event": MOCK_EVENT_OBJECT,
    }
    expected_event = json.dumps(test_event)
    actual_event = process_event(test_event)
    assert actual_event == expected_event


def setup_records_for_test(add_sourcetype):
    if add_sourcetype:
        test_event_1 = {
            "sourcetype": "some sourcetype",
            "event": MOCK_EVENT_OBJECT,
        }
        test_event_2 = {
            "sourcetype": "some sourcetype",
            "event": MOCK_EVENT_OBJECT,
        }
    else:
        test_event_1 = MOCK_EVENT_OBJECT
        test_event_2 = MOCK_EVENT_OBJECT

    test_event_3 = MOCK_EVENT_OBJECT
    test_event_4 = MOCK_EVENT_OBJECT

    test_event_1["test_event_id"] = 1
    test_event_2["test_event_id"] = 2
    test_event_3["test_event_id"] = 3
    test_event_4["test_event_id"] = 4

    test_events_1 = f"{json.dumps(test_event_1)}\n{json.dumps(test_event_2)}\n"
    test_events_2 = f"{json.dumps(test_event_3)}\n{json.dumps(test_event_4)}\n"

    mock_data_1_zipped = gzip.compress(test_events_1.encode())
    mock_data_2_zipped = gzip.compress(test_events_2.encode())
    mock_data_1_encoded = base64.b64encode(mock_data_1_zipped)
    mock_data_2_encoded = base64.b64encode(mock_data_2_zipped)

    mock_record_1 = {"recordId": "guid1", "data": mock_data_1_encoded}
    mock_record_2 = {"recordId": "guid2", "data": mock_data_2_encoded}

    input_records = [mock_record_1, mock_record_2]

    if add_sourcetype:
        expected_data_1 = f"{json.dumps(test_event_1)}{json.dumps(test_event_2)}"
    else:
        expected_data_1 = (
            f"{transform_log_event(test_event_1)}{transform_log_event(test_event_2)}"
        )

    expected_data_2 = (
        f"{transform_log_event(test_event_3)}{transform_log_event(test_event_4)}"
    )

    expected_output = [
        {"data": expected_data_1, "result": "Ok", "recordId": "guid1"},
        {"data": expected_data_2, "result": "Ok", "recordId": "guid2"},
    ]

    return input_records, expected_output


def test_process_records():
    input_records, expected_output = setup_records_for_test(False)
    actual_output = process_records(input_records)
    assert actual_output == expected_output


def test_process_records_with_some_already_processed():
    input_records, expected_output = setup_records_for_test(True)
    actual_output = process_records(input_records)
    assert actual_output == expected_output


def test_get_region_from_arn():
    actual_region = get_region_from_arn(MOCK_STREAM_ARN)
    expected_region = "eu-west-2"
    assert actual_region == expected_region


def test_get_stream_name_from_arn():
    actual_stream_name = get_stream_name_from_arn(MOCK_STREAM_ARN)
    expected_stream_name = MOCK_STREAM_NAME
    assert actual_stream_name == expected_stream_name


@mock_s3
@mock_firehose
def test_lambda_handler():
    firehose_client = boto3.client("firehose", region_name="eu-west-2")
    s3_client = boto3.client("s3", region_name="eu-west-2")

    s3_client.create_bucket(
        Bucket="test_firehose_delivery",
        CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
    )

    firehose_client.create_delivery_stream(
        DeliveryStreamName=MOCK_STREAM_NAME,
        S3DestinationConfiguration={
            "RoleARN": "arn:aws:iam::*",
            "BucketARN": "arn:aws:s3:::test_firehose_delivery",
        },
    )

    with open(f"{FILEPATH_FOR_TEST_DATA}/{MOCK_EVENT_NAME}") as test_event:
        test_event_contents = json.load(test_event)

    with open(f"{FILEPATH_FOR_TEST_DATA}/{EXPECTED_OUTPUT_FILE_NAME}") as expected_file:
        expected_output = {"records": json.load(expected_file)}

    actual_output = lambda_handler(test_event_contents, {})

    assert actual_output == expected_output


@mock_firehose
def test_lambda_handler__successfully_deletes_records(mocker):
    firehose_client = boto3.client("firehose", region_name="eu-west-2")
    firehose_client.create_delivery_stream(
        DeliveryStreamName=MOCK_STREAM_NAME,
        S3DestinationConfiguration={
            "RoleARN": "arn:aws:iam::*",
            "BucketARN": "arn:aws:s3:::test_firehose_delivery",
        },
    )
    test_records, _ = setup_records_for_test(False)

    test_event = {
        "deliveryStreamArn": MOCK_STREAM_ARN,
        "records": test_records,
    }

    expected_output = {
        "records": [
            {"recordId": "guid1", "result": "Dropped"},
            {"recordId": "guid2", "result": "Dropped"},
        ]
    }

    mocker.patch(
        MAX_LAMBDA_RETURN_PATH,
        0,
    )
    mocker.patch(
        PUT_RECORDS_TO_FIREHOSE_PATH,
        return_value=None,
    )

    actual_output = lambda_handler(test_event, {})

    assert actual_output == expected_output


@mock_firehose
def test_lambda_handler__successfully_tries_to_reingest(mocker):
    firehose_client = boto3.client("firehose", region_name="eu-west-2")
    firehose_client.create_delivery_stream(
        DeliveryStreamName=MOCK_STREAM_NAME,
        S3DestinationConfiguration={
            "RoleARN": "arn:aws:iam::*",
            "BucketARN": "arn:aws:s3:::test_firehose_delivery",
        },
    )
    test_records, _ = setup_records_for_test(False)
    test_event = {"deliveryStreamArn": MOCK_STREAM_ARN, "records": test_records}

    expected_output = {
        "records": [
            {"recordId": "guid1", "result": "Dropped"},
            {"recordId": "guid2", "result": "Dropped"},
        ]
    }

    mocker.patch(
        MAX_LAMBDA_RETURN_PATH,
        4,
    )
    mock_put_records_to_firehose_stream = mocker.patch(
        PUT_RECORDS_TO_FIREHOSE_PATH,
        return_value=None,
    )

    actual_output = lambda_handler(test_event, {})

    assert actual_output == expected_output
    mock_put_records_to_firehose_stream.assert_called()


def generate_mock_data():
    with open(f"{FILEPATH_FOR_TEST_DATA}/mock_processed_data.json") as mock_data_file:
        mock_data = mock_data_file.read()

    mock_data = base64.b64encode(mock_data.encode()).decode()
    return mock_data
