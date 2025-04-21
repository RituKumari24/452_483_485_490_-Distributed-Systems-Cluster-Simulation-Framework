import time
import threading
from threading import Lock

class HealthMonitor:
    def __init__(self, node_manager, pod_scheduler=None):
        self.node_manager = node_manager
        self.pod_scheduler = pod_scheduler
        self.lock = Lock()
        self.heartbeat_timeout = 30  # seconds
        self.running = False
        self.monitor_thread = None
    
    def set_pod_scheduler(self, scheduler):
        """Set the pod scheduler (used for rescheduling pods from failed nodes)"""
        self.pod_scheduler = scheduler
    
    def start_monitoring(self):
        """Start the health monitoring thread"""
        with self.lock:
            if self.running:
                return False
            
            self.running = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            return True
    
    def stop_monitoring(self):
        """Stop the health monitoring thread"""
        with self.lock:
            if not self.running:
                return False
            
            self.running = False
            if self.monitor_thread:
                self.monitor_thread.join(timeout=5)
            return True
    
    def _monitor_loop(self):
        """Background loop to check node health"""
        while self.running:
            try:
                self._check_node_health()
            except Exception as e:
                print(f"Error in health monitor: {e}")
            
            # Sleep for a bit
            time.sleep(5)
    
    def _check_node_health(self):
        """Check the health of all nodes"""
        current_time = time.time()
        nodes = self.node_manager.get_all_nodes()
        
        for node_id, node_info in nodes.items():
            # Skip nodes that are already marked as failed
            if node_info["status"] == "failed":
                continue
            
            # Check if the node missed a heartbeat
            last_heartbeat = node_info["last_heartbeat"]
            if current_time - last_heartbeat > self.heartbeat_timeout:
                print(f"Node {node_id} marked as failed - missed heartbeat")
                self.node_manager.update_node_status(node_id, "failed")
                
                # Reschedule pods from the failed node
                if self.pod_scheduler:
                    result = self.pod_scheduler.reschedule_pods_from_node(node_id)
                    print(f"Rescheduled pods from node {node_id}: {result}")
    
    def process_heartbeat(self, node_id):
        """Process a heartbeat from a node"""
        return self.node_manager.update_heartbeat(node_id)