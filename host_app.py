import asyncio
import sys
import logging
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QComboBox, 
                            QGroupBox, QScrollArea)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
import json
import os
import socket
import platform
import qasync
from typing import Optional

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
        
        # Update connection info periodically
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(lambda: asyncio.create_task(self._update_connection_info()))
        self.update_timer.start(1000)  # Update every second
        
        # Update controller list periodically
        self.controller_timer = QTimer()
        self.controller_timer.timeout.connect(self._update_controller_list)
        self.controller_timer.start(1000)  # Update every second
        
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
        status_group = QGroupBox("Server Status")
        status_layout = QVBoxLayout(status_group)
        
        status_label = QLabel("Status: Running")
        status_layout.addWidget(status_label)
        
        # Connection info
        self.connection_info = QLabel()
        status_layout.addWidget(self.connection_info)
        
        layout.addWidget(status_group)
        
        # Controller mapping section
        controller_group = QGroupBox("Controller Mapping")
        controller_layout = QVBoxLayout(controller_group)
        
        # Create scroll area for controller list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_widget = QWidget()
        self.controller_list_layout = QVBoxLayout(scroll_widget)
        scroll.setWidget(scroll_widget)
        
        controller_layout.addWidget(scroll)
        layout.addWidget(controller_group)
        
        # Settings section
        settings_group = QGroupBox("Stream Settings")
        settings_layout = QVBoxLayout(settings_group)
        
        quality_layout = QHBoxLayout()
        quality_label = QLabel("Stream Quality:")
        quality_layout.addWidget(quality_label)
        
        quality_dropdown = QComboBox()
        quality_dropdown.addItems(["Low", "Medium", "High"])
        quality_dropdown.currentTextChanged.connect(self._change_quality)
        quality_layout.addWidget(quality_dropdown)
        
        settings_layout.addLayout(quality_layout)
        layout.addWidget(settings_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
    def _update_controller_list(self):
        """Update the list of available controllers."""
        # Clear existing controller widgets
        while self.controller_list_layout.count():
            item = self.controller_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Get available controllers
        controllers = self.controller_manager.get_available_controllers()
        
        # Create widget for each controller
        for controller in controllers:
            container = QWidget()
            container_layout = QHBoxLayout(container)
            
            # Controller info
            info_label = QLabel(f"{controller['name']} ({controller['type']})")
            container_layout.addWidget(info_label)
            
            # Port selection
            port_dropdown = QComboBox()
            port_dropdown.addItem("Not Mapped", None)
            for i in range(1, 5):
                port_dropdown.addItem(f"Port {i}", i)
                
            # Set current port if mapped
            if controller['mapped_port']:
                port_dropdown.setCurrentText(f"Port {controller['mapped_port']}")
                
            # Connect port change handler
            port_dropdown.currentIndexChanged.connect(
                lambda idx, cid=controller['id']: self._handle_port_change(cid, port_dropdown.currentData())
            )
            
            container_layout.addWidget(port_dropdown)
            self.controller_list_layout.addWidget(container)
            
    def _handle_port_change(self, controller_id: str, port: Optional[int]):
        """Handle controller port mapping change."""
        if port is None:
            self.controller_manager.unmap_controller(controller_id)
        else:
            self.controller_manager.map_controller(controller_id, port)
            
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
        self.update_timer.stop()
        self.controller_timer.stop()
        event.accept()

async def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create application
    app = QApplication(sys.argv)
    
    # Create event loop
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # Create and show window
    window = HostWindow()
    window.show()
    
    # Run event loop
    with loop:
        await loop.run_forever()

if __name__ == "__main__":
    asyncio.run(main()) 