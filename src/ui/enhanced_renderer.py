import os
import pygame
import math
from pathlib import Path

class EnhancedTrafficRenderer:
    """
    Enhanced renderer for traffic elements with improved graphics.
    """
    def __init__(self, screen, mapper, offset_x=0, offset_y=0, zoom=1.0):  # Increased default zoom
        """
        Initialize the enhanced traffic renderer.
        
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
        self.id_font = pygame.font.SysFont("Arial", 8)
        
        # Set default colors (used as fallback when sprites aren't available)
        self.colors = {
            "car": (0, 100, 200),      # Blue
            "bus": (0, 150, 0),        # Green
            "truck": (120, 120, 120),  # Gray
            "emergency": (255, 0, 0),  # Red
            "road": (80, 80, 80),      # Dark Gray
            "lane_marking": (255, 255, 255),  # White
            "traffic_light_housing": (50, 50, 50),  # Dark Gray
            "red_light": (255, 0, 0),  # Red
            "yellow_light": (255, 255, 0),  # Yellow
            "green_light": (0, 255, 0),  # Green
            "junction": (100, 100, 100)  # Gray
        }
        
        # Load vehicle sprites
        self.vehicle_sprites = self._load_vehicle_sprites()
        
        # Create glow surfaces for traffic lights
        self.glow_surfaces = self._create_glow_surfaces()
        
        # Debug options
        self.show_vehicle_ids = True
        self.show_speeds = True
        self.show_waiting_times = True
        
        print("Enhanced traffic renderer initialized")
    
    def _load_vehicle_sprites(self):
        """Load vehicle sprite images"""
        sprites = {}
        project_root = Path(__file__).resolve().parent.parent.parent
        vehicles_dir = project_root / "assets" / "vehicles"
        
        # Create directory if it doesn't exist
        os.makedirs(vehicles_dir, exist_ok=True)
        
        # Try to load each vehicle type sprite
        for vehicle_type in ["car", "bus", "truck", "emergency"]:
            sprite_path = vehicles_dir / f"{vehicle_type}.png"
            if sprite_path.exists():
                try:
                    sprites[vehicle_type] = pygame.image.load(str(sprite_path))
                    print(f"Loaded sprite for {vehicle_type} from {sprite_path}")
                except pygame.error as e:
                    print(f"Error loading {vehicle_type} sprite: {e}")
                    sprites[vehicle_type] = None
            else:
                print(f"No sprite found for {vehicle_type} at {sprite_path}")
                sprites[vehicle_type] = None
        
        return sprites
    
    def _create_glow_surfaces(self):
        """Create glow effect surfaces for traffic lights"""
        glow_surfaces = {}
        
        for color_name in ["red_light", "yellow_light", "green_light"]:
            base_color = self.colors[color_name]
            
            # Create surfaces of different sizes for the glow effect
            for size in [12, 16, 20, 24]:
                # Create a surface with alpha channel
                surface = pygame.Surface((size, size), pygame.SRCALPHA)
                
                # Calculate center and radius
                center = (size // 2, size // 2)
                max_radius = size // 2
                
                # Draw concentric circles with decreasing alpha
                for radius in range(max_radius, 0, -1):
                    alpha = 150 * (radius / max_radius) ** 2  # Non-linear falloff
                    glow_color = (*base_color, int(alpha))
                    pygame.draw.circle(surface, glow_color, center, radius)
                
                # Store in dictionary
                glow_surfaces[(color_name, size)] = surface
        
        return glow_surfaces
    
    def update_view_settings(self, offset_x, offset_y, zoom):
        """Update the view settings for panning and zooming."""
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.zoom = zoom
    
    def toggle_vehicle_ids(self):
        """Toggle display of vehicle IDs"""
        self.show_vehicle_ids = not self.show_vehicle_ids
        print(f"Vehicle IDs display: {'On' if self.show_vehicle_ids else 'Off'}")
        return self.show_vehicle_ids
    
    def toggle_speeds(self):
        """Toggle display of vehicle speeds"""
        self.show_speeds = not self.show_speeds
        print(f"Vehicle speeds display: {'On' if self.show_speeds else 'Off'}")
        return self.show_speeds
    
    def toggle_waiting_times(self):
        """Toggle display of vehicle waiting times"""
        self.show_waiting_times = not self.show_waiting_times
        print(f"Vehicle waiting times display: {'On' if self.show_waiting_times else 'Off'}")
        return self.show_waiting_times
    
    def _transform_coordinates(self, x, y):
        """Transform SUMO coordinates to screen coordinates with view settings."""
        pygame_x, pygame_y = self.mapper.sumo_to_pygame(x, y)
        return (pygame_x * self.zoom + self.offset_x, 
                pygame_y * self.zoom + self.offset_y)
    
    def render_vehicle(self, vehicle_id, position, angle, vehicle_type, 
                      speed=None, waiting_time=None, label=None):
        """
        Render a vehicle with improved graphics.
        
        Args:
            vehicle_id: ID of the vehicle
            position: (x, y) position in SUMO coordinates
            angle: Heading angle in degrees (0 = East, 90 = North)
            vehicle_type: Type of vehicle ('car', 'bus', 'truck', 'emergency')
            speed: Current speed in m/s (optional)
            waiting_time: Time spent waiting in seconds (optional)
            label: Text label to display (optional)
        """
        # Transform coordinates
        screen_x, screen_y = self._transform_coordinates(position[0], position[1])
        
        # Convert angle to pygame angle (SUMO: 0 = east, 90 = north, Pygame rotation: clockwise)
        pygame_angle = -angle + 90 - angle  # This adjustment may need calibration based on sprite orientation
        
        # Determine if the vehicle is waiting
        is_waiting = waiting_time is not None and waiting_time > 0
        
        # Determine vehicle size based on type (now 1.5x larger)
        if vehicle_type == 'emergency':
            base_width, base_height = 18, 9
        elif vehicle_type == 'truck':
            base_width, base_height = 24, 12
        elif vehicle_type == 'bus':
            base_width, base_height = 27, 10
        else:  # car or default
            base_width, base_height = 15, 7
        
        # Scale by zoom factor
        width = base_width * self.zoom
        height = base_height * self.zoom
        
        # Determine sprite to use based on vehicle type
        sprite_key = 'car'  # Default
        if vehicle_type == 'emergency':
            sprite_key = 'emergency'
        elif vehicle_type == 'truck':
            sprite_key = 'truck'
        elif vehicle_type == 'bus':
            sprite_key = 'bus'
        
        # Get appropriate sprite
        sprite = self.vehicle_sprites.get(sprite_key)
        
        if sprite is not None:
            # We have a sprite for this vehicle type
            # Scale sprite to the desired size
            scaled_sprite = pygame.transform.scale(sprite, (int(width), int(height)))
            
            # If waiting, create a red tinted copy
            if is_waiting:
                # Create a red surface with alpha
                red_overlay = pygame.Surface(scaled_sprite.get_size(), pygame.SRCALPHA)
                red_overlay.fill((255, 0, 0, 128))  # Semi-transparent red
                
                # Apply the overlay to the sprite
                waiting_sprite = scaled_sprite.copy()
                waiting_sprite.blit(red_overlay, (0, 0))
                scaled_sprite = waiting_sprite
            
            # Flash the sprite if waiting for more than 5 seconds
            flash = False
            if is_waiting and waiting_time > 5.0:
                # Flash at a rate dependent on waiting time (longer wait = faster flash)
                flash_rate = max(0.5, min(5, waiting_time / 5.0))
                flash = (pygame.time.get_ticks() / (500 / flash_rate)) % 2 > 1
            
            if flash:
                # Create a bright flash overlay
                flash_overlay = pygame.Surface(scaled_sprite.get_size(), pygame.SRCALPHA)
                flash_overlay.fill((255, 255, 255, 128))  # Semi-transparent white
                scaled_sprite.blit(flash_overlay, (0, 0))
            
            # Rotate the sprite
            rotated_sprite = pygame.transform.rotate(scaled_sprite, pygame_angle)
            sprite_rect = rotated_sprite.get_rect(center=(screen_x, screen_y))
            
            # Draw the sprite
            self.screen.blit(rotated_sprite, sprite_rect.topleft)
        else:
            # Fallback to drawing a rectangle
            # Create a surface for the vehicle
            vehicle_surface = pygame.Surface((width, height), pygame.SRCALPHA)
            
            # Color based on vehicle type
            color = self.colors.get(vehicle_type, self.colors["car"])
            
            # If waiting, make it red
            if is_waiting:
                # Blend color with red based on waiting time
                wait_factor = min(1.0, waiting_time / 60.0)
                color = tuple(int(c * (1 - wait_factor) + 255 * wait_factor) for c in color[:3])
            
            # Flash if waiting for more than 5 seconds
            flash = False
            if is_waiting and waiting_time > 5.0:
                flash_rate = max(0.5, min(5, waiting_time / 5.0))
                flash = (pygame.time.get_ticks() / (500 / flash_rate)) % 2 > 1
            
            # Fill the vehicle surface
            if flash:
                vehicle_surface.fill((255, 255, 255))  # White flash
            else:
                vehicle_surface.fill(color)
            
            # Draw a direction indicator (arrow)
            arrow_points = [
                (width * 0.8, height // 2),  # Tip of arrow
                (width * 0.5, height * 0.2),  # Left corner
                (width * 0.5, height * 0.8),  # Right corner
            ]
            pygame.draw.polygon(vehicle_surface, (0, 0, 0), arrow_points)
            
            # Rotate and position
            rotated_surface = pygame.transform.rotate(vehicle_surface, pygame_angle)
            rotated_rect = rotated_surface.get_rect(center=(screen_x, screen_y))
            
            # Draw the vehicle
            self.screen.blit(rotated_surface, rotated_rect.topleft)
        
        # Draw vehicle ID if enabled
        label_y_offset = height / 2 + 5
        if self.show_vehicle_ids:
            id_text = self.id_font.render(vehicle_id, True, (255, 255, 255), (0, 0, 0, 180))
            id_rect = id_text.get_rect(center=(screen_x, screen_y + label_y_offset))
            self.screen.blit(id_text, id_rect.topleft)
            label_y_offset += id_rect.height + 2
        
        # Draw speed if enabled
        if self.show_speeds and speed is not None:
            speed_text = self.id_font.render(f"{speed:.1f} m/s", True, (255, 255, 255), (0, 0, 100, 180))
            speed_rect = speed_text.get_rect(center=(screen_x, screen_y + label_y_offset))
            self.screen.blit(speed_text, speed_rect.topleft)
            label_y_offset += speed_rect.height + 2
        
        # Draw waiting time if enabled and vehicle is waiting
        if self.show_waiting_times and is_waiting:
            wait_text = self.id_font.render(f"Wait: {waiting_time:.1f}s", True, (255, 255, 255), (150, 0, 0, 180))
            wait_rect = wait_text.get_rect(center=(screen_x, screen_y + label_y_offset))
            self.screen.blit(wait_text, wait_rect.topleft)
    
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
        
        # Calculate sizes based on zoom (increased by 50%)
        housing_width = 45 * self.zoom
        housing_height = (len(state) * 30 + 15) * self.zoom
        light_radius = 9 * self.zoom
        light_spacing = 30 * self.zoom
        
        # Draw the traffic light housing
        housing_rect = pygame.Rect(
            screen_x - housing_width / 2,
            screen_y - housing_height / 2,
            housing_width,
            housing_height
        )
        
        # Draw the outer housing with a slight bevel
        pygame.draw.rect(self.screen, (30, 30, 30), housing_rect, border_radius=int(5 * self.zoom))
        pygame.draw.rect(self.screen, self.colors["traffic_light_housing"], 
                        housing_rect.inflate(-4, -4), border_radius=int(3 * self.zoom))
        
        # Draw the ID on top of the traffic light
        id_text = self.font.render(tl_id, True, (255, 255, 255))
        id_rect = id_text.get_rect(center=(screen_x, screen_y - housing_height / 2 - 10 * self.zoom))
        self.screen.blit(id_text, id_rect.topleft)
        
        # Draw each light
        for i, light in enumerate(state):
            # Calculate position
            light_y = screen_y - housing_height / 2 + (i + 0.5) * light_spacing + 5 * self.zoom
            
            # Determine color based on the state character
            if light in ('G', 'g'):  # Green
                color = self.colors["green_light"]
                glow_color = "green_light"
            elif light in ('Y', 'y'):  # Yellow
                color = self.colors["yellow_light"]
                glow_color = "yellow_light"
            elif light in ('r', 'R'):  # Red
                color = self.colors["red_light"]
                glow_color = "red_light"
            else:  # Off or unknown
                color = (80, 80, 80)
                glow_color = None
            
            # Draw glow effect first if it's on
            if glow_color:
                # Get appropriate sized glow surface
                glow_size = int(24 * self.zoom)
                glow_size = min(24, max(12, glow_size))  # Clamp to available sizes
                
                glow_key = (glow_color, glow_size)
                if glow_key in self.glow_surfaces:
                    glow_surface = self.glow_surfaces[glow_key]
                    glow_rect = glow_surface.get_rect(center=(screen_x, light_y))
                    self.screen.blit(glow_surface, glow_rect.topleft)
            
            # Draw the light circle with a black outline for better visibility
            pygame.draw.circle(self.screen, (0, 0, 0), (int(screen_x), int(light_y)), 
                              int(light_radius + 1))
            pygame.draw.circle(self.screen, color, (int(screen_x), int(light_y)), 
                              int(light_radius))
            
            # Add a small reflection highlight
            highlight_pos = (int(screen_x - light_radius/3), int(light_y - light_radius/3))
            highlight_radius = max(1, int(light_radius/4))
            pygame.draw.circle(self.screen, (255, 255, 255, 180), highlight_pos, highlight_radius)
    
    def render_network(self, roads=None):
        """
        Render the road network with improved graphics.
        
        Args:
            roads: Optional list of road segments to render, each with format:
                  (start_pos, end_pos, width, color)
        """
        # If roads are explicitly provided, render them
        if roads:
            for start_pos, end_pos, width, color in roads:
                # Transform coordinates
                start_x, start_y = self._transform_coordinates(start_pos[0], start_pos[1])
                end_x, end_y = self._transform_coordinates(end_pos[0], end_pos[1])
                
                # Scale width by zoom
                scaled_width = width * self.zoom
                
                # Draw the road
                pygame.draw.line(self.screen, color, (start_x, start_y), (end_x, end_y), int(scaled_width))
                
                # Draw lane markings
                length = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
                if length > 0:
                    dx = (end_x - start_x) / length
                    dy = (end_y - start_y) / length
                    
                    # Draw dashed line
                    dash_length = 5 * self.zoom
                    gap_length = 5 * self.zoom
                    distance = 0
                    drawing = True
                    
                    while distance < length:
                        if drawing:
                            line_start = (start_x + distance * dx, start_y + distance * dy)
                            line_end = (start_x + min(distance + dash_length, length) * dx, 
                                        start_y + min(distance + dash_length, length) * dy)
                            pygame.draw.line(self.screen, self.colors["lane_marking"], 
                                           line_start, line_end, 1)
                        distance += dash_length if drawing else gap_length
                        drawing = not drawing
        
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
                        
                        # Calculate length for lane markings
                        road_length = math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
                        
                        # Draw the road (increased width by 50%)
                        road_width = 50 * self.zoom
                        pygame.draw.line(self.screen, self.colors["road"], start, end, int(road_width))
                        
                        # Draw lane markings if long enough
                        if road_length > 30 * self.zoom:
                            # Normalize direction
                            if road_length > 0:
                                dx = (end[0] - start[0]) / road_length
                                dy = (end[1] - start[1]) / road_length
                                
                                # Draw dashed line
                                dash_length = 5 * self.zoom
                                gap_length = 5 * self.zoom
                                distance = 0
                                drawing = True
                                
                                while distance < road_length:
                                    if drawing:
                                        line_start = (start[0] + distance * dx, start[1] + distance * dy)
                                        line_end = (start[0] + min(distance + dash_length, road_length) * dx, 
                                                    start[1] + min(distance + dash_length, road_length) * dy)
                                        pygame.draw.line(self.screen, self.colors["lane_marking"], 
                                                       line_start, line_end, max(1, int(self.zoom)))
                                    distance += dash_length if drawing else gap_length
                                    drawing = not drawing
    
    def render_junction(self, junction_id):
        """
        Render a junction (intersection) with improved graphics.
        
        Args:
            junction_id: ID of the junction in the SUMO network
        """
        # Get the junction position
        pos = self.mapper.get_node_position(junction_id)
        if not pos:
            return
        
        # Transform coordinates
        screen_x, screen_y = pos[0] * self.zoom + self.offset_x, pos[1] * self.zoom + self.offset_y
        
        # Draw the junction (50% larger)
        radius = max(7, 22 * self.zoom)
        pygame.draw.circle(self.screen, self.colors["junction"], (screen_x, screen_y), radius)
        pygame.draw.circle(self.screen, (50, 50, 50), (screen_x, screen_y), radius, width=2)