# API
from dataclasses import dataclass

from flask import Flask, jsonify, request
# logging
from datetime import datetime
import io
import tarfile
# job scheduling / multithreading
import threading
import queue
import time
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
pods = []  # collection of nodes (docker containers)
jobs = []  # all jobs - ssh files
logs = []  # self-explanatory
wait_queue = queue.Queue()  # jobs that are waiting to be assigned
'''
pods := [ {'id', 'name', 'type', 'nodes': [ {'id', 'name', 'port', 'status'}, ... ] }, ... ] 
jobs := [ {'id', 'name', 'content', 'status', 'node_id'}, ... ]
wait_queue := [ job_id, ... ]
logs := job ID, date & time, content 
'''

# What's new in A2 :
# - maximum number of nodes
# - present cpu and memory limits
# - status idle->new ; running->online
# TODO get rid of wait_queue, no pods, ports?

# heavy pod properties
DEFAULT_POD = "Heavy"
max_nodes = 10
# nodes at first
initial = 1 # TODO each pod has a job attributed upon initialization
first_port = 15000
# large nodes properties
cpus = 0.8
memory = "500m"


### helpers ##########################################################################################################

def node_init(node_name, port, pod_id=DEFAULT_POD, cpu_ratio=cpus, ram=memory, storage="dm.basesize=20G"):
    """ Creates a new node

        :returns: the node that was initialized
        """
    # doc: https://docker-py.readthedocs.io/en/stable/containers.html#docker.models.containers.Container.status

    # linux Alpine image is running the containers, each has a specific CPU, memory, and storage limit factor
    client.containers.run('alpine', log_config=LogConfig(type='local'), stop_signal='SIGINT',
                          detach=True, name=node_name, stdin_open=True, tty=True,
                          cap_add='SYS_ADMIN', nano_cpus=cpu_ratio * pow(10, 9), mem_limit=ram)  # storage_opt=storage)
    container = client.containers.get(node_name)
    container.exec_run(f"mkdir -p {LOG_DIR}")
    container.exec_run(f"mkdir -p {JOB_DIR}")
    container.pause()

    # add the new node to the pod; initially, it has the “idle” status
    node_id = container.__getattribute__('id')
    get_pod_by_id(pod_id)['nodes'].append({'id': node_id, 'name': node_name, 'port': port, 'status': 'NEW'})

    # the newly created node is assigned to a job if one is waiting in the queue
    # the wait gives enough time so that the status is updated before returning
    if not wait_queue.empty():
        time.sleep(0.2)

    # return the node
    return get_node_by_name(node_name, pod_id)


def get_node_by_port_with_pod(port, pod_id):
    """ Gets the node with the specified name

        :returns: node with the given name or None if there are not any
        """
    # we are assuming the pod exists
    nodes = get_pod_by_id(pod_id)['nodes']
    return next(filter(lambda node: node['port'] == port, nodes), None)


def get_node_by_port(port):
    """ Gets the node with the specified name

        :returns: node with the given name or None if there are not any
        """
    # we are assuming the pod exists
    for pod in pods:
        if (node := get_node_by_port_with_pod(port, pod['id'])) is not None:
            return node
    return None


def get_node_by_name(name, pod_id=DEFAULT_POD):
    """ Gets the node with the specified name

        :returns: node with the given name or None if there are not any
        """
    # we are assuming the pod exists
    nodes = get_pod_by_id(pod_id)['nodes']
    return next(filter(lambda node: node['name'] == name, nodes), None)


def get_node_by_id_with_pod(node_id, pod_id):
    """ Gets the node with the specified name in the specified pod

        :returns: node with the given name or None if there are not any
        """
    # we are assuming the pod exists
    nodes = get_pod_by_id(pod_id)['nodes']
    return next(filter(lambda node: node['id'] == node_id, nodes), None)


def get_node_by_id(node_id):
    """ Gets the node with the specified name

        :returns: node with the given name or None if there are not any
        """
    for pod in pods:
        if (node := get_node_by_id_with_pod(node_id, pod['id'])) is not None:
            return node
    return None


def get_pod_by_id(pod_id):
    """ Gets the pod with the specified ID

        :returns: pod with the given ID or None if there are not any
        """
    return next(filter(lambda pod: pod['id'] == pod_id, pods), None)


def get_pod_by_name(pod_name):
    """ Gets the pod with the specified name

        :returns: pod with the given ID or None if there are not any
        """
    return next(filter(lambda pod: pod['name'] == pod_name, pods), None)


