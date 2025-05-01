import platform
import logging
from typing import Dict, List, Optional
import pygame

class ControllerManager:
    def __init__(self):
        """Initialize the controller manager."""
        self.logger = logging.getLogger('ControllerManager')
        self.running = False
        self.controllers: Dict[str, pygame.joystick.Joystick] = {}
        
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
        """Scan for connected controllers."""
        try:
            # Initialize all connected controllers
            for i in range(pygame.joystick.get_count()):
                joystick = pygame.joystick.Joystick(i)
                joystick.init()
                self.controllers[str(joystick.get_id())] = joystick
                self.logger.info(f"Found controller: {joystick.get_name()}")
        except Exception as e:
            self.logger.error(f"Error scanning controllers: {e}")
            
    def get_controller_state(self, controller_id: str) -> Optional[dict]:
        """Get the current state of a controller."""
        try:
            if controller_id in self.controllers:
                joystick = self.controllers[controller_id]
                return {
                    'axes': [joystick.get_axis(i) for i in range(joystick.get_numaxes())],
                    'buttons': [joystick.get_button(i) for i in range(joystick.get_numbuttons())],
                    'hats': [joystick.get_hat(i) for i in range(joystick.get_numhats())]
                }
            return None
        except Exception as e:
            self.logger.error(f"Error getting controller state: {e}")
            return None
            
    def get_connected_controllers(self) -> List[dict]:
        """Get list of connected controllers."""
        return [
            {
                'id': controller_id,
                'name': controller.get_name()
            }
            for controller_id, controller in self.controllers.items()
        ] 