import cv2
import numpy as np
import threading
import queue
import time
from typing import Optional, Tuple, Dict
import mss
import mss.tools
import subprocess
import os
import logging
import platform

class Streamer:
    def __init__(self, quality: str = 'medium'):
        """
        Initialize the streamer.
        
        Args:
            quality (str): Stream quality ('low', 'medium', 'high')
        """
        self.quality = quality
        self.running = False
        self.logger = logging.getLogger('Streamer')
        
        # Initialize quality settings
        self.quality_settings = {
            'low': {
                'width': 1280,
                'height': 720,
                'fps': 30,
                'bitrate': '2M',
                'preset': 'ultrafast'
            },
            'medium': {
                'width': 1920,
                'height': 1080,
                'fps': 60,
                'bitrate': '5M',
                'preset': 'fast'
            },
            'high': {
                'width': 2560,
                'height': 1440,
                'fps': 60,
                'bitrate': '10M',
                'preset': 'medium'
            }
        }
        
        # Initialize hardware acceleration
        self.hw_accel = self._init_hardware_acceleration()
        
        # Initialize screen capture
        try:
            self.sct = mss.mss()
            # Get the primary monitor
            self.monitor = self.sct.monitors[1]
            self.logger.info("Screen capture initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize screen capture: {e}")
            self.sct = None
        
    def _init_hardware_acceleration(self) -> str:
        """Initialize hardware acceleration based on available hardware."""
        if platform.system() == 'Windows':
            try:
                import nvidia_smi
                nvidia_smi.nvmlInit()
                return 'nvenc'
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
        
    def start(self):
        """Start streaming."""
        self.running = True
        self.logger.info(f"Starting stream with {self.quality} quality using {self.hw_accel} encoding")
        
    def stop(self):
        """Stop streaming."""
        self.running = False
        if self.sct:
            self.sct.close()
        
    def get_next_frame(self) -> Optional[bytes]:
        """Get the next frame from the stream."""
        if not self.running or not self.sct:
            return None
            
        try:
            # Capture screen
            frame = self._capture_screen()
            if frame is None:
                return None
                
            # Process frame
            return self._process_frame(frame)
            
        except Exception as e:
            self.logger.error(f"Error getting frame: {e}")
            return None
            
    def _capture_screen(self) -> Optional[np.ndarray]:
        """Capture the screen using mss."""
        try:
            # Capture the screen
            screenshot = self.sct.grab(self.monitor)
            
            # Convert to numpy array
            frame = np.array(screenshot)
            
            # Convert from BGRA to BGR
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            
            return frame
            
        except Exception as e:
            self.logger.error(f"Error capturing screen: {e}")
            return None
            
    def _process_frame(self, frame: np.ndarray) -> Optional[bytes]:
        """Process and encode the frame."""
        try:
            # Get quality settings
            settings = self.quality_settings[self.quality]
            
            # Resize frame if needed
            if frame.shape[1] != settings['width'] or frame.shape[0] != settings['height']:
                frame = cv2.resize(frame, (settings['width'], settings['height']))
                
            # Encode frame
            if self.hw_accel == 'nvenc':
                # NVIDIA hardware encoding
                encode_param = [
                    int(cv2.IMWRITE_JPEG_QUALITY), 90,
                    int(cv2.IMWRITE_JPEG_OPTIMIZE), 1,
                    int(cv2.IMWRITE_JPEG_PROGRESSIVE), 1
                ]
                _, encoded = cv2.imencode('.jpg', frame, encode_param)
                return encoded.tobytes()
                
            elif self.hw_accel == 'qsv':
                # Intel QuickSync hardware encoding
                encode_param = [
                    int(cv2.IMWRITE_JPEG_QUALITY), 90,
                    int(cv2.IMWRITE_JPEG_OPTIMIZE), 1,
                    int(cv2.IMWRITE_JPEG_PROGRESSIVE), 1
                ]
                _, encoded = cv2.imencode('.jpg', frame, encode_param)
                return encoded.tobytes()
                
            else:
                # Software encoding
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
                _, encoded = cv2.imencode('.jpg', frame, encode_param)
                return encoded.tobytes()
                
        except Exception as e:
            self.logger.error(f"Error processing frame: {e}")
            return None 