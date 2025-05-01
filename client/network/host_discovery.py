import socket
import json
import asyncio
import logging
from typing import Dict, List, Optional
import time

class HostDiscovery:
    def __init__(self, port: int = 8765, discovery_port: int = 8766):
        """
        Initialize host discovery service.
        
        Args:
            port (int): Main application port
            discovery_port (int): Port for host discovery broadcasts
        """
        self.port = port
        self.discovery_port = discovery_port
        self.running = False
        self.discovered_hosts: Dict[str, dict] = {}
        self.logger = logging.getLogger('HostDiscovery')
        
    async def start_discovery(self):
        """Start the host discovery service."""
        self.running = True
        
        # Start UDP server for receiving broadcasts
        self.server = await asyncio.start_server(
            self._handle_discovery,
            '0.0.0.0',
            self.discovery_port,
            family=socket.AF_INET
        )
        
        # Start periodic cleanup of stale hosts
        asyncio.create_task(self._cleanup_stale_hosts())
        
        self.logger.info(f"Host discovery started on port {self.discovery_port}")
        
    async def stop_discovery(self):
        """Stop the host discovery service."""
        self.running = False
        if hasattr(self, 'server'):
            self.server.close()
            await self.server.wait_closed()
            
    async def _handle_discovery(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle incoming host discovery messages."""
        try:
            data = await reader.read(1024)
            message = json.loads(data.decode())
            
            if message.get('type') == 'host_announce':
                host_info = message.get('data', {})
                host_ip = writer.get_extra_info('peername')[0]
                
                self.discovered_hosts[host_ip] = {
                    'name': host_info.get('name', 'Unknown'),
                    'last_seen': time.time(),
                    'quality': host_info.get('quality', 'medium'),
                    'connected_clients': host_info.get('connected_clients', 0)
                }
                
                self.logger.info(f"Discovered host: {host_ip} ({host_info.get('name')})")
                
        except Exception as e:
            self.logger.error(f"Error handling discovery message: {e}")
            
    async def _cleanup_stale_hosts(self):
        """Remove hosts that haven't been seen in a while."""
        while self.running:
            current_time = time.time()
            stale_timeout = 10  # Remove hosts not seen in 10 seconds
            
            for host_ip in list(self.discovered_hosts.keys()):
                if current_time - self.discovered_hosts[host_ip]['last_seen'] > stale_timeout:
                    del self.discovered_hosts[host_ip]
                    self.logger.info(f"Removed stale host: {host_ip}")
                    
            await asyncio.sleep(5)  # Check every 5 seconds
            
    def get_discovered_hosts(self) -> List[dict]:
        """
        Get list of discovered hosts.
        
        Returns:
            List[dict]: List of discovered hosts with their information
        """
        return [
            {
                'ip': ip,
                **info
            }
            for ip, info in self.discovered_hosts.items()
        ]
        
    @staticmethod
    async def broadcast_host_info(port: int, host_info: dict):
        """
        Broadcast host information on the local network.
        
        Args:
            port (int): Port to broadcast on
            host_info (dict): Host information to broadcast
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        message = {
            'type': 'host_announce',
            'data': host_info
        }
        
        try:
            sock.sendto(
                json.dumps(message).encode(),
                ('<broadcast>', port)
            )
        except Exception as e:
            logging.error(f"Error broadcasting host info: {e}")
        finally:
            sock.close() 