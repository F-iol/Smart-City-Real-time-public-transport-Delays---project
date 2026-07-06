import requests
import json
import os

def fetch_data():
    secrets_path='./secrets/apiKey.txt'
    if not os.path.exists(secrets_path):
        print("API file is not in secrets/")

    with open(secrets_path,'r') as f:
        API_KEY = f.read().strip()
        print(API_KEY)

    BASE_URL ='https://api.um.warszawa.pl/api/action/dbstore_get/'

    VEHICLES_URL = 'https://dane.um.warszawa.pl/api/action/get_ztm_lokalizacja_pojazdow'
    STOPS_URL = 'https://dane.um.warszawa.pl/api/action/get_ztm_przystanki_komunikacji_miejskiej'
    TRAFFIC_DISRUPTIONS = 'https://dane.um.warszawa.pl/api/action/get_bin_utrudnienia_drogowe'


    headers = {
        'accept':'application/json',
        'Content-Type':'application/json',
        'Authorization':API_KEY,
    }

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
        
        with open('sample_vehicles.json','w',encoding='utf-8') as f:
            json.dump(vehicles,f,indent=2,ensure_ascii=False)
            print('Vehicles done')
    except requests.exceptions.RequestException as e:
        print('Vehicle Request failed: ',e)

    try:
        print('Requesting Stops')

        response_stops=requests.post(STOPS_URL,headers=headers,json={},timeout=30)
        response_stops.raise_for_status()
        stops_data=response_stops.json()

        with open('sample_stops.json','w',encoding='utf-8') as f:
            json.dump(stops_data,f,ensure_ascii=False,indent=2)
            print("Stops done")

    except requests.exceptions.RequestException as e:
        print('Stops Request failed: ',e)


    try:
        print('Requesting traffic')

        response_traffic = requests.post(TRAFFIC_DISRUPTIONS,headers=headers,json={},timeout=30)
        response_traffic.raise_for_status()
        traffic_data = response_traffic.json()

        with open('sample_traffic','w',encoding='utf-8') as f:
            json.dump(traffic_data,f,indent=2,ensure_ascii=False)
            print('Traffic done')

    except requests.exceptions.RequestException as e:
        print('Traffic Request failed: ',e)

if __name__ == '__main__':
    fetch_data()