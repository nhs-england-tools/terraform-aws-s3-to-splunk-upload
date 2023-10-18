import json
import base64
from reingestion_lambda.process_message import process_message
from reingestion_lambda.Dataclasses import (
    EventMetadata,
    ProcessedBody,
)


def process_body(
    object_body,
    event_metadata: EventMetadata,
):
    processed_body = ProcessedBody()

    for line in object_body.split("\n"):
        if len(line) == 0:
            continue

        message = get_message_from_line(line)
        processed_body = process_message(processed_body, message, event_metadata)

    return processed_body


def get_message_from_line(line):
    batch = json.loads(line)
    base64_message = batch["rawData"]
    base64_bytes = base64_message.encode()
    message_bytes = base64.b64decode(base64_bytes)
    message = message_bytes.decode()
    return message
