import base64
import gzip
import json
import pytest
import boto3
from moto import mock_s3, mock_firehose
from reingestion_lambda.reingestion_lambda import (
    lambda_handler,
    get_environment_variables,
    put_records_to_s3,
)
from reingestion_lambda.Dataclasses import (
    EventMetadata,
    ProcessedBody,
)

from tests.mock_constants import (
    MOCK_BUCKET_NAME,
    MOCK_STREAM_NAME,
    REGION,
)


def test_get_environment_variables(monkeypatch):
    expected_max_ingest = 5

    monkeypatch.setenv("Firehose", MOCK_STREAM_NAME)
    monkeypatch.setenv("Region", REGION)
    monkeypatch.setenv("max_ingest", str(expected_max_ingest))

    actual_stream_name, actual_region, actual_max_ingest = get_environment_variables()

    assert actual_stream_name == MOCK_STREAM_NAME
    assert actual_region == REGION
    assert actual_max_ingest == expected_max_ingest


def test_get_environment_variables__missing_firehose(monkeypatch):
    expected_max_ingest = 5

    monkeypatch.setenv("Region", REGION)
    monkeypatch.setenv("max_ingest", str(expected_max_ingest))

    with pytest.raises(KeyError) as error_content:
        get_environment_variables()

    assert "'Firehose environment variable not set.'" == str(error_content.value)


def test_get_environment_variables__missing_region(monkeypatch):
    expected_max_ingest = 5

    monkeypatch.setenv("Firehose", MOCK_STREAM_NAME)
    monkeypatch.setenv("max_ingest", str(expected_max_ingest))

    with pytest.raises(KeyError) as error_content:
        get_environment_variables()

    assert "'Region environment variable not set'" == str(error_content.value)


def test_get_environment_variables__missing_max_ingest(monkeypatch, capfd):
    monkeypatch.setenv("Firehose", MOCK_STREAM_NAME)
    monkeypatch.setenv("Region", REGION)

    _, _, actual_max_ingest = get_environment_variables()
    expected_log, _ = capfd.readouterr()

    assert actual_max_ingest == 2
    assert "max_ingest environment variable not set. Defaulted to 2.\n" == expected_log


@mock_s3
def test_put_records_to_s3():
    mock_s3_client = boto3.client("s3", region_name=REGION)
    mock_s3_client.create_bucket(
        Bucket=MOCK_BUCKET_NAME,
        CreateBucketConfiguration={"LocationConstraint": REGION},
    )
    mock_key = "mock_file_key"

    input_processed_body = ProcessedBody()
    input_event_metadata = EventMetadata("", {}, REGION, 10, MOCK_BUCKET_NAME, mock_key)

    input_s3_payload = {MOCK_BUCKET_NAME: '{"key": "value"}'}
    input_processed_body.s3_payload = input_s3_payload

    put_records_to_s3(input_event_metadata, input_processed_body)

    actual_s3_object = mock_s3_client.get_object(
        Key="SplashbackRawFailed/mock_file_key", Bucket=MOCK_BUCKET_NAME
    )

    assert actual_s3_object["Body"].read().decode() == '{"key": "value"}'


@mock_s3
@mock_firehose
def test_lambda_handler(monkeypatch):
    s3_client = boto3.client("s3", region_name=REGION)
    firehose_client = boto3.client("firehose", region_name=REGION)

    s3_client.create_bucket(
        Bucket=MOCK_BUCKET_NAME,
        CreateBucketConfiguration={"LocationConstraint": REGION},
    )
    s3_client.create_bucket(
        Bucket="test_firehose_delivery",
        CreateBucketConfiguration={"LocationConstraint": REGION},
    )
    firehose_client.create_delivery_stream(
        DeliveryStreamName=MOCK_STREAM_NAME,
        S3DestinationConfiguration={
            "RoleARN": "arn:aws:iam::*",
            "BucketARN": "arn:aws:s3:::test_firehose_delivery",
        },
    )
    monkeypatch.setenv("Firehose", MOCK_STREAM_NAME)
    monkeypatch.setenv("Region", REGION)
    monkeypatch.setenv("max_ingest", str(5))

    test_file_name = "test_file"

    mock_data1 = json.dumps({"event": "event 1"})
    mock_data2 = json.dumps({"event": "event 2"})

    mock_data1_encoded = mock_data1.encode()
    mock_data2_encoded = mock_data2.encode()

    mock_event1 = {"rawData": base64.b64encode(mock_data1_encoded).decode()}
    mock_event2 = {"rawData": base64.b64encode(mock_data2_encoded).decode()}

    input_line1 = json.dumps(mock_event1)
    input_line2 = json.dumps(mock_event2)
    input_body = f"{input_line1}\n{input_line2}\n".encode()

    test_file_contents_zipped = gzip.compress(input_body)

    s3_client.put_object(
        Bucket=MOCK_BUCKET_NAME,
        Key=test_file_name,
        Body=test_file_contents_zipped,
    )

    mock_event = {
        "Records": [
            {
                "s3": {
                    "bucket": {
                        "name": MOCK_BUCKET_NAME,
                        "arn": f"arn:aws:s3:::{MOCK_BUCKET_NAME}",
                    },
                    "object": {
                        "key": test_file_name,
                    },
                },
            }
        ]
    }

    lambda_handler(mock_event, {})

    expected_contents_in_s3 = '{"sourcetype": "aws:firehose", "source": "aws:reingested", "event": "event 1", "fields": {"reingest": 1, "origin_bucket_name": "test-bucket"}}{"sourcetype": "aws:firehose", "source": "aws:reingested", "event": "event 2", "fields": {"reingest": 1, "origin_bucket_name": "test-bucket"}}'

    bucket_contents = s3_client.list_objects_v2(Bucket="test_firehose_delivery")[
        "Contents"
    ]
    assert len(bucket_contents) == 1

    key = bucket_contents[0]["Key"]
    actual_file = s3_client.get_object(Bucket="test_firehose_delivery", Key=key)
    actual_file_zipped = actual_file["Body"].read()
    actual_file_contents = gzip.decompress(actual_file_zipped).decode()
    assert actual_file_contents == expected_contents_in_s3


