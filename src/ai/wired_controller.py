import time
import random
import numpy as np
from src.ai.controller import TrafficController

class WiredController(TrafficController):
    """
    Wired AI Traffic Controller implementation.
    
    This controller simulates a fixed-network connection with consistent
    but non-zero latency for communication between the traffic lights
    and the central control system.
    """
    def __init__(self, junction_ids, network_latency=0.1):
        """
        Initialize the wired controller.
        
        Args:
            junction_ids (list): List of junction IDs to control
            network_latency (float): Simulated network latency in seconds
        """
        super().__init__(junction_ids)
        self.network_latency = network_latency
        
        # Define phase durations for each junction (in seconds)
        self.phase_durations = {
            junction_id: {
                "GrYr": 30.0,  # Green for north-south, red for east-west
                "yrGr": 5.0,   # Yellow transitioning to red for north-south
                "rGry": 30.0,  # Red for north-south, green for east-west
                "ryrG": 5.0    # Red for north-south, yellow transitioning to red for east-west
            }
            for junction_id in junction_ids
        }
        
        # Define the phase sequence for each junction
        self.phase_sequence = ["GrYr", "yrGr", "rGry", "ryrG"]
        
        # Initialize the current phase for each junction
        for junction_id in junction_ids:
            self.current_phase[junction_id] = self.phase_sequence[0]
    
    def decide_phase(self, junction_id, current_time):
        """
        Decide the next traffic light phase for a junction.
        
        Args:
            junction_id (str): The ID of the junction to control
            current_time (float): Current simulation time
            
        Returns:
            str: The traffic light state to set
        """
        # Simulate network latency for the wired connection
        # This represents the delay in sending commands over the network
        time.sleep(self.network_latency)
        
        # Record start time for response time measurement
        response_start = time.time()
        
        # Get the current phase
        current_phase = self.current_phase[junction_id]
        
        # Basic AI logic based on traffic state
        # If we have traffic data for this junction
        if junction_id in self.traffic_state:
            junction_data = self.traffic_state[junction_id]
            
            # Get vehicle counts on each approach
            north_south_count = junction_data.get('north_count', 0) + junction_data.get('south_count', 0)
            east_west_count = junction_data.get('east_count', 0) + junction_data.get('west_count', 0)
            
            # Compare vehicle counts and adjust timing if significant difference
            # (This is a simplified AI approach - we'd use more sophisticated methods in a real system)
            if north_south_count > east_west_count * 1.5 and north_south_count > 0:
                # Heavy north-south traffic - extend green time for north-south
                if current_phase == "GrYr":
                    # Safely calculate new duration avoiding division by zero FIX
                    if east_west_count > 0:
                        self.phase_durations[junction_id]["GrYr"] = min(60.0, 30.0 + (north_south_count / east_west_count) * 10)
                    else:
                        # Maximum green time if no east-west traffic
                        self.phase_durations[junction_id]["GrYr"] = 60.0
                else:
                    # Move to north-south green phase
                    next_phase_index = (self.phase_sequence.index(current_phase) + 1) % len(self.phase_sequence)
                    next_phase = self.phase_sequence[next_phase_index]
                    
                    # Record response time
                    self.response_times.append(time.time() - response_start)
                    
                    return next_phase
            
            elif east_west_count > north_south_count * 1.5 and east_west_count > 0:
                # Heavy east-west traffic - extend green time for east-west
                if current_phase == "rGry":
                    # Safely calculate new duration avoiding division by zero
                    if north_south_count > 0:
                        self.phase_durations[junction_id]["rGry"] = min(60.0, 30.0 + (east_west_count / north_south_count) * 10)
                    else:
                        # Maximum green time if no north-south traffic
                        self.phase_durations[junction_id]["rGry"] = 60.0
                else:
                    # Move to east-west green phase
                    next_phase_index = (self.phase_sequence.index(current_phase) + 1) % len(self.phase_sequence)
                    next_phase = self.phase_sequence[next_phase_index]
                    
                    # Record response time
                    self.response_times.append(time.time() - response_start)
                    
                    return next_phase
        
        # If no specific traffic condition requires attention or no traffic data,
        # follow the normal phase sequence
        current_index = self.phase_sequence.index(current_phase)
        next_phase = self.phase_sequence[(current_index + 1) % len(self.phase_sequence)]
        
        # Record response time
        self.response_times.append(time.time() - response_start)
        
        return next_phase