from flask import Flask, jsonify, request, render_template
import json
from io import BytesIO
import sys
import requests
import pycurl

app = Flask(__name__)

cURL = pycurl.Curl()

URL = 'http://10.140.17.121:5000'

# pod_id = 0
ip_proxy_light = 'http://10.140.17.119:5000'

# pod_id = 1
ip_proxy_medium = 'http://10.140.17.120:5000'

# pod_id = 2
ip_proxy_heavy = 'http://10.140.17.121:5000'

id_to_proxy_ip = {
    0: ip_proxy_light,
    1: ip_proxy_medium,
    2: ip_proxy_heavy
}


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
            cloud_node = {"id": node_id, "name": f"Node{node_id}", "pod_id": pod["id"],
                          "status": node["status"].capitalize()}
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
    # pods_json = requests.get(URL + '/cloudproxy/pods').json()
    # pods = pods_json['result']
    pods_json_light = requests.get(ip_proxy_light + '/cloudproxy/pods').json()
    pods_json_light_exist = "pod" in pods_json_light and pods_json_light["pod"]

    pods_json_medium = requests.get(ip_proxy_medium + '/cloudproxy/pods').json()
    pods_json_medium_exist = "pod" in pods_json_medium and pods_json_medium["pod"]

    pods_json_heavy = requests.get(ip_proxy_heavy + '/cloudproxy/pods').json()
    pods_json_heavy_exist = "pod" in pods_json_heavy and pods_json_heavy["pod"]

    cld_pods = []


    if pods_json_light_exist:
        pods_json_light = pods_json_light["pod"]
        pods_json_light["id"] = 0
        pods_json_light["name"] = "Light"
        pods_json_light["num_nodes"] = len(pods_json_light["nodes"])
        cld_pods.append(pods_json_light)
    if pods_json_medium_exist:
        pods_json_medium = pods_json_medium["pod"]
        pods_json_medium["id"] = 1
        pods_json_medium["name"] = "Medium"
        pods_json_medium["num_nodes"] = len(pods_json_medium["nodes"])
        cld_pods.append(pods_json_medium)
    if pods_json_heavy_exist:
        pods_json_heavy = pods_json_heavy["pod"]
        pods_json_heavy["id"] = 2
        pods_json_heavy["name"] = "Heavy"
        pods_json_heavy["num_nodes"] = len(pods_json_heavy["nodes"])
        cld_pods.append(pods_json_heavy)

    return render_template("index.html", cloud_pods=cld_pods)


@app.route("/cloud/pod/ls", methods=["GET"])
def list_pods():
    return render_template("cloud_pods.html", cloud_pods=cloud_pods)


@app.route("/cloud/node/ls/<int:pod_id>", methods=["GET"])
def list_nodes(pod_id=None):
    url = id_to_proxy_ip[pod_id]
    # print("got pod id as", pod_id, url)
    nodes_json = requests.get(url + '/cloudproxy/nodes').json()
    nodes = []
    if "nodes" in nodes_json:
        nodes = nodes_json["nodes"]
    # print("got pods json as", pods_json)
    # pods = pods_json['result']
    # print("got nodes as", nodes)
    return render_template("cloud_nodes.html", nodes=nodes, pod_id=pod_id)


@app.route("/cloud/job/ls", methods=["GET"])
@app.route("/cloud/job/ls/<node_id>", methods=["GET"])
def list_jobs(node_id=None):
    jobs = []
    if node_id:
        jobs_json = requests.get(URL + f'/cloudproxy/job/{node_id}').json()
        jobs = [job for job in jobs_json['result'] if job['node_id'] == node_id]
    else:
        jobs_json = requests.get(URL + '/cloudproxy/job').json()
        jobs = jobs_json['result']

    return render_template("cloud_jobs.html", jobs=jobs)


@app.route("/cloud/lb", methods=["GET"])
def watch_lb():
    rm_url = 'http://10.140.17.120:5001'
    response = requests.get(f'{rm_url}/cloudproxy/loadbalancer/watch').json()
    arr = response["array"]
    array = [arr.pop(0).replace("|", " ")]
    for line in arr:
        array.append(line)
    if response:
        return render_template("load_balancer_status.html", infos=array)
    else:
        return "LB not found", 404


@app.route("/cloud/job/log/<job_id>", methods=["GET"])
def get_job_log(job_id):
    job_log = requests.get(URL + f'/cloudproxy/logs').json()
    if job_log:
        return render_template("logs.html", logs=job_log)
    else:
        return "Job not found", 404


@app.route("/cloud/log/node/<node_id>/<pod_id>", methods=["GET"])
def get_node_log(node_id, pod_id):
    url = id_to_proxy_ip[int(pod_id)]
    node_log = requests.get(url + f'/cloudproxy/logs/{node_id}').content.decode('utf-8').splitlines()
    print("got log as", node_log, file=sys.stdout)
    if node_log:
        return render_template("node_logs.html", logs=node_log)
    else:
        return "Node not found", 404


# flask app created
if __name__ == '__main__':
    # pods_json = requests.get(URL + '/cloudproxy/pods').json()

    cloud_pods, cloud_nodes, cloud_jobs, node_logs, job_logs = [], [], [], [], []
    app.run(host="0.0.0.0", port=3000, debug=True)
