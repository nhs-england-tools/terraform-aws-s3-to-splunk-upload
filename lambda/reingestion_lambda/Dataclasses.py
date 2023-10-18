from dataclasses import dataclass, field
from botocore.client import BaseClient


@dataclass
class ProcessedBody:
    count_for_s3: int = 0
    count_for_firehose: int = 0
    s3_payload: dict = field(default_factory=dict)
    record_batch: list = field(default_factory=list)
    reingest_json: dict = field(default_factory=dict)
    sent_to_s3: bool = False


@dataclass
class ProcessedMessageLine:
    reingest_json: dict = field(default_factory=dict)
    s3_payload: dict = field(default_factory=dict)
    count_for_s3: int = 0
    sent_to_s3: bool = False


@dataclass
class EventMetadata:
    FIREHOSE_STREAM_NAME: str
    firehose_client: BaseClient
    REGION: str
    MAX_INGEST: int
    bucket_name: str
    key: str


@dataclass
class FieldsToReingest:
    reingest: int
    origin_bucket_name: str


@dataclass
class MessageMetadata:
    fields_to_reingest: FieldsToReingest
    source: str = "aws:reingested"
    sourcetype: str = "aws:firehose"
