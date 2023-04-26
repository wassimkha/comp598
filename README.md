# Overview 
 In this project's third milestone, the resource manager is made elastic, meaning it can automatically adjust resource allocation based on user demand. The user specifies the limits of elastic scaling and the resource manager adjusts resource allocation within those limits.

## Class Structure Overview 

### Elastic Manager

The Elasticity Manager is activated when the Cloud User enables the "Elastic Mode" by calling a new REST endpoint in the Resource Manager. The Cloud User can enable and disable the Elasticity Manager for a given pod, which specifies the pod size in terms of the node size range. The Elasticity Manager uses the upper and lower threshold values specified by the Cloud User to create a valid allocation.

### Simple Cloud Manager

The Simple Cloud Manager has the following classes:

* Node: represents a machine in the simple cloud (docker container). 
* Resource Pod: the cloud needs to support three pods (light, medium, heavy) with each having its own Resource Proxy. Each pod has a limit on the number of nodes that can be added to them, and each node in the different pods will have different CPU and memory limits.
* Resource Manager: a continuously running daemon that is responsible for making all the management decisions.
* Cloud Dashboard: a component of the ResourceManager or a standalone web server that is connected to the ResourceManager.
* Cloud Toolset: commands that are supported by the ResourceManager.
* Job: This milestone requires three types of jobs: heavy, medium, and light. Each job is accessible through a URL endpoint and can be invoked by sending an HTTP request to the load balancer.
* Proxy: Handles requests to by carrying out the docker commands to manipulate the docker containers (there are 3 proxies)
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
* `cloud register NODE_NAME POD_ID`: Creates a new node and registers it to the specified pod ID.

### Using the Elasticity Manager
* `cloud elasticity enable [POD_NAME] [lower_size] [upper_size]`: enables the elasticity for the given pod. The Cloud User specifies the pod size in terms of node size range. The elastic manager is responsible for picking the correct pod size (I.e., the number of nodes) at run time. The elastic manager uses the upper and lower threshold values specified by the Cloud User as the allowed ranges in creating a valid allocation.
* `cloud elasticity disable [POD_NAME]`: disables the elasticity manager for the given pod. When the elasticity manager is disabled, the cloud management commands (Register and Launch) become available to the Cloud User. By default the elasticity management is disabled for a pod.
* `cloud elasticity lower_threshold [POD_NAME] [value]`: Settings the lower threshold of the CPU value for the given pod
* `cloud elasticity upper_threshold [POD_NAME] [value]`:  Settings the upper threshold of the CPU value for the given pod

### Commands available when elasticity manager is deactivated
* `cloud rm NODE_NAME POD_ID`: removes the specified node from the specified POD_ID
* `cloud launch POD_ID`: picks up the first node with the “NEW” status in the specified POD_ID and switches its status to “ONLINE”, the node starts its HTTP web server. Load balancer notified if POD_ID is up and running
* `cloud resume POD_ID`: Resumes the specified POD_ID
* `cloud pause POD_ID`:  Pauses the specified POD_ID


## Sending Request as End User
1. Assuming servers are created and launched by the cloud user
2. cd into private folder `cs598-group07-key` containing the private key
3. ssh into the server (VM2) load balancer sits on by the following command `ssh -i cs598-group07-key comp598-user@winter2023-comp598-group07-02.cs.mcgill.ca`
3. Use curl to send request
* to send a request to run a light job: `curl localhost:5002/light`
* to send a request to run a medium job: `curl localhost:5002/medium`
* to send a request to run a heavy job: `curl localhost:5002/heavy`

## Cloud Dashboard
To view the status of different cloud components (status/name/id of nodes and pods, etc) via a web interface, please use the [url to dashboard](https://winter2023-comp598-group07-02.cs.mcgill.ca/)


