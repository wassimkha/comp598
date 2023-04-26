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
pod = dict()
initialized = False
# pod properties
POD_TYPE = ""
JOB_TYPE = ""
MAX_NODES = 0
# node properties
CPUS = 0
MEMORY = ""
logs = []

##############################For A3 - in case helpful#############################
# Endpoint ts to implement
# /cloudproxy/elasticity/enable/<lower_size>/<upper_size> - pod's elasticity enabled, update the pod's lower and upper size
# /cloudproxy/elasticity/disable - pod's elasticity disabled - back to A2's constraints
# /scale/<lower_threshold>/<upper_threshold> - add or remove nodes based on constraint

# variables for the elasticity
min_nodes = 0
max_nodes = MAX_NODES
elasticity = False
max_cpu = 0.0
min_cpu = 0.0


# API endpoint that returns average cpu utilization
@app.route('/cloudproxy/monitor', methods=["GET"])
def monitor():
    if request.method == 'GET':
        # if there are no containers
        if pod and 'nodes' in pod and len(pod['nodes']) == 0:
            return jsonify({'cpu_usage': None, 'mem_percent': None})
        # otherwise get the average and return it
        cpu_usage = get_avg_cpu()
        memory_usage = get_avg_memory()
        return jsonify({'cpu_usage': cpu_usage, 'mem_percent': memory_usage, "min_nodes": min_nodes, "max_nodes": max_nodes})


# pod's elasticity enabled, update the pod's lower and upper size
@app.route('/cloudproxy/elasticity/<lower_size>/<upper_size>', methods=["POST"])
def enable_elasticity(lower_size, upper_size):
    if request.method == 'POST':
        print(f"Enabling elasticity.")
        global min_nodes, max_nodes, elasticity
        # ensure the values are valid
        if (int(lower_size) < 0) or (int(upper_size) > MAX_NODES):
            result = 'Failure : invalid bounds.'
        else:
            result = 'Success'
            # enable elasticity (disable register and launch)
            elasticity = True
            # update the lower_size and upper_size
            min_nodes = int(lower_size)
            max_nodes = int(upper_size)
        return jsonify({'result': result})


# add or remove nodes based on constraint
@app.route('/cloudproxy/elasticity', methods=["DELETE"])
def disable_elasticity():
    if request.method == 'DELETE':
        print(f"Disabling elasticity.")
        global min_nodes, max_nodes, elasticity
        # disable elasticity (enable register and launch)
        elasticity = False
        return jsonify({'result': 'Success'})


import math

# pod's elasticity enabled, update the pod's lower and upper size
@app.route('/cloudproxy/scale/<lower_threshold>/<upper_threshold>', methods=["POST"])
def scale(lower_threshold, upper_threshold):
    if request.method == 'POST':
        print(f"Request to scale the number of pods.")
        global min_nodes, max_nodes, elasticity, max_cpu, min_cpu
        currently_online = len([node for node in pod['nodes'] if node['status'] == 'ONLINE'])
        removed = []
        added = []
        max_cpu = float(upper_threshold)
        min_cpu = float(lower_threshold)
        # we only scale if elasticity is enabled
        if not elasticity:
            result = 'Failure : elasticity needs to be enabled for the pods to be scaled.'
        else:
            result = 'Success'
            # 1. get the average cpu utilization
            avg_cpu_usage = get_avg_cpu()
            # 2. compare it against the upper and lower thresholds to get the number of containers to add or remove
            if avg_cpu_usage > max_cpu:
                # 3a. trigger the addition actions
                # we want  ( average * curr / new ) <= upper   implies   ( average * curr / upper ) <= new
                online_after_scaling = min(math.ceil(avg_cpu_usage * currently_online / max_cpu), MAX_NODES)
                num_of_nodes_to_add = online_after_scaling - currently_online
                # assign jobs to the all the nodes to add
                for i in range(num_of_nodes_to_add):
                    # make sure there is a free node available
                    if (node := get_free_node()) is None:
                        break
                    # this node will now go online
                    added.append(node)
                    # execute the job
                    thr = threading.Thread(target=exec_job, args=(node,))
                    thr.start()
                # NOTE : the CPU usage will lower naturally because the demands from the load balancer will
                #        be shared amongst more nodes that's it

                # update the CPU usage limit for all nodes
                # for container in client.containers.list():
                #     container.update(cpu_quota=int(100000*1*CPUS/online_after_scaling))
            elif avg_cpu_usage < min_cpu:
                # 3a. trigger the deletion actions
                # we want  ( average * curr / new ) >= lower  implies   ( average * curr / lower ) >= new
                online_after_scaling = max(math.floor(avg_cpu_usage * currently_online / max_cpu), min_nodes)
                num_of_nodes_to_remove = currently_online - online_after_scaling
                # assign jobs to the all the nodes to add
                for i in range(num_of_nodes_to_remove):
                    # make sure there is a free node available
                    if (node := get_online_node()) is None:
                        break
                    # this node will now go offline (new)
                    removed.append(node)
                    # abort the job
                    thr = threading.Thread(target=abort_job, args=(node,))
                    thr.start()
                    thr.join()

                # NOTE : the individual CPU usage will go up naturally because the demands from the load
                #        balancer will be shared amongst fewer nodes that's it
        print(result)
        return jsonify({'result': result, 'removed': removed, 'added': added})


