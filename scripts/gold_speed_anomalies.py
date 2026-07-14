import sys
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
from pyspark.sql import SparkSession
from pyspark.sql.window import Window
import pyspark.sql.functions as F


args = getResolvedOptions(sys.argv,['JOB_NAME','SILVER_BUCKET','GOLD_BUCKET'])

session = SparkContext()
glueContext = GlueContext(session)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'],args)


spark.conf.set('spark.sql.sources.partitionOverwriteMode','dynamic')

SILVER_BUCKET = args['SILVER_BUCKET']
GOLD_BUCKET = args['GOLD_BUCKET']
R=6731000

df_vehicles = spark.read.parquet(f's3://{SILVER_BUCKET}/vehicles/')

windowSpec =Window.partitionBy('VehicleNumber','year','month','day').orderBy('Time')

lat1 = F.radians(F.lag("Lat", 1).over(windowSpec))
lon1 = F.radians(F.lag("Lon", 1).over(windowSpec))
lat2 = F.radians("Lat")
lon2 = F.radians("Lon")

dlat = lat2 - lat1
dlon = lon2 - lon1

a = F.sin(dlat / 2)**2 + F.cos(lat1) * F.cos(lat2) * F.sin(dlon / 2)**2
c = 2 * F.atan2(F.sqrt(a), F.sqrt(1 - a))
distance_meters = R * c

time_diff_seconds = F.col('Time').cast('long') - F.lag('Time',1).over(windowSpec).cast('long')

speed_kmh= (distance_meters/F.when(time_diff_seconds>0,time_diff_seconds).otherwise(None))*3.6

df_speed = (
    df_vehicles
    .withColumn('distance_moved_m',distance_meters)
    .withColumn('time_diff_s',time_diff_seconds)
    .withColumn('speed_kmh',F.when(speed_kmh < 120,speed_kmh).otherwise(None))
    .filter(F.col("speed_kmh").isNotNull())
)

gold_speed_anomalies = (
    df_speed
    .groupBy('type','year','month',"day",'hour')
    .agg(
        F.round(F.avg('speed_kmh'),2).alias("avg_speed_kmh"),
        F.round(F.min("speed_kmh"),2).alias('min_speed_kmh'),
        F.round(F.max('speed_kmh'),2).alias('max_speed_kmh'),
        F.count("VehicleNumber").alias("counted_vehicles")
    )
)

gold_speed_anomalies.write.mode("overwrite").partitionBy("year", "month", "day").parquet(f"s3://{GOLD_BUCKET}/line_speed_anomalies/")

job.commit()