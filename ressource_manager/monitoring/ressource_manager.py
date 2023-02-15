from flask import Flask, jsonify, request, render_template
import json
from io import BytesIO
import sys
import requests
import pycurl


app = Flask(__name__)

cURL = pycurl.Curl()

URL = 'http://10.140.17.121:6000'

# Define fake data for the cloud system

def transform_data(pods, jobs, logs):
    cloud_pods = []
    cloud_nodes = []
    cloud_jobs = []
    node_logs = {}
    job_logs = {}

    node_id = 1
    for pod in pods:
        cloud_pod = {"id": pod["id"], "name": f"Pod{pod['id']}", "nodes": len(pod["nodes"])}
        cloud_pods.append(cloud_pod)
        for node in pod["nodes"]:
            cloud_node = {"id": node_id, "name": f"Node{node_id}", "pod_id": pod["id"], "status": node["status"].capitalize()}
            cloud_nodes.append(cloud_node)
            node_logs[node_id] = f"Node{node_id} log"
            node_id += 1

    job_id = 1
    for job in jobs:
        if job["node"] is not None:
            node_id = [node["id"] for node in cloud_nodes if node["name"] == job["node"]][0]
        else:
            node_id = None
        cloud_job = {"id": job_id, "name": f"Job{job_id}", "node_id": node_id, "status": job["status"].capitalize()}
        cloud_jobs.append(cloud_job)
        job_logs[job_id] = f"Job{job_id} log"
        job_id += 1

    for log in logs:
        if log["job_id"] is not None:
            job_logs[log["job_id"]] += f" - {log['message']}"
        else:
            node_logs[log["node_id"]] += f" - {log['message']}"

    return cloud_pods, cloud_nodes, cloud_jobs, node_logs, job_logs

cloud_pods, cloud_nodes, cloud_jobs, node_logs, job_logs = None, None, None, None, None

# Implement the RESTful API
@app.route("/")
def index():
    pods_json = requests.get(URL + '/cloudproxy/pods').json()
    pods = pods_json['result']
    cld_pods = []
    for pod in pods:
        cld_pods.append({
            'id': pod['id'],
            'name': pod['name'],
            'nodes': len(pod['nodes'])
        })

    return render_template("index.html", cloud_pods=cld_pods)

@app.route("/cloud/pod/ls", methods=["GET"])
def list_pods():
    return render_template("cloud_pods.html", cloud_pods=cloud_pods)

@app.route("/cloud/node/ls/<int:pod_id>", methods=["GET"])
def list_nodes(pod_id=None):
    pods_json = requests.get(URL + '/cloudproxy/pods').json()
    pods = pods_json['result']
    nodes = []

    for pod in pods:
        if int(pod['id']) == int(pod_id):
            nodes = pod['nodes']
    
    return render_template("cloud_nodes.html", nodes=nodes, pod_id=pod_id)
@app.route("/cloud/job/ls", methods=["GET"])
@app.route("/cloud/job/ls/<node_id>", methods=["GET"])
def list_jobs(node_id=None):
    jobs = []
    
    if node_id:
        jobs_json = requests.get(URL + f'/cloudproxy/jobs/{node_id}').json()
        jobs = [job for job in jobs_json['result'] if job['node_id'] == node_id]
    else:
        jobs_json = requests.get(URL + '/cloudproxy/jobs').json()
        jobs = jobs_json['result']

    return render_template("cloud_jobs.html", jobs=jobs)

@app.route("/cloud/job/log/<int:job_id>", methods=["GET"])
def get_job_log(job_id):
    job = next((job for job in cloud_jobs if job["id"] == job_id), None)
    if job:
        job_log = job_logs.get(job_id, None)
        return render_template("logs.html", logs=job_log)
    else:
        return "Job not found", 404

@app.route("/cloud/log/node/<int:node_id>", methods=["GET"])
def get_node_log(node_id):
    node_log = node_logs.get(node_id, None)
    if node_log:
        return render_template("logs.html", logs=node_log)
    else:
        return "Node not found", 404

#flask app created
if __name__ == '__main__':
    pods_json = requests.get(URL + '/cloudproxy/pods').json()
    
    pods = [
    {"id": 1, "nodes": [
        {"name": "Node1", "status": "Idle"},
        {"name": "Node2", "status": "Running"},
        {"name": "Node3", "status": "Idle"}
    ]},
    {"id": 2, "nodes": [
        {"name": "Node4", "status": "Idle"},
        {"name": "Node5", "status": "Running"}
    ]}
    ]



    jobs = [
    {"id": 1, "path": "Job1", "status": "Running", "node": "Node2"},
    {"id": 2, "path": "Job2", "status": "Completed", "node": "Node5"},
    {"id": 3, "path": "Job3", "status": "Registered", "node": None}
    ]
    logs = [
        {"message": "Node1 log", "node_id": 1, "job_id": None},
        {"message": "Node2 log - Job1 log", "node_id": 2, "job_id": 1},
        {"message": "Node3 log", "node_id": 3, "job_id": None},
        {"message": "Node4 log", "node_id": 4, "job_id": None},
        {"message": "Node5 log - Job2 log", "node_id": 5, "job_id": 2},
    ]

    cloud_pods, cloud_nodes, cloud_jobs, node_logs, job_logs = transform_data(pods, jobs, logs)
    app.run(host="0.0.0.0", port=8080, debug=True)
