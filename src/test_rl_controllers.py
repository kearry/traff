import os
import sys
import time
import argparse
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import json

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

import traci
from src.utils.sumo_integration import SumoSimulation
from src.ai.controller_factory import ControllerFactory

def run_test(controller_type, config_path, model_path=None, steps=1000, gui=False, delay=0):
    """
    Run a test with a specific controller.
    
    Args:
        controller_type (str): Type of controller to test
        config_path (str): Path to the SUMO configuration file
        model_path (str): Path to the trained model (for RL controllers)
        steps (int): Number of simulation steps
        gui (bool): Whether to show SUMO GUI
        delay (int): Delay between steps in milliseconds
        
    Returns:
        dict: Test metrics
    """
    # Start the simulation
    sim = SumoSimulation(config_path, gui=gui)
    sim.start()
    
    # Get traffic light IDs
    tl_ids = traci.trafficlight.getIDList()
    
    if not tl_ids:
        print("No traffic lights found in the simulation.")
        sim.close()
        return {}
    
    # Create controller
    controller_kwargs = {}
    if "RL" in controller_type and model_path:
        controller_kwargs["model_path"] = model_path
        # Set low exploration rate for testing
        controller_kwargs["exploration_rate"] = 0.05
    
    controller = ControllerFactory.create_controller(controller_type, tl_ids, **controller_kwargs)
    
    # Initialize metrics
    metrics = {
        "controller_type": controller_type,
        "steps": steps,
        "waiting_times": [],
        "speeds": [],
        "throughput": 0,
        "vehicle_counts": [],
        "traffic_states": {}
    }
    
    start_time = time.time()
    
    # Run the simulation
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
            
            # Store traffic state
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
        
        # Store traffic state for analysis
        if step % 50 == 0:  # Store every 50th step to save memory
            metrics["traffic_states"][step] = traffic_state
        
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
        
        # Collect metrics
        vehicles = traci.vehicle.getIDList()
        metrics["vehicle_counts"].append(len(vehicles))
        
        if vehicles:
            avg_wait = sum(traci.vehicle.getWaitingTime(v) for v in vehicles) / len(vehicles)
            avg_speed = sum(traci.vehicle.getSpeed(v) for v in vehicles) / len(vehicles)
            metrics["waiting_times"].append(avg_wait)
            metrics["speeds"].append(avg_speed)
        else:
            metrics["waiting_times"].append(0)
            metrics["speeds"].append(0)
        
        metrics["throughput"] += traci.simulation.getArrivedNumber()
        
        # Step the simulation
        sim.step()
        
        # Add delay
        if delay > 0:
            time.sleep(delay / 1000.0)
        
        # Print progress
        if step % 100 == 0 and step > 0:
            print(f"Step {step}/{steps} - "
                  f"Vehicles: {len(vehicles)}, "
                  f"Avg Wait: {metrics['waiting_times'][-1]:.2f}s, "
                  f"Avg Speed: {metrics['speeds'][-1]:.2f}m/s")
    
    # Add controller-specific metrics
    if hasattr(controller, "get_network_stats"):
        metrics["network_stats"] = controller.get_network_stats()
    
    if hasattr(controller, "get_average_reward") and "RL" in controller_type:
        metrics["average_reward"] = controller.get_average_reward()
    
    # Add decision and response times
    if controller.decision_times:
        metrics["avg_decision_time"] = sum(controller.decision_times) / len(controller.decision_times)
    else:
        metrics["avg_decision_time"] = 0
    
    if controller.response_times:
        metrics["avg_response_time"] = sum(controller.response_times) / len(controller.response_times)
    else:
        metrics["avg_response_time"] = 0
    
    # Calculate aggregate metrics
    if metrics["waiting_times"]:
        metrics["avg_waiting_time"] = sum(metrics["waiting_times"]) / len(metrics["waiting_times"])
    else:
        metrics["avg_waiting_time"] = 0
    
    if metrics["speeds"]:
        metrics["avg_speed"] = sum(metrics["speeds"]) / len(metrics["speeds"])
    else:
        metrics["avg_speed"] = 0
    
    # Record total time
    metrics["total_time"] = time.time() - start_time
    
    # Close the simulation
    sim.close()
    
    # Print results
    print(f"\nTest Results for {controller_type}:")
    print(f"Average waiting time: {metrics['avg_waiting_time']:.2f}s")
    print(f"Average speed: {metrics['avg_speed']:.2f}m/s")
    print(f"Total throughput: {metrics['throughput']} vehicles")
    print(f"Average decision time: {metrics['avg_decision_time']*1000:.2f}ms")
    print(f"Average response time: {metrics['avg_response_time']*1000:.2f}ms")
    
    if "network_stats" in metrics:
        net_stats = metrics["network_stats"]
        print(f"Network statistics:")
        print(f"  Average latency: {net_stats.get('avg_latency', 0)*1000:.2f}ms")
        print(f"  Packet loss rate: {net_stats.get('packet_loss_rate', 0)*100:.2f}%")
    
    if "average_reward" in metrics:
        print(f"Average reward: {metrics['average_reward']:.2f}")
    
    return metrics

