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

proxies running on 5000 of the 3 VMs
middleware running on port 5001 (VM2)

load balancer listening on requests sent to 10.140.17.255 (vm2): 5002 and depending on ending of curl (ex. /heavy), request forward to respective node using specified balance options

(if end user calls 'curl 10.140.17.255:5002/heavy', the request is forwarded to one of the nodes added by the cloud user through cloud_toolset or thorugh curl PROXYIP/register/nodeName/portNumber)

**only commands listed on the handout need to be implemented and tested on

**instruction**
VM 1: 
```nohup /home/comp598-user/comp598/app_light/proxy.py```
```cd /home/comp598-user/comp598/cloud_toolset/cloud_toolset.py```
```python3 cloud_toolset.py```

VM 2:
```nohup /home/comp598-user/comp598/app_medium/proxy.py```
```nohup /home/comp598-user/comp598/ressource_manager/middleware/middleware.py```

VM 3: 
```nohup /home/comp598-user/comp598/app_heavy/proxy.py```

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
