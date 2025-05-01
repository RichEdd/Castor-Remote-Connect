import asyncio
import websockets
import json
import logging
from typing import Dict, Set, Optional
import aiohttp
import socket
import threading
import queue

class ConnectionManager:
    def __init__(self, port: int = 8765):
        """
        Initialize the connection manager.
        
        Args:
            port (int): Port to listen on for WebSocket connections
        """
        self.port = port
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.client_info: Dict[str, dict] = {}
        self.running = False
        self.input_queue = queue.Queue()
        self.logger = logging.getLogger('ConnectionManager')
        
    async def start(self):
        """Start the connection manager and begin accepting connections."""
        self.running = True
        
        # Start WebSocket server
        server = await websockets.serve(
            self._handle_client,
            '0.0.0.0',
            self.port,
            ping_interval=20,
            ping_timeout=60
        )
        
        self.logger.info(f"Server started on port {self.port}")
        
        # Start input processing
        asyncio.create_task(self._process_inputs())
        
        # Keep the server running
        await server.wait_closed()
        
    async def stop(self):
        """Stop the connection manager and close all connections."""
        self.running = False
        
        # Close all client connections
        for client in self.clients.values():
            await client.close()
            
        self.clients.clear()
        self.client_info.clear()
        
    async def _handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """
        Handle a new client connection.
        
        Args:
            websocket: WebSocket connection
            path: Connection path
        """
        client_id = str(id(websocket))
        self.clients[client_id] = websocket
        self.client_info[client_id] = {
            'connected_at': asyncio.get_event_loop().time(),
            'last_ping': asyncio.get_event_loop().time()
        }
        
        try:
            async for message in websocket:
                await self._handle_message(client_id, message)
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"Client {client_id} disconnected")
        finally:
            await self._cleanup_client(client_id)
            
    async def _handle_message(self, client_id: str, message: str):
        """
        Handle incoming messages from clients.
        
        Args:
            client_id: ID of the client
            message: Message data
        """
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type == 'ping':
                self.client_info[client_id]['last_ping'] = asyncio.get_event_loop().time()
                await self._send_to_client(client_id, {'type': 'pong'})
                
            elif message_type == 'controller_input':
                # Queue the input for processing
                self.input_queue.put((client_id, data.get('data', {})))
                
            elif message_type == 'client_info':
                self.client_info[client_id].update(data.get('data', {}))
                
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON from client {client_id}")
        except Exception as e:
            self.logger.error(f"Error handling message from client {client_id}: {e}")
            
    async def _process_inputs(self):
        """Process input queue and distribute to appropriate handlers."""
        while self.running:
            try:
                client_id, input_data = self.input_queue.get_nowait()
                # TODO: Process input data and update virtual controllers
                self.input_queue.task_done()
            except queue.Empty:
                await asyncio.sleep(0.01)
            except Exception as e:
                self.logger.error(f"Error processing input: {e}")
                
    async def _send_to_client(self, client_id: str, data: dict):
        """
        Send data to a specific client.
        
        Args:
            client_id: ID of the client
            data: Data to send
        """
        if client_id in self.clients:
            try:
                await self.clients[client_id].send(json.dumps(data))
            except Exception as e:
                self.logger.error(f"Error sending to client {client_id}: {e}")
                
    async def broadcast(self, data: dict, exclude: Optional[Set[str]] = None):
        """
        Broadcast data to all connected clients.
        
        Args:
            data: Data to broadcast
            exclude: Set of client IDs to exclude from broadcast
        """
        exclude = exclude or set()
        message = json.dumps(data)
        
        for client_id, websocket in self.clients.items():
            if client_id not in exclude:
                try:
                    await websocket.send(message)
                except Exception as e:
                    self.logger.error(f"Error broadcasting to client {client_id}: {e}")
                    
    async def _cleanup_client(self, client_id: str):
        """
        Clean up resources for a disconnected client.
        
        Args:
            client_id: ID of the client to clean up
        """
        if client_id in self.clients:
            del self.clients[client_id]
        if client_id in self.client_info:
            del self.client_info[client_id]
            
    @staticmethod
    async def get_public_ip() -> Optional[str]:
        """
        Get the public IP address of the server.
        
        Returns:
            Optional[str]: Public IP address or None if unable to determine
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.ipify.org') as response:
                    return await response.text()
        except Exception as e:
            logging.error(f"Error getting public IP: {e}")
            return None
            
    @staticmethod
    def get_local_ip() -> Optional[str]:
        """
        Get the local IP address of the server.
        
        Returns:
            Optional[str]: Local IP address or None if unable to determine
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as e:
            logging.error(f"Error getting local IP: {e}")
            return None 