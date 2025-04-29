import os
import sys
import argparse
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

import pygame
import time
import traci
import numpy as np
import math
from src.ai.controller_factory import ControllerFactory
from src.utils.sumo_integration import SumoSimulation

class TrafficVisualizer:
    """
    Custom pygame visualizer for traffic simulation with AI controllers.
    """
    def __init__(self, width=1024, height=768):
        """Initialize the pygame visualizer"""
        self.width = width
        self.height = height
        self.project_root = project_root
        
        # View settings (pan and zoom)
        self.offset_x = 0
        self.offset_y = 0
        self.zoom = 1.0
        self.dragging = False
        self.drag_start = None
        
        # Initialize pygame
        pygame.init()
        pygame.font.init()
        
        # Create display window
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("AI Traffic Control Visualization")
        
        # Load fonts
        self.title_font = pygame.font.SysFont("Arial", 22, bold=True)
        self.subtitle_font = pygame.font.SysFont("Arial", 18, bold=True)
        self.info_font = pygame.font.SysFont("Arial", 16)
        self.stats_font = pygame.font.SysFont("Arial", 14)
        
        # Define colors
        self.colors = {
            "background": (240, 240, 240),
            "road": (80, 80, 80),
            "car": (0, 100, 200),
            "emergency": (255, 0, 0),
            "truck": (120, 120, 120),
            "bus": (0, 150, 0),
            "text": (20, 20, 20),
            "green": (0, 180, 0),
            "yellow": (255, 255, 0),
            "red": (255, 0, 0),
            "waiting": (255, 100, 100),
            "highlight": (255, 140, 0),
            "grid": (200, 200, 200),
            "panel_bg": (240, 240, 255, 200)  # Semi-transparent background
        }
        
        # Traffic network layout (SUMO coordinates)
        self.intersections = {
            "A0": (0, 0),
            "A1": (0, 100),
            "B0": (100, 0),
            "B1": (100, 100)
        }
        
        # Define roads as lane collections
        self.roads = [
            {"from": "A0", "to": "A1", "width": 10},  # A0-A1 (North)
            {"from": "A1", "to": "A0", "width": 10},  # A1-A0 (South)
            {"from": "B0", "to": "B1", "width": 10},  # B0-B1 (North)
            {"from": "B1", "to": "B0", "width": 10},  # B1-B0 (South)
            {"from": "A0", "to": "B0", "width": 10},  # A0-B0 (East)
            {"from": "B0", "to": "A0", "width": 10},  # B0-A0 (West)
            {"from": "A1", "to": "B1", "width": 10},  # A1-B1 (East)
            {"from": "B1", "to": "A1", "width": 10}   # B1-A1 (West)
        ]
        
        # Simulation properties
        self.vehicles = {}
        self.traffic_lights = {}
        self.step = 0
        
        # Controller performance metrics
        self.metrics = {
            "waiting_times": [],
            "speeds": [],
            "throughput": 0,
            "controller_lag": [],
            "decision_times": []
        }
        
        # Vehicle ID to color mapping (for consistent colors)
        self.vehicle_colors = {}
        
        # Create a clock for controlling frame rate
        self.clock = pygame.time.Clock()
    
    def run_simulation(self, scenario_file, controller_type, steps=1000, delay=50):
        """
        Run the traffic simulation with visualization.
        
        Args:
            scenario_file: Path to the SUMO scenario file
            controller_type: Type of controller to use
            steps: Number of simulation steps to run
            delay: Delay between steps in milliseconds
        """
        # Set up SUMO
        config_path = self._create_temp_config(scenario_file)
        sim = SumoSimulation(config_path, gui=False)
        sim.start()
        
        # Get traffic light IDs
        tl_ids = traci.trafficlight.getIDList()
        
        if not tl_ids:
            print("No traffic lights found in the simulation!")
            return
        
        # Create controller
        controller = ControllerFactory.create_controller(controller_type, tl_ids)
        
        # Set window title
        pygame.display.set_caption(f"AI Traffic Control - {controller_type} - {os.path.basename(scenario_file)}")
        
        # Center the view initially
        self._center_view()
        
        running = True
        try:
            for step in range(steps):
                # Process pygame events
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                        break
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            running = False
                            break
                        # Pan with arrow keys
                        elif event.key == pygame.K_LEFT:
                            self.offset_x += 50
                        elif event.key == pygame.K_RIGHT:
                            self.offset_x -= 50
                        elif event.key == pygame.K_UP:
                            self.offset_y += 50
                        elif event.key == pygame.K_DOWN:
                            self.offset_y -= 50
                        # Zoom with + and -
                        elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                            self.zoom *= 1.2
                        elif event.key == pygame.K_MINUS:
                            self.zoom /= 1.2
                    # Handle mouse for panning
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        if event.button == 1:  # Left mouse button
                            self.dragging = True
                            self.drag_start = event.pos
                        elif event.button == 4:  # Mouse wheel up
                            self.zoom *= 1.1
                        elif event.button == 5:  # Mouse wheel down
                            self.zoom /= 1.1
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
                
                if not running:
                    break
                
                self.step = step
                
                # Update vehicle positions
                self._update_vehicles()
                
                # Update traffic light states
                self._update_traffic_lights(tl_ids)
                
                # Collect traffic state
                traffic_state = self._collect_traffic_state(tl_ids)
                
                # Update controller with traffic state
                controller.update_traffic_state(traffic_state)
                
                # Get current simulation time
                current_time = traci.simulation.getTime()
                
                # Get phase decisions from controller for each junction
                for tl_id in tl_ids:
                    phase = controller.get_phase_for_junction(tl_id, current_time)
                    
                    # Set traffic light phase in SUMO
                    current_sumo_state = traci.trafficlight.getRedYellowGreenState(tl_id)
                    
                    # Only update if phase is different
                    if phase != current_sumo_state:
                        traci.trafficlight.setRedYellowGreenState(tl_id, phase)
                        if step % 20 == 0:
                            print(f"Step {step}: Traffic light {tl_id} changed to {phase}")
                
                # Update metrics
                self._update_metrics()
                
                # Store controller performance data
                if controller.response_times:
                    self.metrics["controller_lag"].append(controller.response_times[-1] * 1000)  # ms
                
                if controller.decision_times:
                    self.metrics["decision_times"].append(controller.decision_times[-1] * 1000)  # ms
                
                # Draw everything
                self._draw_simulation(controller_type)
                
                # Step the simulation
                sim.step()
                
                # Control the frame rate
                self.clock.tick(1000 / delay)  # Convert delay ms to fps
                
                # Print progress
                if step % 100 == 0:
                    print(f"Step {step}/{steps}")
        
        finally:
            # Close the simulation
            sim.close()
            pygame.quit()
            
            # Print final metrics
            self._print_final_metrics(controller_type)
    
    def _center_view(self):
        """Center the view on the simulation area"""
        # Calculate the center of the network
        center_x = 50  # Middle of A0(0,0) and B0(100,0)
        center_y = 50  # Middle of A0(0,0) and A1(0,100)
        
        # Set the offset to center this point
        self.offset_x = self.width / 2 - center_x * self.zoom
        self.offset_y = self.height / 2 - center_y * self.zoom
    
    def _create_temp_config(self, route_file):
        """
        Create a temporary SUMO configuration file.
        
        Args:
            route_file: Path to the route file
            
        Returns:
            Path to the created config file
        """
        # Network file
        network_file = os.path.join(self.project_root, "config", "maps", "traffic_grid.net.xml")
        
        # Create a unique config file name
        config_name = f"temp_viz_{os.path.basename(route_file).split('.')[0]}.sumocfg"
        config_path = os.path.join(self.project_root, "config", "scenarios", config_name)
        
        # Write the config file
        with open(config_path, 'w') as f:
            f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/sumoConfiguration.xsd">
    <input>
        <net-file value="{network_file}"/>
        <route-files value="{route_file}"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="3600"/>
        <step-length value="1.0"/>
    </time>
    <processing>
        <time-to-teleport value="-1"/>
    </processing>
    <report>
        <verbose value="false"/>
        <no-step-log value="true"/>
    </report>
