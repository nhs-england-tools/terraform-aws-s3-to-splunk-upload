import os
import boto3
import pytest
from moto import mock_s3, mock_firehose
from s3_to_firehose.s3_to_firehose import lambda_handler


BUCKET_NAME = "test_bucket"
FILEPATH_FOR_TEST_DATA = os.path.dirname(os.path.realpath(__file__))
TEST_FILE_NAME = "mock_data.txt"
MOCK_STREAM_NAME = "audit_log_delivery_stream"


@pytest.fixture
def aws_services():
    with mock_s3(), mock_firehose():
        s3_client = boto3.client("s3", region_name="eu-west-2")
        firehose_client = boto3.client("firehose", region_name="eu-west-2")

        s3_client.create_bucket(
            Bucket=f"{BUCKET_NAME}",
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
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
        yield s3_client, firehose_client


def test_successful_get_object(aws_services, monkeypatch):
    s3_client, _ = aws_services
    monkeypatch.setenv("Firehose", MOCK_STREAM_NAME)

    with open(f"{FILEPATH_FOR_TEST_DATA}/{TEST_FILE_NAME}") as test_file:
        test_file_contents = test_file.read()

    s3_client.put_object(
        Bucket=f"{BUCKET_NAME}",
        Key=f"{TEST_FILE_NAME}",
        Body=test_file_contents,
    )

    test_notification = build_test_notification(BUCKET_NAME, TEST_FILE_NAME)

    firehose_response = lambda_handler(test_notification, {})
    assert firehose_response["ResponseMetadata"]["HTTPStatusCode"] == 200

    bucket_contents = s3_client.list_objects_v2(Bucket="test_firehose_delivery")[
        "Contents"
    ]
    assert len(bucket_contents) == 1

    key = bucket_contents[0]["Key"]
    actual_file = s3_client.get_object(Bucket="test_firehose_delivery", Key=key)
    actual_file_contents = actual_file["Body"].read().decode("utf-8")
    assert actual_file_contents == test_file_contents


def test_unsuccessful_request_raises_error(aws_services):
    test_notification = build_test_notification(BUCKET_NAME, TEST_FILE_NAME)

    with pytest.raises(Exception):
        lambda_handler(test_notification, {})


def build_test_notification(bucket_name, test_file_name):
    return {
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "awsRegion": "us-west-2",
                "eventTime": "1970-01-01T00:00:00.000Z",
                "eventName": "ObjectCreated:Put",
                "userIdentity": {"principalId": "ExampleId"},
                "requestParameters": {"sourceIPAddress": "127.0.0.1"},
                "responseElements": {
                    "x-amz-request-id": "C3D13FE58DE4C810",
                    "x-amz-id-2": "FMyUVURIY8/IgAtTv8xRjskZQpcIZ9KG4V5Wp6S7S/JRWeUWerMUE5JgHvANOjpD",
                },
                "s3": {
                    "s3SchemaVersion": "1.0",
                    "configurationId": "testConfigRule",
                    "bucket": {
                        "name": f"{bucket_name}",
                        "ownerIdentity": {"principalId": "A3NL1KOZZKExample"},
                        "arn": f"arn:aws:s3:::{bucket_name}",
                    },
                    "object": {
                        "key": f"{test_file_name}",
                        "size": 9,
                        "eTag": "d41d8cd98f00b204e9800998ecf8427e",
                        "versionId": "096fKKXTRTtl3on89fVO.nfljtsv6qko",
                        "sequencer": "0055AED6DCD90281E5",
                    },
                },
            }
        ]
    }