# get the average cpu utilization
def get_avg_cpu():
    # for each container
    cpu_usage = 0.0
    currently_online = [node for node in pod['nodes'] if node['status'] == 'ONLINE']
    total = len(currently_online)
    for node in currently_online:
        container = client.containers.get(node["id"])
        # get cpu usage statistics from the current and last read
        stats = container.stats(stream=False)
        curr_stats = stats["cpu_stats"]
        prev_stats = stats["precpu_stats"]
        # get the total usage
        delta = float(curr_stats["cpu_usage"]["total_usage"]) - float(prev_stats["cpu_usage"]["total_usage"])
        sys_delta = float(curr_stats["system_cpu_usage"]) - float(prev_stats["system_cpu_usage"])
        # compute the percentage
        percentage = (delta / sys_delta) * 100
        # add all cpu usage of all containers
        cpu_usage += percentage
    # get average cpu usage of the pod
    cpu_usage /= max(1, total)
    # round the answer so it's prettier
    return round(cpu_usage, 2)


# get the average memory utilization
def get_avg_memory():
    # for each container
    memory_usage = 0.0
    currently_online = [node for node in pod['nodes'] if node['status'] == 'ONLINE']
    total = len(currently_online)
    for node in currently_online:
        container = client.containers.get(node["id"])
        # get memory usage statistics from the current read
        stats = container.stats(stream=False)
        memory_stats = stats["memory_stats"]
        # get the total usage
        usage = float(memory_stats["usage"]) - float(memory_stats["stats"]["cache"]) \
                + float(memory_stats["stats"]["active_file"])
        limit = float(memory_stats["limit"])
        # compute the percentage
        percentage = (usage / limit) * 100
        # add all memory usage of all containers
        memory_usage += percentage
    # get average memory usage of the pod
    memory_usage /= max(1, total)
    # round the answer so it's prettier
    return round(memory_usage, 2)


### helpers ##########################################################################################################

def node_init(node_name, port, cpus=CPUS, memory=MEMORY):
    """ Creates a new node

        :returns: the node that was initialized
        """
    # doc: https://docker-py.readthedocs.io/en/stable/containers.html#docker.models.containers.Container.status

    # build the image from the DockerFile
    [img, log] = client.images.build(path=pod['job']['path'], rm=True, dockerfile=pod['job']['dockerfile'])

    # linux Alpine image is running the containers, each has a specific CPU, memory, and storage limit factor
    client.containers.run(image=img, ports={'5000/tcp': port},
                          # command=['python', 'app.py', node_name],
                          stop_signal='SIGINT',
                          detach=True, name=node_name, stdin_open=True, tty=True,
                          cap_add='SYS_ADMIN', mem_limit=memory,
                          cpuset_cpus='0', cpu_shares=int(cpus * 1024))
    # cpu_quota = cpu_period * (number of CPUs assigned to the container) * (desired CPU usage percentage)
    container = client.containers.get(node_name)

    # make a directory for the logs
    container.exec_run(f"mkdir -p {LOG_DIR}")
    container.exec_run(f'touch {LOG_DIR}/{JOB_TYPE.lower()}_{port}.log')

    # add the new node to the pod; initially, it has the “NEW” status
    node_id = container.__getattribute__('id')
    pod['nodes'].append({'id': node_id, 'name': node_name, 'port': port, 'status': 'NEW'})

    # return the node
    return get_node_by_name(node_name)


def get_node_by_port(port):
    """ Gets the node with the specified port.

        :returns: node with the given name or None if there are not any
        """
    return next(filter(lambda node: node['port'] == port, pod['nodes']), None)


def get_node_by_name(name):
    """ Gets the node with the specified name

        :returns: node with the given name or None if there are not any
        """
    return next(filter(lambda node: node['name'] == name, pod['nodes']), None)