def get_free_node_in_pod(pod_id):
    """ Gets a free node in the specified pod

        :returns: a free node or None if there are not any
        """
    # we are assuming the pod exists
    nodes = get_pod_by_id(pod_id)['nodes']
    return next(filter(lambda node: node['status'] == 'NEW', nodes), None)


def get_free_node():
    """ Gets a free node in any pod

        :returns: a free node or None if there are not any
        """
    for pod in pods:
        if (node := get_free_node_in_pod(pod['id'])) is not None:
            return node
    return None


def get_job_by_name(job_name):
    """ Gets the node with the specified name

        :returns: node with the given name or None if there are not any
        """
    return next(filter(lambda job: job['name'] == job_name, jobs), None)


def get_job_by_id(job_id):
    """ Get the node with the specified name

        :returns: node with the given name or None if there are not any
        """
    return next(filter(lambda job: job['id'] == job_id, jobs), None)


### job execution and scheduling #####################################################################################

def exec_job(node, job):  # , process):
    """ Executes the job on a new thread, and append its output to a log file inside the node it's running on """

    # once the manager dispatches the job, the ID of the job is printed to stdout
    print(f"Job with name {job['name']} and id {job['id']} is being dispatched.")

    # start the container
    container = client.containers.get(node['name'])
    container.unpause()

    # create the files for job and log, and upload it to the container
    path_to_job = f"{JOB_DIR}/{job['name']}"
    path_to_log = f"{LOG_DIR}/job_{job['id']}.log"
    content = job['content']
    job_id = job['id']
    date_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    container.exec_run(f'touch {path_to_job}')
    container.exec_run(f"chmod 777 {path_to_job}")
    container.exec_run(["/bin/sh", "-c", f"echo '{content}' > {path_to_job}"])

    # execute the job
    exit_code, output = container.exec_run(["/bin/sh", "-c", f"sh {path_to_job}"])

    # if the job was aborted
    if exit_code != 0:
        print(f"Job with name {job['name']} and id {job['id']} was aborted during execution.")

    # save the output to a log file
    output = io.StringIO(output.decode()).getvalue()
    container.exec_run(["/bin/sh", "-c", f"echo 'log file for job {job_id}' > {path_to_log}"])
    container.exec_run(["/bin/sh", "-c", f"echo '{date_time}' >> {path_to_log}"])
    container.exec_run(["/bin/sh", "-c", f"echo '{output}' >> {path_to_log}"])

    # pause the container
    container.pause()

    # assign the “completed” status to the job and the node becomes “idle” again
    job['status'] = 'completed'
    node['status'] = 'NEW'

    # we are done
    print(f"Job with path {job['name']} and id {job['id']} was successfully completed.")


# https://docs.python.org/3/library/queue.html
def wait_queue_exec():
    """ Dispatches jobs that are waiting to be assigned when a node becomes available (this runs in the background) """
    while True:
        node = get_free_node()
        if node and not wait_queue.empty():
            job_id = wait_queue.get()
            job = get_job_by_id(job_id)
            job['node_id'] = node['id']
            node['status'] = 'ONLINE'
            job['status'] = 'ONLINE'
            thr = threading.Thread(target=exec_job, args=(node, job))
            thr.start()
            wait_queue.task_done()


# turn-on the worker thread
threading.Thread(target=wait_queue_exec, daemon=True).start()


### A1 functions #####################################################################################################

@app.route('/cloudproxy', methods=["POST"])
def cloud_init():
    """ Initializes the main resource cluster. All cloud services are set up.

        :return: true if the cluster was successfully initialized
    """
    # if it was requested to initialize a new cluster
    if request.method == 'POST':
        # if the cluster was already initialized, we just return
        if len(pods) != 0:
            result = 'Resource cluster was already initialized.'
        else: # instantiate the default pod (a pod is a collection of nodes)
            pods.append({'id': DEFAULT_POD, 'name': 'default', 'nodes': []})
            # instantiate the initial number of nodes per pod
            for i in range(0, initial):
                node_init('node_' + str(i), first_port+i)
            # a cluster is a set of pods => this is a cluster so nothing else to do here
            result = f'Successfully initialized {DEFAULT_POD} pod.'
        print(result)
        return jsonify({'result': result})


