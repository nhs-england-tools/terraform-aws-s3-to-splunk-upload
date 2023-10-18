import gzip
import os
from urllib.parse import unquote_plus
import boto3
from utils.utils import put_records_to_firehose_stream
from reingestion_lambda.Dataclasses import (
    EventMetadata,
    ProcessedBody,
)
from reingestion_lambda.process_body import process_body


def lambda_handler(event, _context):
    s3_client = boto3.client("s3")
    bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
    key = unquote_plus(event["Records"][0]["s3"]["object"]["key"], encoding="utf-8")

    FIREHOSE_STREAM_NAME, REGION, MAX_INGEST = get_environment_variables()
    firehose_client = boto3.client("firehose", region_name=REGION)

    event_metadata = EventMetadata(
        FIREHOSE_STREAM_NAME, firehose_client, REGION, MAX_INGEST, bucket_name, key
    )

    object_from_s3 = s3_client.get_object(Bucket=event_metadata.bucket_name, Key=key)

    with gzip.GzipFile(fileobj=object_from_s3["Body"], mode="r") as f:
        object_body = f.read().decode()

    processed_body = process_body(object_body, event_metadata)

    if processed_body.count_for_firehose > 0:
        put_records_to_firehose_stream(
            event_metadata.FIREHOSE_STREAM_NAME,
            processed_body.record_batch,
            event_metadata.firehose_client,
            0,
            20,
        )
    if processed_body.count_for_s3 > 0:
        put_records_to_s3(event_metadata, processed_body)


def get_environment_variables():
    try:
        FIREHOSE_STREAM_NAME = os.environ["Firehose"]
    except Exception:
        raise KeyError("Firehose environment variable not set.")
    try:
        REGION = os.environ["Region"]
    except Exception:
        raise KeyError("Region environment variable not set")
    try:
        MAX_INGEST = int(os.environ["max_ingest"])
    except Exception:
        print("max_ingest environment variable not set. Defaulted to 2.")
        MAX_INGEST = 2
    return FIREHOSE_STREAM_NAME, REGION, MAX_INGEST


def put_records_to_s3(event_metadata: EventMetadata, processed_body: ProcessedBody):
    print(
        "Already re-ingested more than max attempts, will write to S3 to prevent looping"
    )
    file_name = event_metadata.key
    s3_path = f"SplashbackRawFailed/{file_name}"
    for bucket in processed_body.s3_payload:
        print(f"writing to bucket:{bucket} with s3_key:{s3_path}")

        s3write = boto3.resource("s3")
        s3write.Bucket(bucket).put_object(
            Key=s3_path, Body=processed_body.s3_payload[bucket].encode()
        )
