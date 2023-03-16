# comp598 - A2

For now:

Light jobs on:   
VM1: 10.140.17.119    
pod_id = 0   

medium jobs on:     
VM2: 10.140.17.255   
pod_id = 1   

heavy jobs on:     
VM1: 10.140.17.121  
pod_id = 2  

proxies running on 6000

load balancer listening on requests sent to 10.140.17.255 (vm2): 5000 and depending on ending of curl (ex. /heavy), request forward to respective node using specified balance options

nodes in all three pods must have: node_id, node_name, status (new/online), port_number  
new - added to proxy, not running container  
online - added to load balancer, when called will run the job (refer to tutorialA2-proxy.py)

**the proxy code from the tutorial is in the repo - and refer to the implementation in RM/middleware/middleware.py on interactions of nodes with load balancer
