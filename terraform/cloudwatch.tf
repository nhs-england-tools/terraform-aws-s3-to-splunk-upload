resource "aws_cloudwatch_log_group" "s3_to_firehose_lambda_log_group" {
  name              = "/aws/lambda/audit_logs_s3_to_firehose_lambda"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "splashback_lambda_log_group" {
  name              = "/aws/lambda/audit_logs_splashback_retry_lambda"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "transformation_lambda_log_group" {
  name              = "/aws/lambda/audit_logs_transformation_lambda"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "audit_logs_firehose_log_group" {
  name = "/aws/kinesisfirehose/audit_logs_delivery_stream"
}

resource "aws_cloudwatch_log_stream" "audit_logs_firehose_log_stream" {
  name           = "audit_logs_stream"
  log_group_name = aws_cloudwatch_log_group.audit_logs_firehose_log_group.name
}

