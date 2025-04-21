# Distributed Systems Cluster Simulation Framework

A simulation framework for distributed systems that models nodes, pods, and cluster management concepts.

## Features

- **Node Management**: Add and remove compute nodes from the cluster
- **Pod Scheduling**: Schedule pods with CPU requirements across available nodes
- **Health Monitoring**: Detect node failures through heartbeat mechanism
- **Pod Resource Monitoring**: Track CPU and memory usage of pods
- **Web Interface**: Visualize and manage cluster resources
- **Docker Integration**: Simulates nodes as Docker containers

## Architecture

The framework consists of three main components:

1. **API Server**: Core logic for cluster management
   - Node registration and health monitoring
   - Pod scheduling algorithms
   - Resource tracking

2. **Node Simulation**: Simulates cluster nodes
   - Sends heartbeats to API server
   - Reports simulated resource metrics
   - Handles pod lifecycle events

3. **Web Interface**: UI for cluster management
   - Real-time dashboard with resource visualization
   - Node and pod management controls
   - Resource metrics and health status

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.8+

### Installation

1. Clone the repository
```bash
git clone https://github.com/yourusername/distributed-cluster-simulation.git
cd distributed-cluster-simulation
```

2. Build and start the simulation
```bash
docker-compose up --build
```

3. Access the web interface at http://localhost:8080

## Usage

### Managing Nodes

- Add a new node with specified CPU cores from the Nodes page
- Remove nodes that are no longer needed
- View node status and health information

### Deploying Pods

- Launch new pods with CPU requirements
- View pod resource usage statistics
- Monitor pod placement across nodes

## Extending the Framework

### Add New Scheduling Algorithms

Extend the `PodScheduler` class in `api_server/pod_scheduler.py` with your own scheduling algorithm.

### Add Node Failure Simulation

Implement additional logic in the node simulation to simulate various failure scenarios.

### Add Network Topology Simulation

Extend the framework to simulate network partitions and latency between nodes.

## License

This project is licensed under the MIT License - see the LICENSE file for details.