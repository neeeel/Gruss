__author__ = 'neil'

__author__ = 'neil'

import time
import gruss
import threading
from flask import Flask, render_template
from flask_socketio import SocketIO

async_mode = None

if async_mode is None:
    try:
        import eventlet
        async_mode = 'eventlet'
    except ImportError:
        pass

if async_mode is None:
        async_mode = 'threading'

print("selected async mode is " ,async_mode)

if async_mode == 'eventlet':
    import eventlet
    eventlet.monkey_patch()

app = Flask(__name__)
app.debug = True
eventlet.monkey_patch()
socketio = SocketIO(app, async_mode=async_mode)
thread = None
count = 0

def background_thread():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        time.sleep(10)
        count += 1
        #socketio.emit('my response',
                     # {'data': 'Server generated event', 'count': count},
                     # namespace='/test')
        socketio.emit("my event",{"data":"test","count":count},namespace="/test")
        d = gruss.get_prices_as_list()
        #socketio.emit("prices",d,namespace="/test")

@app.route("/")
def base():
    d = gruss.get_prices_as_list()
    meetings = gruss.get_meetings()
    races = gruss.get_win_markets(meetings[0])
    return render_template("index.html",meetings = meetings,races = races)

@socketio.on("connect",namespace = "/test")
def ws_connect():
    print("received connection")
    global thread
    if thread is None:
        thread = threading.Thread(target = background_thread)
        thread.start()
    d = gruss.get_prices_as_list()
    socketio.emit("prices",d,namespace = "/test")

@socketio.on('disconnect request', namespace='/test')
def disconnect_request():
    socketio.disconnect()

@socketio.on('request movers',namespace="/test")
def request_movers(data):
    print("received movers request event",data)
    try:
        val = int(data["data"])
    except Exception as e:
        return
    movers = gruss.get_movers(val)
    socketio.emit("movers",movers,namespace="/test")

@socketio.on('meeting_change', namespace='/test')
def meeting_request(data):
    print("received meeting change event",data)
    races = gruss.get_win_markets(data["data"])
    print("races from database",races)
    socketio.emit("races",races,namespace="/test")

@socketio.on("my event",namespace = "/test")
def ws_myevent(data):
    print(data)


socketio.run(app)