@app.route('/cloudproxy/pods/<pod_name>', methods=["POST"])
def cloud_pod_register(pod_name):
    """ Registers a new pod with the specified name to the main resource cluster. Note: pod names must be unique.

    :param: name of the pod to be created
    :returns: json containing registration result and pod name
    """
    # if it was requested to register a new pod
    if request.method == 'POST':
        # for A1 we consider a single Resource Pod – no Resource Cluster
        print('Command unavailable due to insufficient resources.')
        return jsonify({'result': 'unknown', 'pod_name': 'unknown'})


@app.route('/cloudproxy/pods/<pod_name>', methods=["DELETE"])
def cloud_pod_rm(pod_name):
    """ Removes the specified pod.

    :param: name of the pod to be deleted
    :returns: json containing registration result and pod name
    """
    # if it was requested to delete a pod
    if request.method == 'DELETE':
        pod = get_pod_by_name(pod_name)
        # verify that the pod exists
        if pod is None:
            print(f'Pod with name "{pod_name}" does not exist.')
            return jsonify({'result': "pod does not exist", 'pod_name': pod_name})
        # the command fails if this is the default pod
        if pod['id'] == DEFAULT_POD:
            print('Cannot delete the default pod.')
            return jsonify({'result': "cannot delete default pod", 'pod_name': pod_name})
        # the command fails if there are nodes registered to this pod
        if len(pod['nodes']) != 0:
            print('Cannot delete pod with registered nodes.')
            return jsonify({'result': 'pod contains nodes', 'pod_name': pod_name})
        # else ...
        # for A1 pod_name is always the default pod if it exists, so nothing goes here for now
        return jsonify({'result': "unknown", 'pod_name': "unknown"})


# route to register new node with name provided
@app.route('/cloudproxy/nodes/<node_name>/<port_number>', methods=["POST"])
@app.route('/cloudproxy/nodes/<node_name>/<port_number>/<pod_id>', methods=["POST"])
def cloud_register(node_name, port_number, pod_id=DEFAULT_POD):
    """ Creates a new node and registers it to the specified pod ID.

        :param port_number: port for the node
        :param node_name: name of the node to be created
        :param pod_id: id of the pod it will be created in
        :returns: json containing registration result, node status and node name
        """

    # if it was requested to register a new node
    if request.method == 'POST':
        print(f'Request to register new node: {node_name}')
        node_status = 'unknown'
        # if the pod with specified ID does not exist, the command fails
        if (pod := get_pod_by_id(pod_id)) is None:
            result = 'Failure: pod with specified ID does not exist.'
        # if the limit of nodes registered for this pod has already been met, the command fails
        elif max_nodes >= len(pod['nodes']):
            result = 'Failure: pod is already at maximum resource capacity.'
        # if the node already exists, we return its status
        elif get_node_by_name(node_name, pod_id) is not None:
            result = 'Failure: node already exists.'
            node_status = get_node_by_name(node_name, pod_id)['status']
        # if there is already a node on this port
        elif get_node_by_port(port_number) is not None:
            result = 'Failure: port already taken.'
        # otherwise, we create a new node
        else:
            result = 'Node added successfully.'
            node_init(node_name, port_number, pod_id)
            node_status = 'NEW'
        # print and return the result, the current status of the node and its name
        print({'result': result, 'node_status': node_status, 'node_name': node_name})
        return jsonify({'result': result, 'node_status': node_status, 'node_name': node_name})


# route to remove nodes
@app.route('/cloudproxy/nodes/<node_name>', methods=["DELETE"])
def cloud_rm(node_name):
    """ Removes the specified node.

        :param node_name: name of the node to be deleted
        :returns: json of the result along with the node name
        """

    # if it was requested to delete a node
    if request.method == 'DELETE':
        # the command fails if the name does not exist or if its status is not “idle”
        for pod in pods:
            node = get_node_by_name(node_name, pod['id'])
            if node is not None:
                port = node['port']
                # if the node has the “ONLINE” status, then it has to notify the Load Balancer that it should
                # not redirect traffic through it anymore
                was_online = (node['status'] == "ONLINE")
                # whether the node has the “NEW” or "ONLINE" status, the Docker container
                # is shut down and the pod should remove its reference to the node
                print('Successfully removed node: ' + node_name)
                container = client.containers.get(node_name)
                container.remove(force=True)
                pod['nodes'].remove(node)
                # If this removed node was the last node of the pod, then the pod is paused and responds to
                # any incoming client requests.
                pause_pod = len(pod['nodes']) == 0
                return jsonify({'result': 'Node successfully deleted.', 'node_name': node_name, 'port': port,
                                'was_online': str(was_online), 'pause_pod': str(pause_pod)})
        # if the node does not exist, the command fails
        print('Node does not exists: ' + str(node_name))
        return jsonify({'result': 'Node does not exist.', 'node_name': node_name})


