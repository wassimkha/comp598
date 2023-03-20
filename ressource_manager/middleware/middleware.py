from flask import Flask, Response, render_template, request, jsonify
import pycurl
import sys
import os
import requests

cURL = pycurl.Curl()

#TODO: change return based on proxy's output implementation

app = Flask(__name__)

#----------global var------------
#pod_id = 0 
ip_proxy_light = 'http://10.140.17.119:6000' 
ip_proxy_light_no_port = '10.140.17.119'

#pod_id = 1
ip_proxy_medium = 'http://10.140.17.255:6000'
ip_proxy_medium_no_port = '10.140.17.255'

#pod_id = 2
ip_proxy_heavy = 'http://10.140.17.121:6000'
ip_proxy_heavy_no_port = '10.140.17.121'


URL = '' 
ip_no_port = ''
servers = ''
port_list = {}

port_numbers_light = {key: False for key in range(15000, 15009)} #10
port_numbers_medium = {key: False for key in range(15000, 15014)} #15
port_numbers_heavy = {key: False for key in range(15000, 15019)} #20

#Helper function to get URL based on specified pod
def get_serverPrams(pod_id):
    if pod_id == 0:
        URL = ip_proxy_light
        ip_no_port = ip_proxy_light_no_port
        servers = 'light_servers'
        port_list = port_numbers_light
    elif pod_id == 1:
        URL = ip_proxy_medium
        ip_no_port = ip_proxy_medium_no_port
        servers == 'medium_servers'
        port_list = port_numbers_medium
    elif pod_id == 2:
        URL = ip_proxy_heavy
        ip_no_port = ip_proxy_heavy_no_port
        severs = 'heavy_servers'
        port_list = port_numbers_heavy
    return URL, ip_no_port

def update_portList(pod_id):
    if pod_id == 0:
        port_numbers_light = port_list
    elif pod_id == 1:
        port_numbers_medium = port_list
    elif pod_id == 2:
        port_numbers_heavy = port_list

#URL, ip_no_port, servers, port_list = get_serverPrams(pod_id)
#Helper function 
#servers, port_list = get_servername_and_portList(pod_id)

#TODO: parse json file 
@app.route('/cloudproxy', methods=["POST"]) 
#initialize all 3 proxies
def cloud_init():
    #re-set global vars 

    URL = '' 
    ip_no_port = ''
    port_numbers_light = {key: False for key in range(15000, 15009)} 
    port_numbers_medium = {key: False for key in range(15000, 15014)} 
    port_numbers_heavy = {key: False for key in range(15000, 15019)}

    #json files for proxy config data
    with open('jsons/light_pod.json', 'r') as f:
        light_config = json.load(f)

    with open('jsons/medium_pod.json', 'r') as f:
        medium_config = json.load(f)

    with open('jsons/heavy_pod.json', 'r') as f:
        heavy_config = json.load(f)
    
    #call init on all three proxies
    response_light = requests.post(ip_proxy_light + '/cloudproxy', json = light_config)
    #TODO: uncomment
    #response_medium = requests.post(ip_proxy_medium + '/cloudproxy', json = medium_config)
    #response_heavy = requests.post(ip_proxy_medium + '/cloudproxy', json = heavy_config)
    
    all_responses = {
        'light initialization': response_light.json(),
       # 'medium initialization': response_medium.json(),
       # 'heavy pod initialization': response_heavy.json()
    }

    print(all_responses)

    return jsonify(all_responses)

#left unimplemented for the project - only cloud toolset returns a message
@app.route('/cloudproxy/pods/<pod_name>', methods=["POST"]) 
def cloud_pod_register(pod_name):
    pass
 

#left unimplemented for the project - only cloud toolset returns a message?
@app.route('/cloudproxy/pods/<pod_name>', methods=["DELETE"])
def cloud_pod_rm(pod_name):
    pass

