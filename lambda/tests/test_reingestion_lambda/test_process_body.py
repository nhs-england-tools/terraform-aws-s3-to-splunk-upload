import json
import base64
from reingestion_lambda.process_body import (
    process_body,
    get_message_from_line,
)
from reingestion_lambda.Dataclasses import ProcessedBody


def test_process_body(mocker):
    mock_data1 = "some data to be encoded"
    mock_data2 = "some more data to be encoded"

    mock_data1_encoded = mock_data1.encode()
    mock_data2_encoded = mock_data2.encode()

    mock_event1 = {"rawData": base64.b64encode(mock_data1_encoded).decode()}
    mock_event2 = {"rawData": base64.b64encode(mock_data2_encoded).decode()}

    input_line1 = json.dumps(mock_event1)
    input_line2 = json.dumps(mock_event2)
    input_body = f"{input_line1}\n{input_line2}\n"

    mocker.patch(
        "reingestion_lambda.process_body.process_message",
        return_value="success",
    )

    actual_output = process_body(input_body, {})

    assert actual_output == "success"


def test_process_body__empty_body():
    input_body = ""

    actual_processed = process_body(input_body, {})
    expected_processed_body = ProcessedBody()

    assert actual_processed == expected_processed_body


def test_get_message_from_line():
    mock_data = "some data to be encoded"
    mock_data_encoded = mock_data.encode()
    mock_event = {"rawData": base64.b64encode(mock_data_encoded).decode()}
    input_line = json.dumps(mock_event)

    expected_message = mock_data
    actual_message = get_message_from_line(input_line)
    assert actual_message == expected_message
