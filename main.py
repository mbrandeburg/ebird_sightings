import os
import csv
# import click
import datetime
from datetime import datetime,timedelta
import logging
import requests
import threading
import time
from flask import Flask, render_template, request, send_from_directory, redirect
app = Flask(__name__)

'''
@click.command()
@click.option('--distance', '-d', default='10', help='Distance (in kilometers) from the center point')
@click.option('--days-back', '-b', default='30', help='Number of days back to search for observations')
@click.option('--mode', '-m', default='unique', help='Mode of operation: all birds or unique birds (from last 24 hours)')
'''

# Define the base directory for storing CSV files
base_directory = '/mnt/'
# base_directory = '/Users/matthewbrandeburg/dmc/tests/ebird/'

def read_lat_long_from_file(default_lat_long="38.9394,-77.0312"):
    try:
        with open(f'{base_directory}lat_long.txt', 'r') as file:
            lat_long = file.read().strip()
            return lat_long if lat_long else default_lat_long
    except FileNotFoundError:
        return default_lat_long

def write_lat_long_to_file(lat_long):
    with open(f'{base_directory}lat_long.txt', 'w') as file:
        file.write(lat_long)

def store_to_csv(set_name, data, base_filename='unique_birds'):
    csv_filename = f"{base_directory}{base_filename}_{set_name}.csv"
    # Check if the file exists and read species codes if it does
    existing_species = set()
    if os.path.exists(csv_filename):
        with open(csv_filename, mode='r', newline='') as file:
            reader = csv.reader(file)
            for row in reader:
                existing_species.add(row[0])  # Assuming species_code is in the first column

    # Write new species code if not found
    if data[0] not in existing_species:
        with open(csv_filename, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(data)
            logging.info(f"Added new unique bird to {csv_filename}: {data[1]}")
    else:
        logging.info(f"Species {data[0]} already exists in {csv_filename}. No addition made.")


def unique_birds_fn(distance, days_back, mode, ebirdKey, NTFY_TOKEN):

    # Get the eBird API key from the environment variable.
    # ebirdKey = os.environ['EBIRDAPI']

    # Define the eBird API endpoint
    ebird_url = 'https://api.ebird.org/v2/data/obs/geo/recent'

    current_lat_long = read_lat_long_from_file()
    lat = current_lat_long.split(',')[0]
    long = current_lat_long.split(',')[1]
    logging.info(f"Current Lat: {lat} | Long: {long}")


    # Set the parameters for the API request
    params = {
        # 'lat': '38.9394',
        # 'lng': '-77.0312',
        'lat':lat,
        'lng':long,
        'dist': int(distance), # in miles
        'back': int(days_back), # in days
        'includeProvisional': 'false', # only return observations that are final
        'maxResults': '10000'
    }

    # Make the API request and get the response
    try:
        response = requests.get(ebird_url, headers={'X-eBirdApiToken': ebirdKey}, params=params)
        # logging.info(f"Response: {response.text}")  
    except Exception as e:
        logging.error(f"Caught Exception: {e}")
    except BaseException as be:
        logging.error(f"Caught BaseException: {be}")

    # If the request was successful, print the bird observations
    if response.status_code == 200:
        data = response.json()
        # exit(0)

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
                try:
                    observation_date = datetime.strptime(obs['obsDt'], '%Y-%m-%d %H:%M')
                    today = datetime.now().date()
                    row_data = [species_code, obs['comName'], obs['obsDt'], obs['locName']]
                    
                    if (today - observation_date.date()) > timedelta(days=1):
                        if species_code not in unique_birds_more_than_24_hours:
                            unique_birds_more_than_24_hours.add(species_code)
                            store_to_csv('more_than_24_hours', row_data)

                    if (today - observation_date.date()) <= timedelta(days=1):
                        if species_code not in unique_birds_today:
                            unique_birds_today.add(species_code)
                            store_to_csv('today', row_data)
                            logging.info(f"Sighted Bird not seen in last 30 days: {obs['comName']}, {obs['obsDt']}, {obs['locName']}")
                            # exit(0)

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

                except Exception as e:
                    logging.error(f"Caught Exception: {e}")
                    logging.error(f"Error parsing date: {obs['obsDt']}")
                    continue
        else:
            logging.error('Error: mode must be "all" or "unique". Run --help for more information.')
    else:
        logging.error(f'Error: {response.status_code}')

def reset_csv_file():
    csv_filenames=['unique_birds_more_than_24_hours.csv','unique_birds_today.csv']
    for csv_filename in csv_filenames:
        full_path = f"{base_directory}{csv_filename}"
        try:
            os.remove(full_path)
            logging.info("CSV file reset successfully.")
        except OSError as e:
            logging.error(f"Error resetting CSV file: {e}")


def run_background_task():
    last_reset_time = time.time()
    while True:

        # Clear out CSV files every 25 hours
        current_time = time.time()
        if (current_time - last_reset_time) > 90000:  # 90000 seconds = 25 hours
            reset_csv_file()
            last_reset_time = current_time

        unique_birds_fn(distance=10,days_back=30,mode='unique',ebirdKey=os.environ['EBIRDAPI'], NTFY_TOKEN = os.environ["NTFY_TOKEN"])
        time.sleep(3600) # Check 1x per hour
        # time.sleep(10)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        new_lat = request.form['latitude']
        new_long = request.form['longitude']
        new_lat_long = f"{new_lat},{new_long}"
        write_lat_long_to_file(new_lat_long)
    current_lat_long = read_lat_long_from_file()
    lat = current_lat_long.split(',')[0]
    long = current_lat_long.split(',')[1]
    return render_template('index.html', lat=lat, long=long)

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
    app.run(host='0.0.0.0', port=8124)

    # Keep background task running
    try:
        while True:
            time.sleep(1)  # Keep the main thread alive with minimal CPU usage.
    except KeyboardInterrupt:
        print("Program interrupted by user, exiting.")

