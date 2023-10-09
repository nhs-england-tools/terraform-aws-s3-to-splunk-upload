locals {
  kms_key_deletion_duration = 7
  splashback_bucket_name    = "${var.audit_logs_bucket_name}-splashback"
}

locals {
  all_lambdas = fileset("${path.module}/../lambda/", "**")

  transformation_lambda_included_files = fileset("${path.module}/../lambda/", "{transformation_lambda,utils}/**")
  transformation_lambda_excluded_files = [for f in local.all_lambdas : f if !contains(local.transformation_lambda_included_files, f)]

  reingestion_lambda_included_files = fileset("${path.module}/../lambda/", "{reingestion_lambda,utils}/**")
  reingestion_lambda_excluded_files = [for f in local.all_lambdas : f if !contains(local.reingestion_lambda_included_files, f)]

  s3_to_firehose_included_files = fileset("${path.module}/../lambda/", "s3_to_firehose/**")
  s3_to_firehose_excluded_files = [for f in local.all_lambdas : f if !contains(local.s3_to_firehose_included_files, f)]
}
