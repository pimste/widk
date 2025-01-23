from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, join_room, leave_room, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['SERVER_NAME'] = '0.0.0.0:4000'
socketio = SocketIO(app)

rooms = {} 

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('join_room')
def join_game(data):
    room = data['room']
    player = data['player']
    join_room(room)

    if room not in rooms:
        rooms[room] = {
            "current_odds": 0,
            "previous_odds": 0,
            "player_numbers": {},
            "players": [],
            "result": None
        }

    if player not in rooms[room]['players']:
        rooms[room]['players'].append(player)

    emit('room_joined', {"room": room, "player": player}, room=room)

@socketio.on('leave_room')
def leave_game(data):
    room = data['room']
    player = data['player']
    leave_room(room)

    if room in rooms:
        if player in rooms[room].get("players", []):
            rooms[room]['players'].remove(player)
        if player in rooms[room].get("player_numbers", {}):
            del rooms[room]['player_numbers'][player]

    emit('player_left', {"room": room, "player": player}, room=room)

@socketio.on('set_odds')
def set_odds(data):
    room = data['room']
    odds = data['odds']

    if room in rooms:
        current_odds = rooms[room]['current_odds']
        previous_odds = rooms[room]['previous_odds']

        if odds > previous_odds and previous_odds != 0:
            emit('odds_set', {"error": True, "message": "De kans mag niet hoger zijn dan de vorige ronde."}, room=request.sid)
            return

        rooms[room]['previous_odds'] = current_odds  
        rooms[room]['current_odds'] = odds
        rooms[room]['player_numbers'] = {} 
        rooms[room]['result'] = None
        emit('odds_set', {"error": False, "odds": odds}, room=room)

@socketio.on('submit_number')
def submit_number(data):
    room = data['room']
    player = data['player']
    number = data['number']

    if room in rooms:
        game_state = rooms[room]
        game_state['player_numbers'][player] = number

        if len(game_state['player_numbers']) == len(game_state['players']):
            numbers = list(game_state['player_numbers'].values())
            players = list(game_state['player_numbers'].keys())

            if len(set(numbers)) < len(numbers):
                matches = [p for p in players if numbers.count(game_state['player_numbers'][p]) > 1]
                game_state['result'] = {"result": "match", "players": matches}
            else:
                game_state['result'] = {"result": "no_match", "players": []}

            emit('result', game_state['result'], room=room)

@socketio.on('reset_game')
def reset_game(data):
    room = data['room']

    if room in rooms:
        rooms[room]['previous_odds'] = rooms[room]['current_odds']  
        rooms[room]['current_odds'] = 0
        rooms[room]['player_numbers'] = {}
        rooms[room]['result'] = None
        emit('game_reset', {}, room=room)

import os

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 4000))  # Default to 5000 for local testing
    socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)

