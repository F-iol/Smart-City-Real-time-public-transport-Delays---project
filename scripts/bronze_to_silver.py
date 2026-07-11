import sys
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
from pyspark.sql import SparkSession
import pyspark.sql.functions as F

args = getResolvedOptions(sys.argv,['JOB_NAME', 'BRONZE_BUCKET', 'SILVER_BUCKET'])

session = SparkContext.getOrCreate()
gluecontext=GlueContext(session)

spark=gluecontext.spark_session

job = Job(gluecontext)
job.init(args['JOB_NAME'],args)

BRONZE_BUCKET = args['BRONZE_BUCKET']
SILVER_BUCKET = args['SILVER_BUCKET']

LAT_MIN,LAT_MAX = 52.05,52.40
LON_MIN,LON_MAX = 20.70,21.45

df_vehicles = spark.read.option("multiLine",'true').json(f"s3://{BRONZE_BUCKET}/vehicles/*/*.json")
df_stops = spark.read.option("multiLine",'true').json(f"s3://{BRONZE_BUCKET}/stops/*/*.json")
df_traffic = spark.read.option("multiLine",'true').json(f"s3://{BRONZE_BUCKET}/traffic/*/*.json")


buses_df =df_vehicles.select(F.explode('buses').alias('buses'))
buses_df = buses_df.select('buses.*').withColumn('Type',F.lit('Bus'))

trams_df =df_vehicles.select(F.explode('trams').alias('trams'))
trams_df = trams_df.select("trams.*").withColumn('Type',F.lit('Tram'))

vehicle_df =buses_df.unionByName(trams_df)
vehicle_df = vehicle_df.withColumn('Time',F.to_timestamp(F.col('Time'),'yyyy-MM-dd HH:mm:ss'))

vehicle_df = vehicle_df.filter(
    (F.col('Lat') >= LAT_MIN) & (F.col('Lat') <= LAT_MAX) &
    (F.col("Lon") >= LON_MIN) & (F.col('Lon') <= LON_MAX)
)

vehicle_df = vehicle_df.filter(
    (F.col('Time') >= F.current_timestamp() - F.expr('INTERVAL 2 HOURS'))
)

vehicle_df = (
    vehicle_df
    .withColumn('year', F.date_format(F.col('Time'), 'yyyy'))
    .withColumn('month', F.date_format(F.col('Time'), 'MM'))
    .withColumn('day', F.date_format(F.col('Time'), 'dd'))
    .withColumn('hour', F.date_format(F.col('Time'), 'HH'))
)

vehicle_df.write.mode('append').partitionBy('year', 'month', 'day', 'hour').parquet(f's3://{SILVER_BUCKET}/vehicles/')


stops_df = df_stops.withColumn('id', F.monotonically_increasing_id())
stops_df = stops_df.select('id', F.explode('values').alias('item'))
stops_df = stops_df.select('id', F.col('item.key').alias('key'), F.col('item.value').alias('value'))

stops_df = stops_df.groupBy('id').pivot('key').agg(F.first('value'))

stops_df = (stops_df
    .withColumn('lat', F.col('szer_geo').cast('Double'))
    .withColumn('lon', F.col('dlug_geo').cast('Double'))
    .filter(
        (F.col("lat").between(LAT_MIN, LAT_MAX)) &
        (F.col('lon').between(LON_MIN, LON_MAX))
    )
    .select(
        F.col('id_ulicy'),
        F.col('nazwa_zespolu'),
        F.col('slupek'),
        F.col("zespol"),
        F.col('lat'),
        F.col('lon')
    )
)

stops_df.write.mode('overwrite').parquet(f's3://{SILVER_BUCKET}/stops/')


traffic_df = df_traffic.withColumn('id', F.monotonically_increasing_id())
traffic_df = traffic_df.select('*', F.explode('geo').alias('geo_group'))
traffic_df = traffic_df.select('*', F.explode('geo_group').alias('geomerty'))

traffic_df = traffic_df.select(
    '*',
    F.col('geomerty.geomType').alias('geoType'),
    F.col('geomerty.latlngs').alias('latlngs')
)

traffic_df = (
    traffic_df
    .select('*', F.posexplode('latlngs').alias('point_order', 'point'))
    .select('*', F.col('point.lat').cast('Double').alias('lat'),
                 F.col('point.lng').cast('Double').alias('lon'))
).drop('geo_group', 'geomerty', 'latlngs', 'point', 'geo')

traffic_df = traffic_df.filter(
    (F.col('lat').between(LAT_MIN, LAT_MAX)) &
    (F.col('lon').between(LON_MIN, LON_MAX))
)

traffic_df = (
    traffic_df
    .withColumn('content',F.explode('content'))
    .withColumn('detour_type',F.explode('detour_type'))
    .withColumn('streets',F.explode('streets'))
)


traffic_df.write.mode('overwrite').parquet(f's3://{SILVER_BUCKET}/traffic/')

job.commit()