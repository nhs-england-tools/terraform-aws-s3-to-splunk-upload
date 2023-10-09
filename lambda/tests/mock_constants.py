import json
import os

MOCK_EVENT_STRING = json.dumps(
    {
        "someData": 1234,
        "moreData": "testData",
        "@timestamp": 1234567890,
    }
)
MOCK_EVENT_OBJECT = {
    "someData": 1234,
    "moreData": "testData",
    "@timestamp": 1234567890,
}

MOCK_STREAM_NAME = "test_stream"
MOCK_STREAM_ARN = f"arn:aws:kinesis:eu-west-2:123456789012:stream/{MOCK_STREAM_NAME}"
MAX_BATCH_LENGTH_PATH = "transformation_lambda.reingest.MAX_BATCH_LENGTH"
MAX_LAMBDA_RETURN_PATH = "transformation_lambda.reingest.MAX_LAMBDA_RETURN_SIZE"
PUT_RECORDS_TO_FIREHOSE_PATH = "utils.utils.put_records_to_firehose_stream"
FILEPATH_FOR_TEST_FOLDER = os.path.dirname(os.path.realpath(__file__))
MOCK_EVENT_NAME = "mock_event.json"
EXPECTED_OUTPUT_FILE_NAME = "expected_response.json"
MOCK_BUCKET_NAME = "test-bucket"
MOCK_SOURCE = "auditLogs"
MOCK_SOURCETYPE = "auditLogs:json"
REGION = "eu-west-2"
