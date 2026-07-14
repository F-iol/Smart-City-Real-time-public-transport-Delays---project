terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws={
        source = "hashicorp/aws"
        version = "~>5.0"
    }
  }
}


provider "aws" {
    region = var.location
  
}

## buckets

resource "aws_s3_bucket" "bronze" {
    bucket ="${var.project_name}-bronze-${var.suffix}"
    force_destroy = true
}

resource "aws_s3_bucket" "silver" {
    bucket = "${var.project_name}-silver-${var.suffix}"
    force_destroy = true
}


resource "aws_s3_bucket" "glue_config" {
  bucket = "${var.project_name}-glue-config-${var.suffix}"
  force_destroy = true  
  
}

resource "aws_s3_bucket" "gold" {
    bucket = "${var.project_name}-gold-${var.suffix}"
    force_destroy = true
  
}

## catalog

resource "aws_glue_catalog_database" "smart_city_catalog" {
    name = "${var.project_name}-catalog-${var.suffix}"

  
}
# IAM ROLES

resource "aws_iam_role" "glue_service_role" {
    name = "${var.project_name}-glue-service-role-${var.suffix}"

    assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "glue.amazonaws.com"
      }
    }]
  })
  
}

resource "aws_iam_policy" "glue_s3_access" {
    name = "${var.project_name}-glue-s3-acess-${var.suffix}"
    policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.bronze.arn,
          "${aws_s3_bucket.bronze.arn}/*",
          aws_s3_bucket.silver.arn,
          "${aws_s3_bucket.silver.arn}/*",
          aws_s3_bucket.glue_config.arn,
          "${aws_s3_bucket.glue_config.arn}/*",
          aws_s3_bucket.gold.arn,
          "${aws_s3_bucket.gold.arn}/*",
        ]
      }
    ]
  })
  
}

resource "aws_iam_role_policy_attachment" "glue_s3_attach" {
  role       = aws_iam_role.glue_service_role.name
  policy_arn = aws_iam_policy.glue_s3_access.arn
}

resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

## Crawlers


resource "aws_glue_crawler" "silver_crawler" {
    database_name = aws_glue_catalog_database.smart_city_catalog.name
    name="${var.project_name}-silver-crawler-${var.suffix}"
    role=aws_iam_role.glue_service_role.arn 
    
    s3_target {
      path="s3://${aws_s3_bucket.silver.bucket}/"
    }
}

resource "aws_glue_crawler" "gold_crawler" {
    database_name = aws_glue_catalog_database.smart_city_catalog.name
    name="${var.project_name}-gold-crawler-${var.suffix}"
    role=aws_iam_role.glue_service_role.arn 
    
    s3_target {
      path="s3://${aws_s3_bucket.gold.bucket}/"
    }

    configuration = jsonencode({
    Version = 1.0
    Grouping = {
        TableLevelConfiguration = 2
    }
  })

}


## ETL 

resource "aws_glue_job" "bronze_to_silver" {
    name = "${var.project_name}-bronze-to-silver-${var.suffix}"
    role_arn = aws_iam_role.glue_service_role.arn
    glue_version="5.0"
    command{
      name = "glueetl"
      script_location = "s3://${aws_s3_bucket.glue_config.bucket}/scripts/bronze_to_silver.py"
      python_version = "3"
    }  

    number_of_workers = 2
    worker_type = "G.1X"

    timeout = 20

    default_arguments = {
      "--job-language" = "python"
      "--continuous-log-logGroup" = "/aws-glue/jobs/smart-city-silver"
      "--enable-continuous-cloudwatch-log" = "true"
      "--BRONZE_BUCKET" = aws_s3_bucket.bronze.bucket
      "--SILVER_BUCKET" = aws_s3_bucket.silver.bucket
    }
}

resource "aws_glue_job" "gold_stop_congestion" {
    name = "${var.project_name}-gold-stop-congestion-${var.suffix}"
    role_arn = aws_iam_role.glue_service_role.arn
    glue_version="5.0"
    command{
      name = "glueetl"
      script_location = "s3://${aws_s3_bucket.glue_config.bucket}/scripts/gold_stop_congestion.py"
      python_version = "3"
    }  

    number_of_workers = 2
    worker_type = "G.1X"

    timeout = 20

    default_arguments = {
      "--job-language" = "python"
      "--continuous-log-logGroup" = "/aws-glue/jobs/smart-city-silver"
      "--enable-continuous-cloudwatch-log" = "true"
      "--SILVER_BUCKET" = aws_s3_bucket.silver.bucket
      "--GOLD_BUCKET" = aws_s3_bucket.gold.bucket
    }
}

