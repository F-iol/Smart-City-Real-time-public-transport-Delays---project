import sys
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
from pyspark.sql import SparkSession
import pyspark.sql.functions as F
from pyspark.sql.window import Window

args = getResolvedOptions(sys.argv, ['JOB_NAME', 'SILVER_BUCKET', 'GOLD_BUCKET'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")

SILVER_BUCKET = args['SILVER_BUCKET']
GOLD_BUCKET = args['GOLD_BUCKET']

df_vehicle = spark.read.format('parquet').load(f's3://{SILVER_BUCKET}/vehicles/')


fleet_df = (
    df_vehicle
    .groupBy('brigade','type','year','month','day','hour')
    .agg(
        F.countDistinct('vehiclenumber').alias('active_vehicles'),
    )
    .withColumn('total_vehicles_per_hour',F.sum('active_vehicles').over(Window.partitionBy('brigade','type')))
    .withColumn('active_vehicles_pcn',F.round((F.col('active_vehicles')/F.col('total_vehicles_per_hour'))*100,2))
)

fleet_df.write.mode('overwrite').partitionBy('year','month','day').parquet(F's3://{GOLD_BUCKET}/active_fleet')

job.commit()