def get_node_by_id(node_id):
    """ Gets the node with the specified name

        :returns: node with the given name or None if there are not any
        """
    return next(filter(lambda node: node['id'] == node_id, pod['nodes']), None)


def get_free_node():
    """ Gets a free node in the specified pod

        :returns: a free node or None if there are not any
        """
    return next(filter(lambda node: node['status'] == 'NEW', pod['nodes']), None)


def get_online_node():
    """ Gets an online node in the specified pod

        :returns: an online node or None if there are not any
        """
    return next(filter(lambda node: node['status'] == 'ONLINE', pod['nodes']), None)


def exec_job(node):
    """ Executes the job on a new thread, and append its output to a log file inside the node it's running on """

    # node is now ONLINE
    node['status'] = "ONLINE"

    # once the manager dispatches the job, the ID of the job is printed to stdout
    port = node['port']
    print(f"Job with is being dispatched on port {port}.")

    # execute the job
    container = client.containers.get(node['name'])
    exit_code, output = container.exec_run(['python', 'app.py'], stdin=True)

    # if the job was aborted
    if exit_code != 0:
        print(f"Job on port {port} was aborted during execution.")
        return

    # save the output to a log file
    date_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    log_file = f'{LOG_DIR}/{JOB_TYPE.lower()}_{port}.log'
    output = io.StringIO(output.decode()).getvalue()
    container.exec_run(["/bin/sh", "-c", f"echo 'LOG - {JOB_TYPE.lower()} on port {port}' > {log_file}"])
    container.exec_run(["/bin/sh", "-c", f"echo '({date_time})' >> {log_file}"])
    container.exec_run(["/bin/sh", "-c", f"echo '{output}' >> {log_file}"])


def abort_job(node):
    """ Aborts the job on the specified node """

    # node is now NEW
    node['status'] = 'NEW'

    # once the manager dispatches the job, the ID of the job is printed to stdout
    port = node['port']
    print(f"Job with name is being aborted on port {port}.")

    # abort the job
    container = client.containers.get(node['id'])
    container.kill()
    container.start()
    # container.pause()

    print(f"Job running on port {port} was successfully aborted.")


### A2 functions #####################################################################################################

@app.route(f'/cloudproxy', methods=["POST"])
def cloud_init():
    """ Initializes the main resource cluster. All cloud services are set up.

        :return: true if the cluster was successfully initialized
    """
    # if it was requested to initialize a new cluster
    if request.method == 'POST':
        global POD_TYPE, JOB_TYPE, MAX_NODES, CPUS, MEMORY
        global pod, initialized, logs, elasticity, min_nodes, max_nodes
        print("Request to initialize main resource cluster.")
        # proxy type is provided as a JSON request
        if (not request.is_json) or ((request_data := request.get_json()) is None) or (len(request_data) != 5):
            result = 'Failure : proxy type information needs to be provided in JSON file.'
        # each pod has exactly one job that can be served by any node in the pod
        # the job is specified through a Dockerfile in the same directory as the proxy
        elif not os.path.exists(wrk_dir := os.getcwd()):
            result = 'Failure: invalid path.'
        elif not os.path.isfile(dockerfile := f'{wrk_dir}/Dockerfile'):
            result = 'Failure: no Dockerfile found in the working directory.'
        else:
            initialized = True
            # # we reinitialize the cluster each time init is called
            # # terminate all threads
            # for thread in threading.enumerate():
            #     if thread is threading.current_thread():
            #         continue
            #     thread.join()
            # remove all containers
            for container in client.containers.list():
                container.remove(v=True, force=True)
            # constant values related to the proxy type
            POD_TYPE = request_data['type']
            JOB_TYPE = request_data['node_type']
            MAX_NODES = request_data['max_nodes']
            CPUS = request_data['cpus']
            MEMORY = request_data['memory']
            logs = []
            # by default, elasticity is disabled
            elasticity = False
            min_nodes = 0
            max_nodes = MAX_NODES
            # save the job
            job = {'id': JOB_TYPE,
                   'path': wrk_dir,
                   'dockerfile': dockerfile,
                   'was_launched': False}
            # instantiate the default pod (a pod is a collection of nodes)
            # each pod is initially paused since it has no Node
            pod = {'id': POD_TYPE,
                   'paused': True,
                   'job': job,
                   'max_nodes': MAX_NODES,
                   'nodes': []}
            # a cluster is a set of pods => this is a cluster so nothing else to do here
            result = 'Successfully initialized pod.'
        print(result)
        return jsonify({'result': result})


@app.route(f'/cloudproxy/pods/<pod_name>', methods=["POST"])
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


