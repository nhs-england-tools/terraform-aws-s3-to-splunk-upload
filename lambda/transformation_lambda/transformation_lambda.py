import base64
import gzip
import os
import boto3
import io
import json
import re
from transformation_lambda.constants import MAX_REINGESTION_ATTEMPTS
from transformation_lambda.reingest import (
    get_records_to_reingest,
    delete_records_to_be_reingested,
)
from utils.utils import put_records_to_firehose_stream


def transform_log_event(log_event):
    return_event = {}
    return_event["host"] = os.environ["splunk_host"]
    return_event["index"] = os.environ["splunk_index"]
    return_event["source"] = os.environ["splunk_source"]
    return_event["sourcetype"] = os.environ["splunk_sourcetype"]
    return_event["time"] = log_event[os.environ["timestamp_key"]]
    return_event["event"] = log_event
    return f"{json.dumps(return_event)}\n"


def encode_record_data(original_record):
    record_id = original_record["recordId"]
    result = original_record["result"]

    if original_record.get("data") == None:
        return {"recordId": record_id, "result": result}

    original_data = original_record["data"]

    # convert string to base64 encoded string for firehose.
    # b64encode requires bytes as input, so we need to encode the string first.
    # b64encode returns bytes, so we need to decode it back to a string.
    encoded_data = base64.b64encode(original_data.encode()).decode()
    return {"data": encoded_data, "recordId": record_id, "result": result}


def process_event(event):
    event_is_not_already_processed = event.get("sourcetype") == None

    if event_is_not_already_processed:
        processed_event = transform_log_event(event)
    else:
        processed_event = json.dumps(event)

    return processed_event


def process_records(records):
    processed_records = []

    for record in records:
        decoded_data = base64.b64decode(record["data"])
        io_data = io.BytesIO(decoded_data)

        with gzip.GzipFile(fileobj=io_data, mode="r") as unzipped_file:
            data = unzipped_file.read().decode()

        events_as_strings = data.split("\n")

        last_event_is_empty = events_as_strings[-1] == ""

        if last_event_is_empty:
            events_as_strings = events_as_strings[:-1]

        events = [json.loads(event) for event in events_as_strings]

        record_id = record["recordId"]
        processed_data = ""

        for event in events:
            processed_event = process_event(event)
            processed_data = f"{processed_data}{processed_event}"

        processed_record = {
            "data": processed_data,
            "result": "Ok",
            "recordId": record_id,
        }

        processed_records.append(processed_record)

    return processed_records


def get_region_from_arn(stream_arn):
    return re.search(r":(\w+-\w+-\w+):", stream_arn).group(1)


def get_stream_name_from_arn(stream_arn):
    return re.search(r"\/(.+)$", stream_arn).group(1)


def lambda_handler(event, _context):
    print(f"Received {len(event['records'])} records")
    stream_arn = event["deliveryStreamArn"]
    stream_name = get_stream_name_from_arn(stream_arn)
    region = get_region_from_arn(stream_arn)

    processed_records = process_records(event["records"])

    records_to_reingest, record_ids_to_delete = get_records_to_reingest(
        processed_records
    )

    if records_to_reingest:
        client = boto3.client("firehose", region_name=region)
        put_records_to_firehose_stream(
            stream_name,
            records_to_reingest,
            client,
            attempts_made=0,
            max_attempts=MAX_REINGESTION_ATTEMPTS,
        )

        processed_records = delete_records_to_be_reingested(
            processed_records, record_ids_to_delete
        )

    encoded_records = [encode_record_data(record) for record in processed_records]

    record_return_count = len(encoded_records) - len(records_to_reingest)
    print(
        f"{record_return_count} batches returned by handler, {len(records_to_reingest)} batches reingested"
    )
    return {"records": encoded_records}
