import requests
import json
import sys
import time

# Update BASE_URL to use the IP address where the server is running
BASE_URL = 'http://127.0.0.1:5000'

def check_server():
    try:
        response = requests.get(f'{BASE_URL}/cluster/status')
        return True
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to the API server.")
        print("Please make sure the API server is running (python api_server.py)")
        print(f"Trying to connect to: {BASE_URL}")
        return False
    except Exception as e:
        print(f"Error checking server: {str(e)}")
        return False

def print_help():
    print("""
Kubernetes-like Simulator CLI
----------------------------
Commands:
1. add-node <cpu_capacity>    - Add a new node with specified CPU capacity
2. remove-node <node_id>      - Remove a node by ID
3. create-pod <cpu_required>  - Create a new pod with CPU requirements
4. status                    - Show cluster status
5. pod-metrics <pod_id>      - Show resource usage metrics for a pod
6. node-usage <node_id>      - Show resource usage for a node
7. help                      - Show this help message
8. exit                      - Exit the program
    """)

def add_node(cpu_capacity):
    try:
        response = requests.post(f'{BASE_URL}/nodes', json={'cpu_capacity': int(cpu_capacity)})
        print(json.dumps(response.json(), indent=2))
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to the API server. Is it running?")
    except Exception as e:
        print(f"Error: {str(e)}")

def remove_node(node_id):
    try:
        response = requests.delete(f'{BASE_URL}/nodes/{node_id}')
        print(json.dumps(response.json(), indent=2))
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to the API server. Is it running?")
    except Exception as e:
        print(f"Error: {str(e)}")

def create_pod(cpu_required):
    try:
        response = requests.post(f'{BASE_URL}/pods', json={'cpu_required': int(cpu_required)})
        print(json.dumps(response.json(), indent=2))
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to the API server. Is it running?")
    except Exception as e:
        print(f"Error: {str(e)}")

def show_status():
    try:
        response = requests.get(f'{BASE_URL}/cluster/status')
        print(json.dumps(response.json(), indent=2))
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to the API server. Is it running?")
    except Exception as e:
        print(f"Error: {str(e)}")

def show_pod_metrics(pod_id):
    try:
        response = requests.get(f'{BASE_URL}/pods/{pod_id}/metrics')
        data = response.json()
        
        if 'error' in data:
            print(f"Error: {data['error']}")
            return
            
        print(f"\nPod Metrics for {pod_id}:")
        print("-" * 40)
        
        # Display averages
        averages = data.get('averages', {})
        print(f"Average CPU Usage:    {averages.get('cpu', 0):.2f}%")
        print(f"Average Memory Usage: {averages.get('memory', 0):.2f} MB")
        print(f"Average Network I/O:  {averages.get('network', 0):.2f} KB/s")
        
        # Show latest metrics if available
        metrics = data.get('metrics', {})
        if metrics and all(len(metrics.get(k, [])) > 0 for k in ['cpu_usage', 'memory_usage', 'network_io']):
            print("\nCurrent Metrics:")
            print(f"CPU Usage:    {metrics['cpu_usage'][-1]:.2f}%")
            print(f"Memory Usage: {metrics['memory_usage'][-1]:.2f} MB")
            print(f"Network I/O:  {metrics['network_io'][-1]:.2f} KB/s")
            
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to the API server. Is it running?")
    except Exception as e:
        print(f"Error: {str(e)}")

def show_node_resource_usage(node_id):
    try:
        response = requests.get(f'{BASE_URL}/nodes/{node_id}/resource-usage')
        data = response.json()
        
        if 'error' in data:
            print(f"Error: {data['error']}")
            return
            
        print(f"\nNode Resource Usage for {node_id}:")
        print("-" * 40)
        
        # Display resource usage
        usage = data.get('resource_usage', {})
        capacity = data.get('capacity', {})
        
        cpu_usage = usage.get('cpu', 0)
        cpu_capacity = capacity.get('cpu', 1)
        cpu_percent = (cpu_usage / cpu_capacity) * 100
        
        print(f"CPU Usage:      {cpu_usage:.2f}/{cpu_capacity} cores ({cpu_percent:.2f}%)")
        print(f"Memory Usage:   {usage.get('memory', 0):.2f} MB")
        print(f"Network I/O:    {usage.get('network', 0):.2f} KB/s")
        print(f"Pods Running:   {usage.get('pod_count', 0)}")
            
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to the API server. Is it running?")
    except Exception as e:
        print(f"Error: {str(e)}")

def main():
    print("Welcome to Kubernetes-like Simulator CLI")
    print_help()
    
    # Wait for server to be ready
    print("Waiting for API server to be ready...")
    for _ in range(5):  # Try for 5 seconds
        if check_server():
            break
        time.sleep(1)
    
    while True:
        try:
            command = input("\nEnter command: ").strip().split()
            if not command:
                continue
                
            cmd = command[0].lower()
            
            if cmd == 'exit':
                print("Goodbye!")
                sys.exit(0)
            elif cmd == 'help':
                print_help()
            elif cmd == 'status':
                show_status()
            elif cmd == 'add-node' and len(command) == 2:
                add_node(command[1])
            elif cmd == 'remove-node' and len(command) == 2:
                remove_node(command[1])
            elif cmd == 'create-pod' and len(command) == 2:
                create_pod(command[1])
            elif cmd == 'pod-metrics' and len(command) == 2:
                show_pod_metrics(command[1])
            elif cmd == 'node-usage' and len(command) == 2:
                show_node_resource_usage(command[1])
            else:
                print("Invalid command. Type 'help' for available commands.")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == '__main__':
    main() 