@app.route(f'/cloudproxy/pods/<pod_name>', methods=["DELETE"])
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
@app.route(f'/cloudproxy/nodes/<node_name>/<port_number>', methods=["POST"])
def cloud_register(node_name, port_number):
    """ Creates a new node and registers it to the specified pod ID.

        :param port_number: port for the node
        :param node_name: name of the node to be created
        :param pod_id: id of the pod it will be created in
        :returns: json containing registration result, node status and node name
        """
    # if it was requested to register a new node
    if request.method == 'POST':
        print(f"Request to register new node {node_name} at port {port_number}.")
        global pod, MAX_NODES, POD_TYPE
        node_status = 'unknown'
        # nodes can only be registered when elasticity is disabled
        if elasticity:
            result = 'Failure: elasticity must be disabled to register new nodes.'
        # if the limit of nodes registered for this pod has already been met, the command fails
        elif len(pod['nodes']) >= MAX_NODES:
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
        print({'result': result, 'node_status': node_status, 'port_number': port_number, 'node_name': node_name})
        return jsonify({'result': result, 'node_status': node_status, 'port_number': port_number,
                        'node_name': node_name})


# route to remove nodes
@app.route(f'/cloudproxy/nodes/<node_name>', methods=["DELETE"])
def cloud_rm(node_name):
    """ Removes the specified node.

        :param node_name: name of the node to be deleted
        :returns: json of the result along with the node name
        """

    # if it was requested to delete a node
    if request.method == 'DELETE':
        print(f"Request to delete the node {node_name}.")
        global pod
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
            pod['nodes'].remove(node)
            # If this removed node was the last node of the pod, then the pod is paused and responds to
            # any incoming client requests
            pod['paused'] = (len(pod['nodes']) == 0)
            result = 'Node successfully deleted.'
        # if the node does not exist, the command fails
        print(result)
        return jsonify({'result': result, 'node_name': node_name, 'port': port,
                        'was_online': was_online, 'is_paused': pod['paused']})


# route to launch the node
@app.route(f'/cloudproxy/launch', methods=["POST"])
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
        # nodes can only be launched when elasticity is disabled
        if elasticity:
            result = 'Failure: elasticity must be disabled to launch a job.'
        # launch the first node that has 'NEW' status
        elif (node := get_free_node()) is None:
            result = 'Failure : no node available to serve the job.'
        else:
            pod['job']['was_launched'] = True
            # for the response
            port = node['port']
            node_name = node['name']
            # set the node status to "ONLINE"
            node['status'] = "ONLINE"
            container = client.containers.get(node['id'])
            # run app.py on the container at the specified port
            thr = threading.Thread(target=exec_job, args=(node,))
            thr.start()
            result = 'Successfully launched the job.'

        # if the pod is paused, remains “ONLINE” but doesn't notify the Load Balancer
        # if the pod is running, then the Load Balancer must be notified that this node is now available
        print(result)
        return jsonify({'result': result, 'port': port, 'name': node_name, 'is_paused': pod['paused']})


@app.route(f'/cloudproxy/resume', methods=["PUT"])
def cloud_resume():
    """ Unpauses the pod.

        :returns: all nodes that are online
        """
    # if it was requested to get all pods
    if request.method == 'PUT':
        print(f"Unpausing the pod.")
        # unpause the container
        pod['paused'] = False
        return jsonify({'result': 'success',
                        'online': [node for node in pod['nodes'] if node['status'] == "ONLINE"]})


@app.route(f'/cloudproxy/pause', methods=["PUT"])
def cloud_pause():
    """ Pauses the pod.

        :returns: all nodes that are online
        """
    # if it was requested to get all pods
    if request.method == 'PUT':
        print(f"Pausing the pod.")
        # pause the container
        pod['paused'] = True
        return jsonify({'result': 'success',
                        'online': [node for node in pod['nodes'] if node['status'] == "ONLINE"]})


# route to list all pods
@app.route(f'/cloudproxy/pods', methods=["GET"])
def cloud_pod_ls():
    """ Lists all resource pods in the main cluster.

        :returns: For each resource pod, the name, ID and number of nodes
    """
    # if it was requested to get all pods
    if request.method == 'GET':
        print(f"Request to list all pods.")
        if not initialized:
            result = 'Pod was not initialized yet.'
        else:
            global min_cpu, max_cpu, min_nodes, max_nodes
            print()
            pod["cpu"] = get_avg_cpu()
            pod["elasticity_range"] = f'{int(min_nodes)} - {int(max_nodes)}'
            pod["elasticity_enabled"] = elasticity
            pod["cpu_range"] = f'{min_cpu} - {max_cpu}'
            pod["memory"] = get_avg_memory()
            result = pod
        print(result)
        return jsonify(pod=pod)


