import platform
import logging
from typing import Dict, List, Optional, Tuple
import pygame
import json
import time

class ControllerManager:
    def __init__(self):
        """Initialize the controller manager."""
        self.logger = logging.getLogger('ControllerManager')
        self.running = False
        self.local_controllers: Dict[str, pygame.joystick.Joystick] = {}
        self.remote_controllers: Dict[str, dict] = {}
        self.controller_mappings: Dict[str, Tuple[str, int]] = {}  # Maps controller_id to (type, port)
        self.max_ports = 4
        self.last_scan_time = 0
        self.scan_interval = 1.0  # Scan every second
        
    def initialize(self):
        """Initialize controller subsystem."""
        try:
            pygame.init()
            pygame.joystick.init()
            self.logger.info("Controller manager initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize controller manager: {e}")
            
    def start(self):
        """Start the controller manager."""
        self.running = True
        self._scan_controllers()
        
    def stop(self):
        """Stop the controller manager."""
        self.running = False
        pygame.quit()
        
    def _scan_controllers(self):
        """Scan for connected local controllers."""
        if not self.running:
            return
            
        current_time = time.time()
        if current_time - self.last_scan_time < self.scan_interval:
            return
            
        self.last_scan_time = current_time
        
        try:
            # Get current connected controller IDs
            current_controllers = set()
            for i in range(pygame.joystick.get_count()):
                joystick = pygame.joystick.Joystick(i)
                joystick.init()
                controller_id = f"local_{joystick.get_id()}"
                current_controllers.add(controller_id)
                
                # Add new controllers
                if controller_id not in self.local_controllers:
                    self.local_controllers[controller_id] = joystick
                    self.logger.info(f"Found new local controller: {joystick.get_name()}")
                    
            # Remove disconnected controllers
            for controller_id in list(self.local_controllers.keys()):
                if controller_id not in current_controllers:
                    # Unmap the controller if it was mapped
                    if controller_id in self.controller_mappings:
                        del self.controller_mappings[controller_id]
                    del self.local_controllers[controller_id]
                    self.logger.info(f"Local controller disconnected: {controller_id}")
                    
        except Exception as e:
            self.logger.error(f"Error scanning controllers: {e}")
            
    def add_remote_controller(self, client_id: str, controller_info: dict):
        """Add a remote controller from a client."""
        controller_id = f"remote_{client_id}"
        self.remote_controllers[controller_id] = {
            'client_id': client_id,
            'name': controller_info.get('name', 'Unknown Controller'),
            'last_seen': time.time()
        }
        self.logger.info(f"Added remote controller: {controller_info.get('name')} from client {client_id}")
        
    def remove_remote_controller(self, client_id: str):
        """Remove a remote controller."""
        controller_id = f"remote_{client_id}"
        if controller_id in self.remote_controllers:
            del self.remote_controllers[controller_id]
            # Remove any mappings for this controller
            for cid, (_, _) in list(self.controller_mappings.items()):
                if cid == controller_id:
                    del self.controller_mappings[cid]
            self.logger.info(f"Removed remote controller from client {client_id}")
            
    def map_controller(self, controller_id: str, port: int) -> bool:
        """
        Map a controller to a specific port.
        
        Args:
            controller_id: ID of the controller (local_X or remote_X)
            port: Port number (1-4)
            
        Returns:
            bool: True if mapping was successful
        """
        if port < 1 or port > self.max_ports:
            return False
            
        # Check if port is already mapped
        for cid, (_, p) in self.controller_mappings.items():
            if p == port:
                del self.controller_mappings[cid]
                
        # Add new mapping
        controller_type = 'local' if controller_id.startswith('local_') else 'remote'
        self.controller_mappings[controller_id] = (controller_type, port)
        self.logger.info(f"Mapped {controller_type} controller {controller_id} to port {port}")
        return True
        
    def unmap_controller(self, controller_id: str) -> bool:
        """
        Remove a controller mapping.
        
        Args:
            controller_id: ID of the controller to unmap
            
        Returns:
            bool: True if unmapping was successful
        """
        if controller_id in self.controller_mappings:
            del self.controller_mappings[controller_id]
            self.logger.info(f"Unmapped controller {controller_id}")
            return True
        return False
        
    def get_controller_state(self, controller_id: str) -> Optional[dict]:
        """Get the current state of a controller."""
        try:
            if controller_id in self.local_controllers:
                joystick = self.local_controllers[controller_id]
                return {
                    'axes': [joystick.get_axis(i) for i in range(joystick.get_numaxes())],
                    'buttons': [joystick.get_button(i) for i in range(joystick.get_numbuttons())],
                    'hats': [joystick.get_hat(i) for i in range(joystick.get_numhats())]
                }
            return None
        except Exception as e:
            self.logger.error(f"Error getting controller state: {e}")
            return None
            
    def get_available_controllers(self) -> List[dict]:
        """Get list of all available controllers (local and remote)."""
        controllers = []
        
        # Add local controllers
        for controller_id, joystick in self.local_controllers.items():
            controllers.append({
                'id': controller_id,
                'name': joystick.get_name(),
                'type': 'local',
                'mapped_port': self.controller_mappings.get(controller_id, (None, None))[1]
            })
            
        # Add remote controllers
        for controller_id, info in self.remote_controllers.items():
            controllers.append({
                'id': controller_id,
                'name': info['name'],
                'type': 'remote',
                'mapped_port': self.controller_mappings.get(controller_id, (None, None))[1]
            })
            
        return controllers
        
    def get_mapped_controllers(self) -> Dict[int, dict]:
        """Get dictionary of port to controller mappings."""
        mapped = {}
        for controller_id, (controller_type, port) in self.controller_mappings.items():
            if controller_type == 'local':
                controller = self.local_controllers.get(controller_id)
                if controller:
                    mapped[port] = {
                        'id': controller_id,
                        'name': controller.get_name(),
                        'type': 'local'
                    }
            else:
                controller = self.remote_controllers.get(controller_id)
                if controller:
                    mapped[port] = {
                        'id': controller_id,
                        'name': controller['name'],
                        'type': 'remote'
                    }
        return mapped 