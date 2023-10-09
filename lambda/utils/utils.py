def put_records_to_firehose_stream(
    stream_name, records, client, attempts_made, max_attempts
):
    failed_records = []
    codes = []
    err_msg = ""
    firehose_response = None

    try:
        firehose_response = client.put_record_batch(
            DeliveryStreamName=stream_name, Records=records
        )
    except Exception as e:
        failed_records = records
        err_msg = str(e)

    if firehose_response and firehose_response["FailedPutCount"] > 0:
        for idx, event_response in enumerate(firehose_response["RequestResponses"]):
            if event_response.get("ErrorCode") == None:
                continue

            codes.append(event_response["ErrorCode"])
            failed_records.append(records[idx])

        codes_string = ", ".join(codes)
        err_msg = f"Individual error codes: {codes_string}"

    if len(failed_records) > 0:
        if attempts_made + 1 < max_attempts:
            print(
                f"Some records failed while calling PutRecordBatch to Firehose stream, retrying. {err_msg}"
            )
            put_records_to_firehose_stream(
                stream_name, failed_records, client, attempts_made + 1, max_attempts
            )
        else:
            raise RuntimeError(
                f"Could not put records after {max_attempts} attempts. {err_msg}"
            )