# route to list all nodes in the provided pod
@app.route(f'/cloudproxy/nodes', methods=["GET"])
def cloud_node_ls():
    """ Lists all the nodes in the specified resource pod. If no resource
        pod was specified, all nodes of the cloud system are listed.

        :returns: For each node, the name, ID and status
    """
    # if it was requested to get all nodes
    if request.method == 'GET':
        print(f"Request to list all nodes in pod {POD_TYPE}.")
        #  If no resource pod was specified, all nodes of the cloud system are listed
        if not initialized:
            result = 'Pod was not initialized yet.'
            nodes = []
        else:
            result = 'Success.'
            nodes = pod['nodes']
        print(result)
        return jsonify({'result': result, 'nodes': nodes})


# route to list all jobs in the provided node
@app.route(f'/cloudproxy/job', methods=["GET"])
@app.route(f'/cloudproxy/job/<node_id>', methods=["GET"])
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
        elif node['status'] == 'NEW':
            result = f'Node is new; no assigned job.'
        else:
            result = f"app.py on port {node['port']}"
        # return the info
        return jsonify(result=result)


# route to get all the logs
@app.route(f'/cloudproxy/logs', methods=["GET"])
def cloud_job_log():
    """ Prints all logs from the job associated to this pod.

        :returns: job log as json
    """
    # if it was requested to get a job's log
    if request.method == 'GET':
        print(f"Request to list all logs.")
        if (job := pod['job']) is None:
            return jsonify({'result': 'Job does not exist.', 'job': JOB_TYPE})
        elif not job['was_launched']:
            return jsonify({'result': 'Job has not been launched.', 'job': JOB_TYPE})
        else:
            online = []
            result = []
            for node in pod['nodes']:
                if node['status'] == "ONLINE":
                    online.append(node)
            for node in online:
                job_id = pod['job']['id'].lower()
                port = node['port']
                container = client.containers.get(node['id'])
                bits, stat = container.get_archive(f"{LOG_DIR}/{job_id}_{port}.log")
                # https://stackoverflow.com/questions/50552501/how-get-file-from-docker-container-in-python
                file = open(f'./sh_bin_{job_id}_{port}.tar', 'wb')
                for chunk in bits:
                    file.write(chunk)
                file.seek(0)
                file.close()
                # https://stackoverflow.com/questions/2018512/reading-tar-file-contents-without-untarring-it-in-python-script
                tar = tarfile.open(f'./sh_bin_{job_id}_{port}.tar')
                f = tar.extractfile(tar.getmembers()[0])
                content = f.read()
                result.append(content.decode())
                tar.close()
            # delete the temporary files before returning
            thr = threading.Thread(target=delete_local_logs, args=([node['port'] for node in online],))
            thr.start()
        return result


# route to get the logs from node
@app.route(f'/cloudproxy/logs/<node_id>', methods=["GET"])
def cloud_node_log(node_id):
    """ Returns the specified node logs

        :returns: node log as json
    """
    # if it was requested to get a node's logs
    if request.method == 'GET':
        print(f"Request to list logs of node {node_id}.")
        # the command fails if the node does not exist
        if ((node := get_node_by_id(node_id)) is None) and ((node := get_node_by_name(node_id)) is None):
            return jsonify({'result': 'Node with does not exist.', 'node_id': node_id})
        else:
            job_id = pod['job']['id'].lower()
            port = node['port']
            container = client.containers.get(node_id)
            bits, stat = container.get_archive(f"{LOG_DIR}/{job_id}_{port}.log")
            # https://stackoverflow.com/questions/50552501/how-get-file-from-docker-container-in-python
            file = open(f'./sh_bin_{job_id}_{port}.tar', 'wb')
            for chunk in bits:
                file.write(chunk)
            file.seek(0)
            file.close()
            # https://stackoverflow.com/questions/2018512/reading-tar-file-contents-without-untarring-it-in-python-script
            tar = tarfile.open(f'./sh_bin_{job_id}_{port}.tar')
            f = tar.extractfile(tar.getmembers()[0])
            content = f.read()
            result = content.decode()
            tar.close()
            # delete the temporary files before returning
            thr = threading.Thread(target=delete_local_logs, args=([port],))
            thr.start()
            return result


def delete_local_logs(ports):
    """ Deletes temporary log files that are saved locally """
    for port in ports:
        os.remove(f"./sh_bin_{JOB_TYPE.lower()}_{port}.tar")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
