from flask import Flask, render_template
from turbo_flask import Turbo
import threading
import socketio
import logging
import time
from datetime import datetime


ws_url = 'https://live.racefacer.com:3123/socket.io/'
# ws_url = 'http://localhost:8080'
ws_channel = 'kartarenacheb'
# ws_channel = 'denizkarting'


logging.basicConfig(
    filename="socketio.log",
    # format="%(asctime)s %(levelname)s %(name)s %(message)s",
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.DEBUG,
)


app = Flask(__name__)
turbo = Turbo(app)

sio = socketio.Client()


# Global variable to store the latest message
latest_message = None

def start_socketio_client():

    @sio.event
    def connect():
        logging.info(f"Connection to ws server {ws_url} established")
        sio.emit('join', ws_channel)

    @sio.event
    def connect_error(data):
        logging.error(f"Cannot connect to ws server {ws_url}")
        
    @sio.event
    def disconnect():
        logging.info(f"Disconnected from server {ws_url}")

    # @sio.event
    def message(data):
        logging.info(f"message received: {ws_channel} - {data}")

        sorted_results = process_data(data)

        global latest_message
        latest_message = sorted_results
        with app.app_context():
            turbo.push(turbo.update(render_template('_message.html', message=latest_message), 'messages'))

    @sio.on('*')
    def any_event(event, sid, data):
        logging.info(f"event received: {event} - {sid} - {data}")

    sio.on(ws_channel, message)
    sio.connect(ws_url)
    sio.wait()


@app.template_filter('elapsed_time')
def elapsed_time_filter(timestamp):
    if timestamp is None:
        return "N/A"
    now = datetime.now().timestamp()
    elapsed = now - timestamp
    minutes, seconds = divmod(int(elapsed), 60)
    return f"{minutes:02d}:{seconds:02d}"


@app.template_filter('format_time')
def format_time_filter(timestamp):
    if timestamp is None:
        return "N/A"
    formatted = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')
    return f"{formatted}"


@app.route("/")
def index():    
    # Find out, if thread named "ws_client" exists
    threads = threading.enumerate()
    if not any(thread.name == "ws_client" for thread in threads):
        logging.debug('before thread start')
        thread = threading.Thread(name="ws_client", target=start_socketio_client)
        thread.daemon = True
        thread.start()
        logging.debug('after thread start')

    data = fetch_data()
    results = process_data(data)
    global latest_message
    latest_message = results  # Reset the message when the page is loaded

    return render_template('index.html', message=latest_message)

def fetch_data():
    # Fetch json response from https://live.racefacer.com/ajax/live-data?slug=denizkarting
    import requests
    import json
    url = f"https://live.racefacer.com/ajax/live-data?slug={ws_channel}"
    response = requests.get(url)
    data = json.loads(response.text)
    return data


def process_data(data):
    results = []

    if 'runs' in data['data']:
        # iterate over data['data']['runs'] and create a tuple for each run
        for run in data['data']['runs']:
            results.append({
                'kart': run.get('kart', ''), # "kart": "18",
                'total_laps': run.get('total_laps', ''), # "total_laps": 8,
                'last_time': run.get('last_time', 0), # "last_time": "1:10.574",
                'last_time_raw': run.get('last_time_raw', 0), # "last_time_raw": 70574,
                'last_passing': run.get('last_passing', 0), # "last_passing": 1721900723855,
                'current_lap_start_timestamp': run.get('current_lap_start_timestamp', -1), # "current_lap_start_timestamp": 1721900755,
                'current_lap_start_microtimestamp': run.get('current_lap_start_microtimestamp', -1) # "current_lap_start_microtimestamp": 1721900726428,
            })

    # get current timestamp in seconds
    current_timestamp = time.time()
    current_timestamp_formatted = datetime.fromtimestamp(current_timestamp).strftime('%H:%M:%S')

    # Find results where the current_lap_start_timestamp is more than 60 seconds old
    filtered_results = []
    for result in results:
        current_lap_start_timestamp_formatted = datetime.fromtimestamp(result['current_lap_start_timestamp']).strftime('%H:%M:%S')

        diff = int(current_timestamp - result['current_lap_start_timestamp'])
        minutes, seconds = divmod(diff, 60)
        diff_formatted = f"{minutes:02}:{seconds:02}"

        logging.info(f"Adding result:   kart {result['kart']}, {current_timestamp_formatted} - {current_lap_start_timestamp_formatted} = {diff_formatted}")
        result['diff_formatted'] = diff_formatted
        filtered_results.append(result)

    # Sort the filtered results by the current_lap_start_timestamp in ascending order
    sorted_results = sorted(filtered_results, key=lambda x: x['current_lap_start_timestamp'])

    # Print the sorted results
    for result in sorted_results:
        logging.info(f"kart: {result['kart']}, total_laps: {result['total_laps']}, last_time: {result['last_time']}, last_time_raw: {result['last_time_raw']}, last_passing: {result['last_passing']}, current_lap_start_timestamp: {result['current_lap_start_timestamp']}, current_lap_start_microtimestamp: {result['current_lap_start_microtimestamp']}")
    
    return sorted_results


if __name__ == '__main__':
    app.run()
