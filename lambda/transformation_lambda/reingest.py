import gzip
import json
from transformation_lambda.constants import (
    MAX_BATCH_LENGTH,
    MAX_LAMBDA_RETURN_SIZE,
)


def get_records_to_reingest(processed_records):
    projected_size = 0
    records_to_reingest = []
    record_ids_to_delete = []

    for record in processed_records:
        projected_size += len(record["data"]) + len(record["recordId"])

        if projected_size > MAX_LAMBDA_RETURN_SIZE:
            record_to_reingest, record_id_to_delete = get_record_to_reingest(record)
            record_ids_to_delete.append(record_id_to_delete)
            records_to_reingest.append(record_to_reingest)

    return records_to_reingest, record_ids_to_delete


def get_record_to_reingest(record):
    formatted_record = format_record_for_firehose(record)
    record_to_reingest = create_batches_from_record(formatted_record)
    return record_to_reingest, record["recordId"]


def format_record_for_firehose(record_to_reingest):
    return {"Data": record_to_reingest["data"]}


def create_batches_from_record(record):
    processed_batches = []

    events_with_final_newline = record["Data"].split("\n")
    events_as_strings = events_with_final_newline[:-1]
    events_to_ingest = [json.loads(event) for event in events_as_strings]

    remaining_size = len(events_to_ingest)
    batch_start_offset = 0

    while remaining_size > MAX_BATCH_LENGTH:
        batch_data = events_to_ingest[batch_start_offset:]

        batch = create_batch(
            batch_data,
            MAX_BATCH_LENGTH,
        )

        processed_batches.append(batch)
        batch_start_offset += MAX_BATCH_LENGTH
        remaining_size -= MAX_BATCH_LENGTH

    remaining_events = events_to_ingest[batch_start_offset:]
    final_batch = create_batch(remaining_events, remaining_size)

    processed_batches.append(final_batch)

    return processed_batches


def create_batch(events, upper_limit):
    batch_data = json.dumps(events[:upper_limit])
    zip_data = gzip.compress(batch_data.encode())
    return {"Data": zip_data}


def delete_records_to_be_reingested(processed_records, record_ids_to_delete):
    def delete_record(record):
        if record["recordId"] in record_ids_to_delete:
            del record["data"]
            record["result"] = "Dropped"
        return record

    records_to_return = map(delete_record, processed_records)

    return list(records_to_return)
