# src/ui/enhanced_sumo_visualization.py
import pygame
import os
import sys
import traci
from pathlib import Path

# Add project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from src.ui.sumo_visualization import SumoVisualization
from src.ui.enhanced_renderer import EnhancedTrafficRenderer

class EnhancedSumoVisualization(SumoVisualization):
    """
    Enhanced SUMO visualization with improved graphics.
    """
    def __init__(self, sumo_config_path, width=1024, height=768, use_gui=False):
        """
        Initialize the enhanced SUMO visualization.
        
        Args:
            sumo_config_path (str): Path to the SUMO configuration file
            width (int): Width of the visualization window
            height (int): Height of the visualization window
            use_gui (bool): Whether to use SUMO GUI alongside the visualization
        """
        # Call the parent class constructor
        super().__init__(sumo_config_path, width, height, use_gui)
        
        # Set a better initial view position and zoom
        self.visualization.zoom = 2.0
        self._center_view()
        
        # Replace the traffic renderer with our enhanced version
        self.traffic_renderer = EnhancedTrafficRenderer(self.visualization.screen, self.mapper,
                                                     self.visualization.offset_x, 
                                                     self.visualization.offset_y,
                                                     self.visualization.zoom)
        
        # Mouse tracking for dragging
        self.visualization.dragging = False
        self.visualization.drag_start = None
        
        # Update window title
        pygame.display.set_caption("Enhanced SUMO Traffic Visualization")
        
        print("Enhanced SUMO visualization initialized")
    
    def _center_view(self):
        """Center the view on the simulation area"""
        if hasattr(self.mapper, 'min_x') and hasattr(self.mapper, 'max_x'):
            # Calculate center of the network
            center_x = (self.mapper.min_x + self.mapper.max_x) / 2
            center_y = (self.mapper.min_y + self.mapper.max_y) / 2
            
            # Set offsets to center the view
            self.visualization.offset_x = self.visualization.width / 2 - center_x * self.visualization.zoom * self.mapper.scale
            self.visualization.offset_y = self.visualization.height / 2 - center_y * self.visualization.zoom * self.mapper.scale
            
            # Update traffic renderer
            self.traffic_renderer.update_view_settings(
                self.visualization.offset_x,
                self.visualization.offset_y,
                self.visualization.zoom
            )
    
    def _draw_ui_overlay(self):
        """Draw UI overlay with help text"""
        # Draw help text in the bottom left
        help_texts = [
            "Mouse Drag: Pan view",
            "Mouse Wheel: Zoom in/out",
            "I: Toggle vehicle IDs",
            "S: Toggle speed display",
            "W: Toggle waiting time display",
            "ESC: Quit"
        ]
        
        font = pygame.font.SysFont("Arial", 14)
        y_offset = self.visualization.height - len(help_texts) * 20 - 10
        
        for i, help_text in enumerate(help_texts):
            text = font.render(help_text, True, (50, 50, 50))
            self.visualization.screen.blit(text, (10, y_offset + i * 20))
    
    def step(self, delay_ms=100):
        """
        Perform one simulation and visualization step with delay to slow down simulation.
        Override to use enhanced rendering.
        
        Args:
            delay_ms (int): Delay in milliseconds to slow down the simulation
        """
        if not self.running:
            return False
        
        try:
            # Add delay to slow down simulation
            pygame.time.delay(delay_ms)
            
            # Step the SUMO simulation
            self.simulation.step()
            
            # Update statistics
            self._update_stats()
            
            # Handle visualization events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.close()
                    return False
                elif event.type == pygame.KEYDOWN:
                    # Press ESC to quit
                    if event.key == pygame.K_ESCAPE:
                        self.close()
                        return False
                    # Toggle vehicle IDs with I key
                    elif event.key == pygame.K_i:
                        self.traffic_renderer.toggle_vehicle_ids()
                    # Toggle speed display with S key
                    elif event.key == pygame.K_s:
                        self.traffic_renderer.toggle_speeds()
                    # Toggle waiting time display with W key
                    elif event.key == pygame.K_w:
                        self.traffic_renderer.toggle_waiting_times()
                # Handle mouse panning with left button
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left mouse button
                        self.visualization.dragging = True
                        self.visualization.drag_start = event.pos
                    # Mouse wheel zooming
                    elif event.button == 4:  # Scroll up
                        self.visualization.zoom *= 1.1
                        self.traffic_renderer.update_view_settings(
                            self.visualization.offset_x, 
                            self.visualization.offset_y, 
                            self.visualization.zoom)
                    elif event.button == 5:  # Scroll down
                        self.visualization.zoom /= 1.1
                        self.traffic_renderer.update_view_settings(
                            self.visualization.offset_x, 
                            self.visualization.offset_y, 
                            self.visualization.zoom)
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:  # Left mouse button
                        self.visualization.dragging = False
                elif event.type == pygame.MOUSEMOTION:
                    if self.visualization.dragging:
                        # Calculate the drag distance
                        dx = event.pos[0] - self.visualization.drag_start[0]
                        dy = event.pos[1] - self.visualization.drag_start[1]
                        self.visualization.offset_x += dx
                        self.visualization.offset_y += dy
                        self.visualization.drag_start = event.pos
                        
                        # Update the renderer view settings
                        self.traffic_renderer.update_view_settings(
                            self.visualization.offset_x, 
                            self.visualization.offset_y, 
                            self.visualization.zoom)
            
            # Clear the visualization
            self.visualization.clear()
            
            # Update renderer with current visualization settings
            self.traffic_renderer.update_view_settings(
                self.visualization.offset_x,
                self.visualization.offset_y,
                self.visualization.zoom
            )
            
            # Render the network
            self.traffic_renderer.render_network()
            
            # Render all vehicles
            vehicles = traci.vehicle.getIDList()
            for vehicle_id in vehicles:
                try:
                    # Get vehicle position
                    position = traci.vehicle.getPosition(vehicle_id)
                    
                    # Get vehicle angle (heading)
                    angle = traci.vehicle.getAngle(vehicle_id)
                    
                    # Get vehicle type
                    v_type = traci.vehicle.getTypeID(vehicle_id)
                    vehicle_type = self._map_vehicle_type(v_type)
                    
                    # Get speed and waiting time
                    speed = traci.vehicle.getSpeed(vehicle_id)
                    waiting_time = traci.vehicle.getWaitingTime(vehicle_id)
                    
                    # Render the vehicle
                    self.traffic_renderer.render_vehicle(
                        vehicle_id, position, angle, vehicle_type, 
                        speed, waiting_time, None  # Skip label for better performance
                    )
                
                except Exception as e:
                    print(f"Error rendering vehicle {vehicle_id}: {e}")
                    continue

            # Render junctions
            for junction_id in self.mapper.net_parser.nodes.keys():
                self.traffic_renderer.render_junction(junction_id)
            
            # Render all traffic lights
            for tl_id in traci.trafficlight.getIDList():
                try:
                    # Get traffic light state
                    state = traci.trafficlight.getRedYellowGreenState(tl_id)
                    
                    # Get position
                    if tl_id in self.traffic_light_positions:
                        position = self.traffic_light_positions[tl_id]
                        
                        # Render the traffic light
                        self.traffic_renderer.render_traffic_light(tl_id, position, state)
                
                except Exception as e:
                    print(f"Error rendering traffic light {tl_id}: {e}")
                    continue
            
            # Render statistics
            formatted_stats = {
                "Vehicles": self.stats["vehicles"],
                "Avg Speed": f"{self.stats['avg_speed']:.2f} m/s",
                "Avg Wait Time": f"{self.stats['avg_wait_time']:.2f} s",
                "Throughput": self.stats["throughput"],
                "Simulation Time": f"{self.stats['step']:.1f} s",
                "Mode": self.stats["mode"]
            }
            self.visualization.draw_stats(formatted_stats)
            
            # Draw additional UI overlay
            self._draw_ui_overlay()
            
            # Update the visualization
            self.visualization.update()
            
            return True
        
        except Exception as e:
            print(f"Error in simulation step: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _map_vehicle_type(self, sumo_type):
        """Map SUMO vehicle type to our internal vehicle type"""
        sumo_type = sumo_type.lower()
        if "bus" in sumo_type:
            return "bus"
        elif "truck" in sumo_type or "trailer" in sumo_type:
            return "truck"
        elif "emergency" in sumo_type or "police" in sumo_type or "ambulance" in sumo_type:
            return "emergency"
        else:
            return "car"