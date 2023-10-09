import json
import gzip
from reingestion_lambda.Dataclasses import (
    EventMetadata,
    ProcessedBody,
)
from utils.utils import put_records_to_firehose_stream
from reingestion_lambda.process_message_line import process_message_line


MAX_BATCH_SIZE = 400
FIREHOSE_MAX_ATTEMPTS = 20


def process_message(
    processed_body: ProcessedBody, message, event_metadata: EventMetadata
):
    for message_line in message.split("\n"):
        if len(message_line) == 0:
            continue

        processed_message_line = process_message_line(
            message_line, processed_body.s3_payload, event_metadata
        )
        processed_body.reingest_json = processed_message_line.reingest_json
        processed_body.s3_payload = processed_message_line.s3_payload
        processed_body.count_for_s3 = processed_message_line.count_for_s3
        processed_body.sent_to_s3 = processed_message_line.sent_to_s3

        if not processed_body.sent_to_s3:
            processed_body = process_for_firehose(processed_body)

        if processed_body.count_for_firehose >= MAX_BATCH_SIZE:
            put_records_to_firehose_stream(
                event_metadata.FIREHOSE_STREAM_NAME,
                processed_body.record_batch,
                event_metadata.firehose_client,
                attempts_made=0,
                max_attempts=FIREHOSE_MAX_ATTEMPTS,
            )
            processed_body.count_for_firehose = 0
            processed_body.record_batch = []

    return processed_body


def process_for_firehose(processed_body: ProcessedBody):
    message_line = json.dumps(processed_body.reingest_json)
    message_bytes = gzip.compress(message_line.encode())
    new_record_batch = [*processed_body.record_batch]
    new_record_batch.append({"Data": message_bytes})

    processed_body.count_for_firehose += 1
    processed_body.record_batch = new_record_batch

    return processed_body