@mock_s3
@mock_firehose
def test_lambda_handler__puts_to_s3(monkeypatch):
    s3_client = boto3.client("s3", region_name=REGION)
    firehose_client = boto3.client("firehose", region_name=REGION)

    s3_client.create_bucket(
        Bucket=MOCK_BUCKET_NAME,
        CreateBucketConfiguration={"LocationConstraint": REGION},
    )
    s3_client.create_bucket(
        Bucket="test_firehose_delivery",
        CreateBucketConfiguration={"LocationConstraint": REGION},
    )
    firehose_client.create_delivery_stream(
        DeliveryStreamName=MOCK_STREAM_NAME,
        S3DestinationConfiguration={
            "RoleARN": "arn:aws:iam::*",
            "BucketARN": "arn:aws:s3:::test_firehose_delivery",
        },
    )
    max_ingest = 2
    monkeypatch.setenv("Firehose", MOCK_STREAM_NAME)
    monkeypatch.setenv("Region", REGION)
    monkeypatch.setenv("max_ingest", str(max_ingest))

    test_file_name = "test_file"

    mock_data1 = json.dumps(
        {
            "event": "event 1",
            "fields": {
                "origin_bucket_name": MOCK_BUCKET_NAME,
                "reingest": max_ingest,
            },
        }
    )
    mock_data2 = json.dumps(
        {
            "event": "event 2",
            "fields": {
                "origin_bucket_name": MOCK_BUCKET_NAME,
                "reingest": max_ingest,
            },
        }
    )

    mock_data1_encoded = mock_data1.encode()
    mock_data2_encoded = mock_data2.encode()

    mock_event1 = {"rawData": base64.b64encode(mock_data1_encoded).decode()}
    mock_event2 = {"rawData": base64.b64encode(mock_data2_encoded).decode()}

    input_line1 = json.dumps(mock_event1)
    input_line2 = json.dumps(mock_event2)
    input_body = f"{input_line1}\n{input_line2}\n".encode()

    test_file_contents_zipped = gzip.compress(input_body)

    s3_client.put_object(
        Bucket=MOCK_BUCKET_NAME,
        Key=test_file_name,
        Body=test_file_contents_zipped,
    )

    mock_event = {
        "Records": [
            {
                "s3": {
                    "bucket": {
                        "name": MOCK_BUCKET_NAME,
                        "arn": f"arn:aws:s3:::{MOCK_BUCKET_NAME}",
                    },
                    "object": {
                        "key": test_file_name,
                    },
                },
            }
        ]
    }

    lambda_handler(mock_event, {})

    destination_bucket_key_count = s3_client.list_objects_v2(
        Bucket="test_firehose_delivery"
    )["KeyCount"]
    assert destination_bucket_key_count == 0

    original_bucket_contents = s3_client.list_objects_v2(Bucket=MOCK_BUCKET_NAME)[
        "Contents"
    ]
    expected_contents_in_s3 = '"event 1"\n"event 2"\n'

    key = original_bucket_contents[0]["Key"]
    actual_file = s3_client.get_object(Bucket=MOCK_BUCKET_NAME, Key=key)
    actual_file_contents = actual_file["Body"].read().decode()

    assert actual_file_contents == expected_contents_in_s3


@mock_s3
def test_lambda_handler__raises_error(monkeypatch):
    s3_client = boto3.client("s3", region_name=REGION)

    s3_client.create_bucket(
        Bucket=MOCK_BUCKET_NAME,
        CreateBucketConfiguration={"LocationConstraint": REGION},
    )

    monkeypatch.setenv("Firehose", MOCK_STREAM_NAME)
    monkeypatch.setenv("Region", REGION)
    monkeypatch.setenv("max_ingest", str(5))

    incorrect_key = "wrong key"

    mock_event = {
        "Records": [
            {
                "s3": {
                    "bucket": {
                        "name": MOCK_BUCKET_NAME,
                        "arn": f"arn:aws:s3:::{MOCK_BUCKET_NAME}",
                    },
                    "object": {
                        "key": incorrect_key,
                    },
                },
            }
        ]
    }

    with pytest.raises(Exception) as error_content:
        lambda_handler(mock_event, {})

    expected_error_value = "An error occurred (NoSuchKey) when calling the GetObject operation: The specified key does not exist."
    assert expected_error_value == str(error_content.value)
