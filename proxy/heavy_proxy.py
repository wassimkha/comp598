# API
from flask import Flask, jsonify, request
# logging
from datetime import datetime
import io
import tarfile
#  multithreading
import threading
# docker
import docker  # can't use swarm or networks !
from docker import errors
from docker.types import LogConfig
# interactions with the VM
import os

# set up the network
client = docker.from_env()
try:
    network = client.networks.get('container_network')
except docker.errors.NotFound:
    network = client.networks.create('container_network', driver='bridge')
# set up the app
app = Flask(__name__)

# constants
WRK_DIR = '/home'
LOG_DIR = f'{WRK_DIR}/logs'
JOB_DIR = f'{WRK_DIR}/jobs'
# structure - the cluster is a set of pods
'''
pod = {'id', 'status', 'job_path', 'nodes': [ {'id', 'name', 'port', 'status'}, ... ] }, ...
'''

# a pod will have one job assigned to it, and this job can
# be served by any node in the pod

# there is only one pod
heavy_pod = dict()
initialized = False
# heavy pod properties
DEFAULT_POD = "Heavy"
DEFAULT_JOB = "Large"
MAX_NODES = 10
# large nodes properties
cpus = 0.8
memory = "500m"


### helpers ##########################################################################################################

def node_init(node_name, port, cpu_ratio=cpus, ram=memory):
    """ Creates a new node

        :returns: the node that was initialized
        """
    # doc: https://docker-py.readthedocs.io/en/stable/containers.html#docker.models.containers.Container.status

    # build the image from the DockerFile
    [img, logs] = client.images.build(path=heavy_pod['job']['path_to_dockerfile'], rm=True,
                                      dockerfile=f"{heavy_pod['job']['path_to_dockerfile']}/Dockerfile")

    # linux Alpine image is running the containers, each has a specific CPU, memory, and storage limit factor
    client.containers.run(image=img, ports={'5000/tcp': port}, log_config=LogConfig(type='local'), stop_signal='SIGINT',
                          detach=True, name=node_name, stdin_open=True, tty=True,
                          cap_add='SYS_ADMIN', cpu_shares=int(cpu_ratio*1024), mem_limit=ram)  # storage_opt=storage)
    container = client.containers.get(node_name)
    container.exec_run(f"mkdir -p {LOG_DIR}")
    container.exec_run(f"mkdir -p {JOB_DIR}")

    # at this point, the node is running, but it is not running the job (i.e. the corresponding web server)
    # container.pause()

    # add the new node to the pod; initially, it has the “NEW” status
    node_id = container.__getattribute__('id')
    heavy_pod['nodes'].append({'id': node_id, 'name': node_name, 'port': port, 'status': 'NEW'})

    # return the node
    return get_node_by_name(node_name)


def get_node_by_port(port):
    """ Gets the node with the specified port.

        :returns: node with the given name or None if there are not any
        """
    return next(filter(lambda node: node['port'] == port, heavy_pod['nodes']), None)


def get_node_by_name(name):
    """ Gets the node with the specified name

        :returns: node with the given name or None if there are not any
        """
    return next(filter(lambda node: node['name'] == name, heavy_pod['nodes']), None)


def get_node_by_id(node_id):
    """ Gets the node with the specified name

        :returns: node with the given name or None if there are not any
        """
    return next(filter(lambda node: node['id'] == node_id, heavy_pod['nodes']), None)


def get_free_node():
    """ Gets a free node in the specified pod

        :returns: a free node or None if there are not any
        """
    return next(filter(lambda node: node['status'] == 'NEW', heavy_pod['nodes']), None)


### A2 functions #####################################################################################################