# route to launch the node at this port
@app.route('/cloudproxy/launch', methods=["POST"])
def cloud_launch():
    """ Launches the specified job.

        :param: path to the job to be launched
        :returns: json of the result along with the job id
        """
    # if it was requested to launch a job
    if request.method == 'POST':
        # launch the first node that has 'NEW' status
        if (node := get_free_node()) is not None:
            node['status'] = "ONLINE"
            node_name = node['name']
            # TODO The node should now start its HTTP web server and be ready to serve the corresponding pod’s
            #  job upon incoming user requests.
            # TODO pod is running or paused
            # ooooh jobs are at the specified path (launch_job)
            
            # TODO queue?? no because they never terminate?

            # once the manager dispatches the job, the ID of the job is printed to stdout
            return jsonify({'result': 'Node successfully launched.', 'port':  node['port'], 'name': node['name']})
        else:
            return jsonify({'result': 'No node available.'})

# helper
def launch_job():
    """ Launches the specified job.

        :param: path to the job to be launched
        :returns: json of the result along with the job id
        """
    # input file
    file = request.files['file']
    file_name = file.filename
    file_content = file.read().decode()
    file.seek(0)
    # ensure a file was provided
    if file_name == '':
        return jsonify({'result': 'no file provided'})
    # current job
    job = {'id': str(len(jobs)), 'name': file_name, 'content': io.StringIO(file_content).getvalue(),
           'status': 'registered',
           'node_id': None}
    jobs.append(job)
    # assign the job to the first free node
    node = get_free_node()
    if node:
        # once the job is assigned to a node, both components have their status updated to “running”
        job['node_id'] = node['id']
        node['status'] = 'running'
        job['status'] = 'running'
        # execute the job in the background, and go on with this function
        thr = threading.Thread(target=exec_job, args=(node, job))
        thr.start()
        # once the manager dispatches the job, the ID of the job is printed to stdout
        return jsonify({'result': 'job dispatched', 'job_id': job['id']})

    # if no node is available, the job is simply queued in the manager and is assigned the “Registered” status.
    print(f"Job with name {file_name} and id {job['id']} is waiting to be dispatched, no node is available.")
    wait_queue.put(job['id'])

    return jsonify({'result': 'no node is available', 'job_id': job['id']})

# route to abort a job
@app.route('/cloudproxy/jobs/<job_id>', methods=["DELETE"])
def cloud_abort(job_id):
    """ Aborts the specified job.

        :param: id of the job to be aborted
        :returns: json of the result along with the job id
        """
    # if it was requested to abort a job
    if request.method == 'DELETE':
        result = 'unknown'
        job = get_job_by_id(job_id)
        # The command fails if the job does not exist or if it has “Completed” status
        if job is None:
            result = 'job does not exist'
        elif job['status'] == 'completed':
            result = 'previously completed'
        # If the job has a “registered” status, it is removed from the waiting queue
        elif job['status'] == 'registered':
            result = 'successfully dequeued'
            wait_queue.get(job['id'])
        # If the job has a “running” status, we assign the “aborted” status and the corresponding node becomes “idle”
        elif job['status'] == 'ONLINE':
            result = 'successfully aborted'
            job['status'] = 'aborted'
            node = get_node_by_id(job['node_id'])
            if node:
                node['status'] = 'NEW'
                container = client.containers.get(node['id'])
                container.kill()
                container.start()
                container.pause()
        # print and return the result
        print(f"Job with id {job_id} was {result}")
        return jsonify({'result': result, 'job_id': job_id})


# route to list all pods
@app.route('/cloudproxy/pods', methods=["GET"])
def cloud_pod_ls():
    """ Lists all resource pods in the main cluster.

        :returns: For each resource pod, the name, ID and number of nodes
    """
    # if it was requested to get all pods
    if request.method == 'GET':
        return jsonify(result=pods)


