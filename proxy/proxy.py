import ast
from datetime import datetime
import shutil
import tarfile
import threading
import queue
import atexit
import time
from apscheduler.schedulers.background import BackgroundScheduler
import io
from io import BytesIO
from flask import Flask, jsonify, request
import docker  # can't use swarm or networks !
from docker import errors
import os
import asyncio
import multiprocessing as mp
from docker.types import LogConfig
import tarfile,os
import sys

client = docker.from_env()
try :
    network = client.networks.get('container_network')
except docker.errors.NotFound:
    network = client.networks.create('container_network', driver='bridge')

app = Flask(__name__)

# ---------- TODO --------------
# team
# 1. endpoints!
# 2. response when it fails (e.g. pod doesn't exist)

# 4. not sure about launch
# me
# 1. logs at creation (returned to STDOUT and STDERR may be read only if either json-file or journald logging driver used. Thus, if you are using none of these drivers, a None object is returned instead.)
# or auto generated? dunno

# constants
DEFAULT_POD = "0"  # for A1 we consider a single Resource Pod – no Resource Cluster
WRK_DIR = '/home'
LOG_DIR = f'{WRK_DIR}/logs'
JOB_DIR = f'{WRK_DIR}/jobs'
# variables - the cluster is a set of pods TODO set these as environment variables on the VM
pods = []  # collection of nodes (docker containers)
jobs = []   # all jobs - ssh files
logs = []

# processes = [] # processes that are being executed
# main_process = mp.current_process()

'''
pod := [  ]
node = { 'id', 'name',  'status' }
jobs = [ { 'id', 'name', 'status', 'node_id' }, ... ]
wait_queue = [ job_id, ... ]
'''
'''
pod := name, ID, number of nodes
node := name, ID, status
job := name, ID, node ID, and status
logs (handled by docker)
'''

### helpers ##########################################################################################################

def node_init(node_name, pod_id=DEFAULT_POD, cpu=1024, memory="6m", storage="dm.basesize=20G"):  # TODO more appropriate default parameter values
    """ Creates a new node

        :returns: not sure yet
        """
    # doc: https://docker-py.readthedocs.io/en/stable/containers.html#docker.models.containers.Container.status

    log_config = LogConfig(type='local')

    # initially, the node has the “idle” status
    # The newly created node is assigned to a job if one is waiting in the queue.
    # In this case, both the status of the job and node must be updated accordingly
    status = 'idle'  # if wait_queue.empty() else 'running'

    # linux Alpine image is running the containers, each has a specific CPU, memory, and storage limit factor
    client.containers.run('alpine', log_config=log_config, stop_signal='SIGINT', detach=True, name=node_name,
                          stdin_open = True, tty = True, cap_add='SYS_ADMIN') #, cpu_shares=cpu, mem_limit=memory, storage_opt=storage)
    container = client.containers.get(node_name)
    container.exec_run(f"mkdir -p {LOG_DIR}")
    container.exec_run(f"mkdir -p {JOB_DIR}")
    container.pause()

    node_id = container.__getattribute__('id')
    get_pod_by_id(pod_id)['nodes'].append({'id': node_id, 'name': node_name, 'status': status})

    # TODO if logs aren't auto generated, save one here

    if not wait_queue.empty() :
        time.sleep(0.2)

    # return the node
    return get_node_by_name(node_name, pod_id)


def get_node_by_name(name, pod_id=None):
    """ Get the node with the specified name

        :returns: node with the given name or None if there are not any
        """
    # we are assuming the pod exists
    nodes = get_pod_by_id(pod_id)['nodes']
    return next(filter(lambda node: node['name'] == name, nodes), None)

def get_node_by_id(node_id, pod_id=None): # TODO add impl if none
    """ Get the node with the specified name

        :returns: node with the given name or None if there are not any
        """
    # we are assuming the pod exists
    nodes = get_pod_by_id(pod_id)['nodes']
    return next(filter(lambda node: node['id'] == node_id, nodes), None)

def get_pod_by_id(pod_id):
    """ Get the pod with the specified ID

        :returns: pod with the given ID or None if there are not any
        """
    return next(filter(lambda pod: pod['id'] == pod_id, pods), None)

