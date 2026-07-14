import sys
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
from pyspark.sql import SparkSession
import pyspark.sql.functions as F

args = getResolvedOptions(sys.argv, ['JOB_NAME', 'SILVER_BUCKET', 'GOLD_BUCKET'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")
spark.conf.set("spark.sql.crossJoin.enabled", "true")
SILVER_BUCKET = args['SILVER_BUCKET']
GOLD_BUCKET =   args['GOLD_BUCKET']

df_vehicles = spark.read.parquet(f"s3://{SILVER_BUCKET}/vehicles/")
df_traffic = spark.read.parquet(f"s3://{SILVER_BUCKET}/traffic/")

df_traffic = (
            df_traffic
            .withColumn('start_date',F.to_timestamp(F.col('start_date'),'yyyy-MM-dd HH:mm:ss'))
            .withColumn('end_date',F.to_timestamp(F.col("end_date"),'yyyy-MM-dd HH:mm:ss'))
            )

df_vehicles = df_vehicles.withColumn('lat_1',F.col('lat'))
df_vehicles = df_vehicles.withColumn('lon_1',F.col('lon'))
df_traffic = df_traffic.withColumn('lat_2',F.col('lat'))
df_traffic = df_traffic.withColumn('lon_2',F.col('lon'))


time_difference_seconds = F.col("Time").cast("long") - F.col("start_date").cast("long")
join_con = (
    (df_vehicles['Time']>= df_traffic['start_date'])&
    (df_vehicles['Time'] <= df_traffic['end_date'])&
    (time_difference_seconds >= 0) & (time_difference_seconds<= 259200))

df_joined = (
    df_vehicles.join
    (df_traffic,
    on=join_con)
)

R = 6371000
lat1 = F.radians(df_joined["lat_1"])
lon1 = F.radians(df_joined["lon_1"])
lat2 = F.radians(df_joined["lat_2"])
lon2 = F.radians(df_joined["lon_2"])

dlat = lat2 - lat1
dlon = lon2 - lon1
a = F.sin(dlat / 2)**2 + F.cos(lat1) * F.cos(lat2) * F.sin(dlon / 2)**2
c = 2 * F.atan2(F.sqrt(a), F.sqrt(1 - a))
distance_meters = R * c

df_joined = (df_joined
    .withColumn('distance_to_incident_m',distance_meters)
    .filter(F.col('distance_to_incident_m')<=300))

gold_incidents= (
    df_joined
    .groupBy(
        F.col('id').alias('incident_id'),
        F.col('content').alias('incident_description'),
        F.col('type'),
        F.col('year'),
        F.col('month'),
        F.col('day'),
        F.col('hour')
    )
    .agg(
        F.countDistinct('vehiclenumber').alias('delayed_vehicles_count'),
        F.countDistinct('lines').alias('affected_lines')
    )
)

gold_incidents.write.mode('overwrite').partitionBy("year",'month','day').parquet(f's3://{GOLD_BUCKET}/delayed_by_traffic/')

job.commit()