import socketio
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken
from .models import Match, Room

User = get_user_model()

# Tạo Socket.IO server instance
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',  # Production: thay bằng domain cụ thể
    logger=True,
    engineio_logger=True
)

# Dictionary lưu mapping user_id -> sid và room_id -> [sid1, sid2]
connected_users = {}  # {user_id: sid}
room_sessions = {}    # {room_id: [sid1, sid2]}
game_states = {}      # {room_id: {'board': [[]], 'current_turn': 'X', 'match_id': int}}


def authenticate_user(token: str):
    """Xác thực JWT token và trả về user."""
    try:
        access_token = AccessToken(token)
        user_id = access_token['user_id']
        user = User.objects.get(id=user_id)
        return user
    except Exception:
        return None


@sio.event
async def connect(sid, environ, auth):
    """Xử lý khi client kết nối."""
    token = auth.get('token') if auth else None
    if not token:
        return False  # Từ chối kết nối
    
    user = authenticate_user(token)
    if not user:
        return False
    
    connected_users[user.id] = sid
    print(f"User {user.username} (ID: {user.id}) connected with SID: {sid}")
    return True


@sio.event
async def disconnect(sid):
    """Xử lý khi client ngắt kết nối."""
    # Tìm user_id từ sid
    user_id = None
    for uid, s in connected_users.items():
        if s == sid:
            user_id = uid
            break
    
    if user_id:
        # Tìm room mà user đang ở
        room_id = None
        for rid, sids in room_sessions.items():
            if sid in sids:
                room_id = rid
                break
        
        if room_id:
            try:
                room = await Room.objects.aget(id=room_id)
                
                # Nếu host rời
                if room.host_id == user_id:
                    # Thông báo cho player_2 (nếu có)
                    if room.player_2_id and room.player_2_id in connected_users:
                        await sio.emit('room_closed', {
                            'message': 'Chủ phòng đã thoát'
                        }, room=connected_users[room.player_2_id])
                    
                    # Xóa phòng
                    await room.adelete()
                    print(f"Đã xóa phòng {room_id} vì host thoát.")
                
                # Nếu player_2 rời
                elif room.player_2_id == user_id:
                    room.player_2 = None
                    room.status = Room.Status.WAITING
                    await room.asave(update_fields=['player_2', 'status'])
                    
                    # Thông báo cho host
                    if room.host_id in connected_users:
                        await sio.emit('player_left', {
                            'message': 'Đối thủ đã thoát'
                        }, room=connected_users[room.host_id])
                    
                    print(f"Phòng {room_id} đã trở về trạng thái chờ.")
                
                # Dọn session
                if room_id in room_sessions:
                    room_sessions[room_id] = [s for s in room_sessions[room_id] if s != sid]
                    if not room_sessions[room_id]:
                        del room_sessions[room_id]
                        
            except Room.DoesNotExist:
                pass
        
        del connected_users[user_id]
        print(f"User ID {user_id} disconnected")