def get_pod_by_name(name):
    """ Get the pod with the specified name

        :returns: pod with the given ID or None if there are not any
        """
    return next(filter(lambda pod: pod['name'] == name, pods), None)

def get_free_node_in_pod(pod_id):
    """ Get a free node in the specified pod

        :returns: a free node or None if there are not any
        """
    # we are assuming the pod exists
    nodes = get_pod_by_id(pod_id)['nodes']
    return next(filter(lambda node: node['status'] == 'idle', nodes), None)


def get_free_node():
    """ Get a free node in any pod

        :returns: a free node or None if there are not any
        """
    for pod in pods:
        node = get_free_node_in_pod(pod['id'])
        if node :
            return node
    return None

def get_job_by_name(name):
    """ Get the node with the specified name

        :returns: node with the given name or None if there are not any
        """
    return next(filter(lambda job: job['name'] == name, jobs), None)


def get_job_by_id(id):
    """ Get the node with the specified name

        :returns: node with the given name or None if there are not any
        """
    return next(filter(lambda job: job['id'] == id, jobs), None)

### job management ####################################################################################################

# execute the job on a new thread, and append its output to a log file in the node it is running on
def exec_job(node, job):  #, process):
    #load_env_var()

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
    node['status'] = 'idle'
    #save_env_var()

    # we are done
    print(f"Job with path {job['name']} and id {job['id']} was successfully completed.")

wait_queue = queue.Queue()  # jobs that are waiting to be assigned

# https://docs.python.org/3/library/queue.html
def wait_queue_exec():
    while True:
        node = get_free_node()
        if node and not wait_queue.empty():
            job_id = wait_queue.get()
            job = get_job_by_id(job_id)
            job['node_id'] = node['id']
            node['status'] = 'running'
            job['status'] = 'running'
            thr = threading.Thread(target=exec_job, args=(node, job))
            thr.start()
            wait_queue.task_done()

# def #save_env_var():
#     global pods, jobs
#     if str(pods) != os.getenv('PODS'):
#         os.environ["PODS"] = str(pods)
#     if str(jobs) != os.getenv('JOBS'):
#         os.environ["JOBS"] = str(jobs)
#
# def #load_env_var(): # maybe get this from docker... :(
#     global pods, jobs
#     if not os.getenv('PODS'):
#         os.environ['PODS'] = "[]"
#         os.environ['JOBS'] = "[]"
#     if str(pods) != os.getenv('PODS'):
#         pods = ast.literal_eval(os.getenv('PODS'))
#     if str(jobs) != os.getenv('JOBS'):
#         jobs = ast.literal_eval(os.getenv('JOBS'))

# Turn-on the worker thread.
# scheduler = BackgroundScheduler()
# scheduler.add_job(func=wait_queue_exec, trigger="interval", seconds=1)
threading.Thread(target=wait_queue_exec, daemon=True).start()
#scheduler.add_job(func=save_env_var, trigger="interval", seconds=1)
#scheduler.start()

# Shut down the scheduler when exiting the app
#atexit.register(lambda: scheduler.shutdown())

# everytime we queue a job
# when wait returns, we schedule from wait queue

### A1 functions #####################################################################################################

@app.route('/cloudproxy', methods=["POST"])
def cloud_init():
    """ Initializes the main resource cluster. All cloud services are set up.
        :return: if the cluster was successfully initialized
    """
    # if it was requested to initialize a new cluster
    if request.method == 'POST':
        # if the cluster was never initialized
        #load_env_var()
        # if the cluster was already initialized, we just return
        if len(pods) != 0:
            print('Resource cluster was already initialized.')
            return jsonify({'result': 'already exists'})
        # instantiate the default pod (a pod is a collection of nodes)
        pods.append({'id': DEFAULT_POD, 'name': 'default', 'nodes': []})
        # instantiate 50 default nodes in the default pod
        for i in range(0, 50):
             node_init('node_' + str(i))
        # a cluster is a set of pods => this is a cluster so nothing else to do here
        #save_env_var()
        print('Successfully initialized default pod')
        return jsonify({'result': 'success'})


