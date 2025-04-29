import time
import random
import numpy as np
from src.ai.controller import TrafficController

class WirelessController(TrafficController):
    """
    Wireless AI Traffic Controller implementation.
    
    This controller simulates a wireless connection with variable latency
    that depends on the complexity of the traffic situation and potential
    interference. It includes more computation for optimal routing decisions.
    """
    def __init__(self, junction_ids, base_latency=0.05, computation_factor=0.1):
        """
        Initialize the wireless controller.
        
        Args:
            junction_ids (list): List of junction IDs to control
            base_latency (float): Base network latency in seconds
            computation_factor (float): Factor for additional computation time
        """
        super().__init__(junction_ids)
        self.base_latency = base_latency
        self.computation_factor = computation_factor
        
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
        
        # Last decision parameters - used to implement more dynamic AI behavior
        self.last_decision_params = {}
    
    def _calculate_dynamic_latency(self, traffic_complexity):
        """
        Calculate dynamic latency based on traffic complexity and random factors
        (simulating wireless interference, computation time, etc.)
        
        Args:
            traffic_complexity (float): Measure of traffic complexity (0.0-1.0)
            
        Returns:
            float: Total latency time in seconds
        """
        # Base latency
        latency = self.base_latency
        
        # Add computation time based on traffic complexity
        computation_time = traffic_complexity * self.computation_factor
        
        # Add random fluctuation to simulate wireless interference
        # More traffic means more devices, potentially more interference
        interference = random.uniform(0, 0.1) * traffic_complexity
        
        return latency + computation_time + interference
    
    def decide_phase(self, junction_id, current_time):
        """
        Decide the next traffic light phase for a junction.
        Implements a more sophisticated AI approach than the wired controller.
        
        Args:
            junction_id (str): The ID of the junction to control
            current_time (float): Current simulation time
            
        Returns:
            str: The traffic light state to set
        """
        # Get the current phase
        current_phase = self.current_phase[junction_id]
        
        # Default complexity for the case where we don't have traffic data
        traffic_complexity = 0.5
        
        # Initialize variables for AI decision
        north_south_count = 0
        east_west_count = 0
        waiting_times = {"north": 0, "south": 0, "east": 0, "west": 0}
        queue_lengths = {"north": 0, "south": 0, "east": 0, "west": 0}
        
        # If we have traffic data, extract relevant metrics
        if junction_id in self.traffic_state:
            junction_data = self.traffic_state[junction_id]
            
            # Extract vehicle counts, waiting times, and queue lengths
            north_south_count = junction_data.get('north_count', 0) + junction_data.get('south_count', 0)
            east_west_count = junction_data.get('east_count', 0) + junction_data.get('west_count', 0)
            
            for direction in ['north', 'south', 'east', 'west']:
                waiting_times[direction] = junction_data.get(f'{direction}_wait', 0)
                queue_lengths[direction] = junction_data.get(f'{direction}_queue', 0)
            
            # Calculate traffic complexity based on total vehicle count and balance
            total_vehicles = north_south_count + east_west_count
            if total_vehicles > 0:
                # Balance factor: 0 for perfectly balanced, 1 for completely imbalanced
                balance = abs(north_south_count - east_west_count) / total_vehicles
                # Normalize total vehicles to a 0-1 scale (assuming max of 50 vehicles is high complexity)
                volume_factor = min(1.0, total_vehicles / 50.0)
                # Combine factors to get overall complexity
                traffic_complexity = (volume_factor * 0.7) + (balance * 0.3)
            else:
                traffic_complexity = 0.0
        
        # Simulate dynamic latency based on traffic complexity
        dynamic_latency = self._calculate_dynamic_latency(traffic_complexity)
        
        # Simulate the wireless latency and computation time
        time.sleep(dynamic_latency)
        
        # Record start time for response time measurement
        response_start = time.time()
        
        # Advanced AI logic for decision making
        # Store decision parameters for more complex behavior
        decision_params = {
            'north_south_count': north_south_count,
            'east_west_count': east_west_count,
            'waiting_times': waiting_times,
            'queue_lengths': queue_lengths,
            'traffic_complexity': traffic_complexity
        }
        
        # Implement a weighted decision approach based on multiple factors
        if traffic_complexity > 0.3:  # Only apply sophisticated logic for non-trivial traffic situations
            # Calculate the weighted priority for each direction
            ns_priority = (
                north_south_count * 1.0 +
                (waiting_times['north'] + waiting_times['south']) * 0.5 +
                (queue_lengths['north'] + queue_lengths['south']) * 2.0
            )
            
            ew_priority = (
                east_west_count * 1.0 +
                (waiting_times['east'] + waiting_times['west']) * 0.5 +
                (queue_lengths['east'] + queue_lengths['west']) * 2.0
            )
            
            # Decision logic based on phase and priorities
            if current_phase == "GrYr" and ns_priority > ew_priority * 1.25:
                # Extend north-south green time if priority is significantly higher
                if ew_priority > 0:
                    self.phase_durations[junction_id]["GrYr"] = min(60.0, 30.0 + (ns_priority / ew_priority) * 5)
                else:
                    # Max green time if no east-west priority
                    self.phase_durations[junction_id]["GrYr"] = 60.0
                
                # Record response time
                self.response_times.append(time.time() - response_start)
                
                # Continue with the same phase
                self.last_decision_params[junction_id] = decision_params
                return current_phase
                
            elif current_phase == "rGry" and ew_priority > ns_priority * 1.25:
                # Extend east-west green time if priority is significantly higher
                if ns_priority > 0:
                    self.phase_durations[junction_id]["rGry"] = min(60.0, 30.0 + (ew_priority / ns_priority) * 5)
                else:
                    # Max green time if no north-south priority
                    self.phase_durations[junction_id]["rGry"] = 60.0
                
                # Record response time
                self.response_times.append(time.time() - response_start)
                
                # Continue with the same phase
                self.last_decision_params[junction_id] = decision_params
                return current_phase
        
        # If no specific condition requires maintaining the current phase,
        # proceed to the next phase in sequence
        current_index = self.phase_sequence.index(current_phase)
        next_phase = self.phase_sequence[(current_index + 1) % len(self.phase_sequence)]
        
        # Record response time
        self.response_times.append(time.time() - response_start)
        
        # Store the decision parameters for reference in future decisions
        self.last_decision_params[junction_id] = decision_params
        
        return next_phase