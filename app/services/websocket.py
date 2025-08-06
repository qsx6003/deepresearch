"""
WebSocket 连接管理器
"""
from typing import Dict
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """建立新的WebSocket连接"""
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        """断开WebSocket连接"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_update(self, client_id: str, data: dict):
        """发送更新消息"""
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(data)

    async def broadcast(self, data: dict):
        """广播消息给所有连接"""
        for connection in self.active_connections.values():
            await connection.send_json(data)

# 创建全局连接管理器实例
manager = ConnectionManager() 