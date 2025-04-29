# src/ui/enhanced_traffic_visualizer.py
import os
import sys
import argparse
import traci
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

import pygame
import time
from src.ui.enhanced_sumo_visualization import EnhancedSumoVisualization
from src.ai.controller_factory import ControllerFactory

def run_enhanced_visualization(config_path, controller_type, steps=1000, delay=50):
    """
    Run the enhanced visualization with a specific controller.
    
    Args:
        config_path: Path to the SUMO configuration file
        controller_type: Type of controller to use
        steps: Number of simulation steps to run
        delay: Delay in milliseconds between steps
    """
    # Create the visualization
    visualization = EnhancedSumoVisualization(config_path, width=1024, height=768, use_gui=False)
    visualization.set_mode(controller_type)
    
    # Start the visualization
    if not visualization.start():
        print("Failed to start visualization")
        return
    
    try:
        # Get traffic light IDs
        tl_ids = traci.trafficlight.getIDList()
        
        if not tl_ids:
            print("No traffic lights found in the simulation!")
            visualization.close()
            return
        
        # Create controller based on selected type
        controller = ControllerFactory.create_controller(controller_type, tl_ids)
        
        print(f"Created {controller_type} controller for traffic lights: {tl_ids}")
        
        # Run the simulation for specified number of steps
        for step in range(steps):
            # Collect traffic state
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
                    waiting_time = sum(traci.vehicle.getWaitingTime(v) for v in traci.lane.getLastStepVehicleIDs(lane))
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
                
                # Store traffic state for this junction
                traffic_state[tl_id] = {
                    'north_count': north_count,
                    'south_count': south_count,
                    'east_count': east_count,
                    'west_count': west_count,
                    'north_wait': north_wait / max(1, north_count) if north_count > 0 else 0,
                    'south_wait': south_wait / max(1, south_count) if south_count > 0 else 0,
                    'east_wait': east_wait / max(1, east_count) if east_count > 0 else 0,
                    'west_wait': west_wait / max(1, west_count) if west_count > 0 else 0,
                    'north_queue': north_queue,
                    'south_queue': south_queue,
                    'east_queue': east_queue,
                    'west_queue': west_queue
                }
            
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
                    if step % 50 == 0:  # Don't print too much
                        print(f"Step {step}: Traffic light {tl_id} changed to {phase}")
            
            # Display step in the simulation
            if step % 50 == 0:
                print(f"Step #{step}/{steps} (Time: {current_time:.2f}s)")
            
            # Step the visualization
            result = visualization.step(delay)
            if not result:
                break
        
        # Close everything properly
        visualization.close()
        
        # Report performance metrics
        if controller.response_times:
            avg_resp = sum(controller.response_times) / len(controller.response_times)
            print(f"Average controller response time: {avg_resp * 1000:.2f} ms")
        
        if controller.decision_times:
            avg_dec = sum(controller.decision_times) / len(controller.decision_times)
            print(f"Average controller decision time: {avg_dec * 1000:.2f} ms")
        
        # Report other simulation metrics
        wait_times = visualization.performance_metrics["wait_times"]
        speeds = visualization.performance_metrics["speeds"]
        throughput = visualization.performance_metrics["throughput"]
        
        if wait_times:
            avg_wait = sum(wait_times) / len(wait_times)
            print(f"Average wait time: {avg_wait:.2f} seconds")
        
        if speeds:
            avg_speed = sum(speeds) / len(speeds)
            print(f"Average speed: {avg_speed:.2f} m/s")
        
        if throughput:
            total_throughput = sum(throughput)
            print(f"Total throughput: {total_throughput} vehicles")
    
    except Exception as e:
        print(f"Error during simulation: {e}")
        import traceback
        traceback.print_exc()
        visualization.close()

def main():
    """Main function to run the enhanced visualization"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run enhanced traffic visualization')
    parser.add_argument('--scenario', type=str, default=None,
                        help='Scenario file to run (without .sumocfg extension)')
    parser.add_argument('--controller', type=str, default="Wired AI",
                        choices=["Wired AI", "Wireless AI", "Traditional"],
                        help='Controller type to use')
    parser.add_argument('--steps', type=int, default=1000,
                        help='Number of simulation steps to run')
    parser.add_argument('--delay', type=int, default=50,
                        help='Delay in milliseconds between steps')
    args = parser.parse_args()
    
    # Determine which configuration file to use
    if args.scenario:
        # Use the specified scenario
        config_path = os.path.join(project_root, "config", "scenarios", f"{args.scenario}.sumocfg")
        if not os.path.exists(config_path):
            print(f"Scenario configuration file not found: {config_path}")
            return
    else:
        # Use the default configuration
        config_path = os.path.join(project_root, "config", "maps", "traffic_grid.sumocfg")
    
    print(f"Using configuration file: {config_path}")
    
    # Run the visualization
    run_enhanced_visualization(config_path, args.controller, args.steps, args.delay)

if __name__ == "__main__":
    main()