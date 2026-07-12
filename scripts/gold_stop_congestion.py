import sys
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
from pyspark.sql import SparkSession
import pyspark.sql.functions as F

args = getResolvedOptions(sys.argv,['JOB_NAME','SILVER_BUCKET','GOLD_BUCKET'])

session = SparkContext()
glueContext = GlueContext(session)
spark = glueContext.spark_session
job =  Job(glueContext)
job.init(args['JOB_NAME'],args)

spark.conf.set('spark.sql.sources.partitionOverwriteMode','dynamic')

SILVER_BUCKET = args['SILVER_BUCKET']
GOLD_BUCKET = args['GOLD_BUCKET']
R = 6371000


df_vehicles = spark.read.parquet(f's3://{SILVER_BUCKET}/vehicles/')
df_stops = spark.read.parquet(f's3://{SILVER_BUCKET}/stops/')

df_vehicles_min = df_vehicles.withColumn('Time_Minute',F.date_trunc('minute',F.col('Time')))

lat1 = F.radians(df_vehicles_min['Lat'])
lon1 = F.radians(df_vehicles_min['Lon'])
lat2 = F.radians(df_stops['lat'])
lon2 = F.radians(df_stops['lon'])

dlat = lat2-lat1    
dlon=lon2-lon1

# haversine eq
a = F.sin(dlat / 2)**2 + F.cos(lat1) * F.cos(lat2) * F.sin(dlon / 2)**2
c = 2 * F.atan2(F.sqrt(a), F.sqrt(1 - a))
distance_meters = R * c

congestion_df = (
    df_vehicles_min.join(df_stops)
    .withColumn('distance_to_stop_meters',distance_meters)
    .filter(F.col('distance_to_stop_meters') <=60)
)

gold_stop_congestion = (
    congestion_df
    .groupBy(
        F.col('zespol').alias('stop_team_id'),
        F.col('nazwa_zespolu').alias('stop_name'),
        F.col('year'),
        F.col("month"),
        F.col('day'),
        F.col('hour')
    )
    .agg(
        F.countDistinct("vehiclenumber").alias('unique_vehicle_count'),
        F.round(F.avg('distance_to_stop_meters'),2).alias('avg_distance_meters')
    )
)


gold_stop_congestion.write.mode('overwrite').partitionBy('year','month','day').parquet(f's3://{GOLD_BUCKET}//stop_congestion')
job.commit()