import asyncio
import sys
import logging
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel, QComboBox
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
import json
import os
import socket
import platform

from host.core.streamer import Streamer
from host.controllers.controller_manager import ControllerManager
from host.network.connection_manager import ConnectionManager
from client.network.host_discovery import HostDiscovery

class StreamThread(QThread):
    frame_ready = pyqtSignal(bytes)
    
    def __init__(self, streamer):
        super().__init__()
        self.streamer = streamer
        self.running = True
        
    def run(self):
        self.streamer.start()
        while self.running:
            frame = self.streamer.get_next_frame()
            if frame:
                self.frame_ready.emit(frame)
            self.msleep(1)  # Small delay to prevent CPU overuse
            
    def stop(self):
        self.running = False
        self.streamer.stop()
        self.wait()

class HostWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Castor Remote Connect - Host")
        self.setMinimumSize(800, 600)
        
        # Initialize components
        self.streamer = Streamer()
        self.controller_manager = ControllerManager()
        self.connection_manager = ConnectionManager()
        
        # Initialize UI
        self._init_ui()
        
        # Start streaming thread
        self.stream_thread = StreamThread(self.streamer)
        self.stream_thread.frame_ready.connect(self._handle_frame)
        self.stream_thread.start()
        
        # Start controller manager
        self.controller_manager.initialize()
        self.controller_manager.start()
        
        # Start connection manager
        asyncio.create_task(self.connection_manager.start())
        
        # Set up LAN broadcast
        self._setup_lan_broadcast()
        
    def _setup_lan_broadcast(self):
        """Set up periodic LAN broadcast of host information."""
        self.broadcast_timer = QTimer()
        self.broadcast_timer.timeout.connect(self._broadcast_host_info)
        self.broadcast_timer.start(5000)  # Broadcast every 5 seconds
        
    def _broadcast_host_info(self):
        """Broadcast host information on the LAN."""
        host_info = {
            'name': platform.node(),
            'quality': self.streamer.quality,
            'connected_clients': len(self.connection_manager.clients)
        }
        
        asyncio.create_task(HostDiscovery.broadcast_host_info(8766, host_info))
        
    def _init_ui(self):
        """Initialize the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Status section
        status_label = QLabel("Server Status: Running")
        layout.addWidget(status_label)
        
        # Connection info
        self.connection_info = QLabel()
        layout.addWidget(self.connection_info)
        
        # Controller mapping section
        controller_label = QLabel("Controller Mapping")
        layout.addWidget(controller_label)
        
        # Controller selection dropdowns
        self.controller_dropdowns = []
        for i in range(4):
            container = QWidget()
            container_layout = QVBoxLayout(container)
            
            port_label = QLabel(f"Port {i+1}:")
            container_layout.addWidget(port_label)
            
            dropdown = QComboBox()
            dropdown.addItem("No Controller")
            # TODO: Add detected controllers
            container_layout.addWidget(dropdown)
            
            self.controller_dropdowns.append(dropdown)
            layout.addWidget(container)
            
        # Settings section
        settings_label = QLabel("Stream Settings")
        layout.addWidget(settings_label)
        
        quality_dropdown = QComboBox()
        quality_dropdown.addItems(["Low", "Medium", "High"])
        quality_dropdown.currentTextChanged.connect(self._change_quality)
        layout.addWidget(quality_dropdown)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
    def _handle_frame(self, frame_data: bytes):
        """Handle a new frame from the streamer."""
        # TODO: Send frame to connected clients
        pass
        
    def _change_quality(self, quality: str):
        """Change stream quality."""
        quality = quality.lower()
        self.streamer.quality = quality
        
    async def _update_connection_info(self):
        """Update connection information display."""
        public_ip = await self.connection_manager.get_public_ip()
        local_ip = self.connection_manager.get_local_ip()
        
        info_text = f"Public IP: {public_ip or 'Unknown'}\n"
        info_text += f"Local IP: {local_ip or 'Unknown'}\n"
        info_text += f"Connected Clients: {len(self.connection_manager.clients)}"
        
        self.connection_info.setText(info_text)
        
    def closeEvent(self, event):
        """Handle window close event."""
        self.stream_thread.stop()
        self.controller_manager.stop()
        asyncio.create_task(self.connection_manager.stop())
        self.broadcast_timer.stop()
        event.accept()

def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create application
    app = QApplication(sys.argv)
    window = HostWindow()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 