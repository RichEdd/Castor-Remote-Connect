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
from xvfbwrapper import Xvfb
import platform

class Streamer:
    def __init__(self, quality: str = 'high', fps: int = 60):
        """
        Initialize the streamer with specified quality and FPS settings.
        
        Args:
            quality (str): Stream quality ('low', 'medium', 'high')
            fps (int): Target frames per second
        """
        self.quality = quality
        self.fps = fps
        self.running = False
        self.frame_queue = queue.Queue(maxsize=2)
        self.logger = logging.getLogger('Streamer')
        
        # Initialize quality settings with hardware acceleration parameters
        self.quality_settings = {
            'low': {
                'width': 1280,
                'height': 720,
                'bitrate': '2M',
                'preset': 'ultrafast',
                'tune': 'zerolatency'
            },
            'medium': {
                'width': 1920,
                'height': 1080,
                'bitrate': '4M',
                'preset': 'veryfast',
                'tune': 'zerolatency'
            },
            'high': {
                'width': 2560,
                'height': 1440,
                'bitrate': '8M',
                'preset': 'fast',
                'tune': 'zerolatency'
            }
        }
        
        # Initialize screen capture
        self.sct = mss.mss()
        
        # Initialize virtual display if needed
        self.vdisplay = None
        self._setup_virtual_display()
        
        # Initialize hardware acceleration
        self._init_hardware_acceleration()
        
    def _setup_virtual_display(self):
        """Set up virtual display for headless operation."""
        if platform.system() == 'Linux':
            try:
                self.vdisplay = Xvfb(width=1920, height=1080)
                self.vdisplay.start()
                self.logger.info("Virtual display started")
            except Exception as e:
                self.logger.warning(f"Failed to start virtual display: {e}")
                
    def _init_hardware_acceleration(self):
        """Initialize hardware acceleration for encoding."""
        self.hw_accel = None
        self.hw_device = None
        
        # Check for NVIDIA GPU
        if platform.system() == 'Windows':
            try:
                import nvidia_smi
                nvidia_smi.nvmlInit()
                self.hw_accel = 'nvenc'
                self.logger.info("NVIDIA hardware acceleration enabled")
            except:
                self.logger.warning("NVIDIA hardware acceleration not available")
                
        # Check for Intel QuickSync
        elif platform.system() == 'Linux':
            try:
                # Check for Intel GPU
                result = subprocess.run(['lspci'], capture_output=True, text=True)
                if 'Intel' in result.stdout and 'VGA' in result.stdout:
                    self.hw_accel = 'qsv'
                    self.hw_device = '/dev/dri/renderD128'
                    self.logger.info("Intel QuickSync hardware acceleration enabled")
            except:
                self.logger.warning("Intel QuickSync hardware acceleration not available")
                
    def start(self):
        """Start the streaming process."""
        self.running = True
        self.capture_thread = threading.Thread(target=self._capture_loop)
        self.capture_thread.start()
        
    def stop(self):
        """Stop the streaming process."""
        self.running = False
        if hasattr(self, 'capture_thread'):
            self.capture_thread.join()
        if self.vdisplay:
            self.vdisplay.stop()
            
    def _capture_loop(self):
        """Main capture loop that captures screen and processes frames."""
        while self.running:
            try:
                # Capture screen
                frame = self._capture_screen()
                
                # Process frame (resize, encode)
                processed_frame = self._process_frame(frame)
                
                # Add to queue, remove old frame if queue is full
                if self.frame_queue.full():
                    self.frame_queue.get_nowait()
                self.frame_queue.put_nowait(processed_frame)
                
                # Maintain target FPS
                time.sleep(1/self.fps)
                
            except Exception as e:
                print(f"Error in capture loop: {e}")
                time.sleep(0.1)
                
    def _capture_screen(self) -> np.ndarray:
        """
        Capture the current screen using MSS.
        
        Returns:
            np.ndarray: Captured frame
        """
        try:
            # Capture the primary monitor
            monitor = self.sct.monitors[1]  # Primary monitor
            screenshot = self.sct.grab(monitor)
            
            # Convert to numpy array
            frame = np.array(screenshot)
            
            # Convert BGRA to BGR
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            
            return frame
            
        except Exception as e:
            self.logger.error(f"Error capturing screen: {e}")
            settings = self.quality_settings[self.quality]
            return np.zeros((settings['height'], settings['width'], 3), dtype=np.uint8)
            
    def _process_frame(self, frame: np.ndarray) -> bytes:
        """
        Process and encode the frame using hardware acceleration if available.
        
        Args:
            frame (np.ndarray): Input frame
            
        Returns:
            bytes: Encoded frame data
        """
        settings = self.quality_settings[self.quality]
        
        # Resize frame if needed
        if frame.shape[1] != settings['width'] or frame.shape[0] != settings['height']:
            frame = cv2.resize(frame, (settings['width'], settings['height']))
            
        try:
            if self.hw_accel == 'nvenc':
                # NVIDIA hardware encoding
                fourcc = cv2.VideoWriter_fourcc(*'H264')
                out = cv2.VideoWriter(
                    'appsrc ! videoconvert ! nvh264enc ! h264parse ! appsink',
                    cv2.CAP_GSTREAMER,
                    fourcc,
                    self.fps,
                    (settings['width'], settings['height'])
                )
                out.write(frame)
                encoded_frame = out.read()
                out.release()
                return encoded_frame
                
            elif self.hw_accel == 'qsv':
                # Intel QuickSync hardware encoding
                fourcc = cv2.VideoWriter_fourcc(*'H264')
                out = cv2.VideoWriter(
                    f'appsrc ! videoconvert ! qsvh264enc ! h264parse ! appsink',
                    cv2.CAP_GSTREAMER,
                    fourcc,
                    self.fps,
                    (settings['width'], settings['height'])
                )
                out.write(frame)
                encoded_frame = out.read()
                out.release()
                return encoded_frame
                
            else:
                # Software encoding as fallback
                encode_params = [
                    int(cv2.IMWRITE_JPEG_QUALITY), 90,
                    int(cv2.IMWRITE_JPEG_OPTIMIZE), 1
                ]
                _, encoded_frame = cv2.imencode('.jpg', frame, encode_params)
                return encoded_frame.tobytes()
                
        except Exception as e:
            self.logger.error(f"Error encoding frame: {e}")
            # Fallback to basic encoding
            _, encoded_frame = cv2.imencode('.jpg', frame)
            return encoded_frame.tobytes()
            
    def get_next_frame(self) -> Optional[bytes]:
        """
        Get the next frame from the queue.
        
        Returns:
            Optional[bytes]: Next frame data or None if no frame is available
        """
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return None 