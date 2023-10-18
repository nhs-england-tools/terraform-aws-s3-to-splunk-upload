import json
import os
import urllib.parse
import boto3


def get_bucket_name_and_key(event):
    bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
    object_key = urllib.parse.unquote_plus(
        event["Records"][0]["s3"]["object"]["key"], encoding="utf-8"
    )
    return bucket_name, object_key


def lambda_handler(event, _context):
    s3_client = boto3.client("s3", region_name="eu-west-2")
    firehose_client = boto3.client("firehose", region_name="eu-west-2")

    try:
        FIREHOSE_STREAM_NAME = os.environ["Firehose"]
    except Exception:
        raise KeyError("Firehose environment variable not set.")

    bucket_name, object_key = get_bucket_name_and_key(event)

    object_to_send = s3_client.get_object(Bucket=bucket_name, Key=object_key)
    object_contents = object_to_send["Body"].read()

    response = firehose_client.put_record(
        DeliveryStreamName=FIREHOSE_STREAM_NAME,
        Record={"Data": object_contents},
    )

    return json.loads(json.dumps(response, default=str))
