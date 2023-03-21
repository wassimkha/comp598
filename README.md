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
haproxy listening on 5001

load balancer listening on requests sent to 10.140.17.255 (vm2): 5002 and depending on ending of curl (ex. /heavy), request forward to respective node using specified balance options

(if end user calls 'curl 10.140.17.255:5002/heavy', the request is forwarded to one of the nodes added by the cloud user through cloud_toolset or thorugh curl PROXYIP/register/nodeName/portNumber)

**only commands listed on the handout need to be implemented and tested on

**instruction**
VM 1: 
```nohup sudo python3 /home/comp598-user/comp598/app_light/proxy.py &```

```cd /home/comp598-user/comp598/cloud_toolset/cloud_toolset```

```python3 cloud_toolset.py```

VM 2:
```nohup sudo python3 /home/comp598-user/comp598/app_medium/proxy.py &```

```python3 /home/comp598-user/comp598/ressource_manager/middleware/middleware.py```

VM 3: 
```nohup sudo python3 /home/comp598-user/comp598/app_heavy/proxy.py &```

**commands for haproxy on VM2**

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

- see running or not
`sudo systemctl status haproxy`

- see ports taken
`sudo netstat -tnlp`

---------------------------------------------

- EXAMPLE server runing on port 15000
`python3 -m http.server 15000 --bind 0.0.0.0`

- to watch status
`watch 'echo "show stat" | sudo socat stdio /var/run/haproxy.sock | cut -d "," -f 1-2,5-10,34-36 | column -s, -t'`

- Send request 
`curl localhost:5002/medium` (change the ending)


- adding server dynamically (example)
`echo "experimental-mode on; add server medium_servers/server1 0.0.0.0:15000" | sudo socat stdio /var/run/haproxy.sock`

- enabling the server after adding
`echo "experimental-mode on; set server medium_servers/server1 state ready" | sudo socat stdio /var/run/haproxy.sock`

- disabling the server before deleting
`echo "experimental-mode on; set server medium_servers/server1 state maint" | sudo socat stdio /var/run/haproxy.sock`

- deleting the server completely
`echo "experimental-mode on; del server medium_servers/server1" | sudo socat stdio /var/run/haproxy.sock`

- see server status (using haproxy CLI)
`sudo socat stdio /var/run/haproxy.sock`

`show servers state`
