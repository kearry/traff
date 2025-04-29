import os
import sys
import time
import numpy as np
import json
import pickle
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))

from src.ai.reinforcement_learning.rl_controller import RLController

class QLearningController(RLController):
    """
    Q-Learning implementation for traffic control.
    
    This controller uses the Q-learning algorithm to learn optimal
    traffic signal timing policies based on traffic conditions.
    """
    def __init__(self, junction_ids, learning_rate=0.1, discount_factor=0.9, 
                exploration_rate=0.3, state_bins=3, model_path=None):
        """
        Initialize the Q-Learning controller.
        
        Args:
            junction_ids (list): List of junction IDs to control
            learning_rate (float): Alpha parameter for Q-learning updates (0-1)
            discount_factor (float): Gamma parameter for future reward discounting (0-1)
            exploration_rate (float): Epsilon parameter for exploration vs. exploitation (0-1)
            state_bins (int): Number of bins to discretize continuous state variables
            model_path (str): Path to load a pre-trained Q-table (optional)
        """
        super().__init__(junction_ids, learning_rate, discount_factor, exploration_rate)
        
        # Number of bins for state discretization
        self.state_bins = state_bins
        
        # Initialize Q-table for each junction
        self.q_tables = {junction_id: {} for junction_id in junction_ids}
        
        # Load pre-trained model if provided
        if model_path and os.path.exists(model_path):
            self.load_q_table(model_path)
            print(f"Loaded pre-trained Q-table from {model_path}")
        
        # Additional stats
        self.exploration_count = 0
        self.exploitation_count = 0
        
        print(f"Initialized Q-Learning Controller with {state_bins} state bins")
    
    def _discretize_state(self, traffic_state):
        """
        Convert continuous traffic state into a discrete state representation.
        
        Args:
            traffic_state (dict): Traffic state information
            
        Returns:
            tuple: Discretized state representation
        """
        # Extract relevant metrics
        north_count = traffic_state.get('north_count', 0)
        south_count = traffic_state.get('south_count', 0)
        east_count = traffic_state.get('east_count', 0)
        west_count = traffic_state.get('west_count', 0)
        
        north_queue = traffic_state.get('north_queue', 0)
        south_queue = traffic_state.get('south_queue', 0)
        east_queue = traffic_state.get('east_queue', 0)
        west_queue = traffic_state.get('west_queue', 0)
        
        # Calculate aggregate metrics
        ns_count = north_count + south_count
        ew_count = east_count + west_count
        
        ns_queue = north_queue + south_queue
        ew_queue = east_queue + west_queue
        
        # Discretize using bins
        # We use vehicle counts and queue lengths as our state variables
        discretized_ns_count = min(self.state_bins-1, int(ns_count / 5))
        discretized_ew_count = min(self.state_bins-1, int(ew_count / 5))
        discretized_ns_queue = min(self.state_bins-1, int(ns_queue / 3))
        discretized_ew_queue = min(self.state_bins-1, int(ew_queue / 3))
        
        # Return as a hashable tuple (for Q-table lookup)
        return (discretized_ns_count, discretized_ew_count, 
                discretized_ns_queue, discretized_ew_queue)
    
    def _get_state(self, junction_id):
        """
        Extract the state representation for a junction.
        
        Args:
            junction_id (str): The ID of the junction
            
        Returns:
            tuple: The discretized state representation
        """
        # Get the traffic state for this junction
        if junction_id not in self.traffic_state:
            # Return a default state if no data available
            return (0, 0, 0, 0)
        
        traffic_state = self.traffic_state[junction_id]
        
        # Convert to discrete state
        return self._discretize_state(traffic_state)
    
    def _get_reward(self, junction_id):
        """
        Calculate the reward for the current state.
        
        The reward function is designed to:
        - Minimize waiting time (negative reward for waiting)
        - Maximize throughput (positive reward for moving vehicles)
        - Balance flow (penalize imbalanced vehicle distribution)
        
        Args:
            junction_id (str): The ID of the junction
            
        Returns:
            float: The calculated reward
        """
        if junction_id not in self.traffic_state:
            return 0  # No data, no reward
        
        traffic_state = self.traffic_state[junction_id]
        
        # Extract metrics
        north_count = traffic_state.get('north_count', 0)
        south_count = traffic_state.get('south_count', 0)
        east_count = traffic_state.get('east_count', 0)
        west_count = traffic_state.get('west_count', 0)
        
        north_wait = traffic_state.get('north_wait', 0)
        south_wait = traffic_state.get('south_wait', 0)
        east_wait = traffic_state.get('east_wait', 0)
        west_wait = traffic_state.get('west_wait', 0)
        
        north_queue = traffic_state.get('north_queue', 0)
        south_queue = traffic_state.get('south_queue', 0)
        east_queue = traffic_state.get('east_queue', 0)
        west_queue = traffic_state.get('west_queue', 0)
        
        # Calculate reward components
        
        # 1. Waiting time penalty (more negative for longer waits)
        wait_penalty = -1.0 * (north_wait + south_wait + east_wait + west_wait)
        
        # 2. Queue length penalty (more negative for longer queues)
        queue_penalty = -0.5 * (north_queue + south_queue + east_queue + west_queue)
        
        # 3. Throughput reward (more positive for more vehicles moving)
        total_vehicles = north_count + south_count + east_count + west_count
        total_queue = north_queue + south_queue + east_queue + west_queue
        moving_vehicles = max(0, total_vehicles - total_queue)
        throughput_reward = 0.3 * moving_vehicles
        
        # 4. Balance reward (penalize imbalance between directions)
        ns_total = north_count + south_count
        ew_total = east_count + west_count
        
        if total_vehicles > 0:
            # Calculate ratio of smaller direction to larger direction (0-1)
            if ns_total > 0 and ew_total > 0:
                balance_factor = min(ns_total, ew_total) / max(ns_total, ew_total)
            else:
                balance_factor = 0  # If one direction has no vehicles
            
            balance_reward = 1.0 * balance_factor
        else:
            balance_reward = 1.0  # Perfect balance with no vehicles
        
        # Combine all reward components
        total_reward = wait_penalty + queue_penalty + throughput_reward + balance_reward
        
        # Scale reward to make it more meaningful but not extreme
        scaled_reward = max(-20, min(20, total_reward))
        
        return scaled_reward
    
    def _get_q_value(self, state, action, junction_id):
        """
        Get Q-value for a state-action pair.
        
        Args:
            state: The state
            action: The action
            junction_id (str): The ID of the junction
            
        Returns:
            float: The Q-value
        """
        q_table = self.q_tables.get(junction_id, {})
        return q_table.get((state, action), 0.0)
    
    def _select_action(self, state, junction_id):
        """
        Select an action using epsilon-greedy policy.
        
        Args:
            state: The current state
            junction_id (str): The ID of the junction
            
        Returns:
            str: The selected phase (action)
        """
        # Exploration: random action
        if np.random.random() < self.exploration_rate:
            self.exploration_count += 1
            # Make sure we return a phase string, not an index
            return np.random.choice(self.phase_sequence)
        
        # Exploitation: best known action
        self.exploitation_count += 1
        
        # Find the action with the highest Q-value for this state
        best_action = None
        best_value = float('-inf')
        
        for action in self.phase_sequence:
            q_value = self._get_q_value(state, action, junction_id)
            if q_value > best_value:
                best_value = q_value
                best_action = action
        
        # If all Q-values are the same (or not set), choose randomly
        if best_action is None:
            best_action = np.random.choice(self.phase_sequence)
        
        # Make sure we're returning a phase string
        if not isinstance(best_action, str):
            print(f"WARNING: Converting non-string action {best_action} ({type(best_action)}) to string")
            # Fall back to a default phase if something went wrong
            best_action = self.phase_sequence[0]
        
        return best_action
    
    def _update_q_value(self, state, action, next_state, reward, junction_id):
        """
        Update the Q-value for a state-action pair using the Q-learning update rule.
        
        Q(s,a) = Q(s,a) + α * [r + γ * max(Q(s',a')) - Q(s,a)]
        
        Args:
            state: The current state
            action: The taken action
            next_state: The resulting state
            reward (float): The received reward
            junction_id (str): The ID of the junction
        """
        # Get the current Q-value
        current_q = self._get_q_value(state, action, junction_id)
        
        # Find the maximum Q-value for the next state
        max_next_q = float('-inf')
        for next_action in self.phase_sequence:
            next_q = self._get_q_value(next_state, next_action, junction_id)
            max_next_q = max(max_next_q, next_q)
        
        # If no value exists yet, initialize to 0
        if max_next_q == float('-inf'):
            max_next_q = 0
        
        # Calculate the new Q-value
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * max_next_q - current_q)
        
        # Update the Q-table
        if junction_id not in self.q_tables:
            self.q_tables[junction_id] = {}
        
        self.q_tables[junction_id][(state, action)] = new_q
    
    def save_q_table(self, filename):
        """
        Save the Q-table to a file.
        
        Args:
            filename (str): Path to save the Q-table
        """
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Convert dictionary keys to strings for JSON serialization
        serializable_q_tables = {}
        for junction_id, q_table in self.q_tables.items():
            serializable_q_tables[junction_id] = {
                str(key): value for key, value in q_table.items()
            }
        
        # Save model information
        model_info = {
            "q_tables": serializable_q_tables,
            "learning_rate": self.learning_rate,
            "discount_factor": self.discount_factor,
            "exploration_rate": self.exploration_rate,
            "state_bins": self.state_bins,
            "exploration_count": self.exploration_count,
            "exploitation_count": self.exploitation_count,
            "total_rewards": self.total_rewards,
            "reward_history": self.reward_history
        }
        
        # Use pickle for more efficient serialization of complex data
        with open(filename, 'wb') as f:
            pickle.dump(model_info, f)
        
        print(f"Q-table saved to {filename}")
        return True
    
    def load_q_table(self, filename):
        """
        Load the Q-table from a file.
        
        Args:
            filename (str): Path to load the Q-table from
            
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        if not os.path.exists(filename):
            print(f"File not found: {filename}")
            return False
        
        try:
            # Load model data
            with open(filename, 'rb') as f:
                model_info = pickle.load(f)
            
            # Extract Q-tables and convert string keys back to tuples
            serialized_q_tables = model_info.get("q_tables", {})
            for junction_id, q_table in serialized_q_tables.items():
                self.q_tables[junction_id] = {}
                for key, value in q_table.items():
                    state, action = eval(key)
                    if not isinstance(action, str):
                        print(f"WARNING: Invalid action type {type(action)} in loaded Q-table. Converting...")
                        action = self.phase_sequence[action] if isinstance(action, int) else self.phase_sequence[0]
                    self.q_tables[junction_id][(state, action)] = value

            
            # Extract other parameters
            self.learning_rate = model_info.get("learning_rate", self.learning_rate)
            self.discount_factor = model_info.get("discount_factor", self.discount_factor)
            self.exploration_rate = model_info.get("exploration_rate", self.exploration_rate)
            self.state_bins = model_info.get("state_bins", self.state_bins)
            self.exploration_count = model_info.get("exploration_count", 0)
            self.exploitation_count = model_info.get("exploitation_count", 0)
            self.total_rewards = model_info.get("total_rewards", 0)
            self.reward_history = model_info.get("reward_history", [])
            
            print(f"Q-table loaded successfully from {filename}")
            return True
        
        except Exception as e:
            print(f"Error loading Q-table: {e}")
            return False
    
    def get_exploration_stats(self):
        """Get exploration vs. exploitation statistics."""
        total_actions = self.exploration_count + self.exploitation_count
        if total_actions == 0:
            return 0, 0
        
        exploration_ratio = self.exploration_count / total_actions
        exploitation_ratio = self.exploitation_count / total_actions
        
        return exploration_ratio, exploitation_ratio
    
    def get_q_table_stats(self):
        """Get statistics about the Q-table."""
        total_entries = 0
        state_counts = {}
        action_counts = {}
        
        for junction_id, q_table in self.q_tables.items():
            total_entries += len(q_table)
            
            for (state, action) in q_table.keys():
                state_counts[state] = state_counts.get(state, 0) + 1
                action_counts[action] = action_counts.get(action, 0) + 1
        
        return {
            "total_entries": total_entries,
            "unique_states": len(state_counts),
            "unique_actions": len(action_counts),
            "most_common_state": max(state_counts.items(), key=lambda x: x[1])[0] if state_counts else None,
            "most_common_action": max(action_counts.items(), key=lambda x: x[1])[0] if action_counts else None
        }