</configuration>""")
        
        return config_path
    
    def _update_vehicles(self):
        """Update the vehicle positions and states"""
        # Get all vehicles from SUMO
        vehicle_ids = traci.vehicle.getIDList()
        
        # Clear old vehicles that are no longer in the simulation
        self.vehicles = {vid: self.vehicles.get(vid) for vid in vehicle_ids if vid in self.vehicles}
        
        # Update vehicle positions and add new vehicles
        for vid in vehicle_ids:
            x, y = traci.vehicle.getPosition(vid)
            angle = traci.vehicle.getAngle(vid)  # 0 = east, 90 = north
            speed = traci.vehicle.getSpeed(vid)
            waiting_time = traci.vehicle.getWaitingTime(vid)
            v_type = traci.vehicle.getTypeID(vid)
            
            # Convert angle to pygame angle (0 = east, 90 = south)
            angle = (90 - angle) % 360
            
            # Track vehicle color to keep it consistent
            if vid not in self.vehicle_colors:
                if "emergency" in v_type:
                    self.vehicle_colors[vid] = self.colors["emergency"]
                elif "truck" in v_type:
                    self.vehicle_colors[vid] = self.colors["truck"]
                elif "bus" in v_type:
                    self.vehicle_colors[vid] = self.colors["bus"]
                else:
                    # Default car color with slight variation
                    self.vehicle_colors[vid] = self.colors["car"]
            
            # Store vehicle data with correct SUMO coordinates
            self.vehicles[vid] = {
                "position": (x, y),  # SUMO coordinates
                "angle": angle,
                "speed": speed,
                "waiting": waiting_time > 0,
                "type": v_type,
                "color": self.vehicle_colors[vid]
            }
    
    def _update_traffic_lights(self, tl_ids):
        """Update the traffic light states"""
        for tl_id in tl_ids:
            state = traci.trafficlight.getRedYellowGreenState(tl_id)
            pos = self.intersections.get(tl_id, (0, 0))  # Default position if not found
            
            self.traffic_lights[tl_id] = {
                "state": state,
                "position": pos
            }
    
    def _collect_traffic_state(self, tl_ids):
        """
        Collect traffic state for the AI controller.
        
        Args:
            tl_ids: List of traffic light IDs
            
        Returns:
            Dictionary of traffic state information
        """
        traffic_state = {}
        
        for tl_id in tl_ids:
            # Get incoming lanes for this traffic light
            incoming_lanes = []
            for connection in traci.trafficlight.getControlledLinks(tl_id):
                if connection and connection[0]:  # Check if connection exists
                    incoming_lane = connection[0][0]
                    if incoming_lane not in incoming_lanes:
                        incoming_lanes.append(incoming_lane)
            
            # Count vehicles and collect metrics for each direction
            north_count = south_count = east_count = west_count = 0
            north_wait = south_wait = east_wait = west_wait = 0
            north_queue = south_queue = east_queue = west_queue = 0
            
            for lane in incoming_lanes:
                # Determine direction based on lane ID
                direction = "unknown"
                if "A0A1" in lane or "B0B1" in lane:
                    direction = "north"
                elif "A1A0" in lane or "B1B0" in lane:
                    direction = "south"
                elif "A0B0" in lane or "A1B1" in lane:
                    direction = "east"
                elif "B0A0" in lane or "B1A1" in lane:
                    direction = "west"
                
                # Count vehicles on this lane
                vehicle_count = traci.lane.getLastStepVehicleNumber(lane)
                vehicles = traci.lane.getLastStepVehicleIDs(lane)
                waiting_time = sum(traci.vehicle.getWaitingTime(v) for v in vehicles) if vehicles else 0
                queue_length = traci.lane.getLastStepHaltingNumber(lane)
                
                if direction == "north":
                    north_count += vehicle_count
                    north_wait += waiting_time
                    north_queue += queue_length
                elif direction == "south":
                    south_count += vehicle_count
                    south_wait += waiting_time
                    south_queue += queue_length
                elif direction == "east":
                    east_count += vehicle_count
                    east_wait += waiting_time
                    east_queue += queue_length
                elif direction == "west":
                    west_count += vehicle_count
                    west_wait += waiting_time
                    west_queue += queue_length
            
            # Calculate average waiting times (avoiding division by zero)
            avg_north_wait = north_wait / max(1, north_count) if north_count > 0 else 0
            avg_south_wait = south_wait / max(1, south_count) if south_count > 0 else 0
            avg_east_wait = east_wait / max(1, east_count) if east_count > 0 else 0
            avg_west_wait = west_wait / max(1, west_count) if west_count > 0 else 0
            
            # Store traffic state for this junction
            traffic_state[tl_id] = {
                'north_count': north_count,
                'south_count': south_count,
                'east_count': east_count,
                'west_count': west_count,
                'north_wait': avg_north_wait,
                'south_wait': avg_south_wait,
                'east_wait': avg_east_wait,
                'west_wait': avg_west_wait,
                'north_queue': north_queue,
                'south_queue': south_queue,
                'east_queue': east_queue,
                'west_queue': west_queue
            }
        
        return traffic_state
    
    def _update_metrics(self):
        """Update performance metrics"""
        # Get all vehicles
        vehicles = traci.vehicle.getIDList()
        
        # Update throughput (vehicles that have arrived at destination)
        arrived = traci.simulation.getArrivedNumber()
        self.metrics["throughput"] += arrived
        
        # Skip other metrics if no vehicles
        if not vehicles:
            return
        
        # Calculate average waiting time
        total_waiting_time = sum(traci.vehicle.getWaitingTime(v) for v in vehicles)
        avg_waiting_time = total_waiting_time / len(vehicles)
        self.metrics["waiting_times"].append(avg_waiting_time)
        
        # Calculate average speed
        total_speed = sum(traci.vehicle.getSpeed(v) for v in vehicles)
        avg_speed = total_speed / len(vehicles)
        self.metrics["speeds"].append(avg_speed)
    
    def _draw_simulation(self, controller_type):
        """Draw the simulation on the pygame screen"""
        # Clear the screen
        self.screen.fill(self.colors["background"])
        
        # Draw coordinates to help with debugging
        self._draw_grid_overlay()
        
        # Draw the road network
        self._draw_roads()
        
        # Draw intersections and traffic lights
        for tl_id, tl_data in self.traffic_lights.items():
            self._draw_traffic_light(tl_id, tl_data["position"], tl_data["state"])
        
        # Draw all vehicles
        for vid, vehicle in self.vehicles.items():
            self._draw_vehicle(vid, vehicle)
        
        # Draw UI overlay (title and info)
        self._draw_ui_overlay(controller_type)
        
        # Draw performance metrics in the corner
        self._draw_metrics()
        
        # Update the display
        pygame.display.flip()
    
    def _draw_grid_overlay(self):
        """Draw a grid overlay to help with coordinates"""
        # Draw major grid lines every 50 SUMO units
        for x in range(-100, 200, 50):
            screen_x = x * self.zoom + self.offset_x
            pygame.draw.line(self.screen, (200, 200, 200), 
                           (screen_x, 0), (screen_x, self.height), 1)
            
            # Draw coordinate label
            label = self.stats_font.render(f"{x}", True, (150, 150, 150))
            self.screen.blit(label, (screen_x + 2, 5))
        
        for y in range(-100, 200, 50):
            screen_y = y * self.zoom + self.offset_y
            pygame.draw.line(self.screen, (200, 200, 200), 
                           (0, screen_y), (self.width, screen_y), 1)
            
            # Draw coordinate label
            label = self.stats_font.render(f"{y}", True, (150, 150, 150))
            self.screen.blit(label, (5, screen_y + 2))
    
    def _draw_roads(self):
        """Draw the road network using the SUMO coordinates"""
        # Draw roads between intersections
        for road in self.roads:
            start_id = road["from"]
            end_id = road["to"]
            width = road["width"]
            
            # Get intersection positions
            if start_id in self.intersections and end_id in self.intersections:
                start_pos = self.intersections[start_id]
                end_pos = self.intersections[end_id]
                
                # Convert to screen coordinates
                start_screen = self._sumo_to_screen(start_pos)
                end_screen = self._sumo_to_screen(end_pos)
                
                # Calculate road length and direction for lane markings
                road_length = math.sqrt((end_pos[0] - start_pos[0])**2 + (end_pos[1] - start_pos[1])**2)
                if road_length > 0:
                    dx = (end_pos[0] - start_pos[0]) / road_length
                    dy = (end_pos[1] - start_pos[1]) / road_length
                    
                    # Calculate perpendicular direction for lane offset
                    perp_dx = -dy
                    perp_dy = dx
                    
                    # Offset for lanes (5 units to the right of the road direction)
                    lane_offset = 3
                    
                    # Calculate lane positions
                    lane1_start = (
                        start_pos[0] + perp_dx * lane_offset,
                        start_pos[1] + perp_dy * lane_offset
                    )
                    lane1_end = (
                        end_pos[0] + perp_dx * lane_offset,
                        end_pos[1] + perp_dy * lane_offset
                    )
                    
                    lane1_start_screen = self._sumo_to_screen(lane1_start)
                    lane1_end_screen = self._sumo_to_screen(lane1_end)
                    
                    # Draw the main road line
                    pygame.draw.line(self.screen, self.colors["road"], 
                                   start_screen, end_screen, 
                                   max(1, int(width * self.zoom)))
                    
                    # Draw lane markings
                    self._draw_dashed_line(lane1_start_screen, lane1_end_screen, (255, 255, 255), 2)
    
    def _draw_dashed_line(self, start, end, color, width=1, dash_length=10, gap_length=10):
        """Draw a dashed line from start to end"""
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        distance = math.sqrt(dx**2 + dy**2)
        
        if distance == 0:
            return
        
        # Normalize direction
        dx /= distance
        dy /= distance
        
        # Draw dashes
        current_distance = 0
        drawing = True
        
        while current_distance < distance:
            if drawing:
                line_start = (
                    start[0] + dx * current_distance,
                    start[1] + dy * current_distance
                )
                line_end = (
                    start[0] + dx * min(current_distance + dash_length, distance),
                    start[1] + dy * min(current_distance + dash_length, distance)
                )
                pygame.draw.line(self.screen, color, line_start, line_end, width)
            
            current_distance += dash_length if drawing else gap_length
            drawing = not drawing
    
    def _draw_traffic_light(self, tl_id, position, state):
        """
        Draw a traffic light with its current state.
        
        Args:
            tl_id: Traffic light ID
            position: (x, y) position in SUMO coordinates
            state: Traffic light state string
        """
        # Convert to screen coordinates
        screen_pos = self._sumo_to_screen(position)
        
        # Size based on zoom
        intersection_radius = max(5, int(15 * self.zoom))
        
        # Draw the intersection as a circle
        pygame.draw.circle(self.screen, (50, 50, 50), screen_pos, intersection_radius)
        
        # Draw the traffic light ID
        id_text = self.info_font.render(tl_id, True, (255, 255, 255))
        id_rect = id_text.get_rect(center=screen_pos)
        self.screen.blit(id_text, id_rect)
        
        # Draw the traffic light state indicators
        # We'll draw 4 small circles representing the state for each direction
        # North, East, South, West
        directions = [
            (0, -1),  # North
            (1, 0),   # East
            (0, 1),   # South
            (-1, 0)   # West
        ]
        
        light_radius = max(3, int(6 * self.zoom))
        
        # Use first 4 characters of state for the main directions
        for i, direction in enumerate(directions[:min(4, len(state))]):
            if i < len(state):
                c = state[i]
                if c == 'G' or c == 'g':
                    color = self.colors["green"]
                elif c == 'Y' or c == 'y':
                    color = self.colors["yellow"]
                else:  # 'R' or 'r' or any other
                    color = self.colors["red"]
                
                # Calculate position offset
                offset_x = direction[0] * intersection_radius * 1.5
                offset_y = direction[1] * intersection_radius * 1.5
                
                # Draw the light
                pygame.draw.circle(self.screen, color, 
                                  (screen_pos[0] + offset_x, screen_pos[1] + offset_y), 
                                  light_radius)
    
    def _draw_vehicle(self, vid, vehicle):
        """
        Draw a vehicle on the screen.
        
        Args:
            vid: Vehicle ID
            vehicle: Dictionary with vehicle properties
        """
        pos = vehicle["position"]  # SUMO coordinates
        angle = vehicle["angle"]
        color = vehicle["color"]
        waiting = vehicle["waiting"]
        
        # Convert to screen coordinates
        screen_pos = self._sumo_to_screen(pos)
        
        # Determine vehicle size based on type and zoom
        if "emergency" in vehicle["type"]:
            width, height = 12 * self.zoom, 6 * self.zoom
        elif "truck" in vehicle["type"]:
            width, height = 16 * self.zoom, 8 * self.zoom
        elif "bus" in vehicle["type"]:
            width, height = 18 * self.zoom, 7 * self.zoom
        else:
            width, height = 10 * self.zoom, 5 * self.zoom
        
        # Ensure minimum size
        width = max(4, width)
        height = max(2, height)
        
        # Create a surface for the vehicle
        vehicle_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        
        # Draw the vehicle
        if waiting:
            # Add a red overlay for waiting vehicles
            pygame.draw.rect(vehicle_surface, self.colors["waiting"], (0, 0, width, height))
        else:
            pygame.draw.rect(vehicle_surface, color, (0, 0, width, height))
        
        # Draw a direction indicator
        arrow_width = max(2, width * 0.3)
        pygame.draw.polygon(vehicle_surface, (0, 0, 0), 
                          [(width-arrow_width, height//2), 
                           (width-arrow_width*2, 1), 
                           (width-arrow_width*2, height-1)])
        
        # Draw vehicle type indicator
        if "emergency" in vehicle["type"]:
            # Red stripe for emergency vehicles
            pygame.draw.rect(vehicle_surface, (255, 255, 255), 
                           (2, height//2 - 1, width-4, 2))
        elif "truck" in vehicle["type"]:
            # Cargo area for trucks
            pygame.draw.rect(vehicle_surface, (0, 0, 0), 
                           (width//3, 1, 1, height-2))
        elif "bus" in vehicle["type"]:
            # Windows for buses
            for i in range(3):
                pygame.draw.rect(vehicle_surface, (200, 255, 255), 
                              (width//4 + i*width//4, 1, width//8, 2))
        
        # Rotate the vehicle based on its angle
        rotated_surface = pygame.transform.rotate(vehicle_surface, angle)
        rotated_rect = rotated_surface.get_rect(center=screen_pos)
        
        # Draw the vehicle
        self.screen.blit(rotated_surface, rotated_rect.topleft)
    
    def _draw_ui_overlay(self, controller_type):
        """Draw UI overlay elements like title and controls"""
        # Draw title bar
        title_bg = pygame.Rect(0, 0, self.width, 30)
        pygame.draw.rect(self.screen, (50, 50, 80), title_bg)
        
        # Draw title
        title = self.title_font.render(f"AI Traffic Control Simulation - {controller_type}", 
                                    True, (255, 255, 255))
        self.screen.blit(title, (self.width//2 - title.get_width()//2, 5))
        
        # Draw step counter in bottom right
        step_text = self.info_font.render(f"Step: {self.step}", True, self.colors["text"])
        self.screen.blit(step_text, (self.width - step_text.get_width() - 10, 
                                self.height - step_text.get_height() - 10))
        
        # Draw controls info
        control_text = self.stats_font.render(
            "Controls: Arrow Keys = Pan, +/- = Zoom, Mouse Drag = Pan", 
            True, self.colors["text"])
        self.screen.blit(control_text, (10, self.height - control_text.get_height() - 10))
    
    def _draw_metrics(self):
        """Draw performance metrics on the screen"""
        # Performance metrics panel in top right
        panel_rect = pygame.Rect(self.width - 260, 40, 250, 180)
        
        # Create a transparent surface for the panel
        panel_surface = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        panel_surface.fill((240, 240, 255, 220))  # Semi-transparent background
        
        # Add border to panel
        pygame.draw.rect(panel_surface, (100, 100, 150), 
                        (0, 0, panel_rect.width, panel_rect.height), 2)
        
        # Draw the panel to the screen
        self.screen.blit(panel_surface, panel_rect)
        
        # Panel title
        metrics_title = self.subtitle_font.render("Performance Metrics", True, self.colors["text"])
        self.screen.blit(metrics_title, (panel_rect.centerx - metrics_title.get_width()//2, panel_rect.top + 5))
        
        # Current metrics
        y_offset = panel_rect.top + 30
        line_height = 22
        
        metrics_to_show = [
            ("Vehicles", f"{len(self.vehicles)}"),
            ("Throughput", f"{self.metrics['throughput']}"),
            ("Avg Wait Time", f"{self._get_avg_metric('waiting_times'):.2f} s"),
            ("Avg Speed", f"{self._get_avg_metric('speeds'):.2f} m/s"),
            ("Controller Lag", f"{self._get_avg_metric('controller_lag'):.2f} ms"),
            ("Decision Time", f"{self._get_avg_metric('decision_times'):.2f} ms")
        ]
        
        for label, value in metrics_to_show:
            metric_text = self.info_font.render(f"{label}: {value}", True, self.colors["text"])
            self.screen.blit(metric_text, (panel_rect.left + 10, y_offset))
            y_offset += line_height
        
        # Traffic direction counts panel in top left (so it doesn't cover the roads)
        traffic_panel = pygame.Rect(10, 40, 250, 180)
        
        # Create a transparent surface for the panel
        traffic_surface = pygame.Surface((traffic_panel.width, traffic_panel.height), pygame.SRCALPHA)
        traffic_surface.fill((240, 240, 255, 220))  # Semi-transparent background
        
        # Add border to panel
        pygame.draw.rect(traffic_surface, (100, 100, 150), 
                        (0, 0, traffic_panel.width, traffic_panel.height), 2)
        
        # Draw the panel to the screen
        self.screen.blit(traffic_surface, traffic_panel)
        
        traffic_title = self.subtitle_font.render("Traffic Direction Counts", True, self.colors["text"])
        self.screen.blit(traffic_title, (traffic_panel.centerx - traffic_title.get_width()//2, traffic_panel.top + 5))
        
        # Get total vehicle counts by direction
        n_count = s_count = e_count = w_count = 0
        for tl_id, traffic_state in self._collect_traffic_state(self.traffic_lights.keys()).items():
            n_count += traffic_state['north_count']
            s_count += traffic_state['south_count']
            e_count += traffic_state['east_count']
            w_count += traffic_state['west_count']
        
        # Display direction counts
        y_offset = traffic_panel.top + 30
        
        direction_counts = [
            ("North ↑", n_count),
            ("South ↓", s_count),
            ("East →", e_count),
            ("West ←", w_count),
            ("Total", n_count + s_count + e_count + w_count)
        ]
        
        for label, count in direction_counts:
            count_text = self.info_font.render(f"{label}: {count} vehicles", True, self.colors["text"])
            self.screen.blit(count_text, (traffic_panel.left + 10, y_offset))
            y_offset += line_height
    
    def _get_avg_metric(self, metric_name, window=20):
        """
        Get the average of a metric over the last few steps.
        
        Args:
            metric_name: Name of the metric to average
            window: Number of recent values to average
            
        Returns:
            Average value or 0 if no data
        """
        values = self.metrics.get(metric_name, [])
        if not values:
            return 0
        
        # Return average of last 'window' values
        return sum(values[-window:]) / min(len(values), window)
    
    def _print_final_metrics(self, controller_type):
        """Print final performance metrics to console"""
        print("\nFinal Performance Metrics:")
        print(f"Controller: {controller_type}")
        print("-" * 60)
        
        if self.metrics["waiting_times"]:
            avg_wait = sum(self.metrics["waiting_times"]) / len(self.metrics["waiting_times"])
            print(f"Average Waiting Time: {avg_wait:.2f} seconds")
        
        if self.metrics["speeds"]:
            avg_speed = sum(self.metrics["speeds"]) / len(self.metrics["speeds"])
            print(f"Average Speed: {avg_speed:.2f} m/s")
        
        print(f"Total Throughput: {self.metrics['throughput']} vehicles")
        
        if self.metrics["controller_lag"]:
            avg_lag = sum(self.metrics["controller_lag"]) / len(self.metrics["controller_lag"])
            print(f"Average Controller Lag: {avg_lag:.2f} ms")
        
        if self.metrics["decision_times"]:
            avg_decision = sum(self.metrics["decision_times"]) / len(self.metrics["decision_times"])
            print(f"Average Decision Time: {avg_decision:.2f} ms")
        
        print("-" * 60)
    
    def _sumo_to_screen(self, sumo_pos):
        """
        Convert SUMO coordinates to screen coordinates with zoom and offset.
        
        Args:
            sumo_pos: (x, y) position in SUMO coordinates
            
        Returns:
            (x, y) position in screen coordinates
        """
        return (
            sumo_pos[0] * self.zoom + self.offset_x,
            sumo_pos[1] * self.zoom + self.offset_y
        )

def main():
    """Run the visualization"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Visualize traffic simulation with AI controller')
    parser.add_argument('--scenario', type=str, required=True,
                        help='Scenario file to run (include .rou.xml extension)')
    parser.add_argument('--controller', type=str, default="Wired AI",
                        choices=["Wired AI", "Wireless AI", "Traditional"],
                        help='Controller type to use')
    parser.add_argument('--steps', type=int, default=1000,
                        help='Number of simulation steps to run')
    parser.add_argument('--delay', type=int, default=50,
                        help='Delay in milliseconds between steps')
    args = parser.parse_args()
    
    # Construct the full path to the scenario file
    scenario_path = os.path.join(project_root, "config", "scenarios", args.scenario)
    
    # Check if the scenario file exists
    if not os.path.exists(scenario_path):
        print(f"Scenario file not found: {scenario_path}")
        return
    
    # Run the visualization
    visualizer = TrafficVisualizer()
    visualizer.run_simulation(scenario_path, args.controller, args.steps, args.delay)

if __name__ == "__main__":
    main()