@app.route(f'/cloudproxy/{DEFAULT_POD.lower()}', methods=["POST"])
def cloud_init():
    """ Initializes the main resource cluster. All cloud services are set up.

        :return: true if the cluster was successfully initialized
    """
    # if it was requested to initialize a new cluster
    if request.method == 'POST':
        print("Request to initialize main resource cluster.")
        # TODO hardcode app, pass the parameters as JSON
        # path_to_dockerfile := f'./app/'
        # we can't instantiate a cluster if it was already initialized
        global heavy_pod, initialized
        if initialized:
            result = 'Resource cluster was already initialized.'
        # each pod has exactly one job that can be served by any node in the pod
        elif (len(request.args) == 0) or ((path_to_dockerfile := request.args['dockerfile_dir']) == ""):
            result = 'Failure: no job was provided.'
        elif not os.path.exists(path_to_dockerfile):
            result = 'Failure: invalid path.'
        elif not os.path.isfile(f"{path_to_dockerfile}/Dockerfile"):
            result = 'Failure: no Dockerfile found in the provided directory.'
        else:
            initialized = True
            # if the path is valid, we save the job
            job = {'id': DEFAULT_JOB,
                   'path_to_dockerfile': path_to_dockerfile,
                   'node_id': None}
            # instantiate the default pod (a pod is a collection of nodes)
            # each pod is initially paused since it has no Node
            heavy_pod = {'id': DEFAULT_POD,
                         'paused': True,
                         'job': job,
                         'max_nodes': MAX_NODES,
                         'nodes': []}
            # a cluster is a set of pods => this is a cluster so nothing else to do here
            result = f'Successfully initialized {DEFAULT_POD} pod.'
        print(result)
        return jsonify({'result': result})


@app.route(f'/cloudproxy/{DEFAULT_POD.lower()}/pods/<pod_name>', methods=["POST"])
def cloud_pod_register(pod_name):
    """ Registers a new pod with the specified name to the main resource cluster. Note: pod names must be unique.

    :param: name of the pod to be created
    :returns: json containing registration result and pod name
    """
    # if it was requested to register a new pod
    if request.method == 'POST':
        print(f"Request to register pod with name {pod_name}.")
        # for A1 we consider a single Resource Pod – no Resource Cluster
        result = 'The current cloud system cannot register new pods.'
        print(result)
        return jsonify({'result': result, 'pod_name': 'unknown'})


@app.route(f'/cloudproxy/{DEFAULT_POD.lower()}/pods/<pod_name>', methods=["DELETE"])
def cloud_pod_rm(pod_name):
    """ Removes the specified pod.

    :param: name of the pod to be deleted
    :returns: json containing registration result and pod name
    """
    # if it was requested to delete a pod
    if request.method == 'DELETE':
        print(f"Request to delete pod with name {pod_name}.")
        # for A1 and A2 pod_name is always the default pod if it exists, so nothing goes here for now
        result = 'The current cloud system does not allow users to remove pods'
        print(result)
        return jsonify({'result': result, 'pod_name': pod_name})


# route to register new node with name provided
@app.route(f'/cloudproxy/{DEFAULT_POD.lower()}/nodes/<node_name>/<port_number>', methods=["POST"])
@app.route(f'/cloudproxy/{DEFAULT_POD.lower()}/nodes/<node_name>/<port_number>/<pod_id>', methods=["POST"])
def cloud_register(node_name, port_number, pod_id=DEFAULT_POD):
    """ Creates a new node and registers it to the specified pod ID.

        :param port_number: port for the node
        :param node_name: name of the node to be created
        :param pod_id: id of the pod it will be created in
        :returns: json containing registration result, node status and node name
        """
    # if it was requested to register a new node
    if request.method == 'POST':
        print(f"Request to register new node {node_name} at port {port_number}.")
        global heavy_pod
        node_status = 'unknown'
        # if the pod with specified ID does not exist, the command fails
        if pod_id != DEFAULT_POD:
            result = 'Failure: pod with specified ID does not exist in this cluster.'
        # if the limit of nodes registered for this pod has already been met, the command fails
        elif len(heavy_pod['nodes']) >= MAX_NODES:
            result = 'Failure: pod is already at maximum resource capacity.'
        # if the node already exists, we return its status
        elif get_node_by_name(node_name) is not None:
            result = 'Failure: node already exists.'
            node_status = get_node_by_name(node_name)['status']
        # if there is already a node on this port
        elif get_node_by_port(port_number) is not None:
            result = 'Failure: port already taken.'
        # otherwise, we create a new node (and the associated docker container)
        else:
            result = 'Node added successfully.'
            node_init(node_name, port_number)  # this does not run the job
            node_status = 'NEW'
        # print and return the result, the current status of the node and its name
        print({'result': result, 'node_status': node_status, 'port_numer': port_number, 'node_name': node_name})
        return jsonify({'result': result, 'node_status': node_status, 'port_numer': port_number,
                        'node_name': node_name})


