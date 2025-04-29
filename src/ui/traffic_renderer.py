import pygame
import math
import numpy as np
from enum import Enum

# Define colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
GRAY = (200, 200, 200)
DARK_GRAY = (100, 100, 100)
LIGHT_BLUE = (100, 100, 255)
LIGHT_GREEN = (100, 255, 100)

class VehicleType(Enum):
    """Types of vehicles for visualization."""
    PASSENGER = 0
    TRUCK = 1
    BUS = 2
    MOTORCYCLE = 3
    BICYCLE = 4
    EMERGENCY = 5

class TrafficRenderer:
    """
    Renderer for traffic elements such as vehicles and traffic lights.
    """
    def __init__(self, screen, mapper, offset_x=0, offset_y=0, zoom=1.0):
        """
        Initialize the traffic renderer.
        
        Args:
            screen: Pygame screen to draw on
            mapper: SumoPygameMapper for coordinate conversion
            offset_x: X offset for panning the view
            offset_y: Y offset for panning the view
            zoom: Zoom factor for the view
        """
        self.screen = screen
        self.mapper = mapper
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.zoom = zoom
        
        # Load fonts
        self.font = pygame.font.SysFont("Arial", 10)
        
        # Set up vehicle type configurations
        self.vehicle_configs = {
            VehicleType.PASSENGER: {
                "color": BLUE,
                "size": (8, 4),
            },
            VehicleType.TRUCK: {
                "color": DARK_GRAY,
                "size": (10, 5),
            },
            VehicleType.BUS: {
                "color": LIGHT_GREEN,
                "size": (12, 5),
            },
            VehicleType.MOTORCYCLE: {
                "color": MAGENTA,
                "size": (6, 3),
            },
            VehicleType.BICYCLE: {
                "color": CYAN,
                "size": (4, 2),
            },
            VehicleType.EMERGENCY: {
                "color": RED,
                "size": (8, 4),
            }
        }
        
        print("Traffic renderer initialized")
    
    def update_view_settings(self, offset_x, offset_y, zoom):
        """Update the view settings for panning and zooming."""
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.zoom = zoom
    
    def _transform_coordinates(self, x, y):
        """Transform SUMO coordinates to screen coordinates with view settings."""
        pygame_x, pygame_y = self.mapper.sumo_to_pygame(x, y)
        return (pygame_x * self.zoom + self.offset_x, 
                pygame_y * self.zoom + self.offset_y)
    
    def map_vehicle_type(self, sumo_type):
        """Map SUMO vehicle type to our visualization vehicle type."""
        sumo_type = sumo_type.lower()
        if "bus" in sumo_type:
            return VehicleType.BUS
        elif "truck" in sumo_type or "trailer" in sumo_type:
            return VehicleType.TRUCK
        elif "motorcycle" in sumo_type or "moped" in sumo_type:
            return VehicleType.MOTORCYCLE
        elif "bicycle" in sumo_type:
            return VehicleType.BICYCLE
        elif "emergency" in sumo_type or "police" in sumo_type or "ambulance" in sumo_type:
            return VehicleType.EMERGENCY
        else:
            return VehicleType.PASSENGER
    
    def render_vehicle(self, vehicle_id, position, angle, vehicle_type=VehicleType.PASSENGER, 
                      speed=None, waiting_time=None, label=None):
        """
        Render a vehicle with the given properties.
        
        Args:
            vehicle_id: ID of the vehicle
            position: (x, y) position in SUMO coordinates
            angle: Heading angle in degrees (0 = East, 90 = North)
            vehicle_type: VehicleType enum value
            speed: Current speed in m/s (optional)
            waiting_time: Time spent waiting in seconds (optional)
            label: Text label to display (optional)
        """
        # Get the vehicle configuration
        config = self.vehicle_configs.get(vehicle_type, self.vehicle_configs[VehicleType.PASSENGER])
        
        # Transform coordinates
        screen_x, screen_y = self._transform_coordinates(position[0], position[1])
        
        # Adjust the angle for Pygame (SUMO uses different angle convention)
        # In SUMO, 0 = east, 90 = north, while in Pygame we need 0 = east, 90 = south
        pygame_angle = -angle + 90  # This might need adjustment based on your specific SUMO setup
        
        # Calculate vehicle size
        width = config["size"][0] * self.zoom
        height = config["size"][1] * self.zoom
        
        # Create a surface for the vehicle
        vehicle_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        
        # Color based on vehicle type, with variations based on speed if provided
        base_color = config["color"]
        vehicle_color = base_color
        
        # If speed is provided, adjust color intensity
        if speed is not None:
            # Normalize speed to 0-1 range (assuming max speed is around 30 m/s)
            speed_factor = min(1.0, speed / 30.0)
            # Make faster vehicles brighter
            vehicle_color = tuple(min(255, int(c * (0.5 + 0.5 * speed_factor))) for c in base_color)
        
        # If waiting time is provided, add red tint to indicate waiting
        if waiting_time is not None and waiting_time > 0:
            # Normalize waiting time (max considerd is 60 seconds)
            wait_factor = min(1.0, waiting_time / 60.0)
            # Blend with red based on waiting time
            vehicle_color = tuple(min(255, int(c * (1 - wait_factor) + RED[i] * wait_factor)) 
                                 for i, c in enumerate(vehicle_color))
        
        # Fill the vehicle surface with the calculated color
        vehicle_surface.fill(vehicle_color)
        
        # Draw a small triangle to indicate direction
        arrow_points = [
            (width * 0.8, height // 2),  # Tip of arrow
            (width * 0.5, height * 0.2),  # Left corner
            (width * 0.5, height * 0.8),  # Right corner
        ]
        pygame.draw.polygon(vehicle_surface, BLACK, arrow_points)
        
        # Rotate the vehicle surface
        rotated_surface = pygame.transform.rotate(vehicle_surface, pygame_angle)
        rotated_rect = rotated_surface.get_rect(center=(screen_x, screen_y))
        
        # Draw the vehicle
        self.screen.blit(rotated_surface, rotated_rect.topleft)
        
        # Draw the label if provided
        if label:
            label_surface = self.font.render(label, True, WHITE, BLACK)
            label_rect = label_surface.get_rect(center=(screen_x, screen_y - 15 * self.zoom))
            self.screen.blit(label_surface, label_rect.topleft)
    
    def render_traffic_light(self, tl_id, position, state):
        """
        Render a traffic light with the given state.
        
        Args:
            tl_id: ID of the traffic light
            position: (x, y) position in SUMO coordinates
            state: Traffic light state string (e.g., 'GrYy')
        """
        # Transform coordinates
        screen_x, screen_y = self._transform_coordinates(position[0], position[1])
        
        # Increase sizes for better visibility
        tl_radius = 10 * self.zoom  # Increased from 6
        tl_spacing = 6 * self.zoom  # Increased from 4
        tl_box_width = tl_radius * 2 + 8 * self.zoom  # Increased padding
        tl_box_height = (tl_radius * 2 + tl_spacing) * len(state) + 8 * self.zoom
        
        # Draw traffic light box with more contrasting colors
        tl_box_rect = pygame.Rect(
            screen_x - tl_box_width / 2,
            screen_y - tl_box_height / 2,
            tl_box_width,
            tl_box_height
        )
        pygame.draw.rect(self.screen, BLACK, tl_box_rect, border_radius=4)
        pygame.draw.rect(self.screen, GRAY, tl_box_rect.inflate(-4, -4), border_radius=3)
        
        # Draw each light
        y_offset = screen_y - (tl_box_height / 2) + (tl_radius + 4 * self.zoom)
        
        for i, light in enumerate(state):
            # Determine color based on the state character
            if light in ('G', 'g'):  # Green
                color = GREEN
            elif light in ('Y', 'y'):  # Yellow
                color = YELLOW
            elif light in ('R', 'r'):  # Red
                color = RED
            else:  # Off or unknown
                color = DARK_GRAY
            
            # Draw the light with a black outline for better visibility
            pygame.draw.circle(
                self.screen, 
                BLACK, 
                (screen_x, y_offset + i * (tl_radius * 2 + tl_spacing)), 
                tl_radius + 2  # Slightly larger for outline
            )
            pygame.draw.circle(
                self.screen, 
                color, 
                (screen_x, y_offset + i * (tl_radius * 2 + tl_spacing)), 
                tl_radius
            )
            
            # Add a text label for the traffic light ID
            if i == 0:  # Only show on the first light
                id_text = self.font.render(tl_id, True, WHITE, BLACK)
                id_rect = id_text.get_rect(center=(screen_x, y_offset - tl_radius - 10 * self.zoom))
                self.screen.blit(id_text, id_rect.topleft)
    
    def render_network(self, roads=None):
        """
        Render the road network.
        
        Args:
            roads: Optional list of road segments to render, each with format:
                  (start_pos, end_pos, width, color)
        """
        # If roads are provided, render them
        if roads:
            for start_pos, end_pos, width, color in roads:
                # Transform coordinates
                start_x, start_y = self._transform_coordinates(start_pos[0], start_pos[1])
                end_x, end_y = self._transform_coordinates(end_pos[0], end_pos[1])
                
                # Scale width by zoom
                scaled_width = width * self.zoom
                
                # Draw the road
                pygame.draw.line(self.screen, color, (start_x, start_y), (end_x, end_y), int(scaled_width))
        
        # Otherwise, render all edges from the network parser
        else:
            for edge_id, edge_data in self.mapper.net_parser.edges.items():
                shape = self.mapper.get_edge_shape(edge_id)
                if shape and len(shape) >= 2:
                    for i in range(len(shape) - 1):
                        start = shape[i]
                        end = shape[i + 1]
                        
                        # Apply view transformations
                        start = (start[0] * self.zoom + self.offset_x, 
                                 start[1] * self.zoom + self.offset_y)
                        end = (end[0] * self.zoom + self.offset_x, 
                               end[1] * self.zoom + self.offset_y)
                        
                        # Draw the road
                        pygame.draw.line(self.screen, DARK_GRAY, start, end, int(10 * self.zoom))

    def render_junction(self, junction_id):
        """
        Render a junction (intersection).
        
        Args:
            junction_id: ID of the junction in the SUMO network
        """
        # Get the junction position
        pos = self.mapper.get_node_position(junction_id)
        if not pos:
            return
        
        # Transform coordinates
        screen_x, screen_y = pos[0] * self.zoom + self.offset_x, pos[1] * self.zoom + self.offset_y
        
        # Draw the junction
        pygame.draw.circle(self.screen, DARK_GRAY, (screen_x, screen_y), 15 * self.zoom)
        pygame.draw.circle(self.screen, BLACK, (screen_x, screen_y), 15 * self.zoom, width=2)

# Simple test to verify the traffic renderer works
if __name__ == "__main__":
    import os
    import sys
    from pathlib import Path
    
    # Add project root to Python path
    project_root = Path(__file__).resolve().parent.parent.parent
    sys.path.append(str(project_root))
    
    from src.ui.sumo_pygame_mapper import SumoNetworkParser, SumoPygameMapper
    
    # Initialize pygame
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Traffic Renderer Test")
    
    # Path to the SUMO network file
    net_file_path = os.path.join(project_root, "config", "maps", "grid_network.net.xml")
    
    # Parse the network and create mapper
    parser = SumoNetworkParser(net_file_path)
    mapper = SumoPygameMapper(parser, 800, 600)
    
    # Create traffic renderer
    renderer = TrafficRenderer(screen, mapper)
    
    # Main loop
    clock = pygame.time.Clock()
    running = True
    
    # Create some test vehicles at different positions
    test_vehicles = [
        # (id, position, angle, type, speed, waiting_time, label)
        ("v1", (25, 25), 0, VehicleType.PASSENGER, 10, 0, "Car1"),
        ("v2", (75, 25), 90, VehicleType.TRUCK, 5, 10, "Truck"),
        ("v3", (25, 75), 180, VehicleType.BUS, 0, 30, "Bus"),
        ("v4", (75, 75), 270, VehicleType.EMERGENCY, 15, 0, "Ambulance"),
    ]
    
    # Test traffic lights
    test_tls = [
        # (id, position, state)
        ("tl1", (25, 25), "GrYr"),
        ("tl2", (75, 25), "rGry"),
        ("tl3", (25, 75), "rrGG"),
        ("tl4", (75, 75), "YYrr"),
    ]
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
        
        # Clear the screen
        screen.fill(WHITE)
        
        # Render the network
        renderer.render_network()
        
        # Render test vehicles
        for v_id, pos, angle, v_type, speed, wait, label in test_vehicles:
            renderer.render_vehicle(v_id, pos, angle, v_type, speed, wait, label)
        
        # Render test traffic lights
        for tl_id, pos, state in test_tls:
            renderer.render_traffic_light(tl_id, pos, state)
        
        # Render junctions
        for junction_id in list(parser.nodes.keys())[:4]:  # Just render the first 4 junctions for testing
            renderer.render_junction(junction_id)
        
        # Update the display
        pygame.display.flip()
        
        # Control the frame rate
        clock.tick(30)
    
    pygame.quit()