@sio.event
async def join_room(sid, data):
    """Xử lý khi user join phòng."""
    room_id = data.get('room_id')
    
    # Tìm user từ sid
    user_id = None
    for uid, s in connected_users.items():
        if s == sid:
            user_id = uid
            break
    
    if not user_id:
        await sio.emit('error', {'message': 'Unauthorized'}, room=sid)
        return
    
    try:
        room = await Room.objects.select_related('host', 'player_2').aget(id=room_id)
        
        # Nếu là host
        if room.host_id == user_id:
            await sio.enter_room(sid, f"room_{room_id}")
            if room_id not in room_sessions:
                room_sessions[room_id] = []
            if sid not in room_sessions[room_id]:
                room_sessions[room_id].append(sid)
            
            await sio.emit('joined_room', {
                'room_id': room_id,
                'role': 'host',
                'player_symbol': 'X',
                'room_name': room.room_name,
                'board_size': room.board_size,
                'status': room.status,
                'player_count': room.current_players
            }, room=sid)
        
        # Nếu là player_2
        elif room.player_2_id == user_id:
            await sio.enter_room(sid, f"room_{room_id}")
            if room_id not in room_sessions:
                room_sessions[room_id] = []
            if sid not in room_sessions[room_id]:
                room_sessions[room_id].append(sid)
            
            # Khởi tạo game state khi đủ 2 người
            if room_id not in game_states:
                # Tạo Match trong DB
                match = await Match.objects.acreate(
                    player_x=room.host,
                    player_o=room.player_2,
                    room=room,
                    board_size=room.board_size,
                    current_turn='X'
                )
                
                # Tạo bàn cờ trống
                size = room.board_size
                board = [[None for _ in range(size)] for _ in range(size)]
                game_states[room_id] = {
                    'board': board,
                    'current_turn': 'X',
                    'match_id': match.id,
                    'board_size': size
                }
            
            # Thông báo cho cả phòng
            await sio.emit('player_joined', {
                'username': room.player_2.username,
                'player_count': 2
            }, room=f"room_{room_id}")
            
            await sio.emit('joined_room', {
                'room_id': room_id,
                'role': 'player_2',
                'player_symbol': 'O',
                'room_name': room.room_name,
                'board_size': room.board_size,
                'opponent': room.host.username,
                'status': room.status
            }, room=sid)
            
            # Thông báo game bắt đầu
            await sio.emit('game_start', {
                'current_turn': 'X',
                'board_size': room.board_size,
                'match_id': game_states[room_id]['match_id']
            }, room=f"room_{room_id}")
        else:
            await sio.emit('error', {'message': 'Bạn không ở trong phòng này'}, room=sid)
            
    except Room.DoesNotExist:
        await sio.emit('error', {'message': 'Phòng không tồn tại'}, room=sid)


@sio.event
async def leave_room(sid, data):
    """Xử lý khi user rời phòng."""
    room_id = data.get('room_id')
    
    # Tìm user từ sid
    user_id = None
    for uid, s in connected_users.items():
        if s == sid:
            user_id = uid
            break
    
    if not user_id:
        return
    
    await sio.leave_room(sid, f"room_{room_id}")
    
    # Xử lý logic tương tự disconnect
    try:
        room = await Room.objects.aget(id=room_id)
        
        if room.host_id == user_id:
            await sio.emit('room_closed', {
                'message': 'Chủ phòng đã thoát'
            }, room=f"room_{room_id}")
            await room.adelete()
        
        elif room.player_2_id == user_id:
            room.player_2 = None
            room.status = Room.Status.WAITING
            await room.asave(update_fields=['player_2', 'status'])
            
            await sio.emit('player_left', {
                'message': 'Đối thủ đã thoát'
            }, room=f"room_{room_id}")
        
        if room_id in room_sessions:
            room_sessions[room_id] = [s for s in room_sessions[room_id] if s != sid]
            if not room_sessions[room_id]:
                del room_sessions[room_id]
                
    except Room.DoesNotExist:
        pass


