import os
import sys
import time
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

import traci
from src.utils.sumo_integration import SumoSimulation
from src.ai.controller_factory import ControllerFactory

class ScenarioRunner:
    """
    Class for running SUMO traffic scenarios with different controllers.
    """
    def __init__(self, network_file=None):
        """
        Initialize the scenario runner.
        
        Args:
            network_file: Path to the SUMO network file to use
        """
        self.project_root = project_root
        
        if network_file is None:
            network_file = os.path.join(project_root, "config", "maps", "traffic_grid.net.xml")
        
        self.network_file = network_file
        self.results_dir = os.path.join(project_root, "data", "outputs", "scenarios")
        
        # Ensure results directory exists
        os.makedirs(self.results_dir, exist_ok=True)
    
    def run_scenario(self, scenario_file, controller_type, steps=1000, 
                    gui=False, delay=0, collect_metrics=True, model_path=None):
        """
        Run a specific scenario with a given controller type.
        
        Args:
            scenario_file: Path to the SUMO route file
            controller_type: Type of controller to use ('Wired AI', 'Wireless AI', or 'Traditional')
            steps: Number of simulation steps to run
            gui: Whether to show SUMO GUI
            delay: Delay between steps (ms)
            collect_metrics: Whether to collect performance metrics
            model_path: Path to the model file for RL controllers (optional)
            
        Returns:
            Dictionary of performance metrics
        """
        # Create a SUMO configuration file for this run
        sumo_config = self._create_temp_config(scenario_file)
        
        # Start the SUMO simulation
        sim = SumoSimulation(sumo_config, gui=gui)
        sim.start()
        
        # Initialize metrics collection
        metrics = {
            "controller_type": controller_type,
            "scenario": os.path.basename(scenario_file),
            "steps": steps,
            "waiting_times": [],
            "speeds": [],
            "throughput": 0,
            "response_times": [],
            "decision_times": []
        }
        
        try:
            # Get traffic light IDs
            tl_ids = traci.trafficlight.getIDList()
            
            if not tl_ids:
                print("Warning: No traffic lights found in the simulation!")
                return metrics
            
            # Create controller with model_path if provided
            controller_kwargs = {}
            if model_path and "RL" in controller_type:
                controller_kwargs["model_path"] = model_path
                
            controller = ControllerFactory.create_controller(controller_type, tl_ids, **controller_kwargs)
            
            print(f"Running scenario {os.path.basename(scenario_file)} with {controller_type} controller...")
            
            # Main simulation loop
            for step in range(steps):
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
                
                # Collect metrics if enabled
                if collect_metrics:
                    self._update_metrics(metrics)
                
                # Step the simulation
                sim.step()
                
                # Add delay if specified
                if delay > 0:
                    time.sleep(delay / 1000.0)
                
                # Print progress
                if step % 100 == 0:
                    print(f"Step {step}/{steps}")
            
            # Store final metrics
            if collect_metrics:
                # Get controller-specific metrics and set in metrics
                if controller.response_times:
                    metrics["response_times"] = controller.response_times
                
                if controller.decision_times:
                    metrics["decision_times"] = controller.decision_times
                
                # Calculate avrages metrics
                if metrics["waiting_times"]:
                    metrics["avg_waiting_time"] = sum(metrics["waiting_times"]) / len(metrics["waiting_times"])
                else:
                    metrics["avg_waiting_time"] = 0
                
                if metrics["speeds"]:
                    metrics["avg_speed"] = sum(metrics["speeds"]) / len(metrics["speeds"])
                else:
                    metrics["avg_speed"] = 0
                
                if metrics["response_times"]:
                    metrics["avg_response_time"] = sum(metrics["response_times"]) / len(metrics["response_times"])
                else:
                    metrics["avg_response_time"] = 0
                
                if metrics["decision_times"]:
                    metrics["avg_decision_time"] = sum(metrics["decision_times"]) / len(metrics["decision_times"])
                else:
                    metrics["avg_decision_time"] = 0
                
                # Print summary
                print("\nScenario Results:")
                print(f"Average Waiting Time: {metrics['avg_waiting_time']:.2f} seconds")
                print(f"Average Speed: {metrics['avg_speed']:.2f} m/s")
                print(f"Total Throughput: {metrics['throughput']} vehicles")
                print(f"Average Response Time: {metrics['avg_response_time']*1000:.2f} ms")
                print(f"Average Decision Time: {metrics['avg_decision_time']*1000:.2f} ms")
        
        finally:
            # Close the simulation
            sim.close()
        
        return metrics
    
    def _create_temp_config(self, route_file):
        """
        Create a temporary SUMO configuration file.
        
        Args:
            route_file: Path to the route file
            
        Returns:
            Path to the created config file
        """
        # Create a unique config file name
        config_name = f"temp_{os.path.basename(route_file).split('.')[0]}.sumocfg"
        config_path = os.path.join(project_root, "config", "scenarios", config_name)
        
        # Write the config file
        with open(config_path, 'w') as f:
            f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/sumoConfiguration.xsd">
    <input>
        <net-file value="{self.network_file}"/>
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
        <verbose value="true"/>
        <no-step-log value="false"/>
    </report>
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
        metrics["waiting_times"].append(avg_waiting_time)
        
        # Calculate average speed
        total_speed = sum(traci.vehicle.getSpeed(v) for v in vehicles)
        avg_speed = total_speed / len(vehicles)
        metrics["speeds"].append(avg_speed)