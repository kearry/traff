import os
import sys
import argparse
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

import pygame
import time
from src.ui.sumo_visualization import SumoVisualization
from src.ai.controller_factory import ControllerFactory

def main():
    """Run a visual comparison of traffic controllers on scenarios."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Visualize traffic scenario with a specific controller')
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
    
    print(f"Running scenario {args.scenario} with {args.controller} controller...")
    
    # Create a temporary config file
    config_path = create_temp_config(scenario_path)
    
    # Run the visualization
    vis = SumoVisualization(config_path, width=1024, height=768, use_gui=False)
    vis.set_mode(args.controller)
    
    if not vis.start():
        print("Failed to start visualization")
        return
    
    # Run the simulation
    import traci
    
    # Get traffic light IDs
    tl_ids = traci.trafficlight.getIDList()
    
    if not tl_ids:
        print("No traffic lights found in the simulation!")
        return
    
    # Create controller
    controller = ControllerFactory.create_controller(args.controller, tl_ids)
    
    # Main simulation loop
    for step in range(args.steps):
        # Collect traffic state
        traffic_state = collect_traffic_state(tl_ids)
        
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
                if step % 50 == 0:
                    print(f"Step {step}: Traffic light {tl_id} changed to {phase}")
        
        # Step the visualization
        if not vis.step(args.delay):
            break
        
        # Print progress
        if step % 50 == 0:
            print(f"Step {step}/{args.steps}")
            
            # Get average waiting time and speed
            vehicles = traci.vehicle.getIDList()
            if vehicles:
                total_waiting_time = sum(traci.vehicle.getWaitingTime(v) for v in vehicles)
                total_speed = sum(traci.vehicle.getSpeed(v) for v in vehicles)
                avg_waiting_time = total_waiting_time / len(vehicles)
                avg_speed = total_speed / len(vehicles)
                print(f"  Vehicles: {len(vehicles)}, Avg Wait: {avg_waiting_time:.2f}s, Avg Speed: {avg_speed:.2f}m/s")
                
                if controller.response_times:
                    avg_response = sum(controller.response_times) / len(controller.response_times) * 1000
                    print(f"  Avg Response Time: {avg_response:.2f}ms")
    
    # Close visualization
    vis.close()
    
    # Print final controller metrics
    if controller.response_times:
        avg_response = sum(controller.response_times) / len(controller.response_times) * 1000
        print(f"Average Response Time: {avg_response:.2f}ms")
    
    if controller.decision_times:
        avg_decision = sum(controller.decision_times) / len(controller.decision_times) * 1000
        print(f"Average Decision Time: {avg_decision:.2f}ms")

def create_temp_config(route_file):
    """
    Create a temporary SUMO configuration file.
    
    Args:
        route_file: Path to the route file
        
    Returns:
        Path to the created config file
    """
    # Network file
    network_file = os.path.join(project_root, "config", "maps", "traffic_grid.net.xml")
    
    # Create a unique config file name
    config_name = f"temp_scenario_{os.path.basename(route_file).split('.')[0]}.sumocfg"
    config_path = os.path.join(project_root, "config", "scenarios", config_name)
    
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

def collect_traffic_state(tl_ids):
    """
    Collect the current traffic state for all traffic lights.
    
    Args:
        tl_ids: List of traffic light IDs
        
    Returns:
        Dictionary of traffic state information
    """
    import traci
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

if __name__ == "__main__":
    main()