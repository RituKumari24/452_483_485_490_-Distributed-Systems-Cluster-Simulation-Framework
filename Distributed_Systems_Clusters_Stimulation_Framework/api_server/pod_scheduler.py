from threading import Lock
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PodScheduler:
    def __init__(self, node_manager):
        self.node_manager = node_manager
        self.pods = {}  # pod_id -> {node_id, cpu_cores}
        self.lock = Lock()  # For thread safety
        self.scheduling_algorithm = "first-fit"  # Default algorithm
    
    def set_scheduling_algorithm(self, algorithm):
        """Set the scheduling algorithm to use"""
        valid_algorithms = ["first-fit", "best-fit", "worst-fit"]
        if algorithm not in valid_algorithms:
            return False
        
        self.scheduling_algorithm = algorithm
        return True
    
    def schedule_pod(self, pod_id, cpu_cores):
        """Schedule a pod to a node based on the selected algorithm"""
        with self.lock:
            # Check if pod already exists
            if pod_id in self.pods:
                logger.warning(f"Pod {pod_id} already exists, cannot reschedule")
                return {"success": False, "message": "Pod already exists"}
            
            # Get healthy nodes
            healthy_nodes = self.node_manager.get_healthy_nodes()
            if not healthy_nodes:
                logger.warning("No healthy nodes available for scheduling")
                return {"success": False, "message": "No healthy nodes available"}
            
            # Find node to schedule on
            node_id = None
            
            if self.scheduling_algorithm == "first-fit":
                node_id = self._first_fit_scheduling(healthy_nodes, cpu_cores)
            elif self.scheduling_algorithm == "best-fit":
                node_id = self._best_fit_scheduling(healthy_nodes, cpu_cores)
            elif self.scheduling_algorithm == "worst-fit":
                node_id = self._worst_fit_scheduling(healthy_nodes, cpu_cores)
            
            if not node_id:
                logger.warning(f"No node with sufficient resources for pod {pod_id} requiring {cpu_cores} cores")
                return {"success": False, "message": "No node with sufficient resources"}
            
            logger.info(f"Scheduling pod {pod_id} to node {node_id}")
            
            # Allocate resources on the node
            if not self.node_manager.allocate_resources(node_id, cpu_cores):
                logger.error(f"Failed to allocate resources for pod {pod_id} on node {node_id}")
                return {"success": False, "message": "Failed to allocate resources"}
            
            # Add pod to node
            if not self.node_manager.add_pod_to_node(node_id, pod_id):
                # Roll back resource allocation if adding pod fails
                self.node_manager.release_resources(node_id, cpu_cores)
                logger.error(f"Failed to add pod {pod_id} to node {node_id}")
                return {"success": False, "message": "Failed to add pod to node"}
            
            # Store pod information
            self.pods[pod_id] = {
                "node_id": node_id,
                "cpu_cores": cpu_cores
            }
            
            logger.info(f"Successfully scheduled pod {pod_id} on node {node_id}")
            return {"success": True, "node_id": node_id}
    
    def _first_fit_scheduling(self, nodes, cpu_cores):
        """First-fit scheduling algorithm - use the first node with enough resources"""
        for node_id, node_info in nodes.items():
            if node_info["available_cores"] >= cpu_cores:
                return node_id
        return None
    
    def _best_fit_scheduling(self, nodes, cpu_cores):
        """Best-fit scheduling algorithm - use the node with the least available resources that can fit the pod"""
        best_node = None
        min_available = float('inf')
        
        for node_id, node_info in nodes.items():
            available = node_info["available_cores"]
            if available >= cpu_cores and available < min_available:
                min_available = available
                best_node = node_id
        
        return best_node
    
    def _worst_fit_scheduling(self, nodes, cpu_cores):
        """Worst-fit scheduling algorithm - use the node with the most available resources"""
        worst_node = None
        max_available = -1
        
        for node_id, node_info in nodes.items():
            available = node_info["available_cores"]
            if available >= cpu_cores and available > max_available:
                max_available = available
                worst_node = node_id
        
        return worst_node
    
    def unschedule_pod(self, pod_id):
        """Unschedule a pod"""
        with self.lock:
            if pod_id not in self.pods:
                logger.warning(f"Attempted to unschedule non-existent pod {pod_id}")
                return False
            
            pod_info = self.pods[pod_id]
            node_id = pod_info["node_id"]
            cpu_cores = pod_info["cpu_cores"]
            
            logger.info(f"Unscheduling pod {pod_id} from node {node_id}")
            
            # Remove pod from node
            if not self.node_manager.remove_pod_from_node(node_id, pod_id):
                logger.error(f"Failed to remove pod {pod_id} from node {node_id}")
                # Continue anyway as we want to clean up our internal state
            
            # Release resources
            if not self.node_manager.release_resources(node_id, cpu_cores):
                logger.error(f"Failed to release resources for pod {pod_id} on node {node_id}")
                # Continue anyway as we want to clean up our internal state
            
            # Remove pod from tracking
            del self.pods[pod_id]
            logger.info(f"Successfully unscheduled pod {pod_id}")
            
            return True
    
    def reschedule_pods_from_node(self, node_id):
        """Reschedule all pods from a failed node"""
        with self.lock:
            logger.info(f"Attempting to reschedule all pods from node {node_id}")
            
            # Find all pods on this node
            pods_to_reschedule = []
            for pod_id, info in list(self.pods.items()):
                if info["node_id"] == node_id:
                    pods_to_reschedule.append((pod_id, info["cpu_cores"]))
                    # Remove from internal tracking
                    del self.pods[pod_id]
            
            logger.info(f"Found {len(pods_to_reschedule)} pods to reschedule from node {node_id}")
            
            # Try to reschedule each pod
            rescheduled = []
            failed = []
            
            for pod_id, cpu_cores in pods_to_reschedule:
                logger.info(f"Attempting to reschedule pod {pod_id} with {cpu_cores} CPU cores")
                # Remove the actual pod from the node before rescheduling
                self.node_manager.remove_pod_from_node(node_id, pod_id)
                
                # Schedule the pod on a new node
                result = self.schedule_pod(pod_id, cpu_cores)
                
                if result["success"]:
                    new_node = result["node_id"]
                    logger.info(f"Successfully rescheduled pod {pod_id} to node {new_node}")
                    rescheduled.append(pod_id)
                else:
                    logger.warning(f"Failed to reschedule pod {pod_id}: {result['message']}")
                    failed.append(pod_id)
            
            return {
                "rescheduled": rescheduled,
                "failed": failed
            }
    
    def get_pod(self, pod_id):
        """Get information about a pod"""
        with self.lock:
            return self.pods.get(pod_id)
    
    def get_all_pods(self):
        """Get information about all pods"""
        with self.lock:
            return {pid: info.copy() for pid, info in self.pods.items()}