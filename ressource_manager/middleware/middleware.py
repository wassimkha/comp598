from flask import Flask, Response, render_template, request
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

@app.route('/cloudproxy', methods=["POST"]) 
#initialize all 3 proxies
def cloud_init():
    #re-set global vars 
    URL = '' 
    ip_no_port = ''
    port_numbers_light = {key: False for key in range(15000, 15009)} 
    port_numbers_medium = {key: False for key in range(15000, 15014)} 
    port_numbers_heavy = {key: False for key in range(15000, 15019)}
    
    #call init on all three proxies
    response_light = requests.post(ip_proxy_light + '/cloudproxy')
    response_medium = requests.post(ip_proxy_medium + '/cloudproxy')
    response_heavy = requests.post(ip_proxy_medium + '/cloudproxy')
    
    all_responses = {
        'response_light': response_light.json(),
        'response_medium': response_medium.json(),
        'response_heavy': response_heavy.json()
    }

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
            port_number = key
            break

    if port_number is not None:
        print(f"The first available port is {port_number}")
    else:
        print("All ports are occupied, reach capacity")
        return jsonify({'result': 'failure',
                        'reason:': 'All ports are occupied, reached capacity of pod'}) 

    #call proxy to register this node - its status set to NEW, not running
    response = requests.post(URL +'/cloudproxy/nodes/' + node_name + '/' + port_number)
    response_json = response.json()

    result = response_json["result"]
    #set port_number as false = taken in the list

    #TODO: change below based on proxy's output implementation
    
    if result == 'node added': #successfully registerd
        #set that port number as taken
        port_list[port_number] = False
        update_portList(pod_id) #update global dict for that proxy
        print("node was successfully registered and port number freed")
    
    return Response(response.content, content_type=response.headers['content-type'])

 #remove node on proxy side, then remove from load balancer
@app.route('/cloudproxy/nodes/<node_name>/<pod_id>', methods=["DELETE"])
def cloud_rm(node_name):
    
    URL, ip_no_port, servers, port_list = get_serverPrams(pod_id)

    response = requests.delete(URL +'/cloudproxy/nodes/<pod_id>' + node_name)
    
    if(response.response_code == 200): #success
        #parse json, if the node is online (started a docker container), put to maintenance state then delete
        response_json = response.json()
        result = response_json["result"]
        status = response_json["status"]
        name = response_json['name']
            
        if (result == 'success'): # succesfully removed on proxy
            port = response_json['port']
                
            if status == 'ONLINE': #node is added in LB - started a docker container
                #put the node in maintenance state using HAProxy socket
                disable_command = "echo 'experimental-mode on; set server " + servers + "/'" + name + ' state maint ' + '| sudo socat stdio /var/run/haproxy.sock'
                subprocess.run(disable_command, shell=True, check=True)

                #remove node from load balancer
                rm_command = "echo 'experimental-mode on; set server " + servers + "/'" + name + '| sudo socat stdio /var/run/haproxy.sock'
                subprocess.run(rm_command, shell=True, check=True)

                #set the port number as available for registration
                if port in port_list:
                    port_list[port] = False
                    update_portList(pod_id)

            return jsonify({'response': 'success',
                            'port': port, 
                            'name': name,
                            'status': status})
    else: #faile to remove - return failure response
        return Response(response.content, content_type=response.headers['content-type'])
    
# picks up first node with 'NEW' and switch to 'ONLINE' = running a docker container
#TODO: change in proxy AND cloud toolset 
@app.route('/cloudproxy/jobs/<pod_id>', methods=["POST"])
def cloud_launch():
        
    URL, ip_no_port, servers, port_list = get_serverPrams(pod_id)

    #proxy will find first node with 'NEW' and set to 'ONLINE' 
    response = requests.post(URL + '/cloudproxy/launch')

    response_json = response.json()
    status = response_json["status"]
    if status == 'success':
        name = response_json['name']
        port = response_json['port']

        if status == 'ONLINE': #the node was switched from 'new' to 'online' by proxy successfully
        #add to load balancer
            add_command = "echo 'experimental-mode on; add server " + servers + "/'" + name + ' ' + ip_no_port + ':'  + port + '| sudo socat stdio /var/run/haproxy.sock'
            subprocess.run(disable_command, shell=True, check=True)

            #enable
            enable_command = "echo 'experimental-mode on; set server " + servers + "/'" + name + ' state ready ' + '| sudo socat stdio /var/run/haproxy.sock'
            subprocess.run(enable_command, shell=True, check=True)

            return jsonify({'response': 'success',
                            'port': port, 
                            'name': name,
                            'status': status})

    return jsonify({'response': 'failure'}) 

#function to resume a specified pod_id (put all nodes in LB on pause)
@app.route('/cloudproxy/pods/resume/<pod_id>', methods=["PUT"])
def cloud_resume(pod_id):
    URL, ip_no_port, servers, port_list = get_serverPrams(pod_id) 
    # get all nodes_names from proxy with their status
    response = requests.get(URL +'/cloudproxy/nodes')
    nodes = response.json()
    #TODO: fix based on proxy implementation

    #check if any nodes are online, if yes, then enable them (include in its configuration so that it can send traffic through to this node again)
    online_nodes = [node for node in nodes if node['status'] == 'ONLINE']
    
    if online_nodes:
        for name in online_nodes:
            #set these nodes to ready state:
            enable_command = "echo 'experimental-mode on; set server " + servers + "/'" + name + ' state ready ' + '| sudo socat stdio /var/run/haproxy.sock'
            subprocess.run(enable_command, shell=True, check=True)
        return jsonify({'response': 'successfully resumed the pod'})

    else: #no nodes to be resumed
        return jsonify({'response': 'no nodes to be resumed'})

# function to pause a specified pod_id - set online nodes to maintenance state - will not receive requests
@app.route('/cloudproxy/pods/pause/<pod_id>', methods=["PUT"])
def cloud_pause(pod_id):
    URL, ip_no_port = get_podURL(pod_id)
    # remove all nodes with the ONLINE status from the load balancer configuration
    response = requests.get(URL +'/cloudproxy/nodes')
    nodes = response.json()
    online_nodes = [node for node in nodes if node['status'] == 'ONLINE']

    if online_nodes:
        for name in online_nodes:
            #put the node in maintenance state in HAProxy 
            disable_command = "echo 'experimental-mode on; set server " + servers + "/'" + name + ' state maint ' + '| sudo socat stdio /var/run/haproxy.sock'
            subprocess.run(disable_command, shell=True, check=True)
        return jsonify({'response': 'successfully paused the pod'})
    else:
        # if no online nodes found, return an error response
        return  jsonify({'response': 'no nodes to be resumed'})



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