@app.route('/cloudproxy/pods/<pod_name>', methods=["POST"])
def cloud_pod_register(pod_name):
    """Registers a new pod with the specified name to the
    main resource cluster. Note: pod names must be unique.

    :param: name of the pod to be created
    :returns: json containing registration result and pod name
    """
    # if it was requested to register a new pod
    if request.method == 'POST':
        #load_env_var()
        # for A1 we consider a single Resource Pod – no Resource Cluster
        print('Command unavailable due to insufficient resources.')
        #save_env_var()
        return jsonify({'result': 'unknown', 'pod_name': 'unknown'})


@app.route('/cloudproxy/pods/<pod_name>', methods=["DELETE"])
def cloud_pod_rm(pod_name):
    """Removes the specified pod.

    :param: name of the pod to be deleted
    :returns: json containing registration result and pod name
    """
    # if it was requested to delete a pod
    if request.method == 'DELETE':
        #load_env_var()
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

        # for A1 pod_name is always the default pod if it exists,
        # so nothing goes here for now
        #save_env_var()
        return jsonify({'result': "unknown", 'pod_name': "unknown"})


# route to register new node with name provided
@app.route('/cloudproxy/nodes/<node_name>', methods=["POST"])
@app.route('/cloudproxy/nodes/<node_name>/<pod_id>', methods=["POST"])
def cloud_register(node_name, pod_id=DEFAULT_POD):
    """Creates a new node and registers it to the specified pod ID.

        :param node_name: name of the node to be created
        :param pod_id: id of the pod it will be created in
        :returns: json containing registration result, node status and node name
        """

    # if it was requested to register a new node
    if request.method == 'POST':
        #load_env_var()
        print(f'Request to register new node: {node_name}')
        node_status = 'unknown'
        # if the pod with specified ID does not exist, the command fails
        pod = get_pod_by_id(pod_id)
        if pod is None:
            print('Pod with specified ID does not exist.')
            result = 'failure'
        else:
            # if the node already exists, we return its status
            node = get_node_by_name(node_name, pod_id)
            if node:
                print(f"Node with name {node['name']} already exists with status {node['status']}")
                result = 'already exists'
            # otherwise, we create a new node
            else:
                print('Successfully added a new node: ' + str(node_name))
                result = 'node added'
                node_init(node_name, pod_id)
                #save_env_var()
            # in both cases we return the node's status
            node_status = get_node_by_name(node_name, pod_id)['status']
        # return the result, the current status of the node and its name
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
        #load_env_var()
        # the command fails if the name does not exist or if its status is not “idle”
        for pod in pods:
            node = get_node_by_name(node_name, pod['id'])
            if node:
                # if the container is idle, we can delete it
                if node['status'] == 'idle':
                    print('Successfully removed node: ' + node_name)
                    container = client.containers.get(node_name)
                    container.remove(force=True)
                    pod['nodes'].remove(node)
                    #save_env_var()
                    return jsonify({'result': 'node deleted', 'node_name': node_name})
                else:
                    print(f"Node with name {node['name']} is not “idle”, with status {node['status']}")
                break
        # if the node does not exist, the command fails
        print('Node does not exists: ' + str(node_name))
        return jsonify({'result': 'node does not exist', 'node_name': node_name})


# route to launch a job
@app.route('/cloudproxy/jobs', methods=["POST"])
def cloud_launch():
    """Launches the specified job.

        :param: path to the job to be launched
        :returns: json of the result along with the job id
        """
    # if it was requested to launch a job
    if request.method == 'POST':
        #load_env_var()
        # input file
        file = request.files['file']
        file_name = file.filename
        file_content = file.read().decode()
        file.seek(0)
        # ensure a file was provided
        if file_name == '':
            return jsonify({'result': 'no file provided'})
        # current job
        job = {'id': str(len(jobs)), 'name': file_name, 'content': io.StringIO(file_content).getvalue(), 'status': 'registered',
               'node_id': None}
        jobs.append(job)
        # assign the job to the first free node
        node = get_free_node()
        if node:
            # once the job is assigned to a node, both components have their status updated to “running”
            job['node_id'] = node['id']
            node['status'] = 'running'
            job['status'] = 'running'

            #save_env_var()

            # execute the job in the background, and go on with this function
            thr = threading.Thread(target=exec_job, args=(node, job))
            thr.start()
            # process = mp.Process(target=exec_job, args=(node, job))
            # process.start()

            # once the manager dispatches the job, the ID of the job is printed to stdout
            return jsonify({'result': 'job dispatched', 'job_id': job['id']})

        # if no node is available, the job is simply queued in the manager and is assigned the “Registered” status.
        print(f"Job with name {file_name} and id {job['id']} is waiting to be dispatched, no node is available.")
        wait_queue.put(job['id'])

        return jsonify({'result': 'no node is available', 'job_id': job['id']})

