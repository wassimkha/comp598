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

load balancer listening on requests sent to 10.140.17.255 (vm2): 5000 and depending on ending of curl (ex. /heavy), request forward to respective node using specified balance options
