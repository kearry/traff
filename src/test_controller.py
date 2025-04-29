import os
import sys
import time
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

import traci
from src.utils.sumo_integration import SumoSimulation
from src.ai.controller_factory import ControllerFactory

def main():
    # Path to the SUMO configuration file
    config_path = os.path.join(project_root, "config", "maps", "traffic_grid.sumocfg")
    print(f"Using SUMO config: {config_path}")
    
    # Initialize the SUMO simulation
    sim = SumoSimulation(config_path, gui=True)
    sim.start()
    
    try:
        # Get all traffic light IDs from the simulation
        tl_ids = traci.trafficlight.getIDList()
        print(f"Traffic lights: {tl_ids}")
        
        if not tl_ids:
            print("No traffic lights found in the simulation!")
            return
        
        # Create controllers for testing
        controllers = {
            "Wired AI": ControllerFactory.create_controller("Wired AI", tl_ids, network_latency=0.1),
            "Wireless AI": ControllerFactory.create_controller("Wireless AI", tl_ids, 
                                                              base_latency=0.05, 
                                                              computation_factor=0.1),
            "Traditional": ControllerFactory.create_controller("Traditional", tl_ids)
        }
        
        # Select which controller to test
        active_controller_name = "Wired AI"  # Change this to test different controllers
        active_controller = controllers[active_controller_name]
        
        print(f"Testing {active_controller_name} controller")
        
        # Run the simulation for a specified number of steps
        for step in range(100):
            # Step the simulation
            sim.step()
            
            # Get current simulation time
            current_time = traci.simulation.getTime()
            
            # Collect traffic state information
            traffic_state = {}
            for tl_id in tl_ids:
                # Get the incoming lanes for this traffic light
                incoming_lanes = []
                for connection in traci.trafficlight.getControlledLinks(tl_id):
                    if connection and connection[0]:  # Check if the connection exists
                        incoming_lane = connection[0][0]
                        if incoming_lane not in incoming_lanes:
                            incoming_lanes.append(incoming_lane)
                
                # Count vehicles on the incoming lanes
                north_count = south_count = east_count = west_count = 0
                north_wait = south_wait = east_wait = west_wait = 0
                north_queue = south_queue = east_queue = west_queue = 0
                
                for lane in incoming_lanes:
                    # Determine direction based on lane ID (simplistic approach)
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
                
                # Store the traffic state for this junction
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
            
            # Update the controller with traffic state
            active_controller.update_traffic_state(traffic_state)
            
            # Get phase decisions from the controller for each junction
            for tl_id in tl_ids:
                phase = active_controller.get_phase_for_junction(tl_id, current_time)
                
                # Set the traffic light phase in SUMO
                current_sumo_state = traci.trafficlight.getRedYellowGreenState(tl_id)
                
                # Only update if the phase is different
                if phase != current_sumo_state:
                    traci.trafficlight.setRedYellowGreenState(tl_id, phase)
                    print(f"Step {step}: Traffic light {tl_id} changed to {phase}")
            
            # Print some stats periodically
            if step % 10 == 0:
                print(f"\nStep {step}: Simulation time = {current_time:.1f}s")
                print(f"Average decision time: {active_controller.get_average_decision_time() * 1000:.2f} ms")
                print(f"Average response time: {active_controller.get_average_response_time() * 1000:.2f} ms")
                
                # Print traffic state for the first junction
                if tl_ids:
                    first_tl = tl_ids[0]
                    if first_tl in traffic_state:
                        state = traffic_state[first_tl]
                        print(f"Traffic at {first_tl}: N={state['north_count']}, S={state['south_count']}, "
                              f"E={state['east_count']}, W={state['west_count']}")
    
    finally:
        # Close the simulation
        sim.close()

if __name__ == "__main__":
    main()