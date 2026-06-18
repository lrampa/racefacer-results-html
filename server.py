from flask import Flask, render_template
from turbo_flask import Turbo
import threading
import socketio
import logging
import time
import json
import os
from datetime import datetime


WS_URL = 'https://live.racefacer.com:3123/socket.io/'
# WS_URL = 'http://localhost:8080'
WS_CHANNEL = 'kartarenacheb'
# WS_CHANNEL = 'denizkarting'
RACEFACER_API_URL = 'https://live.racefacer.com/ajax/live-data'
KART_NAME_PREFIX = 'kart'
WS_THREAD_NAME = 'ws_client'
DEBUG_LOG = 'socketio.log'
JSONL_LOG = os.path.join('socketio', 'socketio.log')


logging.basicConfig(
    filename=DEBUG_LOG,
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.DEBUG,
)


app = Flask(__name__)
turbo = Turbo(app)

sio = socketio.Client()

os.makedirs('socketio', exist_ok=True)


def write_jsonl(data):
    record = {'log_ts': datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]}
    record['data'] = data.get('data', data) if isinstance(data, dict) else data
    with open(JSONL_LOG, 'a') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')


# Global variable to store the latest message
latest_message = None

def start_socketio_client():

    @sio.event
    def connect():
        logging.info(f"Connection to ws server {WS_URL} established")
        sio.emit('join', WS_CHANNEL)

    @sio.event
    def connect_error(data):
        logging.error(f"Cannot connect to ws server {WS_URL}")
        
    @sio.event
    def disconnect():
        logging.info(f"Disconnected from server {WS_URL}")

    def message(data):
        logging.info(f"message received: {WS_CHANNEL} - {data}")
        write_jsonl(data)

        sorted_results = process_data(data)

        global latest_message
        latest_message = sorted_results
        with app.app_context():
            turbo.push(turbo.update(render_template('_message.html', message=latest_message), 'messages'))

    @sio.on('*')
    def any_event(event, sid, data):
        logging.info(f"event received: {event} - {sid} - {data}")

    sio.on(WS_CHANNEL, message)
    sio.connect(WS_URL)
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
    threads = threading.enumerate()
    if not any(thread.name == WS_THREAD_NAME for thread in threads):
        logging.debug('before thread start')
        thread = threading.Thread(name=WS_THREAD_NAME, target=start_socketio_client)
        thread.daemon = True
        thread.start()
        logging.debug('after thread start')

    data = fetch_data()
    results = process_data(data)
    global latest_message
    latest_message = results

    return render_template('index.html', message=latest_message)

def fetch_data():
    import requests
    url = f"{RACEFACER_API_URL}?slug={WS_CHANNEL}"
    response = requests.get(url)
    data = json.loads(response.text)
    return data


def process_data(data):
    results = []

    if 'runs' in data['data']:
        for run in data['data']['runs']:
            # TODO *********************************************************************
            # TODO *** Remove this part for races, where drivers has name filled in!
            # TODO *** This ignores results from inner electric track mixed in to race
            # TODO *** results.
            # TODO *********************************************************************
            # if not run.get('kart', '').lstrip().lower().startswith(KART_NAME_PREFIX):
            #     logging.info(f"Skipping run: {run.get('kart', '')}")
            #     continue

            results.append({
                'kart': run.get('kart', ''),
                'total_laps': run.get('total_laps', ''),
                'last_time': run.get('last_time', 0),
                'last_time_raw': run.get('last_time_raw', 0),
                'last_passing': run.get('last_passing', 0),
                'current_lap_start_timestamp': run.get('current_lap_start_timestamp', -1),
                'current_lap_start_microtimestamp': run.get('current_lap_start_microtimestamp', -1),
            })

    current_timestamp = time.time()
    current_timestamp_formatted = datetime.fromtimestamp(current_timestamp).strftime('%H:%M:%S')

    filtered_results = []
    for result in results:
        current_lap_start_timestamp_formatted = datetime.fromtimestamp(result['current_lap_start_timestamp']).strftime('%H:%M:%S')

        diff = int(current_timestamp - result['current_lap_start_timestamp'])
        minutes, seconds = divmod(diff, 60)
        diff_formatted = f"{minutes:02}:{seconds:02}"

        logging.info(f"Adding result:   kart {result['kart']}, {current_timestamp_formatted} - {current_lap_start_timestamp_formatted} = {diff_formatted}")
        result['diff_formatted'] = diff_formatted
        filtered_results.append(result)

    sorted_results = sorted(filtered_results, key=lambda x: x['current_lap_start_timestamp'])

    for result in sorted_results:
        logging.info(f"kart: {result['kart']}, total_laps: {result['total_laps']}, last_time: {result['last_time']}, last_time_raw: {result['last_time_raw']}, last_passing: {result['last_passing']}, current_lap_start_timestamp: {result['current_lap_start_timestamp']}, current_lap_start_microtimestamp: {result['current_lap_start_microtimestamp']}")
    
    return sorted_results


if __name__ == '__main__':
    app.run()
