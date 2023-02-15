from flask import Flask, Response, render_template, request
import pycurl
import sys
import os
import requests

cURL = pycurl.Curl()

app = Flask(__name__)

##TODO: is the URL = 'http://10.140.17.121:6000'?

URL = 'http://10.140.17.121:6000'
DEFAULT_POD = 0

@app.route('/cloudproxy', methods=["POST"]) #TODO: can we use /cloud for client: @app.route('/cloud', methods=['POST']), then /cloudproxy when RM is calling the proxy 
def cloud_init():
    # response = {"status": "connected"}
    response = requests.post(URL + '/cloudproxy') 
    print(response)
    return Response(response.content, content_type=response.headers['content-type'])

@app.route('/cloudproxy/pods/<pod_name>', methods=["POST"]) #same thing here: app.route('/cloud/pods/<pod_name>', methods=['POST'])
def cloud_pod_register(pod_name):
    response = requests.post(URL +'/cloudproxy/pods/' + pod_name) 
    print(response)
    return Response(response.content, content_type=response.headers['content-type'])

@app.route('/cloudproxy/pods/<pod_name>', methods=["DELETE"]) #TODO: @app.route('/cloud', methods=['DELETE'])
def cloud_pod_rm(pod_name):
    response = requests.delete(URL +'/cloudproxy/pods/' + pod_name)
    return Response(response.content, content_type=response.headers['content-type'])

# route to register new node with name provided
@app.route('/cloudproxy/nodes/<node_name>', methods=["POST"])
@app.route('/cloudproxy/nodes/<node_name>/<pod_id>', methods=["POST"])
def cloud_register(node_name, pod_id=DEFAULT_POD):
    if int(pod_id) != DEFAULT_POD:
        response = requests.post(URL +'/cloudproxy/nodes/' + node_name)
        return Response(response.content, content_type=response.headers['content-type'])
    else:
        response = requests.post(URL +'/cloudproxy/nodes/' + node_name + '/' + str(pod_id))
        return Response(response.content, content_type=response.headers['content-type'])

# route to delete nodes
@app.route('/cloudproxy/nodes/<node_name>', methods=["DELETE"])
def cloud_rm(node_name):
    response = requests.delete(URL +'/cloudproxy/nodes/' + node_name)
    return Response(response.content, content_type=response.headers['content-type'])

# route to launch a job
@app.route('/cloudproxy/jobs', methods=["POST"])
def cloud_launch():
    
    file = request.files['file']

    print("got file as", file, file=sys.stderr)
    response = requests.post(URL + '/cloudproxy/jobs', files={'file': file})
    return Response(response.content, content_type=response.headers['content-type'])

# route to abort a job
@app.route('/cloudproxy/jobs/<job_id>', methods=["DELETE"])
def cloud_abort(job_id):
    response = requests.delete(URL + f'/cloudproxy/jobs/{job_id}')
    return Response(response.content, content_type=response.headers['content-type'])

# route to list all pods
@app.route('/cloudproxy/pods', methods=["GET"])
def cloud_pod_ls():
    response = requests.get(URL + '/cloudproxy/pods')
    return Response(response.content, content_type=response.headers['content-type'])

# route to list all nodes in the provided pod
@app.route('/cloudproxy/nodes', methods=["GET"])
@app.route('/cloudproxy/nodes/<pod_id>', methods=["GET"])
def cloud_node_ls(pod_id=None):
    if pod_id:
        response = requests.get(URL +'/cloudproxy/nodes/' + pod_id)
        return Response(response.content, content_type=response.headers['content-type'])
    else:
        response = requests.get(URL +'/cloudproxy/nodes/')
        return Response(response.content, content_type=response.headers['content-type'])

# route to list all jobs in the provided node
@app.route('/cloudproxy/jobs', methods=["GET"])
@app.route('/cloudproxy/jobs/<node_id>', methods=["GET"])
def cloud_job_ls(node_id=None):
    if node_id:
        response = requests.get(URL +'/cloudproxy/jobs/' + node_id)
        return Response(response.content, content_type=response.headers['content-type'])
    else:
        response = requests.get(URL +'/cloudproxy/jobs/')
        return Response(response.content, content_type=response.headers['content-type'])

# route to get the log from a job
@app.route('/cloudproxy/jobs/<job_id>/log', methods=["GET"])
def cloud_job_log(job_id):
    response = requests.get(URL + '/cloudproxy/jobs/' + job_id + '/log')
    return Response(response.content, content_type=response.headers['content-type'])

# route to get the logs from node
@app.route('/cloudproxy/nodes/<node_id>/logs', methods=["GET"])
def cloud_node_log(node_id):
    response = requests.get(URL + f'/cloudproxy/nodes/{node_id}/logs')
    return Response(response.content, content_type=response.headers['content-type'])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
