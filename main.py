import os
import click
import datetime
from datetime import datetime,timedelta
import requests

@click.command()
@click.option('--distance', '-d', default='10', help='Distance (in kilometers) from the center point')
@click.option('--days-back', '-b', default='30', help='Number of days back to search for observations')
@click.option('--mode', '-m', default='all', help='Mode of operation: all birds or unique birds (from last 24 hours)')

def unique_birds(distance, days_back, mode):

    # Get the eBird API key from the environment variable.
    ebirdKey = os.environ['EBIRDAPI']

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
    response = requests.get(ebird_url, headers={'X-eBirdApiToken': ebirdKey}, params=params)

    # If the request was successful, print the bird observations
    if response.status_code == 200:
        data = response.json()
        
        # ALL observations
        if mode.lower() == 'all':    
            for obs in data:
                print(obs['speciesCode'], obs['comName'], obs['obsDt'], obs['locName'])

        # Unique observations (if bird today has not seen in last 30 days)
        elif mode.lower() == 'unique':
            unique_birds = set()
            for obs in data:
                species_code = obs['speciesCode']
                observation_date = datetime.strptime(obs['obsDt'], '%Y-%m-%d %H:%M')
                today = datetime.now().date()
                if (species_code not in unique_birds) and (today - observation_date.date()) <= timedelta(days=1):
                    last_observation_date = datetime.now() - timedelta(days=30)
                    if species_code not in unique_birds and observation_date <= last_observation_date:
                        unique_birds.add(species_code)
                        print(obs['comName'], obs['obsDt'], obs['locName'])
        else:
            print('Error: mode must be "all" or "unique". Run --help for more information.')
    else:
        print('Error:', response.status_code)

if __name__ == '__main__':
    unique_birds()