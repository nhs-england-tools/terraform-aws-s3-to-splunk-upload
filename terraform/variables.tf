variable "splunk_hec_token" {
  type        = string
  description = "The token used to authenticate with the Splunk HEC endpoint."
  sensitive   = true
}

variable "splunk_hec_endpoint" {
  type        = string
  description = "The Splunk HEC endpoint to send data to. This must be the event endpoint type."
  sensitive   = true
  validation {
    condition     = can(regex("\\/event$", var.splunk_hec_endpoint))
    error_message = "This module only supports sending logs to the /event HEC endpoint."
  }
}

variable "audit_logs_bucket_name" {
  type        = string
  description = "The name of the S3 bucket that stores the logs."
}

variable "splunk_index" {
  type        = string
  description = "The Splunk index to send data to."
}

variable "splunk_host" {
  type        = string
  description = "The host value to use when sending data to Splunk."
}

variable "splunk_source" {
  type        = string
  description = "The source value to use when sending data to Splunk."
}

variable "splunk_sourcetype" {
  type        = string
  description = "The sourcetype value to use when sending data to Splunk."
}

variable "timestamp_key" {
  type        = string
  description = "The object key where the timestamp of the log event is located."
}

variable "retention_mode" {
  type        = string
  description = "The retention mode to use for the S3 bucket. Valid values are COMPLIANCE and GOVERNANCE."
  default     = "GOVERNANCE"
}

variable "retention_period" {
  type        = number
  description = "The retention period to use for the S3 bucket. This value is in years."
  default     = 1
}

variable "lifecycle_expiration" {
  type        = number
  description = "The expiration value for the lifecycle policy. This value is in days."
  default     = 365
}