def compare_controllers(controllers, scenario, model_paths=None, steps=1000, output_dir=None, gui=False):
    """
    Compare multiple controllers on the same scenario.
    
    Args:
        controllers (list): List of controller types to compare
        scenario (str): Scenario name
        model_paths (dict): Dictionary mapping controller types to model paths
        steps (int): Number of simulation steps
        output_dir (str): Directory to save results
        gui (bool): Whether to show SUMO GUI
        
    Returns:
        dict: Comparison results
    """
    if output_dir is None:
        output_dir = os.path.join(project_root, "data", "outputs")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Construct scenario path
    scenario_path = os.path.join(project_root, "config", "scenarios", f"{scenario}.sumocfg")
    # Chat
    if not os.path.exists(scenario_path):
        raise FileNotFoundError(f"Scenario configuration file not found: {scenario_path}")
    
    results = {}
    
    for controller_type in controllers:
        print(f"\nTesting controller: {controller_type}")
        
        model_path = None
        if model_paths and controller_type in model_paths:
            model_path = model_paths[controller_type]
        
        # Run the test
        metrics = run_test(
            controller_type=controller_type,
            config_path=scenario_path,
            model_path=model_path,
            steps=steps,
            gui=gui
        )
        
        # Save the metrics to a JSON file
        output_file = os.path.join(output_dir, f"{controller_type}_{scenario}_results.json")
        with open(output_file, "w") as f:
            json.dump(metrics, f, indent=4)
        
        results[controller_type] = metrics
    
    # Plot comparison
    fig, axs = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"Controller Comparison: {scenario}", fontsize=16)
    
    # Plot average waiting times
    for ctrl, data in results.items():
        axs[0, 0].plot(data["waiting_times"], label=ctrl)
    axs[0, 0].set_title("Average Waiting Time per Step")
    axs[0, 0].set_xlabel("Step")
    axs[0, 0].set_ylabel("Waiting Time (s)")
    axs[0, 0].legend()
    
    # Plot average speeds
    for ctrl, data in results.items():
        axs[0, 1].plot(data["speeds"], label=ctrl)
    axs[0, 1].set_title("Average Speed per Step")
    axs[0, 1].set_xlabel("Step")
    axs[0, 1].set_ylabel("Speed (m/s)")
    axs[0, 1].legend()
    
    # Plot vehicle counts
    for ctrl, data in results.items():
        axs[1, 0].plot(data["vehicle_counts"], label=ctrl)
    axs[1, 0].set_title("Vehicle Count per Step")
    axs[1, 0].set_xlabel("Step")
    axs[1, 0].set_ylabel("Number of Vehicles")
    axs[1, 0].legend()
    
    # Plot throughput
    throughputs = [data["throughput"] for data in results.values()]
    ctrl_labels = list(results.keys())
    axs[1, 1].bar(ctrl_labels, throughputs)
    axs[1, 1].set_title("Total Throughput")
    axs[1, 1].set_ylabel("Vehicles Passed")
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    comparison_plot_path = os.path.join(output_dir, f"comparison_{scenario}.png")
    plt.savefig(comparison_plot_path)
    plt.close()
    
    print(f"\nComparison plot saved to: {comparison_plot_path}")
    
    return results
