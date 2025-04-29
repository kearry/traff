import pygame
import os
import sys
import traci
from pathlib import Path

# Add project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

from src.ui.visualization import Visualization
from src.ui.traffic_renderer import TrafficRenderer, VehicleType
from src.ui.sumo_pygame_mapper import SumoNetworkParser, SumoPygameMapper
from src.utils.sumo_integration import SumoSimulation

class SumoVisualization:
    """
    Integrates SUMO simulation with Pygame visualization.
    """
    def __init__(self, sumo_config_path, width=1024, height=768, use_gui=False):
        """
        Initialize the SUMO visualization.
        
        Args:
            sumo_config_path (str): Path to the SUMO configuration file
            width (int): Width of the visualization window
            height (int): Height of the visualization window
            use_gui (bool): Whether to use SUMO GUI alongside the visualization
        """
        self.sumo_config_path = sumo_config_path
        self.width = width
        self.height = height
        self.use_gui = use_gui
        
        # Get the SUMO network file path from the config directory
        self.net_file_path = self._get_net_file_path()
        
        # Initialize the SUMO simulation
        self.simulation = SumoSimulation(sumo_config_path, gui=use_gui)
        
        # Initialize the visualization
        self.visualization = Visualization(width, height, "SUMO Traffic Visualization", self.net_file_path)
        
        # Create network parser and mapper
        self.network_parser = SumoNetworkParser(self.net_file_path)
        self.mapper = SumoPygameMapper(self.network_parser, width, height)
        
        # Create traffic renderer
        self.traffic_renderer = TrafficRenderer(self.visualization.screen, self.mapper)
        
        # Traffic light positions (will be filled during simulation)
        self.traffic_light_positions = {}
        
        # Simulation running flag
        self.running = False
        
        # Statistics
        self.stats = {
            "vehicles": 0,
            "avg_speed": 0.0,
            "avg_wait_time": 0.0,
            "throughput": 0,
            "step": 0,
            "mode": "Wired AI"  # Default mode, can be changed
        }
        
        # Performance metrics (to be collected during simulation)
        self.performance_metrics = {
            "wait_times": [],
            "speeds": [],
            "throughput": []
        }
        
        print(f"SUMO Visualization initialized with {width}x{height} window")
    
    def _get_net_file_path(self):
        """Extract the network file path from the SUMO configuration file."""
        import xml.etree.ElementTree as ET
        
        try:
            # Parse the SUMO config file
            tree = ET.parse(self.sumo_config_path)
            root = tree.getroot()
            
            # Find the net-file entry
            net_file = root.find(".//net-file")
            if net_file is not None:
                net_file_value = net_file.get("value")
                
                # If it's a relative path, convert to absolute path
                if not os.path.isabs(net_file_value):
                    config_dir = os.path.dirname(self.sumo_config_path)
                    return os.path.join(config_dir, net_file_value)
                return net_file_value
            
            print("Warning: Could not find net-file in SUMO config. Using default.")
            # Try to find a .net.xml file in the same directory as the config
            config_dir = os.path.dirname(self.sumo_config_path)
            net_files = [f for f in os.listdir(config_dir) if f.endswith(".net.xml")]
            if net_files:
                return os.path.join(config_dir, net_files[0])
            
            raise FileNotFoundError("No .net.xml file found in the config directory.")
        
        except Exception as e:
            print(f"Error getting net file path: {e}")
            return None
    
    def start(self):
        """Start the SUMO simulation and visualization."""
        try:
            # Start the SUMO simulation
            self.simulation.start()
            
            # Initialize traffic light positions
            self._initialize_traffic_light_positions()
            
            self.running = True
            print("SUMO Visualization started")
            return True
        
        except Exception as e:
            print(f"Error starting SUMO visualization: {e}")
            return False
    
    def _initialize_traffic_light_positions(self):
        """Initialize traffic light positions based on SUMO network."""
        try:
            # Get all traffic lights
            tl_ids = traci.trafficlight.getIDList()
            print(f"Found traffic lights: {tl_ids}")
            
            if not tl_ids:
                print("WARNING: No traffic lights found in the simulation!")
                print("This might be because you're using a network without traffic lights.")
                print("Please check your SUMO network configuration.")
                return
            
            for tl_id in tl_ids:
                # Get all controlled links for this traffic light
                try:
                    controlled_links = traci.trafficlight.getControlledLinks(tl_id)
                    print(f"Traffic light {tl_id} controls {len(controlled_links)} links")
                    
                    # Try to find the junction position directly
                    if tl_id in self.network_parser.nodes:
                        self.traffic_light_positions[tl_id] = self.network_parser.nodes[tl_id]
                        print(f"Positioned traffic light {tl_id} at junction position")
                        continue
                    
                    # If we have links, use the position of the first one
                    if controlled_links and controlled_links[0]:
                        # Get the incoming lane
                        try:
                            incoming_lane = controlled_links[0][0][0]
                            print(f"Using incoming lane {incoming_lane} for traffic light {tl_id}")
                            
                            # Get the lane shape
                            lane_shape = traci.lane.getShape(incoming_lane)
                            
                            # Use the last point of the lane shape (closest to the junction)
                            if lane_shape:
                                self.traffic_light_positions[tl_id] = lane_shape[-1]
                                print(f"Positioned traffic light {tl_id} at lane endpoint")
                                continue
                        except Exception as e:
                            print(f"Error getting lane shape: {e}")
                    
                    # As a fallback, get the controlled junctions
                    try:
                        controlled_junctions = traci.trafficlight.getControlledJunctions(tl_id)
                        for junction_id in controlled_junctions:
                            if junction_id in self.network_parser.nodes:
                                self.traffic_light_positions[tl_id] = self.network_parser.nodes[junction_id]
                                print(f"Positioned traffic light {tl_id} at controlled junction {junction_id}")
                                break
                    except Exception as e:
                        print(f"Error getting controlled junctions: {e}")
                    
                    if tl_id not in self.traffic_light_positions:
                        print(f"WARNING: Could not determine position for traffic light {tl_id}")
                        
                except Exception as e:
                    print(f"Error processing traffic light {tl_id}: {e}")
            
            print(f"Initialized {len(self.traffic_light_positions)} traffic light positions out of {len(tl_ids)} traffic lights")
            
        except Exception as e:
            print(f"Error initializing traffic light positions: {e}")   
    
    def _update_stats(self):
        """Update simulation statistics."""
        try:
            # Update vehicle count
            vehicles = traci.vehicle.getIDList()
            self.stats["vehicles"] = len(vehicles)
            
            # Update average speed and wait time
            if vehicles:
                total_speed = sum(traci.vehicle.getSpeed(v) for v in vehicles)
                total_wait_time = sum(traci.vehicle.getWaitingTime(v) for v in vehicles)
                
                self.stats["avg_speed"] = total_speed / len(vehicles)
                self.stats["avg_wait_time"] = total_wait_time / len(vehicles)
                
                # Store for performance metrics
                self.performance_metrics["speeds"].append(self.stats["avg_speed"])
                self.performance_metrics["wait_times"].append(self.stats["avg_wait_time"])
            else:
                self.stats["avg_speed"] = 0.0
                self.stats["avg_wait_time"] = 0.0
            
            # Update throughput (vehicles that have arrived at their destination)
            arrived = traci.simulation.getArrivedNumber()
            self.stats["throughput"] += arrived
            self.performance_metrics["throughput"].append(arrived)
            
            # Update step number
            self.stats["step"] = traci.simulation.getTime()
        
        except Exception as e:
            print(f"Error updating stats: {e}")
    
    def step(self, delay_ms=100):
        """
        Perform one simulation and visualization step with delay to slow down simulation.
        
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
            running = self.visualization.handle_events()
            if not running:
                self.close()
                return False
            
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
                    vehicle_type = self.traffic_renderer.map_vehicle_type(v_type)
                    
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
            
            # Render junctions
            for junction_id in self.network_parser.nodes:
                self.traffic_renderer.render_junction(junction_id)
            
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
            
            # Draw debug information including traffic light states
            self.draw_debug_info()
            
            # Update the visualization
            self.visualization.update()
            
            return True
        
        except Exception as e:
            print(f"Error in simulation step: {e}")
            return False
    
    def draw_debug_info(self):
        """Draw debug information including traffic light states."""
        y_offset = 100  # Start below the regular stats
        
        # Display traffic light states
        self.visualization.draw_text("Traffic Light States:", 10, y_offset, (0, 0, 0))
        y_offset += 20
        
        tl_ids = traci.trafficlight.getIDList()
        
        if not tl_ids:
            self.visualization.draw_text("No traffic lights found in simulation!", 15, y_offset, (255, 0, 0))
            y_offset += 20
            
            # Show additional debug info about junctions
            self.visualization.draw_text("Junctions in network:", 15, y_offset, (0, 0, 100))
            y_offset += 20
            
            for junction_id in list(self.network_parser.nodes.keys())[:5]:  # Show first 5 junctions
                self.visualization.draw_text(f"  {junction_id}: {self.network_parser.nodes[junction_id]}", 15, y_offset, (0, 0, 100))
                y_offset += 20
        else:
            for tl_id in tl_ids[:5]:  # Show first 5 traffic lights
                try:
                    state = traci.trafficlight.getRedYellowGreenState(tl_id)
                    program = traci.trafficlight.getProgram(tl_id)
                    phase = traci.trafficlight.getPhase(tl_id)
                    phase_duration = traci.trafficlight.getPhaseDuration(tl_id)
                    time_to_change = traci.trafficlight.getNextSwitch(tl_id) - traci.simulation.getTime()
                    
                    # Basic traffic light info
                    self.visualization.draw_text(f"TL {tl_id} (Program {program}, Phase {phase}):", 15, y_offset, (0, 0, 100))
                    y_offset += 20
                    
                    # Show the state with colored characters
                    self.visualization.draw_text("  State: ", 20, y_offset, (0, 0, 0))
                    x_offset = 80
                    for i, c in enumerate(state):
                        color = (0, 0, 0)
                        if c == 'r': color = (255, 0, 0)
                        elif c == 'y': color = (255, 255, 0)
                        elif c == 'g' or c == 'G': color = (0, 255, 0)
                        
                        self.visualization.draw_text(c, x_offset + i*15, y_offset, color)
                    
                    y_offset += 20
                    
                    # Show timer
                    self.visualization.draw_text(f"  Next change in: {time_to_change:.1f}s (Phase duration: {phase_duration}s)", 
                                                20, y_offset, (0, 0, 0))
                    y_offset += 20
                    
                    # Show position information
                    if tl_id in self.traffic_light_positions:
                        pos = self.traffic_light_positions[tl_id]
                        self.visualization.draw_text(f"  Position: ({pos[0]:.1f}, {pos[1]:.1f})", 20, y_offset, (100, 100, 100))
                        y_offset += 20
                    
                    # Add some padding between traffic lights
                    y_offset += 5
                    
                except Exception as e:
                    self.visualization.draw_text(f"{tl_id}: Error getting state - {str(e)}", 15, y_offset, (255, 0, 0))
                    y_offset += 20
    
    def run(self, steps=1000, delay_ms=100):
        """
        Run the simulation for a specified number of steps.
        
        Args:
            steps (int): Number of simulation steps to run
            delay_ms (int): Delay in milliseconds between steps
        """
        if not self.start():
            return False
        
        for _ in range(steps):
            if not self.step(delay_ms):
                break
        
        self.close()
        return True
    
    def set_mode(self, mode):
        """Set the simulation mode (e.g., 'Wired AI', 'Wireless AI')."""
        self.stats["mode"] = mode
    
    def close(self):
        """Close the simulation and visualization."""
        if self.running:
            self.simulation.close()
            self.visualization.close()
            self.running = False
            print("SUMO Visualization closed")

# Test the SUMO visualization
if __name__ == "__main__":
    import os
    
    # Path to the SUMO configuration file
    sumo_config_path = os.path.join(project_root, "config", "maps", "grid_network.sumocfg")
    
    # Create and run the visualization
    visualization = SumoVisualization(sumo_config_path, width=1024, height=768, use_gui=False)
    visualization.run(steps=1000, delay_ms=100)  # Run for 1000 steps with 100ms delay