# route to remove nodes
@app.route(f'/cloudproxy/{DEFAULT_POD.lower()}/nodes/<node_name>', methods=["DELETE"])
def cloud_rm(node_name):
    """ Removes the specified node.

        :param node_name: name of the node to be deleted
        :returns: json of the result along with the node name
        """

    # if it was requested to delete a node
    if request.method == 'DELETE':
        print(f"Request to delete the node {node_name}.")
        global heavy_pod
        was_online = 'unknown'
        port = 'unknown'
        # the command fails if the name does not exist or if its status is not “idle”
        if (node := get_node_by_name(node_name)) is None:
            result = 'Failure : node does not exists.'
        else:
            port = node['port']
            # if the node has the “ONLINE” status, then it has to notify the Load Balancer that it should
            # not redirect traffic through it anymore
            was_online = (node['status'] == "ONLINE")
            # whether the node has the “NEW” or "ONLINE" status, the Docker container
            # is shut down and the pod should remove its reference to the node
            container = client.containers.get(node_name)
            container.remove(force=True)
            heavy_pod['nodes'].remove(node)
            # If this removed node was the last node of the pod, then the pod is paused and responds to
            # any incoming client requests
            heavy_pod['paused'] = (len(heavy_pod['nodes']) == 0)
            result = 'Node successfully deleted.'
        # if the node does not exist, the command fails
        print(result)
        return jsonify({'result': result, 'node_name': node_name, 'port': port,
                        'was_online': was_online, 'is_paused': heavy_pod['paused']})


# route to launch the node
@app.route(f'/cloudproxy/{DEFAULT_POD.lower()}/launch', methods=["POST"])
def cloud_launch():
    """ Launches the specified job.

        :param: path to the job to be launched
        :returns: json of the result along with the job id
        """
    # if it was requested to launch a job
    if request.method == 'POST':
        print(f"Request to launch the job.")
        port = 'unknown'
        node_name = 'unknown'
        # launch the first node that has 'NEW' status
        if (node := get_free_node()) is None:
            result = 'Failure : no node available to serve the job.'
        else:
            # for the response
            port = node['port']
            node_name = node['name']
            # set the node status to "ONLINE"
            node['status'] = "ONLINE"
            container = client.containers.get(node['id'])
            # run app.py on the container at the specified port
            container.exec_run(['python', 'app.py'])
            result = 'Successfully launched the job.'

        # if the pod is paused, remains “ONLINE” but doesn't notify the Load Balancer
        # if the pod is running, then the Load Balancer must be notified that this node is now available
        print(result)
        return jsonify({'result': result, 'port': port, 'name': node_name, 'is_paused': heavy_pod['paused']})


@app.route(f'/cloudproxy/{DEFAULT_POD.lower()}/resume', methods=["PUT"])
def cloud_resume():
    """ Unpauses the pod.

        :returns: all nodes that are online
        """
    # if it was requested to get all pods
    if request.method == 'PUT':
        print(f"Unpausing the pod.")
        # unpause the container
        heavy_pod['paused'] = False
        return jsonify({'result': 'success',
                        'online': [node for node in heavy_pod['nodes'] if node['status'] == "ONLINE"]})


@app.route(f'/cloudproxy/{DEFAULT_POD.lower()}/pause', methods=["PUT"])
def cloud_pause():
    """ Pauses the pod.

        :returns: all nodes that are online
        """
    # if it was requested to get all pods
    if request.method == 'PUT':
        print(f"Pausing the pod.")
        # pause the container
        heavy_pod['paused'] = True
        # for node in heavy_pod['nodes']:
        #     if node['status'] == "ONLINE":
        #         container = client.containers.get(node['id'])
        #         container.remove(force=True)
        #         heavy_pod['nodes'].remove(node)
        return jsonify({'result': 'success',
                        'online': [node for node in heavy_pod['nodes'] if node['status'] == "ONLINE"]})


# route to list all pods
@app.route(f'/cloudproxy/{DEFAULT_POD.lower()}/pods', methods=["GET"])
def cloud_pod_ls():
    """ Lists all resource pods in the main cluster.

        :returns: For each resource pod, the name, ID and number of nodes
    """
    # if it was requested to get all pods
    if request.method == 'GET':
        print(f"Request to list all pods.")
        return jsonify(pod=heavy_pod)


# route to list all nodes in the provided pod
@app.route(f'/cloudproxy/{DEFAULT_POD.lower()}/nodes', methods=["GET"])
def cloud_node_ls():
    """ Lists all the nodes in the specified resource pod. If no resource
        pod was specified, all nodes of the cloud system are listed.

        :returns: For each node, the name, ID and status
    """
    # if it was requested to get all nodes
    if request.method == 'GET':
        print(f"Request to list all nodes in pod {DEFAULT_POD}.")
        #  If no resource pod was specified, all nodes of the cloud system are listed
        if not initialized:
            result = 'Pod was not initialized yet.'
        else:
            result = heavy_pod['nodes']
        return jsonify(result=result)


