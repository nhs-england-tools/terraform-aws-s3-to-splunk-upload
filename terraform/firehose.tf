resource "aws_kms_key" "ssm_key" {
  description             = "KMS Key for parameter store"
  deletion_window_in_days = local.kms_key_deletion_duration
  enable_key_rotation     = true
}
resource "aws_ssm_parameter" "splunk_secrets" {
  name   = "audit-log-splunk-secrets"
  type   = "SecureString"
  key_id = aws_kms_key.ssm_key.id
  value = jsonencode({
    HEC_Endpoint = var.splunk_hec_endpoint
    HEC_Token    = var.splunk_hec_token
  })
}

resource "aws_kinesis_firehose_delivery_stream" "audit_logs_stream" {
  name        = "audit_logs_delivery_stream"
  destination = "splunk"

  s3_configuration {
    role_arn           = aws_iam_role.audit_logs_firehose_role.arn
    bucket_arn         = aws_s3_bucket.audit_logs_splashback.arn
    buffer_size        = 10
    compression_format = "GZIP"
  }

  splunk_configuration {
    hec_endpoint               = jsondecode(aws_ssm_parameter.splunk_secrets.value)["HEC_Endpoint"]
    hec_token                  = jsondecode(aws_ssm_parameter.splunk_secrets.value)["HEC_Token"]
    hec_acknowledgment_timeout = 600
    hec_endpoint_type          = "Event"
    s3_backup_mode             = "FailedEventsOnly"
    retry_duration             = 300

    processing_configuration {
      enabled = "true"

      processors {
        type = "Lambda"

        parameters {
          parameter_name  = "LambdaArn"
          parameter_value = "${aws_lambda_function.transformation_lambda.arn}:$LATEST"
        }
        parameters {
          parameter_name  = "RoleArn"
          parameter_value = aws_iam_role.transformation_lambda_invoke_role.arn
        }
      }
    }

    cloudwatch_logging_options {
      enabled         = true
      log_group_name  = aws_cloudwatch_log_group.audit_logs_firehose_log_group.name
      log_stream_name = aws_cloudwatch_log_stream.audit_logs_firehose_log_stream.name
    }
  }
}