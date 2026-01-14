import socketio
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from .models import Room

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
                'room_name': room.room_name,
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
            
            # Thông báo cho cả phòng
            await sio.emit('player_joined', {
                'username': room.player_2.username,
                'player_count': 2
            }, room=f"room_{room_id}")
            
            await sio.emit('joined_room', {
                'room_id': room_id,
                'role': 'player_2',
                'room_name': room.room_name,
                'opponent': room.host.username,
                'status': room.status
            }, room=sid)
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
    room_id = data.get('room_id')
    position = data.get('position')  # [row, col]
    
    # Broadcast nước đi cho cả phòng
    await sio.emit('move_made', {
        'position': position,
        'timestamp': data.get('timestamp')
    }, room=f"room_{room_id}", skip_sid=sid)


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
