import os
import sys
import time
import numpy as np
import random
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))

from src.ai.controller import TrafficController

class RLController(TrafficController):
    """
    Base class for reinforcement learning traffic controllers.
    
    This controller implements the core RL functionality while
    maintaining compatibility with the existing controller framework.
    """
    def __init__(self, junction_ids, learning_rate=0.1, discount_factor=0.9, exploration_rate=0.3):
        """
        Initialize the RL controller.
        
        Args:
            junction_ids (list): List of junction IDs to control
            learning_rate (float): Alpha parameter for Q-learning updates (0-1)
            discount_factor (float): Gamma parameter for future reward discounting (0-1)
            exploration_rate (float): Epsilon parameter for exploration vs. exploitation (0-1)
        """
        # Call the parent constructor with only the junction_ids parameter
        super().__init__(junction_ids)
        
        # RL parameters
        self.learning_rate = learning_rate 
        self.discount_factor = discount_factor
        self.exploration_rate = exploration_rate
        
        # Define the phase sequences same as other controllers for compatibility
        self.phase_sequence = ["GrYr", "yrGr", "rGry", "ryrG"]
        
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
        
        # Initialize state-action values (Q-table)
        # We'll implement this in subclasses based on specific RL approach
        self.q_table = {}
        
        # Track current state for each junction
        self.current_states = {junction_id: None for junction_id in junction_ids}
        
        # Track last action for each junction
        self.last_actions = {junction_id: None for junction_id in junction_ids}
        
        # Track accumulated rewards for performance monitoring
        self.total_rewards = 0
        self.reward_history = []
        
        # Store traffic light state lengths for each junction
        self.tl_state_lengths = {}
        
        print(f"Initialized RL Controller with parameters: lr={learning_rate}, df={discount_factor}, er={exploration_rate}")
    
    def _get_state(self, junction_id):
        """
        Extract the state representation for a junction.
        
        To be implemented by subclasses based on specific state representation.
        
        Args:
            junction_id (str): The ID of the junction
            
        Returns:
            State representation (implementation-dependent)
        """
        raise NotImplementedError("Subclasses must implement _get_state method")
    
    def _get_reward(self, junction_id):
        """
        Calculate the reward for the current state.
        
        To be implemented by subclasses based on specific reward function.
        
        Args:
            junction_id (str): The ID of the junction
            
        Returns:
            float: The calculated reward
        """
        raise NotImplementedError("Subclasses must implement _get_reward method")
    
    def _select_action(self, state, junction_id):
        """
        Select an action using epsilon-greedy policy.
        
        To be implemented by subclasses based on specific action selection mechanism.
        
        Args:
            state: The current state
            junction_id (str): The ID of the junction
            
        Returns:
            The selected action
        """
        raise NotImplementedError("Subclasses must implement _select_action method")
    
    def _update_q_value(self, state, action, next_state, reward, junction_id):
        """
        Update the Q-value for a state-action pair.
        
        To be implemented by subclasses based on specific RL algorithm.
        
        Args:
            state: The current state
            action: The taken action
            next_state: The resulting state
            reward (float): The received reward
            junction_id (str): The ID of the junction
        """
        raise NotImplementedError("Subclasses must implement _update_q_value method")
    
    def decide_phase(self, junction_id, current_time):
        """
        Decide the next traffic light phase using RL.
        
        Args:
            junction_id (str): The ID of the junction to control
            current_time (float): Current simulation time
            
        Returns:
            str: The traffic light state to set
        """
        # Record start time for response time measurement
        response_start = time.time()
        
        # Get the current state
        current_state = self._get_state(junction_id)
        self.current_states[junction_id] = current_state
        
        # If this is the first time, just select an action
        if self.last_actions.get(junction_id) is None:
            action = self._select_action(current_state, junction_id)
            # Ensure action is a valid phase string
            if not isinstance(action, str) or action not in self.phase_sequence:
                print(f"Warning: Invalid action type {type(action)} or value {action}. Using default phase.")
                action = self.phase_sequence[0]
            
            self.last_actions[junction_id] = action
            
            # Record response time
            self.response_times.append(time.time() - response_start)
            
            return action
        
        # Get reward for the previous action
        reward = self._get_reward(junction_id)
        self.total_rewards += reward
        self.reward_history.append(reward)
        
        # Get the previous state and action
        prev_state = self.current_states[junction_id]
        prev_action = self.last_actions[junction_id]
        
        # Update Q-value
        self._update_q_value(prev_state, prev_action, current_state, reward, junction_id)
        
        # Select next action
        action = self._select_action(current_state, junction_id)
        # Ensure action is a valid phase string
        if not isinstance(action, str) or action not in self.phase_sequence:
            print(f"Warning: Invalid action type {type(action)} or value {action}. Using default phase.")
            action = self.phase_sequence[0]
        
        self.last_actions[junction_id] = action
        
        # Record decision time
        self.decision_times.append(time.time() - response_start)
        
        # Record response time
        self.response_times.append(time.time() - response_start)
        
        return action
    
    def get_average_reward(self):
        """Get the average reward received by the controller."""
        if not self.reward_history:
            return 0
        return sum(self.reward_history) / len(self.reward_history)
    
    def save_q_table(self, filename):
        """
        Save the Q-table to a file.
        
        Args:
            filename (str): Path to save the Q-table
        """
        raise NotImplementedError("Subclasses must implement save_q_table method")
    
    def load_q_table(self, filename):
        """
        Load the Q-table from a file.
        
        Args:
            filename (str): Path to load the Q-table from
            
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        raise NotImplementedError("Subclasses must implement load_q_table method")