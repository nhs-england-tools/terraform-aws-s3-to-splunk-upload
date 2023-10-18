data "archive_file" "s3_to_firehose_archive" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda/"
  excludes    = local.s3_to_firehose_excluded_files
  output_path = "${path.module}/lambda_archive/s3_to_firehose.zip"
}

data "archive_file" "reingestion_lambda_archive" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda/"
  excludes    = local.reingestion_lambda_excluded_files
  output_path = "${path.module}/lambda_archive/reingestion_lambda.zip"
}

data "archive_file" "transformation_lambda_archive" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda/"
  excludes    = local.transformation_lambda_excluded_files
  output_path = "${path.module}/lambda_archive/transformation_lambda.zip"
}

resource "aws_lambda_permission" "audit_logs_bucket_permission" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.s3_to_firehose_lambda.arn
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.audit_logs_bucket.arn
}

resource "aws_lambda_function" "s3_to_firehose_lambda" {
  filename         = "${path.module}/lambda_archive/s3_to_firehose.zip"
  function_name    = "audit_logs_s3_to_firehose_lambda"
  role             = aws_iam_role.lambda_role.arn
  handler          = "s3_to_firehose.s3_to_firehose.lambda_handler"
  runtime          = "python3.9"
  source_code_hash = filebase64sha256(data.archive_file.s3_to_firehose_archive.output_path)
  memory_size      = 256
  timeout          = 90
  environment {
    variables = {
      Firehose = aws_kinesis_firehose_delivery_stream.audit_logs_stream.name
    }
  }
}

resource "aws_lambda_permission" "splashback_bucket_permission" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.splashback_retry_lambda.arn
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.audit_logs_splashback.arn
}
resource "aws_lambda_function" "splashback_retry_lambda" {
  filename         = "${path.module}/lambda_archive/reingestion_lambda.zip"
  function_name    = "audit_logs_splashback_retry_lambda"
  role             = aws_iam_role.lambda_role.arn
  handler          = "reingestion_lambda.reingestion_lambda.lambda_handler"
  runtime          = "python3.9"
  source_code_hash = filebase64sha256(data.archive_file.reingestion_lambda_archive.output_path)
  memory_size      = 256
  timeout          = 90

  environment {
    variables = {
      Firehose   = aws_kinesis_firehose_delivery_stream.audit_logs_stream.name,
      Region     = "eu-west-2",
      max_ingest = 3
    }
  }
}


resource "aws_lambda_function" "transformation_lambda" {
  filename         = "${path.module}/lambda_archive/transformation_lambda.zip"
  function_name    = "audit_logs_transformation_lambda"
  role             = aws_iam_role.lambda_role.arn
  handler          = "transformation_lambda.transformation_lambda.lambda_handler"
  runtime          = "python3.9"
  source_code_hash = filebase64sha256(data.archive_file.transformation_lambda_archive.output_path)
  memory_size      = 256
  timeout          = 90
  environment {
    variables = {
      splunk_host       = var.splunk_host,
      splunk_source     = var.splunk_source,
      splunk_sourcetype = var.splunk_sourcetype,
      splunk_index      = var.splunk_index,
      timestamp_key     = var.timestamp_key
    }
  }
}