# route to list all nodes in the provided pod
@app.route('/cloudproxy/nodes', methods=["GET"])
@app.route('/cloudproxy/nodes/<pod_id>', methods=["GET"])
def cloud_node_ls(pod_id=None):
    """ Lists all the nodes in the specified resource pod. If no resource
        pod was specified, all nodes of the cloud system are listed.

        :returns: For each node, the name, ID and status
    """
    # if it was requested to get all nodes
    if request.method == 'GET':
        #  If no resource pod was specified, all nodes of the cloud system are listed
        if pod_id is None:
            result = [node for node in [pod['nodes'] for pod in pods]]
        else:
            pod = get_pod_by_id(pod_id)
            # if the pod does not exist
            if pod is None:
                print(f'Pod with id {pod_id} does not exist.')
                return jsonify({'result': 'does not exist', 'pod_id': pod_id})
            else:
                result = pod['nodes']
        return jsonify(result=result)


# route to list all jobs in the provided node
@app.route('/cloudproxy/jobs', methods=["GET"])
@app.route('/cloudproxy/jobs/<node_id>', methods=["GET"])
def cloud_job_ls(node_id=None):
    """Lists all the jobs that were assigned to the specified node. If no
       node is specified, all jobs that were launched by the user are listed.

        :returns: For each job, the name, ID, node ID (if assigned to a node) and status
    """
    # if it was requested to get all jobs
    if request.method == 'GET':
        result = []
        node = None
        #  If no resource node was specified, all jobs of the cloud system are listed
        if node_id:
            node = get_node_by_id(node_id)
            # if the pod does not exist
            if node is None:
                print(f'Node with id {node_id} does not exist.')
                return jsonify({'result': 'does not exist', 'node_id': node_id})
        # we remove the file content since we don't need it
        for job in jobs:
            if not node or (node and job['node_id'] == node['id']):
                tmp = dict(job)
                del tmp['content']
                result.append(tmp)
        # return the info
        return jsonify(result=result)


# route to get the log from a job
@app.route('/cloudproxy/jobs/<job_id>/log', methods=["GET"])
def cloud_job_log(job_id):
    """ Returns the specified job log.

        :returns: job log as json
    """
    # if it was requested to get a job's log
    if request.method == 'GET':
        # the command fails if the job ID does not exist
        job = get_job_by_id(job_id)
        if job is None:
            print(f'Job with id "{job_id}" does not exist.')
            return jsonify({'result': 'does not exist', 'job_id': job_id})
        elif job['status'] != 'completed':
            print(f'Job with id "{job_id}" is not completed yet.')
            return jsonify({'result': 'not completed yet', 'job_id': job_id})
        else:
            node = get_node_by_id(job['node_id'])
            if node is None:
                print(f'Job wit id "{job_id}" was not dispatched.')
                return jsonify({'result': 'unassigned', 'job_id': job_id})
            container = client.containers.get(node['id'])
            bits, stat = container.get_archive(f"{LOG_DIR}/job_{job['id']}.log")
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


# route to get the logs from node
@app.route('/cloudproxy/nodes/<node_id>/logs', methods=["GET"])
def cloud_node_log(node_id):
    """ Returns the specified node logs

        :returns: node log as json
    """
    # if it was requested to get a node's logs
    if request.method == 'GET':
        # the command fails if the node does not exist
        node = get_node_by_id(node_id)
        if node is None:
            print(f'Node with id "{node_id}" does not exist.')
            return jsonify({'result': 'does not exist', 'node_id': node_id})
        else:
            result = []
            job_ids = []
            for job in jobs:
                if job['node_id'] == node_id:
                    job_ids.append(job['id'])
            # https://stackoverflow.com/questions/50552501/how-get-file-from-docker-container-in-python
            container = client.containers.get(node_id)

            for job_id in job_ids:
                file = open(f'./sh_bin_{job_id}.tar', 'wb')
                bits, stat = container.get_archive(f"{LOG_DIR}/job_{job_id}.log")
                for chunk in bits:
                    file.write(chunk)
                file.seek(0)
                file.close()
            # https://stackoverflow.com/questions/2018512/reading-tar-file-contents-without-untarring-it-in-python-script
            for job_id in job_ids:
                tar = tarfile.open(f'./sh_bin_{job_id}.tar')
                for member in tar.getmembers():
                    f = tar.extractfile(member)
                    content = f.read()
                    result.append(content.decode())
                tar.close()
            # delete the temporary files before returning
            thr = threading.Thread(target=delete_local_logs, args=(job_ids,))
            thr.start()
            return jsonify(result)


def delete_local_logs(job_ids):
    """ Deletes temporary log files that are saved locally """
    for job_id in job_ids:
        os.remove(f"./sh_bin_{job_id}.tar")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=6000)
