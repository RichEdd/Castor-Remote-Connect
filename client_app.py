import sys
import asyncio
import websockets
import json
import logging
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QHBoxLayout, QPushButton, QLabel, QLineEdit,
                            QComboBox, QMessageBox, QCheckBox, QListWidget)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QImage, QPixmap
import cv2
import numpy as np
import pygame
import platform
import subprocess
from client.network.host_discovery import HostDiscovery

class StreamReceiver(QThread):
    frame_received = pyqtSignal(bytes)
    
    def __init__(self, websocket):
        super().__init__()
        self.websocket = websocket
        self.running = True
        self.hw_decoder = self._init_hardware_decoder()
        
    def _init_hardware_decoder(self) -> str:
        """Initialize hardware decoder based on available hardware."""
        if platform.system() == 'Windows':
            try:
                import nvidia_smi
                nvidia_smi.nvmlInit()
                return 'nvcuvid'
            except:
                pass
        elif platform.system() == 'Linux':
            try:
                result = subprocess.run(['lspci'], capture_output=True, text=True)
                if 'Intel' in result.stdout and 'VGA' in result.stdout:
                    return 'qsv'
            except:
                pass
        return 'software'
        
    def run(self):
        while self.running:
            try:
                message = asyncio.run(self.websocket.recv())
                data = json.loads(message)
                if data.get('type') == 'frame':
                    self.frame_received.emit(data['data'].encode())
            except Exception as e:
                logging.error(f"Error receiving frame: {e}")
                self.running = False
                
    def stop(self):
        self.running = False
        self.wait()

class ControllerInput(QThread):
    def __init__(self, websocket):
        super().__init__()
        self.websocket = websocket
        self.running = True
        
    def run(self):
        pygame.init()
        pygame.joystick.init()
        
        # Initialize all connected controllers
        joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
        for joystick in joysticks:
            joystick.init()
            
        while self.running:
            pygame.event.pump()
            
            for joystick in joysticks:
                # Get controller state
                axes = [joystick.get_axis(i) for i in range(joystick.get_numaxes())]
                buttons = [joystick.get_button(i) for i in range(joystick.get_numbuttons())]
                
                # Create input data
                input_data = {
                    'type': 'controller_input',
                    'data': {
                        'id': str(joystick.get_id()),
                        'axes': axes,
                        'buttons': buttons
                    }
                }
                
                # Send input data
                try:
                    asyncio.run(self.websocket.send(json.dumps(input_data)))
                except Exception as e:
                    logging.error(f"Error sending controller input: {e}")
                    self.running = False
                    break
                    
            self.msleep(16)  # ~60Hz update rate
            
    def stop(self):
        self.running = False
        pygame.quit()
        self.wait()

class ClientWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Castor Remote Connect - Client")
        self.setMinimumSize(1280, 720)
        
        # Initialize components
        self.websocket = None
        self.stream_receiver = None
        self.controller_input = None
        self.hw_decoder = None
        self.host_discovery = HostDiscovery()
        self.lan_only_mode = False
        
        # Initialize UI
        self._init_ui()
        
        # Start host discovery
        asyncio.create_task(self.host_discovery.start_discovery())
        
        # Set up refresh timer for discovered hosts
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_discovered_hosts)
        self.refresh_timer.start(1000)  # Refresh every second
        
    def _init_ui(self):
        """Initialize the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Connection section
        connection_widget = QWidget()
        connection_layout = QHBoxLayout(connection_widget)
        
        # LAN mode checkbox
        self.lan_mode_checkbox = QCheckBox("LAN Only Mode")
        self.lan_mode_checkbox.stateChanged.connect(self._toggle_lan_mode)
        connection_layout.addWidget(self.lan_mode_checkbox)
        
        # Host input
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("Host IP Address")
        connection_layout.addWidget(self.host_input)
        
        # Connect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self._connect_to_host)
        connection_layout.addWidget(self.connect_button)
        
        layout.addWidget(connection_widget)
        
        # Discovered hosts list
        self.hosts_list = QListWidget()
        self.hosts_list.itemDoubleClicked.connect(self._connect_to_selected_host)
        layout.addWidget(self.hosts_list)
        
        # Stream display
        self.stream_label = QLabel()
        self.stream_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.stream_label)
        
        # Status section
        self.status_label = QLabel("Status: Disconnected")
        layout.addWidget(self.status_label)
        
        # Settings section
        settings_widget = QWidget()
        settings_layout = QHBoxLayout(settings_widget)
        
        quality_label = QLabel("Stream Quality:")
        settings_layout.addWidget(quality_label)
        
        self.quality_dropdown = QComboBox()
        self.quality_dropdown.addItems(["Low", "Medium", "High"])
        self.quality_dropdown.currentTextChanged.connect(self._change_quality)
        settings_layout.addWidget(self.quality_dropdown)
        
        # Hardware acceleration status
        hw_label = QLabel(f"Hardware Decoding: {self._get_hw_decoder_status()}")
        settings_layout.addWidget(hw_label)
        
        settings_layout.addStretch()
        layout.addWidget(settings_widget)
        
    def _toggle_lan_mode(self, state):
        """Toggle LAN only mode."""
        self.lan_only_mode = bool(state)
        if self.lan_only_mode:
            self.host_input.setEnabled(False)
            self.hosts_list.setEnabled(True)
        else:
            self.host_input.setEnabled(True)
            self.hosts_list.setEnabled(False)
            
    def _refresh_discovered_hosts(self):
        """Refresh the list of discovered hosts."""
        if not self.lan_only_mode:
            return
            
        hosts = self.host_discovery.get_discovered_hosts()
        self.hosts_list.clear()
        
        for host in hosts:
            item_text = f"{host['name']} ({host['ip']}) - {host['quality']} quality"
            if host['connected_clients'] > 0:
                item_text += f" - {host['connected_clients']} clients"
            self.hosts_list.addItem(item_text)
            
    def _connect_to_selected_host(self, item):
        """Connect to the selected host from the list."""
        if not self.lan_only_mode:
            return
            
        # Extract IP from the item text
        ip = item.text().split('(')[1].split(')')[0]
        self.host_input.setText(ip)
        self._connect_to_host()
        
    def _get_hw_decoder_status(self) -> str:
        """Get the status of hardware decoding."""
        if platform.system() == 'Windows':
            try:
                import nvidia_smi
                nvidia_smi.nvmlInit()
                return "NVIDIA GPU"
            except:
                pass
        elif platform.system() == 'Linux':
            try:
                result = subprocess.run(['lspci'], capture_output=True, text=True)
                if 'Intel' in result.stdout and 'VGA' in result.stdout:
                    return "Intel QuickSync"
            except:
                pass
        return "Software"
        
    def _handle_frame(self, frame_data: bytes):
        """Handle received frame data with hardware acceleration if available."""
        try:
            # Convert frame data to image
            nparr = np.frombuffer(frame_data, np.uint8)
            
            if self.hw_decoder == 'nvcuvid':
                # NVIDIA hardware decoding
                frame = cv2.cudacodec.createVideoReader(nparr)
                frame = frame.nextFrame()
            elif self.hw_decoder == 'qsv':
                # Intel QuickSync hardware decoding
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)
            else:
                # Software decoding
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Convert to QImage
            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
            
            # Display image
            pixmap = QPixmap.fromImage(q_image)
            self.stream_label.setPixmap(pixmap.scaled(
                self.stream_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
            
        except Exception as e:
            logging.error(f"Error handling frame: {e}")
            
    async def _connect_to_host(self):
        """Connect to the host server."""
        host = self.host_input.text().strip()
        if not host:
            QMessageBox.warning(self, "Error", "Please enter a host address")
            return
            
        try:
            self.websocket = await websockets.connect(f"ws://{host}:8765")
            self.status_label.setText("Status: Connected")
            self.connect_button.setEnabled(False)
            
            # Start stream receiver
            self.stream_receiver = StreamReceiver(self.websocket)
            self.stream_receiver.frame_received.connect(self._handle_frame)
            self.stream_receiver.start()
            
            # Start controller input
            self.controller_input = ControllerInput(self.websocket)
            self.controller_input.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to connect: {str(e)}")
            
    def _change_quality(self, quality: str):
        """Change stream quality."""
        if self.websocket:
            try:
                asyncio.run(self.websocket.send(json.dumps({
                    'type': 'quality_change',
                    'data': quality.lower()
                })))
            except Exception as e:
                logging.error(f"Error changing quality: {e}")
                
    def closeEvent(self, event):
        """Handle window close event."""
        if self.stream_receiver:
            self.stream_receiver.stop()
        if self.controller_input:
            self.controller_input.stop()
        if self.websocket:
            asyncio.run(self.websocket.close())
        asyncio.run(self.host_discovery.stop_discovery())
        event.accept()

def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create application
    app = QApplication(sys.argv)
    window = ClientWindow()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 