resource "aws_glue_job" "gold_active_fleet" {
    name = "${var.project_name}-gold-active-fleet-${var.suffix}"
    role_arn = aws_iam_role.glue_service_role.arn
    glue_version="5.0"
    command{
      name = "glueetl"
      script_location = "s3://${aws_s3_bucket.glue_config.bucket}/scripts/gold_active_fleet.py"
      python_version = "3"
    }  

    number_of_workers = 2
    worker_type = "G.1X"

    timeout = 20

    default_arguments = {
      "--job-language" = "python"
      "--continuous-log-logGroup" = "/aws-glue/jobs/smart-city-silver"
      "--enable-continuous-cloudwatch-log" = "true"
      "--SILVER_BUCKET" = aws_s3_bucket.silver.bucket
      "--GOLD_BUCKET" = aws_s3_bucket.gold.bucket
    }
}

resource "aws_glue_job" "gold_delayed_by_traffic" {
    name = "${var.project_name}-gold-delayed-by-traffic-${var.suffix}"
    role_arn = aws_iam_role.glue_service_role.arn
    glue_version="5.0"
    command{
      name = "glueetl"
      script_location = "s3://${aws_s3_bucket.glue_config.bucket}/scripts/gold_delayed_by_traffic.py"
      python_version = "3"
    }  

    number_of_workers = 2
    worker_type = "G.1X"

    timeout = 20

    default_arguments = {
      "--job-language" = "python"
      "--continuous-log-logGroup" = "/aws-glue/jobs/smart-city-silver"
      "--enable-continuous-cloudwatch-log" = "true"
      "--SILVER_BUCKET" = aws_s3_bucket.silver.bucket
      "--GOLD_BUCKET" = aws_s3_bucket.gold.bucket
    }
}

resource "aws_glue_job" "gold_speed_anomalies" {
    name = "${var.project_name}-gold-speed-anomalies-${var.suffix}"
    role_arn = aws_iam_role.glue_service_role.arn
    glue_version="5.0"
    command{
      name = "glueetl"
      script_location = "s3://${aws_s3_bucket.glue_config.bucket}/scripts/gold_speed_anomalies.py"
      python_version = "3"
    }  

    number_of_workers = 2
    worker_type = "G.1X"

    timeout = 20

    default_arguments = {
      "--job-language" = "python"
      "--continuous-log-logGroup" = "/aws-glue/jobs/smart-city-silver"
      "--enable-continuous-cloudwatch-log" = "true"
      "--SILVER_BUCKET" = aws_s3_bucket.silver.bucket
      "--GOLD_BUCKET" = aws_s3_bucket.gold.bucket
    }
}

### upload to aws

resource "aws_s3_object" "bronze_to_silver_script" {
    bucket = aws_s3_bucket.glue_config.bucket
    key="scripts/bronze_to_silver.py"
    source = "${path.module}/../scripts/bronze_to_silver.py"

    
    etag = filemd5("${path.module}/../scripts/bronze_to_silver.py")
}

resource "aws_s3_object" "gold_stop_congestion_script" {
    bucket = aws_s3_bucket.glue_config.bucket
    key= "scripts/gold_stop_congestion.py"
    source = "${path.module}/../scripts/gold_stop_congestion.py"

    etag = filemd5("${path.module}/../scripts/gold_stop_congestion.py")  
}

resource "aws_s3_object" "gold_active_fleet_script" {
    bucket = aws_s3_bucket.glue_config.bucket
    key="scripts/gold_active_fleet.py"
    source = "${path.module}/../scripts/gold_active_fleet.py"

    etag = filemd5("${path.module}/../scripts/gold_active_fleet.py")
}

resource "aws_s3_object" "gold_delayed_by_traffic_script" {
    bucket = aws_s3_bucket.glue_config.bucket
    key = "scripts/gold_delayed_by_traffic.py"
    source = "${path.module}/../scripts/gold_delayed_by_traffic.py"
    etag = filemd5("${path.module}/../scripts/gold_delayed_by_traffic.py")
}

resource "aws_s3_object" "gold_speed_anomalies" {
    bucket = aws_s3_bucket.glue_config.bucket
    key = "scripts/gold_speed_anomalies.py"
    source = "${path.module}/../scripts/gold_speed_anomalies.py"
    etag = filemd5("${path.module}/../scripts/gold_speed_anomalies.py")
}