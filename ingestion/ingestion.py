import requests
import json
import os
import datetime
import boto3
from dotenv import load_dotenv

load_dotenv()

def fetch_data_and_send_to_s3():

    BUCKET_NAME = os.environ.get('S3_BRONZE_BUCKET')
    API_KEY = os.environ.get('API_KEY')

    s3_client=boto3.client('s3')

    secrets_path='../secrets/apiKey.txt'
    if not os.path.exists(secrets_path):
        print("API file is not in secrets/")
        return
    
    VEHICLES_URL = 'https://dane.um.warszawa.pl/api/action/get_ztm_lokalizacja_pojazdow'
    STOPS_URL = 'https://dane.um.warszawa.pl/api/action/get_ztm_przystanki_komunikacji_miejskiej'
    TRAFFIC_DISRUPTIONS = 'https://dane.um.warszawa.pl/api/action/get_bin_utrudnienia_drogowe'

    now =datetime.datetime.now()
    timestamp_str =now.strftime('%Y%m%d_%H%M%S')
    partition_date = now.strftime('%Y-%m-%d')

    headers = {
        'accept':'application/json',
        'Content-Type':'application/json',
        'Authorization':API_KEY,
    }
    os.makedirs("../data",exist_ok=True)

    try:
        print('Requesting Vehicles ')
        response_buses =requests.post(VEHICLES_URL,headers=headers,json={'type':1},timeout=30)
        response_buses.raise_for_status()
        buses_data=response_buses.json()

        response_trams =requests.post(VEHICLES_URL,headers=headers,json={'type':2},timeout=30)
        response_trams.raise_for_status()
        trams_data=response_trams.json()

        vehicles = {
            'buses':buses_data,
            'trams':trams_data,
        }

        # with open('../data/sample_vehicles.json','w',encoding='utf-8') as f: # to save localy
        #     json.dump(vehicles,f,indent=2,ensure_ascii=False)
             

        s3_key = f'vehicles/load_date={partition_date}/vehicles_{timestamp_str}.json'
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=json.dumps(vehicles,ensure_ascii=False,indent=2),
            ContentType='application/json'
        )
        print('Vehicles done')

    except requests.exceptions.RequestException as e:
        print('Vehicle Request failed: ',e)

    try:
        print('Requesting Stops')

        response_stops=requests.post(STOPS_URL,headers=headers,json={},timeout=30)
        response_stops.raise_for_status()
        stops_data=response_stops.json()

        # with open('../data/sample_stops.json','w',encoding='utf-8') as f:
        #     json.dump(stops_data,f,ensure_ascii=False,indent=2)

        s3_key = f'stops/load_date={partition_date}/stops_{timestamp_str}.json'
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=json.dumps(stops_data,ensure_ascii=False,indent=2),
            ContentType='application/json'
        )
        print('Stops done')

    except requests.exceptions.RequestException as e:
        print('Stops Request failed: ',e)


    try:
        print('Requesting traffic')

        response_traffic = requests.post(TRAFFIC_DISRUPTIONS,headers=headers,json={},timeout=30)
        response_traffic.raise_for_status()
        traffic_data = response_traffic.json()

        # with open('../data/sample_traffic.json','w',encoding='utf-8') as f:
        #     json.dump(traffic_data,f,indent=2,ensure_ascii=False)

        s3_key = f'traffic/load_date={partition_date}/traffic_{timestamp_str}.json'
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=json.dumps(traffic_data,ensure_ascii=False,indent=2),
            ContentType='application/json'
        )
        print('Traffic done')

    except requests.exceptions.RequestException as e:
        print('Traffic Request failed: ',e)

if __name__ == '__main__':
    fetch_data_and_send_to_s3()