import pygame
import os
from pathlib import Path
from src.ui.sumo_pygame_mapper import SumoNetworkParser, SumoPygameMapper

# Define colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
GRAY = (200, 200, 200)
DARK_GRAY = (100, 100, 100)

class Visualization:
    """
    Pygame-based visualization for the traffic simulation.
    """
    def __init__(self, width=800, height=600, title="AI Traffic Control Simulation", net_file=None):
        """
        Initialize the visualization window.
        
        Args:
            width (int): Width of the window in pixels
            height (int): Height of the window in pixels
            title (str): Title of the window
            net_file (str): Path to the SUMO network file
        """
        # Initialize pygame
        pygame.init()
        
        # Set up the display
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption(title)
        
        # Clock for controlling frame rate
        self.clock = pygame.time.Clock()
        self.fps = 30
        
        # Load assets
        self.assets_path = Path(__file__).resolve().parent.parent.parent / "assets"
        self.assets = self._load_assets()
        
        # SUMO Network mapping
        self.net_file = net_file
        self.network_parser = None
        self.mapper = None
        if net_file:
            self._setup_network_mapping()
        
        # Simulation view settings
        self.offset_x = 0
        self.offset_y = 0
        self.zoom = 1.0
        
        # Font for displaying information
        self.font = pygame.font.SysFont("Arial", 16)
        
        print(f"Visualization initialized with window size {width}x{height}")
    
    def _load_assets(self):
        """Load image assets for the visualization"""
        assets = {}
        
        # Create the assets directory if it doesn't exist
        os.makedirs(self.assets_path, exist_ok=True)
        
        # For now, return empty assets dictionary
        # We'll add real assets later
        return assets
    
    def _setup_network_mapping(self):
        """Set up the SUMO to Pygame coordinate mapping."""
        if not os.path.exists(self.net_file):
            print(f"Warning: Network file not found: {self.net_file}")
            return
        
        try:
            self.network_parser = SumoNetworkParser(self.net_file)
            self.mapper = SumoPygameMapper(self.network_parser, self.width, self.height)
            print("SUMO network successfully loaded and mapped to Pygame coordinates")
        except Exception as e:
            print(f"Error setting up network mapping: {str(e)}")
    
    def handle_events(self):
        """Handle pygame events and return whether to continue running"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                # Press ESC to quit
                if event.key == pygame.K_ESCAPE:
                    return False
                # Arrow keys to move the view
                elif event.key == pygame.K_LEFT:
                    self.offset_x += 20
                elif event.key == pygame.K_RIGHT:
                    self.offset_x -= 20
                elif event.key == pygame.K_UP:
                    self.offset_y += 20
                elif event.key == pygame.K_DOWN:
                    self.offset_y -= 20
                # Zoom controls
                elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                    self.zoom *= 1.1
                elif event.key == pygame.K_MINUS:
                    self.zoom /= 1.1
        
        return True
    
    def clear(self):
        """Clear the screen to prepare for drawing"""
        self.screen.fill(WHITE)
    
    def draw_text(self, text, x, y, color=BLACK):
        """Draw text on the screen"""
        text_surface = self.font.render(text, True, color)
        self.screen.blit(text_surface, (x, y))
    
    def draw_stats(self, stats):
        """Draw simulation statistics"""
        y_offset = 10
        for key, value in stats.items():
            self.draw_text(f"{key}: {value}", 10, y_offset)
            y_offset += 20
    
    def draw_road(self, start_pos, end_pos, width=10):
        """Draw a road segment"""
        # Transform coordinates based on offset and zoom
        start_x = start_pos[0] * self.zoom + self.offset_x
        start_y = start_pos[1] * self.zoom + self.offset_y
        end_x = end_pos[0] * self.zoom + self.offset_x
        end_y = end_pos[1] * self.zoom + self.offset_y
        
        # Draw the road (gray background)
        pygame.draw.line(self.screen, DARK_GRAY, (start_x, start_y), (end_x, end_y), width)
        
        # Draw lane markings (dashed white line)
        # This is a simplified representation; you might want to improve it later
        length = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
        if length > 0:
            dx = (end_x - start_x) / length
            dy = (end_y - start_y) / length
            
            # Draw dashed line
            dash_length = 5
            gap_length = 5
            distance = 0
            drawing = True
            
            while distance < length:
                if drawing:
                    line_start = (start_x + distance * dx, start_y + distance * dy)
                    line_end = (start_x + min(distance + dash_length, length) * dx, 
                                start_y + min(distance + dash_length, length) * dy)
                    pygame.draw.line(self.screen, WHITE, line_start, line_end, 1)
                distance += dash_length if drawing else gap_length
                drawing = not drawing
    
    def draw_intersection(self, position, size=20):
        """Draw a road intersection"""
        # Transform coordinates based on offset and zoom
        x = position[0] * self.zoom + self.offset_x
        y = position[1] * self.zoom + self.offset_y
        transformed_size = size * self.zoom
        
        # Draw the intersection as a dark gray rectangle
        rect = pygame.Rect(
            x - transformed_size/2, 
            y - transformed_size/2, 
            transformed_size, 
            transformed_size
        )
        pygame.draw.rect(self.screen, DARK_GRAY, rect)
    
    def draw_traffic_light(self, position, state):
        """
        Draw a traffic light with the given state.
        
        Args:
            position (tuple): (x, y) position of the traffic light
            state (str): Traffic light state (e.g., 'G' for green, 'Y' for yellow, 'R' for red)
        """
        # Transform coordinates based on offset and zoom
        x = position[0] * self.zoom + self.offset_x
        y = position[1] * self.zoom + self.offset_y
        radius = 5 * self.zoom
        
        # Determine color based on state
        if state == 'G':
            color = GREEN
        elif state == 'Y':
            color = YELLOW
        else:  # 'R' or any other state
            color = RED
        
        # Draw the traffic light as a colored circle
        pygame.draw.circle(self.screen, color, (int(x), int(y)), int(radius))
    
    def draw_vehicle(self, position, size=(10, 5), color=BLUE, angle=0):
        """
        Draw a vehicle.
        
        Args:
            position (tuple): (x, y) position of the vehicle
            size (tuple): (width, height) of the vehicle
            color (tuple): RGB color of the vehicle
            angle (float): Rotation angle in degrees
        """
        # Transform coordinates based on offset and zoom
        x = position[0] * self.zoom + self.offset_x
        y = position[1] * self.zoom + self.offset_y
        width = size[0] * self.zoom
        height = size[1] * self.zoom
        
        # Create a surface for the vehicle
        vehicle_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        vehicle_surface.fill(color)
        
        # Rotate the vehicle if needed
        if angle != 0:
            vehicle_surface = pygame.transform.rotate(vehicle_surface, angle)
        
        # Get the rect for the rotated surface
        rect = vehicle_surface.get_rect(center=(x, y))
        
        # Draw the vehicle
        self.screen.blit(vehicle_surface, rect.topleft)
    
    def draw_sumo_network(self):
        """Draw the SUMO network on the screen."""
        if not self.mapper:
            return
        
        # Draw all edges (roads)
        for edge_id, edge_data in self.network_parser.edges.items():
            shape = self.mapper.get_edge_shape(edge_id)
            if shape and len(shape) >= 2:
                for i in range(len(shape) - 1):
                    start = shape[i]
                    end = shape[i + 1]
                    # Apply visualization offsets and zoom
                    start = (start[0] * self.zoom + self.offset_x, start[1] * self.zoom + self.offset_y)
                    end = (end[0] * self.zoom + self.offset_x, end[1] * self.zoom + self.offset_y)
                    self.draw_road(start, end)
        
        # Draw all nodes (junctions)
        for node_id, _ in self.network_parser.nodes.items():
            pos = self.mapper.get_node_position(node_id)
            if pos:
                # Apply visualization offsets and zoom
                pos = (pos[0] * self.zoom + self.offset_x, pos[1] * self.zoom + self.offset_y)
                self.draw_intersection(pos)
    
    def update(self):
        """Update the display"""
        pygame.display.flip()
        self.clock.tick(self.fps)
    
    def close(self):
        """Close the visualization"""
        pygame.quit()

# Simple test to verify the visualization works with a SUMO network
if __name__ == "__main__":
    import os
    from pathlib import Path
    
    # Get the path to the SUMO network file
    project_root = Path(__file__).resolve().parent.parent.parent
    net_file_path = os.path.join(project_root, "config", "maps", "grid_network.net.xml")
    
    # Create the visualization with the SUMO network
    viz = Visualization(net_file=net_file_path)
    running = True
    
    while running:
        running = viz.handle_events()
        
        viz.clear()
        
        # Draw the SUMO network
        viz.draw_sumo_network()
        
        # Draw some example vehicles and traffic lights
        # These positions should be derived from the SUMO simulation in the future
        viz.draw_vehicle((400, 300))
        viz.draw_vehicle((450, 300))
        
        # Draw sample statistics
        viz.draw_stats({
            "Vehicles": 2,
            "Average Wait Time": "5.2s",
            "Throughput": "85 veh/h",
            "Mode": "SUMO Network Test"
        })
        
        viz.update()
    
    viz.close()