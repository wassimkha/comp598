from flask import Flask, jsonify, request
import sys
import docker

client = docker.from_env()
app = Flas(__name__)

node_list = []

#TODO: node_list will have name, port number, status
@app.route('/remove/<node_name>')
def remove (node_name):
    index_to_remove = -1
    for i in range(len(node_list)):
        node = node[i]
        if node['name'] == node_name:
            index_to_remove = i
            break
    
    found = False
    port = -1
    name = ''
    status = ''

    if index_to_remove != -1:
        node = node_list[index_to_remove]
        port = node['port']
        name = node['name']
        status = node['status']

        del node_list[index_to_remove]
        found = True

    #find in docker container and remove
    for container in client.containers.list():
        if container.name == node_name:
            container.remove(v=True, force=True)
            break

        if found:
                return jsonify({'response': 'success',
                                'port':  port,
                                'name': name
                                'status': 'ONLINE'})
        return jsonify({'response': 'failure',
                        'reason': 'port already taken'})

    return ""

#TODO: to be implemented in all three proxies - node registerd with port number for that pod
#create the node here, leave running container to the launch method
#register new node at the given proxy number
@app.route('/register/<node_name>/<port_number>')
def register(name, port):
    for node in node_list:
        if (node['port'] == port) #if port is the same as port we want to specify
        #return failre - can only take one container per port
            return jsonify({'response': 'failure',
                        'reason': 'port already taken'})
        elif node['name'] == name: #containers can't have same name
            return jsonify({'response': 'failure',
                        'reason': 'name already taken'})

    
    #can add
    node_list.append({'port': port, 'name': name, 'status': 'NEW'})
    return jsonify({'response': 'success',
                                'port':  port,
                                'name': name
                                'status': 'NEW'})
                                #not ready to be added to LB - initialize to false for running

#helper method - create docker container
#container_name = node_name, port_number = used when container is created
def launch_node(container_name, port_number){

    [img, logs] = client.images.build(path='home/comp598-user/app_light/', rm=True, dockerfile='/home/comp598-user/app_light/Dockerfile')

    #make sure if the container_name is running ('ONLINE), remove it
    for container in client/containers.list():
        if container.name == container_name:
            container.remove(v=True, force=True)
    
    #run the container 
    client.containers.run(image=img, detach=True, name=container_name, 
                            commad=['python', 'app.py', container_name],
                            ports{'5000/tcp': port_number})
    
    #update dictionary
    index = -1
    for i in range(len(node_list)):
        node = node_list[i]
        if container_name = node['name']:
            index = i
            node_list[i] = {'port:' port_number, 'name': container_name, 'running': True}
            break
    
    print("successfully launched a node")
    return node_list[index]
}

@app.route('/launch') #choose which node will launch the job
def launch():
    #choose the first node that is 'new' and switch to 'online'
    for node in node_list:
        if node['status'] != 'ONLINE': #node is in 'new' status = not in LB, just registered
            node = launch_node(node['name'], node['port'])
            if node is not None:
                return jsonify({'response': 'success',
                                'port':  node['port'],
                                'name': node['name'],
                                'status': 'NEW'})
    
    return jsonify({'response': 'failure',
                        'reason': 'unknown reason'})


if __name__ == "__main__":
 
    app.run(debug=True, host='0.0.0.0', port=5000)

