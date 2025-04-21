import docker
import uuid
import requests

# This URL must match the service name from docker-compose!
API_SERVER_URL = "http://apiserver:5000/register_node"
DOCKER_NETWORK = "backend"  # Match your docker-compose.yml network name
IMAGE_NAME = "node1:latest"  # Match the image name from docker-compose.yml

def main():
    try:
        cpu_cores = input("Enter number of CPU cores: ").strip()
        if not cpu_cores.isdigit() or int(cpu_cores) <= 0:
            print("❌ Invalid number of CPU cores")
            return

        node_id = f"node-{str(uuid.uuid4())[:8]}"

        # Launch the Docker container
        client = docker.from_env()
        container = client.containers.run(
            IMAGE_NAME,
            name=node_id,
            detach=True,
            environment={
                "NODE_ID": node_id,
                "CPU_CORES": cpu_cores,
                "API_SERVER": API_SERVER_URL
            },
            network=DOCKER_NETWORK,
            restart_policy={"Name": "on-failure"},
        )
        print(f"✅ Container launched: {container.short_id}")

        # Register the node with the API server
        response = requests.post(API_SERVER_URL, json={
            "node_id": node_id,
            "cpu_cores": int(cpu_cores)
        })

        if response.status_code == 200:
            print(f"✅ Node registered: {node_id}")
        else:
            print(f"❌ Failed to register node: {response.text}")

    except docker.errors.APIError as e:
        print(f"❌ Docker error: {str(e)}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to reach API server: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()
