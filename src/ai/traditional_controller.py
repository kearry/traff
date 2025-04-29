import time
from src.ai.controller import TrafficController

class TraditionalController(TrafficController):
    """
    Traditional Traffic Controller implementation.
    
    This controller uses fixed timing for traffic lights without any
    adaptive behavior. It serves as a baseline for comparison.
    """
    def __init__(self, junction_ids):
        """
        Initialize the traditional controller.
        
        Args:
            junction_ids (list): List of junction IDs to control
        """
        super().__init__(junction_ids)
        
        # Define fixed phase durations for each junction (in seconds)
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
        For the traditional controller, this simply follows the fixed sequence.
        
        Args:
            junction_id (str): The ID of the junction to control
            current_time (float): Current simulation time
            
        Returns:
            str: The traffic light state to set
        """
        # Record start time for response time measurement
        response_start = time.time()
        
        # Get the current phase
        current_phase = self.current_phase[junction_id]
        
        # Simply move to the next phase in the predefined sequence
        current_index = self.phase_sequence.index(current_phase)
        next_phase = self.phase_sequence[(current_index + 1) % len(self.phase_sequence)]
        
        # Record response time (should be minimal for traditional controller)
        self.response_times.append(time.time() - response_start)
        
        return next_phase