# route to register new node with name and pod_id provided - provide proxy with a port number
@app.route('/cloudproxy/nodes/<node_name>/<pod_id>', methods=["POST"])
def cloud_register(node_name, pod_id):
    URL, ip_no_port, servers, port_list = get_serverPrams(pod_id)
    port_number = None

    #loop through list of port numbers and in find an available one
    for key, value in port_list.items():
        if not value:
            port_number = key #get the first port_number with value=false (avilable)
            break

    if port_number is not None:
        print(f"The first available port is {port_number}")
    else:
        print("All ports are occupied, reach capacity")
        return jsonify({'result': 'Failure: all port numbers are occupied, reached capacity of pod'}) 

    #call proxy to register this node - its status set to NEW, not running
    response = requests.post(URL +'/cloudproxy/nodes/' + node_name + '/' + port_number)
    response_json = response.json()

    result = response_json["result"]
    #set port_number as false = taken in the list
    
    if result == 'Node added successfully.': #successfully registerd
        #set that port number as taken
        port_list[port_number] = False
        update_portList(pod_id) #update global dict for that proxy
        print("node was successfully registered and port number freed")
    
    #return proxy's response
    return Response(response.content, content_type=response.headers['content-type'])

 #remove node on proxy side, then remove from load balancer
@app.route('/cloudproxy/nodes/<node_name>/<pod_id>', methods=["DELETE"])
def cloud_rm(node_name):
    
    URL, ip_no_port, servers, port_list = get_serverPrams(pod_id)

    response = requests.delete(URL +'/cloudproxy/nodes/' + node_name)
    
    if(response.response_code == 200): #success
        #parse json, if the node is online (started a docker container), put to maintenance state then delete
        response_json = response.json()
        result = response_json["result"]

        if result != 'Node successfully deleted.':
            #not deleted, return respone from proxy
            return Response(response.content, content_type=response.headers['content-type'])
            
        else: #succesfully deleted
            port = response_json["port"]
            was_online = response_json["was_online"]
            is_paused = response_json["is_paused"]
                
            if was_online == True: #node was online - remove from load balancer

                #put the node in maintenance state using HAProxy socket
                disable_command = "echo 'experimental-mode on; set server " + servers + "/'" + node_name + ' state maint ' + '| sudo socat stdio /var/run/haproxy.sock'
                subprocess.run(disable_command, shell=True, check=True)

                #remove node from load balancer
                rm_command = "echo 'experimental-mode on; del server " + servers + "/'" + node_name + '| sudo socat stdio /var/run/haproxy.sock'
                subprocess.run(rm_command, shell=True, check=True)

                #set the port number as available for registration
                if port in port_list:
                    port_list[port] = True
                    update_portList(pod_id)

            #if removed node was hte last node of the pod, then pod is paused 
            if is_paused == True:
                cloud_pause(pod_id) 

            return Response(response.content, content_type=response.headers['content-type'])
            
    
@app.route('/cloudproxy/launch/<pod_id>', methods=["POST"])
def cloud_launch():
        
    URL, ip_no_port, servers, port_list = get_serverPrams(pod_id)

    #proxy will find first node with 'NEW' and set to 'ONLINE' 
    response = requests.post(URL + '/cloudproxy/launch')

    response_json = response.json()
    status = response_json["status"]

    if status == 'Successfully launched the job.':
        node_name = response_json["name"]
        port = response_json["port"]
        is_paused = response_json["is_paused"]

    #if pod is paused, does not notify load balancer
    #if pod is up and running (!paused), load balancer notified
    if is_paused == False:
        add_command = "echo 'experimental-mode on; add server " + servers + "/'" + node_name + ' ' + ip_no_port + ':'  + port + '| sudo socat stdio /var/run/haproxy.sock'
        subprocess.run(add_command, shell=True, check=True)

        #enable
        enable_command = "echo 'experimental-mode on; set server " + servers + "/'" + node_name + ' state ready ' + '| sudo socat stdio /var/run/haproxy.sock'
        subprocess.run(enable_command, shell=True, check=True)

    return Response(response.content, content_type=response.headers['content-type'])     

