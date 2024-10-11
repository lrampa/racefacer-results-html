import socketio
import asyncio
from aiohttp import web
import datetime
import json

sio = socketio.AsyncServer(cors_allowed_origins='*')
app = web.Application()
sio.attach(app)

# Read content of test-message.json file to a string
with open('test-message.json', 'r') as file:
    message = file.read()
    # convert to json
    message = json.loads(message)

@sio.event
async def connect(sid, environ):
    print('Client connected:', sid)

@sio.event
async def disconnect(sid):
    print('Client disconnected:', sid)

async def emit_periodic_message():
    while True:
        timestamp = datetime.datetime.now().isoformat()
        # message = f"Server time: {timestamp}"
        # print(f"Emitting: {message}")
        # await sio.emit('message', {'data': message})
        # await sio.emit('kartarenacheb', {'data': message})
        await sio.emit('kartarenacheb', message)
        await asyncio.sleep(60)

async def start_background_tasks(app):
    app['emit_task'] = asyncio.create_task(emit_periodic_message())

async def cleanup_background_tasks(app):
    app['emit_task'].cancel()
    await app['emit_task']

app.on_startup.append(start_background_tasks)
app.on_cleanup.append(cleanup_background_tasks)

if __name__ == '__main__':
    web.run_app(app, port=8080)
