import gzip
import pytest
import boto3
from moto import mock_firehose, mock_s3
from utils.utils import put_records_to_firehose_stream

from tests.mock_constants import (
    MOCK_EVENT_STRING,
    MOCK_STREAM_NAME,
)


@mock_s3
@mock_firehose
def test_put_records_to_firehose_stream():
    firehose_client = boto3.client("firehose", region_name="eu-west-2")
    s3_client = boto3.client("s3", region_name="eu-west-2")

    s3_client.create_bucket(
        Bucket="test_firehose_delivery",
        CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
    )

    zipped_mock_event = gzip.compress(MOCK_EVENT_STRING.encode())
    mock_record = [{"Data": zipped_mock_event}]

    firehose_client.create_delivery_stream(
        DeliveryStreamName=f"{MOCK_STREAM_NAME}",
        S3DestinationConfiguration={
            "RoleARN": "arn:aws:iam::*",
            "BucketARN": "arn:aws:s3:::test_firehose_delivery",
        },
    )

    put_records_to_firehose_stream(MOCK_STREAM_NAME, mock_record, firehose_client, 0, 2)

    bucket_contents = s3_client.list_objects_v2(Bucket="test_firehose_delivery")[
        "Contents"
    ]
    assert len(bucket_contents) == 1

    key = bucket_contents[0]["Key"]
    actual_file = s3_client.get_object(Bucket="test_firehose_delivery", Key=key)
    actual_file_contents = gzip.decompress(actual_file["Body"].read()).decode()
    assert actual_file_contents == MOCK_EVENT_STRING


def test_put_records_to_firehose_stream__raises_error():
    firehose_client = {}

    zipped_mock_event = gzip.compress(MOCK_EVENT_STRING.encode())
    mock_record = [{"Data": zipped_mock_event}]

    with pytest.raises(RuntimeError) as error_content:
        put_records_to_firehose_stream(
            MOCK_STREAM_NAME, mock_record, firehose_client, 0, 2
        )
    assert "Could not put records after 2 attempts." in str(error_content.value)


@mock_firehose
def test_put_records_to_firehose_stream__handles_failed_puts(mocker):
    firehose_client = boto3.client("firehose", region_name="eu-west-2")

    mocker.patch(
        "moto.firehose.models.FirehoseBackend.put_record_batch",
        return_value={
            "FailedPutCount": 1,
            "RequestResponses": [{"ErrorCode": "error1234"}],
        },
        autospec=True,
    )

    zipped_mock_event = gzip.compress(MOCK_EVENT_STRING.encode())
    mock_record = [{"Data": zipped_mock_event}]

    with pytest.raises(RuntimeError) as error_content:
        put_records_to_firehose_stream(
            MOCK_STREAM_NAME, mock_record, firehose_client, 0, 2
        )
    assert "Individual error codes:" in str(error_content.value)


@mock_firehose
def test_put_records_to_firehose_stream__handles_failed_puts_with_no_error_code(mocker):
    firehose_client = boto3.client("firehose", region_name="eu-west-2")

    mocker.patch(
        "moto.firehose.models.FirehoseBackend.put_record_batch",
        return_value={
            "FailedPutCount": 2,
            "RequestResponses": [
                {"RecordId": "guid2", "ErrorCode": "some error"},
                {"RecordId": "guid1"},
            ],
        },
        autospec=True,
    )

    zipped_mock_event_1 = gzip.compress(MOCK_EVENT_STRING.encode())
    zipped_mock_event_2 = gzip.compress(MOCK_EVENT_STRING.encode())
    mock_records = [{"Data": zipped_mock_event_1}, {"Data": zipped_mock_event_2}]

    with pytest.raises(RuntimeError) as error_content:
        put_records_to_firehose_stream(
            MOCK_STREAM_NAME, mock_records, firehose_client, 0, 2
        )

    error_codes = str(error_content.value).split(": ")[1]
    assert error_codes == "some error"
