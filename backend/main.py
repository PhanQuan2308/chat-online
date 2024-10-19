import os
import json
import sqlite3
import asyncio
import websockets
from dotenv import load_dotenv

# Nạp biến môi trường từ tệp .env
load_dotenv()

# Lấy các giá trị nhạy cảm từ biến môi trường
firebase_config = {
    "type": "service_account",
    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n"),  # Lưu ý: cần thay thế \\n thành \n
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
    "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
    "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_CERT_URL"),
    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL")
}

# Cấu hình SQLite để lưu trữ tin nhắn
conn = sqlite3.connect('chat.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS messages (user TEXT, room TEXT, message TEXT)''')

# Biến lưu danh sách các kết nối đang hoạt động
connected_users = {}

# Hàm lưu tin nhắn vào SQLite
async def save_message(user, room, message):
    c.execute("INSERT INTO messages (user, room, message) VALUES (?, ?, ?)", (user, room, message))
    conn.commit()

# Hàm lấy lịch sử tin nhắn từ SQLite cho một phòng cụ thể
def get_chat_history(room):
    c.execute("SELECT user, message FROM messages WHERE room=?", (room,))
    return c.fetchall()

# Hàm xử lý kết nối WebSocket
async def handle_connection(websocket, path):
    try:
        async for message in websocket:
            data = json.loads(message)
            action = data.get('action')

            if action == "join":
                user = data['user']
                room = data['room']

                # Nếu phòng chưa có, tạo mới
                if room not in connected_users:
                    connected_users[room] = []

                # Thêm người dùng vào danh sách kết nối của phòng
                connected_users[room].append(websocket)
                print(f"{user} đã tham gia phòng {room}")

                # Gửi lịch sử chat cho người dùng mới
                chat_history = get_chat_history(room)
                history_message = json.dumps({"action": "load_history", "messages": chat_history})
                await websocket.send(history_message)

                # Phát thông báo cho các người dùng khác trong phòng
                join_message = json.dumps({"action": "join_notification", "message": f"{user} đã tham gia phòng!"})

                # Gửi thông báo tới các kết nối còn hoạt động
                for conn in connected_users[room][:]:
                    if conn != websocket:  # Không gửi cho người vừa tham gia
                        try:
                            await conn.send(join_message)
                        except websockets.exceptions.ConnectionClosed:
                            print("Kết nối bị đóng, loại bỏ kết nối.")
                            connected_users[room].remove(conn)  # Loại bỏ kết nối đã bị đóng

            elif action == "message":
                user = data['user']
                room = data['room']
                msg = data['message']

                # Lưu tin nhắn vào cơ sở dữ liệu
                await save_message(user, room, msg)

                # Tin nhắn để phát cho tất cả người dùng trong phòng
                broadcast_message = json.dumps({"action": "message", "user": user, "message": msg})

                # Phát tin nhắn đến tất cả người dùng trong phòng
                for conn in connected_users[room][:]:
                    try:
                        await conn.send(broadcast_message)
                    except websockets.exceptions.ConnectionClosed:
                        print("Kết nối bị đóng, loại bỏ kết nối.")
                        connected_users[room].remove(conn)  # Loại bỏ kết nối đã bị đóng
    except websockets.exceptions.ConnectionClosed:
        print("Người dùng đã ngắt kết nối")

        # Khi người dùng rời khỏi phòng, gửi thông báo cho các người dùng khác trong phòng
        for room, users in connected_users.items():
            if websocket in users:
                users.remove(websocket)
                if users:  # Nếu còn người trong phòng
                    leave_message = json.dumps({"action": "leave_notification", "message": "Một người dùng đã rời phòng."})
                    for conn in users[:]:
                        try:
                            await conn.send(leave_message)
                        except websockets.exceptions.ConnectionClosed:
                            print("Kết nối bị đóng, loại bỏ kết nối.")
                            users.remove(conn)

# Chạy server WebSocket
start_server = websockets.serve(handle_connection, "localhost", 5000)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
