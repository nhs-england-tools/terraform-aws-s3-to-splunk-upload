resource "aws_iam_role" "lambda_role" {
  name               = "audit_logs_lambda_role"
  assume_role_policy = file("${path.module}/policies/assume-role-lambda.json")
}

resource "aws_iam_role_policy_attachment" "lambda_basic_policy_attachment" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_role.name
}

data "template_file" "audit_logs_lambda_policy_template" {
  template = file("${path.module}/policies/audit-log-lambda.json")
  vars = {
    audit_logs_splashback_kms        = aws_kms_key.audit_logs_splashback_key.arn
    audit_logs_bucket_kms            = aws_kms_key.audit_logs_bucket_key.arn
    audit_logs_bucket_arn            = aws_s3_bucket.audit_logs_bucket.arn
    audit_logs_splashback_bucket_arn = aws_s3_bucket.audit_logs_splashback.arn
    audit_logs_firehose_arn          = aws_kinesis_firehose_delivery_stream.audit_logs_stream.arn
  }
}

resource "aws_iam_policy" "audit_logs_lambda_iam_policy" {
  name   = "audit_logs_lambda_iam_policy"
  policy = data.template_file.audit_logs_lambda_policy_template.rendered
}

resource "aws_iam_role_policy_attachment" "audit_logs_lambda_iam_policy_attachment" {
  policy_arn = aws_iam_policy.audit_logs_lambda_iam_policy.arn
  role       = aws_iam_role.lambda_role.name
}


resource "aws_iam_role" "transformation_lambda_invoke_role" {
  name               = "audit_logs_transformation_lambda_invoke_role"
  assume_role_policy = file("${path.module}/policies/assume-role-firehose.json")

}

data "template_file" "transformation_lambda_invoke_policy_template" {
  template = file("${path.module}/policies/lambda-invoke.json")
  vars = {
    transformation_lambda_arn = aws_lambda_function.transformation_lambda.arn
    audit_logs_splashback_kms = aws_kms_key.audit_logs_splashback_key.arn
  }
}

resource "aws_iam_policy" "transformation_lambda_invoke_policy" {
  name   = "audit_logs_transformation_lambda_invoke_policy"
  policy = data.template_file.transformation_lambda_invoke_policy_template.rendered

}

resource "aws_iam_role_policy_attachment" "transformation_lambda_invoke_policy" {
  role       = aws_iam_role.transformation_lambda_invoke_role.name
  policy_arn = aws_iam_policy.transformation_lambda_invoke_policy.arn
}


resource "aws_iam_role" "audit_logs_firehose_role" {
  name               = "audit_logs_firehose_role"
  assume_role_policy = file("${path.module}/policies/assume-role-firehose.json")
}

data "template_file" "audit_logs_firehose_policy_template" {
  template = file("${path.module}/policies/audit-log-firehose.json")
  vars = {
    audit_logs_splashback_arn            = aws_s3_bucket.audit_logs_splashback.arn
    audit_logs_splashback_kms_arn        = aws_kms_key.audit_logs_splashback_key.arn
    audit_logs_firehose_log_group_arn    = aws_cloudwatch_log_group.audit_logs_firehose_log_group.arn
    audit_logs_firehose_log_stream_arn   = aws_cloudwatch_log_stream.audit_logs_firehose_log_stream.arn
    audit_logs_transformation_lambda_arn = aws_lambda_function.transformation_lambda.arn
  }
}

resource "aws_iam_policy" "audit_logs_firehose_policy" {
  name   = "audit_logs_firehose_policy"
  policy = data.template_file.audit_logs_firehose_policy_template.rendered

}

resource "aws_iam_role_policy_attachment" "audit_logs_firehose_policy" {
  role       = aws_iam_role.audit_logs_firehose_role.name
  policy_arn = aws_iam_policy.audit_logs_firehose_policy.arn
}
