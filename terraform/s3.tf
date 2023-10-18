data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "audit_logs_bucket" {
  bucket = var.audit_logs_bucket_name

  object_lock_enabled = true


  tags = {
    "Name" = var.audit_logs_bucket_name
  }
}

resource "aws_kms_key" "audit_logs_bucket_key" {
  description             = "KMS Key for S3 audit logs Bucket"
  deletion_window_in_days = local.kms_key_deletion_duration
  enable_key_rotation     = true
}

resource "aws_kms_alias" "audit_logs_bucket_key_alias" {
  name          = "alias/${var.audit_logs_bucket_name}-key"
  target_key_id = aws_kms_key.audit_logs_bucket_key.key_id
}

resource "aws_s3_bucket_server_side_encryption_configuration" "audit_logs_bucket_encrypt_config" {
  bucket = aws_s3_bucket.audit_logs_bucket.id
  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.audit_logs_bucket_key.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "audit_logs_bucket_public_access_config" {
  bucket = aws_s3_bucket.audit_logs_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_object_lock_configuration" "audit_logs_bucket_object_lock_config" {
  bucket = aws_s3_bucket.audit_logs_bucket.id

  rule {
    default_retention {
      mode  = var.retention_mode
      years = var.retention_period
    }
  }
}

resource "aws_s3_bucket_versioning" "audit_logs_bucket_versioning" {
  bucket = aws_s3_bucket.audit_logs_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "audit_logs_bucket_lifecycle_config" {
  bucket = aws_s3_bucket.audit_logs_bucket.id
  rule {
    id     = "${var.audit_logs_bucket_name}-s3-bucket-lifecycle"
    status = "Enabled"
    filter {
      prefix = ""
    }
    expiration {
      days = var.lifecycle_expiration
    }
  }
}


data "template_file" "audit_logs_bucket_policy_template" {
  template = file("${path.module}/policies/audit-log-bucket.json")
  vars = {
    account_id                   = data.aws_caller_identity.current.account_id
    aws_s3_bucket_arn            = aws_s3_bucket.audit_logs_bucket.arn
    audit_logs_firehose_role_arn = aws_iam_role.audit_logs_firehose_role.arn
  }
}

resource "aws_s3_bucket_policy" "audit_logs_bucket_policy" {
  bucket = aws_s3_bucket.audit_logs_bucket.bucket
  policy = data.template_file.audit_logs_bucket_policy_template.rendered
}

resource "aws_s3_bucket_notification" "audit_logs_bucket_notification" {
  bucket = aws_s3_bucket.audit_logs_bucket.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.s3_to_firehose_lambda.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".gz"
  }

  depends_on = [aws_lambda_permission.audit_logs_bucket_permission]
}

resource "aws_s3_bucket" "audit_logs_splashback" {
  bucket = local.splashback_bucket_name
  tags = {
    "Name" = local.splashback_bucket_name
  }
}

resource "aws_kms_key" "audit_logs_splashback_key" {
  description             = "KMS Key for S3 audit logs splashback bucket"
  deletion_window_in_days = local.kms_key_deletion_duration
  enable_key_rotation     = true
}

resource "aws_kms_alias" "audit_logs_splashback_key_alias" {
  name          = "alias/${local.splashback_bucket_name}-key"
  target_key_id = aws_kms_key.audit_logs_splashback_key.key_id
}

resource "aws_s3_bucket_server_side_encryption_configuration" "audit_logs_splashback_encryption" {
  bucket = aws_s3_bucket.audit_logs_splashback.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.audit_logs_splashback_key.arn
      sse_algorithm     = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "audit_logs_splashback_public_access_config" {
  bucket = aws_s3_bucket.audit_logs_splashback.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

data "template_file" "splashback_bucket_policy_template" {
  template = file("${path.module}/policies/audit-log-bucket.json")
  vars = {
    account_id                   = data.aws_caller_identity.current.account_id
    aws_s3_bucket_arn            = aws_s3_bucket.audit_logs_splashback.arn
    audit_logs_firehose_role_arn = aws_iam_role.audit_logs_firehose_role.arn
  }
}

resource "aws_s3_bucket_policy" "splashback_bucket_policy" {
  bucket = aws_s3_bucket.audit_logs_splashback.id
  policy = data.template_file.splashback_bucket_policy_template.rendered
}
resource "aws_s3_bucket_notification" "audit_logs_splashback_bucket_notification" {
  bucket = aws_s3_bucket.audit_logs_splashback.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.splashback_retry_lambda.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "splunk-failed/"
  }

  depends_on = [aws_lambda_permission.splashback_bucket_permission]
}