#function to resume a specified pod_id (put all nodes in LB on pause)
@app.route('/cloudproxy/resume/<pod_id>', methods=["PUT"])
def cloud_resume(pod_id):
    URL, ip_no_port, servers, port_list = get_serverPrams(pod_id) 
    # get all nodes_names from proxy with their status
    response = requests.put(URL +'/cloudproxy/resume')

    #get all the nodes with ONLINE status
    response_json = response.json()
    online_nodes = response_json["online"]
    
    if online_nodes: #if not empty
        for name in online_nodes:
            #set these nodes to ready state for load balancer:
            enable_command = "echo 'experimental-mode on; set server " + servers + "/'" + name + ' state ready ' + '| sudo socat stdio /var/run/haproxy.sock'
            subprocess.run(enable_command, shell=True, check=True)

        return jsonify({'result': 'successfully resumed the pod'})

    else: #no nodes to be resumed
        return jsonify({'result': 'no nodes to be resumed, no online nodes'})

# function to pause a specified pod_id - set online nodes to maintenance state - will not receive requests
@app.route('/cloudproxy/pods/pause/<pod_id>', methods=["PUT"])
def cloud_pause(pod_id):
    URL, ip_no_port = get_podURL(pod_id)
    # remove all nodes with the ONLINE status from the load balancer configuration
    response = requests.put(URL +'/cloudproxy/pause')
    response_json = response.json()
    online_nodes = response_json["online"]

    if online_nodes:
        for name in online_nodes:
            #put the node in maintenance state in HAProxy 
            disable_command = "echo 'experimental-mode on; set server " + servers + "/'" + name + ' state maint ' + '| sudo socat stdio /var/run/haproxy.sock'
            subprocess.run(disable_command, shell=True, check=True)

        return jsonify({'response': 'successfully paused the pod'})
    else:
        # if no online nodes found, return an error response
        return  jsonify({'response': 'empty pod paused'})


# ########TODO: below commands not tested 
# #route to abort a job
# @app.route('/cloudproxy/jobs/<job_id>', methods=["DELETE"])
# def cloud_abort(job_id):
#     response = requests.delete(URL + f'/cloudproxy/jobs/{job_id}')
#     return Response(response.content, content_type=response.headers['content-type'])

# # route to list all pods
# @app.route('/cloudproxy/pods', methods=["GET"])
# def cloud_pod_ls():
#     response = requests.get(URL + '/cloudproxy/pods')
#     return Response(response.content, content_type=response.headers['content-type'])

# # route to list all nodes in the provided pod
# @app.route('/cloudproxy/nodes', methods=["GET"])
# @app.route('/cloudproxy/nodes/<pod_id>', methods=["GET"])
# def cloud_node_ls(pod_id=None):
#     if pod_id:
#         response = requests.get(URL +'/cloudproxy/nodes/' + pod_id)
#         return Response(response.content, content_type=response.headers['content-type'])
#     else:
#         response = requests.get(URL +'/cloudproxy/nodes')
#         return Response(response.content, content_type=response.headers['content-type'])

# # route to list all jobs in the provided node
# @app.route('/cloudproxy/jobs', methods=["GET"])
# @app.route('/cloudproxy/jobs/<node_id>', methods=["GET"])
# def cloud_job_ls(node_id=None):
#     if node_id:
#         response = requests.get(URL +'/cloudproxy/jobs/' + node_id)
#         return Response(response.content, content_type=response.headers['content-type'])
#     else:
#         response = requests.get(URL +'/cloudproxy/jobs')
#         return Response(response.content, content_type=response.headers['content-type'])

# # route to get the log from a job
# @app.route('/cloudproxy/jobs/<job_id>/log', methods=["GET"])
# def cloud_job_log(job_id):
#     response = requests.get(URL + '/cloudproxy/jobs/' + job_id + '/log')
#     return Response(response.content, content_type=response.headers['content-type'])

# # route to get the logs from node
# @app.route('/cloudproxy/nodes/<node_id>/logs', methods=["GET"])
# def cloud_node_log(node_id):
#     response = requests.get(URL + f'/cloudproxy/nodes/{node_id}/logs')
#     return Response(response.content, content_type=response.headers['content-type'])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)

