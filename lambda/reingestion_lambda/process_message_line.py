import json
from dataclasses import asdict
from reingestion_lambda.Dataclasses import (
    EventMetadata,
    ProcessedMessageLine,
    FieldsToReingest,
    MessageMetadata,
)


def process_message_line(message_line, s3_payload, event_metadata: EventMetadata):
    processed_message_line = ProcessedMessageLine()

    json_data = json.loads(message_line)

    message_metadata = get_message_metadata(json_data, event_metadata.bucket_name)
    times_reingested = message_metadata.fields_to_reingest.reingest
    origin_bucket_name = message_metadata.fields_to_reingest.origin_bucket_name

    if times_reingested > event_metadata.MAX_INGEST:
        processed_message_line.count_for_s3 += 1
        processed_message_line.sent_to_s3 = True
        processed_message_line.s3_payload = package_for_s3(
            s3_payload, origin_bucket_name, json_data
        )
    else:
        processed_message_line.reingest_json = {
            "sourcetype": message_metadata.sourcetype,
            "source": message_metadata.source,
            "event": json_data["event"],
            "fields": asdict(message_metadata.fields_to_reingest),
        }

    return processed_message_line


def get_message_metadata(json_data, bucket_name):
    reingestion_fields_are_present = json_data.get("fields") != None

    if reingestion_fields_are_present:
        reingest = json_data["fields"]["reingest"]
        origin_bucket_name = json_data["fields"]["origin_bucket_name"]
        fields_to_reingest = FieldsToReingest(reingest + 1, origin_bucket_name)

    else:
        fields_to_reingest = FieldsToReingest(1, bucket_name)

    metadata = MessageMetadata(fields_to_reingest)

    if json_data.get("source") != None:
        metadata.source = json_data["source"]

    if json_data.get("sourcetype") != None:
        metadata.sourcetype = json_data["sourcetype"]

    return metadata


def package_for_s3(s3_payload, bucket_name, json_data):
    new_payload = {**s3_payload}

    bucket_name_not_in_payload = s3_payload.get(bucket_name) == None

    if bucket_name_not_in_payload:
        new_payload[bucket_name] = f"{json.dumps(json_data['event'])}\n"
    else:
        existing_payload = new_payload[bucket_name]
        new_payload[
            bucket_name
        ] = f"{existing_payload}{json.dumps(json_data['event'])}\n"

    return new_payload
