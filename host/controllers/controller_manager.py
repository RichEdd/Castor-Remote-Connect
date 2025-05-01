import vjoy
import threading
import queue
from typing import Dict, Optional, List
import json

class ControllerManager:
    def __init__(self, max_controllers: int = 4):
        """
        Initialize the controller manager.
        
        Args:
            max_controllers (int): Maximum number of virtual controllers to support
        """
        self.max_controllers = max_controllers
        self.virtual_controllers: Dict[int, vjoy.VJoyDevice] = {}
        self.controller_mappings: Dict[str, int] = {}  # Maps physical controller IDs to virtual ports
        self.input_queue = queue.Queue()
        self.running = False
        
    def initialize(self):
        """Initialize virtual controllers."""
        try:
            for i in range(1, self.max_controllers + 1):
                self.virtual_controllers[i] = vjoy.VJoyDevice(i)
            return True
        except Exception as e:
            print(f"Error initializing virtual controllers: {e}")
            return False
            
    def start(self):
        """Start the controller management system."""
        self.running = True
        self.process_thread = threading.Thread(target=self._process_inputs)
        self.process_thread.start()
        
    def stop(self):
        """Stop the controller management system."""
        self.running = False
        if hasattr(self, 'process_thread'):
            self.process_thread.join()
            
    def map_controller(self, physical_id: str, virtual_port: int) -> bool:
        """
        Map a physical controller to a virtual port.
        
        Args:
            physical_id (str): ID of the physical controller
            virtual_port (int): Virtual port number (1-4)
            
        Returns:
            bool: True if mapping was successful
        """
        if virtual_port < 1 or virtual_port > self.max_controllers:
            return False
            
        if virtual_port in self.controller_mappings.values():
            # Unmap the existing controller from this port
            for pid, port in self.controller_mappings.items():
                if port == virtual_port:
                    del self.controller_mappings[pid]
                    break
                    
        self.controller_mappings[physical_id] = virtual_port
        return True
        
    def unmap_controller(self, physical_id: str) -> bool:
        """
        Remove a controller mapping.
        
        Args:
            physical_id (str): ID of the physical controller
            
        Returns:
            bool: True if unmapping was successful
        """
        if physical_id in self.controller_mappings:
            del self.controller_mappings[physical_id]
            return True
        return False
        
    def get_controller_mappings(self) -> Dict[str, int]:
        """
        Get current controller mappings.
        
        Returns:
            Dict[str, int]: Current controller mappings
        """
        return self.controller_mappings.copy()
        
    def process_input(self, controller_id: str, input_data: dict):
        """
        Process input from a physical controller.
        
        Args:
            controller_id (str): ID of the physical controller
            input_data (dict): Controller input data
        """
        self.input_queue.put((controller_id, input_data))
        
    def _process_inputs(self):
        """Process input queue and update virtual controllers."""
        while self.running:
            try:
                controller_id, input_data = self.input_queue.get(timeout=0.1)
                
                if controller_id in self.controller_mappings:
                    virtual_port = self.controller_mappings[controller_id]
                    self._update_virtual_controller(virtual_port, input_data)
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing controller input: {e}")
                
    def _update_virtual_controller(self, virtual_port: int, input_data: dict):
        """
        Update a virtual controller with new input data.
        
        Args:
            virtual_port (int): Virtual controller port
            input_data (dict): Controller input data
        """
        try:
            vjoy_device = self.virtual_controllers[virtual_port]
            
            # Update axes
            if 'axes' in input_data:
                for axis, value in input_data['axes'].items():
                    vjoy_device.set_axis(axis, value)
                    
            # Update buttons
            if 'buttons' in input_data:
                for button, state in input_data['buttons'].items():
                    vjoy_device.set_button(button, state)
                    
        except Exception as e:
            print(f"Error updating virtual controller {virtual_port}: {e}")
            
    def save_mappings(self, filepath: str) -> bool:
        """
        Save controller mappings to a file.
        
        Args:
            filepath (str): Path to save mappings
            
        Returns:
            bool: True if save was successful
        """
        try:
            with open(filepath, 'w') as f:
                json.dump(self.controller_mappings, f)
            return True
        except Exception as e:
            print(f"Error saving controller mappings: {e}")
            return False
            
    def load_mappings(self, filepath: str) -> bool:
        """
        Load controller mappings from a file.
        
        Args:
            filepath (str): Path to load mappings from
            
        Returns:
            bool: True if load was successful
        """
        try:
            with open(filepath, 'r') as f:
                self.controller_mappings = json.load(f)
            return True
        except Exception as e:
            print(f"Error loading controller mappings: {e}")
            return False 