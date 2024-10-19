import React, { useEffect, useState } from 'react';

const App = () => {
  const [name, setName] = useState('');
  const [room, setRoom] = useState('');
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState([]);
  const [socket, setSocket] = useState(null);
  const [inRoom, setInRoom] = useState(false);

  useEffect(() => {
    if (socket) {
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.action === "join_notification") {
          setMessages((prevMessages) => [...prevMessages, { user: 'Thông báo', message: data.message }]);
        } else if (data.action === "leave_notification") {
          setMessages((prevMessages) => [...prevMessages, { user: 'Thông báo', message: data.message }]);
        } else if (data.action === "load_history") {
          // Tải lịch sử tin nhắn khi người dùng tham gia
          const history = data.messages.map((msg) => ({ user: msg[0], message: msg[1] }));
          setMessages((prevMessages) => [...prevMessages, ...history]);
        } else if (data.action === "message" && data.user !== name) {
          // Chỉ hiển thị tin nhắn từ những người dùng khác (tránh hiển thị lại tin nhắn của chính mình)
          setMessages((prevMessages) => [...prevMessages, { user: data.user, message: data.message }]);
        }
      };
    }
  }, [socket, name]);

  const joinRoom = () => {
    const ws = new WebSocket('ws://localhost:5000');
    setSocket(ws);
    setInRoom(true);

    ws.onopen = () => {
      ws.send(JSON.stringify({ action: "join", user: name, room }));
    };
  };

  const sendMessage = () => {
    if (socket && message) {
      socket.send(JSON.stringify({ action: "message", user: name, room, message }));
      // Hiển thị tin nhắn của chính mình ngay lập tức mà không cần đợi từ server
      setMessages((prevMessages) => [...prevMessages, { user: name, message }]);
      setMessage('');  // Xóa nội dung tin nhắn sau khi gửi
    }
  };

  return (
    <div>
      {!inRoom ? (
        <div>
          <input type="text" placeholder="Nhập tên" value={name} onChange={(e) => setName(e.target.value)} />
          <input type="text" placeholder="Nhập phòng" value={room} onChange={(e) => setRoom(e.target.value)} />
          <button onClick={joinRoom}>Tham gia phòng</button>
        </div>
      ) : (
        <div>
          <h2>Phòng: {room}</h2>
          <div>
            {messages.map((msg, index) => (
              <div key={index}><strong>{msg.user}:</strong> {msg.message}</div>
            ))}
          </div>
          <input type="text" value={message} onChange={(e) => setMessage(e.target.value)} placeholder="Nhập tin nhắn..." />
          <button onClick={sendMessage}>Gửi</button>
        </div>
      )}
    </div>
  );
};

export default App;
