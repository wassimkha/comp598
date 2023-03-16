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

(if end user calls 'curl 10.140.17.255:5000/heavy', the request is forwarded to one of the nodes added by the cloud user through cloud_toolset or thorugh curl PROXYIP/register/nodeName/portNumber)

nodes in all three pods must have: node_id, node_name, status (new/online), port_number  
- new: added to proxy, not running container  
- online: added to load balancer, when called will run the job (refer to tutorialA2-proxy.py)

**the proxy code from the tutorial is in the repo - and refer to the implementation in RM/middleware/middleware.py on interactions of nodes with load balancer  

**only commands listed on the handout need to be implemented and tested on

**commands for haproxy**

to see haproxy version:  
`haproxy -v`

to edit haproxy config file (add/remove node manually, change balance option):  
`sudo vi /etc/haproxy/haproxy.cfg`

After making changes: 
- see if changes made to haproxy file is valid:  
`sudo haproxy -c -f /etc/haproxy/haproxy.cfg`

- restart haproxy after changes made  
`sudo systemctl restart haproxy`

- if restart failed, to see failure:  
`haproxy -f /etc/haproxy/haproxy.cfg -db`