# route to abort a job
@app.route('/cloudproxy/jobs/<job_id>', methods=["DELETE"])
def cloud_abort(job_id):
    """Aborts the specified job.

        :param: id of the job to be aborted
        :returns: json of the result along with the job id
        """
    # if it was requested to abort a job
    if request.method == 'DELETE':
        #load_env_var()
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
        # If the job has a “running” status, it is assigned the “aborted” status and the corresponding node becomes “idle”
        elif job['status'] == 'running':
            result = 'successfully aborted'
            job['status'] = 'aborted'
            for pod in pods:
                node = get_node_by_id(job['node_id'], pod['id'])
                if node:
                    node['status'] = 'idle'
                    container = client.containers.get(node['id'])
                    container.kill()
                    container.start()
                    container.pause()
                    break
        # print and return the result
        #save_env_var()
        print(f"Job with id {job_id} was {result}")
        return jsonify({'result': result, 'job_id': job_id})

# route to list all pods
@app.route('/cloudproxy/pods', methods=["GET"])
def cloud_pod_ls():
    """Lists all resource pods in the main cluster.

        :returns: For each resource pod, the name, ID and number of nodes
    """
    # if it was requested to get all pods
    if request.method == 'GET':
        #load_env_var()
        return jsonify(result = pods)

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
        #load_env_var()
        #  If no resource pod was specified, all nodes of the cloud system are listed
        if pod_id is None:
            result = [node for node in [pod['nodes'] for pod in pods]]
        else :
            pod = get_pod_by_id(pod_id)
            # if the pod does not exist
            if pod is None:
                print(f'Pod with id {pod_id} does not exist.')
                return jsonify({'result': 'does not exist', 'pod_id': pod_id})
            else :
                result = pod['nodes']
        return jsonify(result = result)


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
        #load_env_var()
        #  If no resource node was specified, all jobs of the cloud system are listed
        if node_id:
            for pod in pods:
                node = get_node_by_id(node_id, pod['id'])
                if node:
                    break
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
        return jsonify(result = result)

# route to get the log from a job
@app.route('/cloudproxy/jobs/<job_id>/log', methods=["GET"])
def cloud_job_log(job_id):
    """ Returns the specified job log.

        :returns: job log as json
    """
    # if it was requested to get a job's log
    if request.method == 'GET':
        #load_env_var()
        # the command fails if the job ID does not exist
        job = get_job_by_id(job_id)
        if job is None:
            print(f'Job with id "{job_id}" does not exist.')
            return jsonify({'result': 'does not exist', 'job_id': job_id})
        elif job['status'] != 'completed':
            print(f'Job with id "{job_id}" is not completed yet.')
            return jsonify({'result': 'not completed yet', 'job_id': job_id})
        else :
            node = None
            for pod in pods:
                node = get_node_by_id(job['node_id'], pod['id'])
                if node:
                    break
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
        #load_env_var()
        node = None
        # the command fails if the node does not exist
        for pod in pods:
            node = get_node_by_id(node_id, pod['id'])
            if node:
                break
        if node is None:
            print(f'Node with id "{node_id}" does not exist.')
            return jsonify({'result': 'does not exist', 'node_id': node_id})
        else :
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
                for member in tar.getmembers() :
                    f = tar.extractfile(member)
                    content = f.read()
                    result.append(content.decode())
                tar.close()
            # delete the temporary files before returning
            thr = threading.Thread(target=delete_local_logs, args=(job_ids,))
            thr.start()
            return jsonify(result)

def delete_local_logs(job_ids):
    for job_id in job_ids:
        os.remove(f"./sh_bin_{job_id}.tar")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=6000)
