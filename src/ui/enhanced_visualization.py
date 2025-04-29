# src/ui/enhanced_visualization.py
import pygame
import os
import sys
import traci
from pathlib import Path

# Add project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from src.ui.visualization import Visualization
from src.ui.enhanced_renderer import EnhancedTrafficRenderer
from src.ui.sumo_pygame_mapper import SumoNetworkParser, SumoPygameMapper

class EnhancedVisualization(Visualization):
    """
    Enhanced visualization with improved graphics for traffic simulation.
    """
    def __init__(self, width=800, height=600, title="Enhanced AI Traffic Control Simulation", net_file=None):
        """
        Initialize the enhanced visualization window.
        
        Args:
            width (int): Width of the window in pixels
            height (int): Height of the window in pixels
            title (str): Title of the window
            net_file (str): Path to the SUMO network file
        """
        # Call the parent class constructor
        super().__init__(width, height, title, net_file)
        
        # Set a higher initial zoom
        self.zoom = 2.0
        
        # Center the view initially
        self._center_view()
        
        # Create enhanced renderer when network is loaded
        self.enhanced_renderer = None
        if self.mapper:
            self.enhanced_renderer = EnhancedTrafficRenderer(self.screen, self.mapper, 
                                                           self.offset_x, self.offset_y, self.zoom)
        
        # Mouse tracking for dragging
        self.dragging = False
        self.drag_start = None
        
        # Key toggles for debug information
        self.show_ids = True
        self.show_speeds = True
        self.show_waiting = True
        
        # Add keybindings for toggling debug info
        self.controls_help = [
            "Mouse Drag: Pan view",
            "Mouse Wheel: Zoom in/out",
            "I: Toggle vehicle IDs",
            "S: Toggle speed display",
            "W: Toggle waiting time display",
            "ESC: Quit"
        ]
        
        print("Enhanced visualization initialized")
    
    def _center_view(self):
        """Center the view on the network"""
        if self.mapper:
            # Get network bounds
            min_x, min_y = self.mapper.min_x, self.mapper.min_y
            max_x, max_y = self.mapper.max_x, self.mapper.max_y
            
            # Calculate center of network
            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2
            
            # Set offsets to center the view
            self.offset_x = self.width / 2 - center_x * self.zoom * self.mapper.scale
            self.offset_y = self.height / 2 - center_y * self.zoom * self.mapper.scale
    
    def handle_events(self):
        """Handle pygame events and return whether to continue running"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                # Press ESC to quit
                if event.key == pygame.K_ESCAPE:
                    return False
                # Toggle vehicle IDs
                elif event.key == pygame.K_i:
                    if self.enhanced_renderer:
                        self.show_ids = self.enhanced_renderer.toggle_vehicle_ids()
                # Toggle speed display
                elif event.key == pygame.K_s:
                    if self.enhanced_renderer:
                        self.show_speeds = self.enhanced_renderer.toggle_speeds()
                # Toggle waiting time display
                elif event.key == pygame.K_w:
                    if self.enhanced_renderer:
                        self.show_waiting = self.enhanced_renderer.toggle_waiting_times()
            # Handle mouse panning with left button
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left mouse button
                    self.dragging = True
                    self.drag_start = event.pos
                # Mouse wheel zooming
                elif event.button == 4:  # Scroll up
                    self.zoom *= 1.1
                    if self.enhanced_renderer:
                        self.enhanced_renderer.update_view_settings(
                            self.offset_x, self.offset_y, self.zoom)
                elif event.button == 5:  # Scroll down
                    self.zoom /= 1.1
                    if self.enhanced_renderer:
                        self.enhanced_renderer.update_view_settings(
                            self.offset_x, self.offset_y, self.zoom)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:  # Left mouse button
                    self.dragging = False
            elif event.type == pygame.MOUSEMOTION:
                if self.dragging:
                    # Calculate the drag distance
                    dx = event.pos[0] - self.drag_start[0]
                    dy = event.pos[1] - self.drag_start[1]
                    self.offset_x += dx
                    self.offset_y += dy
                    self.drag_start = event.pos
                    
                    # Update the renderer view settings
                    if self.enhanced_renderer:
                        self.enhanced_renderer.update_view_settings(
                            self.offset_x, self.offset_y, self.zoom)
        
        # Update the renderer view settings if it exists
        if self.enhanced_renderer:
            self.enhanced_renderer.update_view_settings(self.offset_x, self.offset_y, self.zoom)
        
        return True
    
    def draw_vehicle(self, position, size=(10, 5), color=(0, 100, 200), angle=0):
        """Override to use enhanced renderer if available"""
        if self.enhanced_renderer:
            # This is just a compatibility method - real rendering is done through the renderer
            pass
        else:
            # Fall back to original method
            super().draw_vehicle(position, size, color, angle)
    
    def draw_traffic_light(self, position, state):
        """Override to use enhanced renderer if available"""
        if self.enhanced_renderer:
            # This is just a compatibility method - real rendering is done through the renderer
            pass
        else:
            # Fall back to original method
            super().draw_traffic_light(position, state)
    
    def draw_road(self, start_pos, end_pos, width=10):
        """Override to use enhanced renderer if available"""
        if self.enhanced_renderer:
            # This is just a compatibility method - real rendering is done through the renderer
            pass
        else:
            # Fall back to original method
            super().draw_road(start_pos, end_pos, width)
    
    def draw_intersection(self, position, size=20):
        """Override to use enhanced renderer if available"""
        if self.enhanced_renderer:
            # This is just a compatibility method - real rendering is done through the renderer
            pass
        else:
            # Fall back to original method
            super().draw_intersection(position, size)
    
    def draw_help(self):
        """Draw help text with keybinding information"""
        y_offset = self.height - len(self.controls_help) * 20 - 10
        for i, help_text in enumerate(self.controls_help):
            text = self.font.render(help_text, True, (50, 50, 50))
            self.screen.blit(text, (10, y_offset + i * 20))
    
    def draw_sumo_network(self):
        """Draw the SUMO network using the enhanced renderer if available"""
        if self.enhanced_renderer:
            self.enhanced_renderer.render_network()
            
            # Render junctions
            for node_id in self.network_parser.nodes:
                self.enhanced_renderer.render_junction(node_id)
        else:
            # Fall back to original method
            super().draw_sumo_network()