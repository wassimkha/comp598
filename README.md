# Overview 
This milestone adds a load balancer to the simple cloud system previously developed in milestone 1. The load balancer distributes work and resources to maximize resource utilization for the cloud and minimize response time for clients based on the balance option specified.

In this assignment, the cloud system is required to support three pods, each with its own Resource Proxy. The pods are designed to run in different virtual machines and have a limit on the number of nodes that can be added to them. The heavy pod can have up to 10 nodes, the medium pod can have up to 15 nodes, and the light pod can have up to 20 nodes. The nodes in the different pods will have different sizes with varying CPU and memory limits, and the resource proxies will be used to manage the resources allocated to each pod. The resource proxies will be responsible for assigning nodes to pods and ensuring that the nodes are not overloaded with more resources than they can handle.


## Class Structure Overview
The Simple Cloud Manager has the following classes:

* Node: represents a machine in the simple cloud (docker container). 
* Resource Pod: the cloud needs to support three pods (light, medium, heavy) with each having its own Resource Proxy. Each pod has a limit on the number of nodes that can be added to them, and each node in the different pods will have different CPU and memory limits.
* Resource Manager: a continuously running daemon that is responsible for making all the management decisions.
* Cloud Dashboard: a component of the ResourceManager or a standalone web server that is connected to the ResourceManager.
* Cloud Toolset: commands that are supported by the ResourceManager.
* Job: This milestone requires three types of jobs: heavy, medium, and light. Each job is accessible through a URL endpoint and can be invoked by sending an HTTP request to the load balancer.
* Proxy: Handles requests to by carrying out the docker commands to manipulate the docker containers (there are 3 proxies 
* Load balancer: Using HAProxy, the load balancer distributes incoming requests to the nodes in the pods based on their load. The goal is to test the load balancer's ability to spread the workload as required by injecting requests from the End user at different rates using an exponential distribution.

**Our VMs structure** (note: comp598 is a shared folder in all VMs): 

Overview: 
* proxies are running on port 5000 of the 3 VMs
* middleware is running on port 5001 (VM2) that forward cloud user request to proxies
* haproxy (load balancer) listening on port 5002 of VM2

VM #1 (Light pod): comp598
* /cloud_toolset/cloud_toolset.py (receiving and sending client requests to the resource manager)
* /app_light (contains the  job (app + Dockerfile) and proxy.py - resource proxy responsible for the light pod, managing and assinging nodes that run the light job)

VM #2 (Medium pod): comp598
* /Ressource_Manager/middleware/middleware.py (for handling requests from client to proxy, and response back to client)
* /Ressource_Manager/monitoring/ressource_manager.py (rendering for the monitoring cloud dashboard)
* /app_medium (contains the  job (app + Dockerfile) and proxy.py - resource proxy responsible for the medium pod, managing and assinging nodes that run the medium job)

VM #3: 
comp598 (Heavy pod): comp598
* /app_heavy (contains the job (app + Dockerfile) and proxy.py - resource proxy responsible for the heavy pod, managing and assinging nodes that run the heavy job)

Load Balancer: listening on requests sent to 10.140.17.255 (vm2): 5002 and depending on ending of curl (ex. /heavy), request forward to respective node using specified balance options

To view the config of load balancer (HAProxy), see in /loadBalancer/haproxy.cfg
or in VM02 enter:
`sudo cat /etc/haproxy/haproxy.cfg`

## Set-Up(running proxies, resource manager and dashboard)
First, cd into private folder `cs598-group07-key` containing the private key

**To run the 3 proxies**
* Light-job Proxy
1. ssh into VM1 by the following command `ssh -i cs598-group07-key comp598-user@winter2023-comp598-group07-01.cs.mcgill.ca`
2. cd into folder containing light proxy `cd /home/comp598-user/comp598/app_light`
3. Start the proxy by running `sudo python3 proxy.py`

* Medium-job Proxy
1. ssh into VM2 by the following command `ssh -i cs598-group07-key comp598-user@winter2023-comp598-group07-02.cs.mcgill.ca`
2. cd into folder containing medium proxy `cd /home/comp598-user/comp598/app_medium`
3. Start the proxy by running `sudo python3 proxy.py`

* Heavy-job Proxy
1. ssh into VM3 by the following command `ssh -i cs598-group07-key comp598-user@winter2023-comp598-group07-03.cs.mcgill.ca`
2. cd into folder containing heavy proxy `cd /home/comp598-user/comp598/app_heavy`
3. Start the proxy by running `sudo python3 proxy.py`

**To run middleware that handles cloud user request and send to the appropriate proxies**
1. ssh into VM2 by the following command `ssh -i cs598-group07-key comp598-user@winter2023-comp598-group07-02.cs.mcgill.ca`
2. cd into folder containing medium proxy `cd /home/comp598-user/comp598/ressource_manager/middleware`
3. Start the middleware by running `python3 middleware.py`

**To run cloud monitor**
1. ssh into VM2 by the following command `ssh -i cs598-group07-key comp598-user@winter2023-comp598-group07-02.cs.mcgill.ca`
2. cd into folder containing medium proxy `cd /home/comp598-user/comp598/ressource_manager/monitoring`
3. Start the monitoring by running `sudo python3 ressource_manager.py`
4. To view the status of different cloud components (status/name/id of nodes and pods, etc) via a web interface, please use the [url to dashboard](https://winter2023-comp598-group07-02.cs.mcgill.ca/)

## Executing the Cloud Infrastructure as Cloud User
To execute the cloud infrastructure, follow these steps:

1. cd into private folder `cs598-group07-key` containing the private key
2. ssh into the client server by the following command `ssh -i cs598-group07-key comp598-user@winter2023-comp598-group07-01.cs.mcgill.ca`
3. Use the cloud toolset to execute commands and launch jobs on the cluster by running `python3 comp598/cloud_toolset/cloud_toolset.py` 
4. Enter the command `cloud init` to initialize 3 pods and setup all cloud services. 
5. The following commands are supported where POD_ID = 0 (light), 1 (medium) or 2 (heavy)
* `cloud pod register POD_NAME`: Registers a new pod with the specified name to the main resource cluster. Note: pod names must be unique. Not supported for this milestone.
* `cloud pod rm POD_NAME`: Removes the specified pod. Not supported for this milestone
* `cloud register NODE_NAME POD_ID`: Creates a new node and registers it to the specified pod ID.
* `cloud rm NODE_NAME POD_ID`: removes the specified node from the specified POD_ID
* `cloud launch POD_ID`: picks up the first node with the “NEW” status in the specified POD_ID and switches its status to “ONLINE”, the node starts its HTTP web server. Load balancer notified if POD_ID is up and running
* `cloud resume POD_ID`: Resumes the specified POD_ID
* `cloud pause POD_ID`:  Pauses the specified POD_ID


## Sending Request as End User
1. Assuming servers are created and launched into as the cloud user
2. cd into private folder `cs598-group07-key` containing the private key
3. ssh into the server load balancer sits on by the following command `ssh -i cs598-group07-key comp598-user@winter2023-comp598-group07-02.cs.mcgill.ca`
3. Use curl to send request
* to send a request to run a light job: `curl localhost:5002/light`
* to send a request to run a medium job: `curl localhost:5002/medium`
* to send a request to run a heavy job: `curl localhost:5002/heavy`

## Cloud Dashboard
To view the status of different cloud components (status/name/id of nodes and pods, etc) via a web interface, please use the [url to dashboard](https://winter2023-comp598-group07-02.cs.mcgill.ca/)

## Throughput and Analytics
To view our report with experimental results on the average throughput and latency of requests on the 3 pods using different load balancing algorithms, please see our report **Experiment_Report.pdf**

