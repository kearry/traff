import os
import sys
import time
import numpy as np
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))

from src.ai.reinforcement_learning.q_learning_controller import QLearningController

class WiredRLController(QLearningController):
    """
    Wired Reinforcement Learning Controller.
    
    This controller extends the Q-Learning controller and simulates
    wired network conditions (fixed latency, reliable communication).
    """
    def __init__(self, junction_ids, learning_rate=0.1, discount_factor=0.9, 
                exploration_rate=0.3, state_bins=3, model_path=None,
                network_latency=0.1):
        """
        Initialize the Wired RL controller.
        
        Args:
            junction_ids (list): List of junction IDs to control
            learning_rate (float): Alpha parameter for Q-learning updates (0-1)
            discount_factor (float): Gamma parameter for future reward discounting (0-1)
            exploration_rate (float): Epsilon parameter for exploration vs. exploitation (0-1)
            state_bins (int): Number of bins to discretize continuous state variables
            model_path (str): Path to load a pre-trained Q-table (optional)
            network_latency (float): Fixed network latency in seconds
        """
        # Call the parent class constructor
        super().__init__(junction_ids, learning_rate=learning_rate, 
                        discount_factor=discount_factor, 
                        exploration_rate=exploration_rate,
                        state_bins=state_bins, 
                        model_path=model_path)
        
        # Wired network simulation parameter
        self.network_latency = network_latency
        
        # Statistics
        self.total_latency = 0
        self.decision_count = 0
        
        # Initialize traffic light state lengths dictionary if not exists
        if not hasattr(self, 'tl_state_lengths'):
            self.tl_state_lengths = {}
        
        print(f"Initialized Wired RL Controller with network_latency={network_latency}")
    
    def decide_phase(self, junction_id, current_time):
        """
        Decide the next traffic light phase using RL and simulating wired conditions.
        
        Args:
            junction_id (str): The ID of the junction to control
            current_time (float): Current simulation time
            
        Returns:
            str: The traffic light state to set
        """
        # Simulate network latency for the wired connection
        time.sleep(self.network_latency)
        self.total_latency += self.network_latency
        self.decision_count += 1
        
        # Get the phase from the base RL implementation
        phase = super().decide_phase(junction_id, current_time)
        
        # Ensure phase is a string
        if not isinstance(phase, str):
            print(f"Warning: decide_phase returned a non-string value: {phase} ({type(phase)}). Using default phase.")
            phase = self.phase_sequence[0]
        
        # Ensure the phase matches the expected length for this junction
        if junction_id in self.tl_state_lengths:
            expected_length = self.tl_state_lengths[junction_id]
            if len(phase) != expected_length:
                # Adjust phase length to match expected length
                if len(phase) < expected_length:
                    # Repeat the pattern to match length
                    phase = phase * (expected_length // len(phase)) + phase[:expected_length % len(phase)]
                else:
                    # Truncate to expected length
                    phase = phase[:expected_length]
        
        return phase
    
    def get_network_stats(self):
        """Get statistics about the simulated wired network."""
        if self.decision_count == 0:
            return {
                "avg_latency": self.network_latency,
                "packet_loss_rate": 0.0,
                "decision_count": 0
            }
        
        return {
            "avg_latency": self.total_latency / self.decision_count,
            "packet_loss_rate": 0.0,  # No packet loss in wired network
            "decision_count": self.decision_count
        }