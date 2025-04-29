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
from src.ui.sumo_visualization import SumoVisualization
from src.ai.controller_factory import ControllerFactory

class ScenarioVisualizer:
    """
    Specialized visualizer for comparing traffic controllers on scenarios.
    """
    def __init__(self, width=1024, height=768):
        """
        Initialize the scenario visualizer.
        
        Args:
            width: Width of the visualization window
            height: Height of the visualization window
        """
        self.width = width
        self.height = height
        self.project_root = project_root
        
        # Initialize pygame
        pygame.init()
        pygame.font.init()
        
        # Set up fonts
        self.title_font = pygame.font.SysFont("Arial", 24, bold=True)
        self.info_font = pygame.font.SysFont("Arial", 18)
        self.stats_font = pygame.font.SysFont("Arial", 16)
        
        # Set up colors
        self.colors = {
            "background": (240, 240, 240),
            "title": (0, 0, 100),
            "wired": (0, 100, 200),
            "wireless": (0, 150, 0),
            "traditional": (150, 0, 0),
            "text": (10, 10, 10),
            "highlight": (255, 140, 0)
        }
    
    def run_split_view(self, scenario_file, steps=1000, delay=50):
        """
        Run a split-view comparison with both wired and wireless controllers.
        
        Args:
            scenario_file: Path to the SUMO route file for the scenario
            steps: Number of simulation steps to run
            delay: Delay in milliseconds between steps
        """
        # Create a temporary config file for each controller
        config_wired = self._create_temp_config(scenario_file, "wired")
        config_wireless = self._create_temp_config(scenario_file, "wireless")
        
        # Start the visualizations
        vis_wired = SumoVisualization(config_wired, width=self.width//2, height=self.height, use_gui=False)
        vis_wired.set_mode("Wired AI")
        
        vis_wireless = SumoVisualization(config_wireless, width=self.width//2, height=self.height, use_gui=False)
        vis_wireless.set_mode("Wireless AI")
        
        # Create the comparison window
        screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption(f"AI Traffic Controller Comparison - {os.path.basename(scenario_file)}")
        
        # Start the visualizations
        if not vis_wired.start() or not vis_wireless.start():
            print("Failed to start one or both visualizations")
            return
        
        # Get traffic light IDs from both simulations
        tl_ids_wired = traci.trafficlight.getIDList()
        
        # Connect to the second SUMO instance
        # (We need to temporarily disconnect from the first one)
        traci.switch("wired")
        traci.close()
        traci.switch("wireless")
        tl_ids_wireless = traci.trafficlight.getIDList()
        traci.switch("wired")
        
        # Create controllers
        controller_wired = ControllerFactory.create_controller("Wired AI", tl_ids_wired)
        controller_wireless = ControllerFactory.create_controller("Wireless AI", tl_ids_wireless)
        
        # Performance metrics
        metrics = {
            "wired": {
                "avg_waiting_time": 0,
                "avg_speed": 0,
                "throughput": 0,
                "response_times": [],
                "decision_times": []
            },
            "wireless": {
                "avg_waiting_time": 0, 
                "avg_speed": 0,
                "throughput": 0,
                "response_times": [],
                "decision_times": []
            }
        }
        
        # Run the simulation
        running = True
        step = 0
        clock = pygame.time.Clock()
        
        while running and step < steps:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
            
            # Clear the screen
            screen.fill(self.colors["background"])
            
            # Draw divider
            pygame.draw.line(screen, (100, 100, 100), (self.width//2, 0), (self.width//2, self.height), 2)
            
            # Draw titles
            wired_title = self.title_font.render("Wired AI Controller", True, self.colors["wired"])
            wireless_title = self.title_font.render("Wireless AI Controller", True, self.colors["wireless"])
            screen.blit(wired_title, (self.width//4 - wired_title.get_width()//2, 10))
            screen.blit(wireless_title, (self.width//4*3 - wireless_title.get_width()//2, 10))
            
            # Step the wired simulation
            traci.switch("wired")
            traffic_state_wired = self._collect_traffic_state(tl_ids_wired)
            controller_wired.update_traffic_state(traffic_state_wired)
            current_time_wired = traci.simulation.getTime()
            
            # Update traffic lights based on controller decisions
            for tl_id in tl_ids_wired:
                phase = controller_wired.get_phase_for_junction(tl_id, current_time_wired)
                current_state = traci.trafficlight.getRedYellowGreenState(tl_id)
                if phase != current_state:
                    traci.trafficlight.setRedYellowGreenState(tl_id, phase)
            
            # Collect metrics
            self._update_metrics(metrics["wired"])
            vis_wired.step(0)  # No delay here, we'll control the timing
            
            # Step the wireless simulation
            traci.switch("wireless")
            traffic_state_wireless = self._collect_traffic_state(tl_ids_wireless)
            controller_wireless.update_traffic_state(traffic_state_wireless)
            current_time_wireless = traci.simulation.getTime()
            
            # Update traffic lights based on controller decisions
            for tl_id in tl_ids_wireless:
                phase = controller_wireless.get_phase_for_junction(tl_id, current_time_wireless)
                current_state = traci.trafficlight.getRedYellowGreenState(tl_id)
                if phase != current_state:
                    traci.trafficlight.setRedYellowGreenState(tl_id, phase)
            
            # Collect metrics
            self._update_metrics(metrics["wireless"])
            vis_wireless.step(0)  # No delay here, we'll control the timing
            
            # Blit the simulation surfaces to our screen
            # (Note: This assumes SumoVisualization exposes its screen as a public attribute)
            screen.blit(vis_wired.screen, (0, 40))
            screen.blit(vis_wireless.screen, (self.width//2, 40))
            
            # Draw performance metrics
            self._draw_metrics(screen, metrics, step)
            
            # Update the display
            pygame.display.flip()
            
            # Control the frame rate
            clock.tick(1000 // delay)  # Convert ms delay to FPS
            
            step += 1
            if step % 100 == 0:
                print(f"Step {step}/{steps}")
        
        # Close visualizations
        vis_wired.close()
        vis_wireless.close()
        
        # Close pygame
        pygame.quit()
        
        # Print final metrics
        self._print_final_metrics(metrics)
    
def _create_temp_config(self, route_file, connection_id):
    """
    Create a temporary SUMO configuration file.
    
    Args:
        route_file: Path to the route file
        connection_id: Identifier for the SUMO connection
        
    Returns:
        Path to the created config file
    """
    # Network file
    network_file = os.path.join(self.project_root, "config", "maps", "traffic_grid.net.xml")
    
    # Create a unique config file name
    config_name = f"temp_{connection_id}_{os.path.basename(route_file).split('.')[0]}.sumocfg"
    config_path = os.path.join(self.project_root, "config", "scenarios", config_name)
    
    # Write the config file with fixed configuration
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
    <gui_only>
        <gui-settings-file value=""/>
        <start value="false"/>
        <quit-on-end value="true"/>
    </gui_only>
</configuration>""")
    
    return config_path
    
    def _collect_traffic_state(self, tl_ids):
        """
        Collect the current traffic state for all traffic lights.
        
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
    
    def _update_metrics(self, metrics):
        """
        Update performance metrics with current simulation state.
        
        Args:
            metrics: Dictionary of metrics to update
        """
        # Get all vehicles
        vehicles = traci.vehicle.getIDList()
        
        # Update throughput (vehicles that have arrived at destination)
        arrived = traci.simulation.getArrivedNumber()
        metrics["throughput"] += arrived
        
        # Skip other metrics if no vehicles
        if not vehicles:
            return
        
        # Calculate average waiting time
        total_waiting_time = sum(traci.vehicle.getWaitingTime(v) for v in vehicles)
        avg_waiting_time = total_waiting_time / len(vehicles)
        metrics["avg_waiting_time"] = avg_waiting_time
        
        # Calculate average speed
        total_speed = sum(traci.vehicle.getSpeed(v) for v in vehicles)
        avg_speed = total_speed / len(vehicles)
        metrics["avg_speed"] = avg_speed
    
    def _draw_metrics(self, screen, metrics, step):
        """
        Draw performance metrics on the screen.
        
        Args:
            screen: Pygame surface to draw on
            metrics: Dictionary of metrics to display
            step: Current simulation step
        """
        # Draw metrics heading
        metrics_title = self.info_font.render(f"Performance Metrics (Step {step})", True, self.colors["text"])
        screen.blit(metrics_title, (self.width//2 - metrics_title.get_width()//2, self.height - 120))
        
        # Draw wired metrics
        wired_wait = self.stats_font.render(f"Avg Wait: {metrics['wired']['avg_waiting_time']:.2f}s", True, self.colors["wired"])
        wired_speed = self.stats_font.render(f"Avg Speed: {metrics['wired']['avg_speed']:.2f}m/s", True, self.colors["wired"])
        wired_throughput = self.stats_font.render(f"Throughput: {metrics['wired']['throughput']} veh", True, self.colors["wired"])
        
        screen.blit(wired_wait, (self.width//4 - 150, self.height - 90))
        screen.blit(wired_speed, (self.width//4 - 150, self.height - 70))
        screen.blit(wired_throughput, (self.width//4 - 150, self.height - 50))
        
        # Draw wireless metrics
        wireless_wait = self.stats_font.render(f"Avg Wait: {metrics['wireless']['avg_waiting_time']:.2f}s", True, self.colors["wireless"])
        wireless_speed = self.stats_font.render(f"Avg Speed: {metrics['wireless']['avg_speed']:.2f}m/s", True, self.colors["wireless"])
        wireless_throughput = self.stats_font.render(f"Throughput: {metrics['wireless']['throughput']} veh", True, self.colors["wireless"])
        
        screen.blit(wireless_wait, (self.width//4*3 - 150, self.height - 90))
        screen.blit(wireless_speed, (self.width//4*3 - 150, self.height - 70))
        screen.blit(wireless_throughput, (self.width//4*3 - 150, self.height - 50))
        
        # Draw performance comparison
        if metrics['wired']['avg_waiting_time'] < metrics['wireless']['avg_waiting_time']:
            better_wait = "Wired"
            wait_color = self.colors["wired"]
        else:
            better_wait = "Wireless"
            wait_color = self.colors["wireless"]
        
        if metrics['wired']['avg_speed'] > metrics['wireless']['avg_speed']:
            better_speed = "Wired"
            speed_color = self.colors["wired"]
        else:
            better_speed = "Wireless"
            speed_color = self.colors["wireless"]
        
        if metrics['wired']['throughput'] > metrics['wireless']['throughput']:
            better_throughput = "Wired"
            throughput_color = self.colors["wired"]
        else:
            better_throughput = "Wireless"
            throughput_color = self.colors["wireless"]
        
        comparison_wait = self.stats_font.render(f"Better Wait Time: {better_wait}", True, wait_color)
        comparison_speed = self.stats_font.render(f"Better Speed: {better_speed}", True, speed_color)
        comparison_throughput = self.stats_font.render(f"Better Throughput: {better_throughput}", True, throughput_color)
        
        screen.blit(comparison_wait, (self.width//2 - comparison_wait.get_width()//2, self.height - 90))
        screen.blit(comparison_speed, (self.width//2 - comparison_speed.get_width()//2, self.height - 70))
        screen.blit(comparison_throughput, (self.width//2 - comparison_throughput.get_width()//2, self.height - 50))
    
    def _print_final_metrics(self, metrics):
        """
        Print the final metrics to the console.
        
        Args:
            metrics: Dictionary of metrics
        """
        print("\nFinal Performance Metrics:")
        print("-" * 60)
        print(f"{'Metric':<20} {'Wired AI':<15} {'Wireless AI':<15} {'Difference':<15}")
        print("-" * 60)
        
        wired_wait = metrics['wired']['avg_waiting_time']
        wireless_wait = metrics['wireless']['avg_waiting_time']
        diff_wait = wired_wait - wireless_wait
        wait_better = "Wired" if diff_wait > 0 else "Wireless"
        
        wired_speed = metrics['wired']['avg_speed']
        wireless_speed = metrics['wireless']['avg_speed']
        diff_speed = wired_speed - wireless_speed
        speed_better = "Wired" if diff_speed > 0 else "Wireless"
        
        wired_throughput = metrics['wired']['throughput']
        wireless_throughput = metrics['wireless']['throughput']
        diff_throughput = wired_throughput - wireless_throughput
        throughput_better = "Wired" if diff_throughput > 0 else "Wireless"
        
        print(f"Average Wait Time:  {wired_wait:.2f}s         {wireless_wait:.2f}s         {abs(diff_wait):.2f}s ({wait_better} better)")
        print(f"Average Speed:      {wired_speed:.2f}m/s       {wireless_speed:.2f}m/s       {abs(diff_speed):.2f}m/s ({speed_better} better)")
        print(f"Total Throughput:   {wired_throughput}           {wireless_throughput}           {abs(diff_throughput)} ({throughput_better} better)")
        
        if len(metrics['wired']['response_times']) > 0 and len(metrics['wireless']['response_times']) > 0:
            wired_resp = sum(metrics['wired']['response_times']) / len(metrics['wired']['response_times']) * 1000  # ms
            wireless_resp = sum(metrics['wireless']['response_times']) / len(metrics['wireless']['response_times']) * 1000  # ms
            diff_resp = wired_resp - wireless_resp
            resp_better = "Wired" if diff_resp < 0 else "Wireless"
            
            print(f"Avg Response Time:  {wired_resp:.2f}ms       {wireless_resp:.2f}ms       {abs(diff_resp):.2f}ms ({resp_better} better)")

def main():
    """Run the scenario visualizer."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Visualize traffic scenarios with different controllers')
    parser.add_argument('--scenario', type=str, required=True,
                        help='Scenario file to run (include .rou.xml extension)')
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
    
    # Run the visualizer
    visualizer = ScenarioVisualizer()
    visualizer.run_split_view(scenario_path, args.steps, args.delay)

if __name__ == "__main__":
    main()