# route to list all jobs in the provided node
@app.route(f'/cloudproxy/{DEFAULT_POD.lower()}/jobs', methods=["GET"])
@app.route(f'/cloudproxy/{DEFAULT_POD.lower()}/jobs/<node_id>', methods=["GET"])
def cloud_job_ls(node_id=None):
    """Lists all the jobs that were assigned to the specified node. If no
       node is specified, all jobs that were launched by the user are listed.

        :returns: For each job, the name, ID, node ID (if assigned to a node) and status
    """
    # if it was requested to get all jobs
    if request.method == 'GET':
        print(f"Request to list job.")
        #  If no resource node was specified, all jobs of the cloud system are listed
        if node_id is None:
            result = "app.py"
        elif (node := get_node_by_id(node_id)) is None:
            result = f'Node with does not exist.'
        elif node['status'] == "NEW":
            result = f'Node is new; no assigned job.'
        else:
            result = "app.py"
        # return the info
        return jsonify(result=result)


# route to get the log from a job
@app.route(f'/cloudproxy/{DEFAULT_POD.lower()}/jobs/<job_id>/log', methods=["GET"])
def cloud_job_log(job_id):
    """ Returns the specified job log.

        :returns: job log as json
    """
    # if it was requested to get a job's log
    if request.method == 'GET':
        print(f"Request to list all logs.")
        # the command fails if the job ID does not exist
        if (job := heavy_pod['job']) is None:
            result = 'Job does not exist.'
        elif job['node_id'] is None:
            result = 'Job has not been launched.'
        else:
            node_ids = []
            result = []
            for node in heavy_pod['nodes']:
                if node['status'] == "ONLINE":
                    node_ids.append(node['id'])
            for node_id in node_ids:
                container = client.containers.get(node_id)
                bits, stat = container.get_archive(f"{LOG_DIR}/job_{job['id']}.log")
                # https://stackoverflow.com/questions/50552501/how-get-file-from-docker-container-in-python
                file = open(f'./sh_bin_{node_id}.tar', 'wb')
                for chunk in bits:
                    file.write(chunk)
                file.seek(0)
                # https://stackoverflow.com/questions/2018512/reading-tar-file-contents-without-untarring-it-in-python-script
                tar = tarfile.open(f'./sh_bin_{node_id}.tar')
                f = tar.extractfile(tar.getmembers()[0])
                content = f.read()
                result.append(content.decode())
                tar.close()
            # delete the temporary files before returning
            thr = threading.Thread(target=delete_local_logs, args=(list(node_ids),))
            thr.start()
        return jsonify({'result': result, 'job_id': job_id})


# route to get the logs from node
@app.route(f'/cloudproxy/{DEFAULT_POD.lower()}/nodes/<node_id>/logs', methods=["GET"])
def cloud_node_log(node_id):
    """ Returns the specified node logs

        :returns: node log as json
    """
    # if it was requested to get a node's logs
    if request.method == 'GET':
        print(f"Request to list logs of node {node_id}.")
        # the command fails if the node does not exist
        if (node := get_node_by_id(node_id)) is None:
            result = 'Node with does not exist.'
        else:
            result = []
            job_id = heavy_pod['job']['id']
            container = client.containers.get(node_id)
            bits, stat = container.get_archive(f"{LOG_DIR}/job_{job_id}.log")
            # https://stackoverflow.com/questions/50552501/how-get-file-from-docker-container-in-python
            file = open(f'./sh_bin_{job_id}.tar', 'wb')
            for chunk in bits:
                file.write(chunk)
            file.seek(0)
            # https://stackoverflow.com/questions/2018512/reading-tar-file-contents-without-untarring-it-in-python-script
            tar = tarfile.open(f'./sh_bin_{job_id}.tar')
            f = tar.extractfile(tar.getmembers()[0])
            content = f.read()
            tar.close()
            # delete the temporary files before returning
            thr = threading.Thread(target=delete_local_logs, args=(list(job_id),))
            thr.start()
            return jsonify(content.decode())
        return jsonify({'result': result, 'node_id': node_id})


def delete_local_logs(job_ids):
    """ Deletes temporary log files that are saved locally """
    for job_id in job_ids:
        os.remove(f"./sh_bin_{job_id}.tar")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=6000)
