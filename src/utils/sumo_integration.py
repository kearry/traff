import os
import sys
import traci
import traci.constants as tc
from pathlib import Path

class SumoSimulation:
    def __init__(self, config_path, gui=False):
        """
        Initialize the SUMO simulation.
        
        Args:
            config_path (str): Path to the SUMO configuration file
            gui (bool): Whether to use the SUMO GUI
        """
        self.config_path = config_path
        self.gui = gui
        self.sumo_binary = "sumo-gui" if gui else "sumo"
        self.running = False
        
    def start(self):
        """Start the SUMO simulation"""
        # Check if the configuration file exists
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"SUMO configuration file not found: {self.config_path}")
        
        # Start the SUMO simulation
        sumo_cmd = [self.sumo_binary, "-c", self.config_path]
        traci.start(sumo_cmd)
        self.running = True
        print(f"Started SUMO simulation with configuration: {self.config_path}")
        
    def step(self):
        """Execute a single simulation step"""
        if not self.running:
            raise RuntimeError("Simulation not running. Call start() first.")
        
        traci.simulationStep()
        
    def get_vehicle_count(self):
        """Get the current number of vehicles in the simulation"""
        if not self.running:
            raise RuntimeError("Simulation not running. Call start() first.")
        
        return len(traci.vehicle.getIDList())
    
    def get_traffic_light_state(self, tl_id):
        """Get the state of a traffic light"""
        if not self.running:
            raise RuntimeError("Simulation not running. Call start() first.")
        
        return traci.trafficlight.getRedYellowGreenState(tl_id)
    
    def set_traffic_light_state(self, tl_id, state):
        """Set the state of a traffic light"""
        if not self.running:
            raise RuntimeError("Simulation not running. Call start() first.")
        
        traci.trafficlight.setRedYellowGreenState(tl_id, state)
    
    def close(self):
        """Close the SUMO simulation"""
        if self.running:
            traci.close()
            self.running = False
            print("Closed SUMO simulation")

    def get_average_waiting_time(self):
        """Calculate the average waiting time for all vehicles"""
        if not self.running:
            raise RuntimeError("Simulation not running. Call start() first.")
        
        vehicles = traci.vehicle.getIDList()
        if not vehicles:
            return 0
        
        total_waiting_time = sum(traci.vehicle.getWaitingTime(vehicle) for vehicle in vehicles)
        return total_waiting_time / len(vehicles)

    def get_traffic_throughput(self, edge_id):
        """Get the number of vehicles that have passed a specific edge"""
        if not self.running:
            raise RuntimeError("Simulation not running. Call start() first.")
        
        return traci.edge.getLastStepVehicleNumber(edge_id)