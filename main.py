import os
# import click
import datetime
from datetime import datetime,timedelta
import logging
import requests
import threading
import time


# @click.command()
# @click.option('--distance', '-d', default='10', help='Distance (in kilometers) from the center point')
# @click.option('--days-back', '-b', default='30', help='Number of days back to search for observations')
# @click.option('--mode', '-m', default='unique', help='Mode of operation: all birds or unique birds (from last 24 hours)')


def unique_birds_fn(distance, days_back, mode, ebirdKey, NTFY_TOKEN):

    # Get the eBird API key from the environment variable.
    # ebirdKey = os.environ['EBIRDAPI']

    # Define the eBird API endpoint
    ebird_url = 'https://api.ebird.org/v2/data/obs/geo/recent'

    # Set the parameters for the API request
    params = {
        'lat': '38.9394',
        'lng': '-77.0312',
        'dist': int(distance), # in miles
        'back': int(days_back), # in days
        'includeProvisional': 'false', # only return observations that are final
        'maxResults': '10000'
    }

    # Make the API request and get the response
    try:
        response = requests.get(ebird_url, headers={'X-eBirdApiToken': ebirdKey}, params=params)
        # print("Response Code:", response.status_code)
        # print("Response Body:", response.text)
        # logging.info(f"Response: {response.text}")  
    except Exception as e:
        logging.error(f"Caught Exception: {e}")
        # print("Exception occurred:", e)
    except BaseException as be:
        logging.error(f"Caught BaseException: {be}")
        # print("Base Exception occurred:", be)

    # If the request was successful, print the bird observations
    if response.status_code == 200:
        data = response.json()
        
        # ALL observations
        if mode.lower() == 'all':    
            for obs in data:
                logging.info(f"{obs['speciesCode']}, {obs['comName']}, {obs['obsDt']}, {obs['locName']}")

        # Unique observations (if bird today has not seen in last 30 days)
        elif mode.lower() == 'unique':
            unique_birds_more_than_24_hours = set()
            unique_birds_today = set()
            for obs in data:
                species_code = obs['speciesCode']
                observation_date = datetime.strptime(obs['obsDt'], '%Y-%m-%d %H:%M')
                today = datetime.now().date()
                if (species_code not in unique_birds_more_than_24_hours) and (today - observation_date.date()) > timedelta(days=1): # Birds sightings over 24 hrs old
                    unique_birds_more_than_24_hours.add(species_code)
                    # logging.info(f"Sighted Bird over 24hrs ago: {obs['comName']}, {obs['obsDt']}, {obs['locName']}")


            for obs in data:
                species_code = obs['speciesCode']
                observation_date = datetime.strptime(obs['obsDt'], '%Y-%m-%d %H:%M')
                today = datetime.now().date()
                if (species_code not in unique_birds_more_than_24_hours) and (today - observation_date.date()) <= timedelta(days=1): # Birds in last 24 hrs
                    if (species_code not in unique_birds_today) and (today - observation_date.date()) <= timedelta(days=1):
                        unique_birds_today.add(species_code)
                        logging.info(f"Sighted Bird not seen in last 30 days: {obs['comName']}, {obs['obsDt']}, {obs['locName']}")

                        '''
                        # Send notification to NTFY
                        try:
                            requests.post('https://ntfy.sh/brandebird',
                                data=f"Sighted Bird not seen in last 30 days: {obs['comName']}, {obs['obsDt']}, {obs['locName']}",
                                headers={
                                    "Title": f"Unique Bird Sighting in Your Area",
                                    "Authorization": f"Bearer {NTFY_TOKEN}",
                                    "Tags": f"bird,ebird-sighting"
                                })
                        except Exception as e:
                            logging.error(f"Caught Exception: {e}")
                        except BaseException as be:
                            logging.error(f"Caught BaseException: {be}")
                        '''
        else:
            logging.error('Error: mode must be "all" or "unique". Run --help for more information.')
    else:
        logging.error(f'Error: {response.status_code}')

# def run_background_task(distance, days_back, mode):
def run_background_task():
    """Background task to check new posts and interact with the database."""
    
    while True:
        # unique_birds_fn(distance, days_back, mode)
        unique_birds_fn(distance=10,days_back=30,mode='unique',ebirdKey=os.environ['EBIRDAPI'], NTFY_TOKEN = os.environ["NTFY_TOKEN"])
        # time.sleep(86400) # Check 1x per day
        time.sleep(1)

def start_background_task():
    """Start the background task in a separate thread."""
    thread = threading.Thread(target=run_background_task)
    thread.daemon = True  # Daemon threads exit when the main program does
    thread.start()

if __name__ == '__main__':
    FORMAT = '%(asctime)s - %(message)s'
    logging.basicConfig(format=FORMAT, level=logging.INFO)
    # unique_birds_fn()
    start_background_task()  # Start the background task
    try:
        while True:
            time.sleep(1)  # Keep the main thread alive with minimal CPU usage.
    except KeyboardInterrupt:
        print("Program interrupted by user, exiting.")