@sio.event
async def make_move(sid, data):
    """Xử lý khi người chơi đánh cờ."""
    from .game_logic import check_winner, is_board_full, validate_move
    
    room_id = data.get('room_id')
    row = data.get('row')
    col = data.get('col')
    
    if room_id not in game_states:
        await sio.emit('error', {'message': 'Game chưa bắt đầu'}, room=sid)
        return
    
    # Tìm user
    user_id = None
    for uid, s in connected_users.items():
        if s == sid:
            user_id = uid
            break
    
    if not user_id:
        await sio.emit('error', {'message': 'Unauthorized'}, room=sid)
        return
    
    try:
        room = await Room.objects.select_related('host', 'player_2').aget(id=room_id)
        game = game_states[room_id]
        
        # Xác định player symbol
        if room.host_id == user_id:
            player_symbol = 'X'
        elif room.player_2_id == user_id:
            player_symbol = 'O'
        else:
            await sio.emit('error', {'message': 'Bạn không ở trong phòng này'}, room=sid)
            return
        
        # Kiểm tra lượt
        if game['current_turn'] != player_symbol:
            await sio.emit('error', {'message': 'Chưa đến lượt của bạn'}, room=sid)
            return
        
        # Validate move
        if not validate_move(game['board'], row, col):
            await sio.emit('error', {'message': 'Nước đi không hợp lệ'}, room=sid)
            return
        
        # Thực hiện nước đi
        game['board'][row][col] = player_symbol
        
        # Kiểm tra thắng
        winner = None
        game_over = False
        
        if check_winner(game['board'], row, col, player_symbol):
            winner = player_symbol
            game_over = True
        elif is_board_full(game['board']):
            game_over = True  # Hòa
        
        # Chuyển lượt
        game['current_turn'] = 'O' if player_symbol == 'X' else 'X'
        
        # Broadcast nước đi
        await sio.emit('move_made', {
            'row': row,
            'col': col,
            'player': player_symbol,
            'current_turn': game['current_turn']
        }, room=f"room_{room_id}")
        
        # Xử lý kết thúc game
        if game_over:
            from .elo_calculator import calculate_elo_change, calculate_elo_draw
            
            match = await Match.objects.aget(id=game['match_id'])
            match.board_state = [[game['board'][r][c] for c in range(game['board_size'])] for r in range(game['board_size'])]
            match.end_time = timezone.now()
            
            if winner:
                match.winner = room.host if winner == 'X' else room.player_2
                # Cập nhật ELO/stats
                winner_user = await User.objects.aget(id=match.winner_id)
                loser_user = await User.objects.aget(id=(room.player_2_id if winner == 'X' else room.host_id))
                
                # Tính toán ELO change dựa trên công thức chuẩn
                winner_change, loser_change = calculate_elo_change(winner_user.elo, loser_user.elo)
                
                winner_user.wins += 1
                winner_user.elo += winner_change
                loser_user.losses += 1
                loser_user.elo = max(0, loser_user.elo + loser_change)  # loser_change là số âm
                
                await winner_user.asave(update_fields=['wins', 'elo'])
                await loser_user.asave(update_fields=['losses', 'elo'])
            else:
                # Hòa
                host_user = await User.objects.aget(id=room.host_id)
                player2_user = await User.objects.aget(id=room.player_2_id)
                
                # Tính toán ELO change cho trường hợp hòa
                host_change, player2_change = calculate_elo_draw(host_user.elo, player2_user.elo)
                
                host_user.draws += 1
                host_user.elo += host_change
                player2_user.draws += 1
                player2_user.elo += player2_change
                
                await host_user.asave(update_fields=['draws', 'elo'])
                await player2_user.asave(update_fields=['draws', 'elo'])
            
            await match.asave()
            
            await sio.emit('game_over', {
                'winner': winner,
                'result': 'win' if winner else 'draw',
                'match_id': match.id
            }, room=f"room_{room_id}")
            
            # Dọn dẹp
            del game_states[room_id]
            room.status = Room.Status.FULL
            await room.asave(update_fields=['status'])
            
    except (Room.DoesNotExist, Match.DoesNotExist):
        await sio.emit('error', {'message': 'Lỗi hệ thống'}, room=sid)


@sio.event
async def send_message(sid, data):
    """Xử lý chat trong phòng."""
    room_id = data.get('room_id')
    message = data.get('message')
    
    # Tìm username
    user_id = None
    for uid, s in connected_users.items():
        if s == sid:
            user_id = uid
            break
    
    if user_id:
        try:
            user = await User.objects.aget(id=user_id)
            await sio.emit('new_message', {
                'username': user.username,
                'message': message
            }, room=f"room_{room_id}")
        except User.DoesNotExist:
            pass
