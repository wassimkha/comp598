import sys
import os
import requests
import subprocess
import time

#-----------CLI Post Commands--------------------------------------------------------
#1. cloud init - initialize main resource cluster
def cloud_init (url):
    try: 
        response = requests.post(url + '/cloudproxy')
        print(response.content)
        #response_json = response.json()
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
    except ValueError as e:
        print(f"An error occurred while parsing the response: {e}")

#TODO: print or return
#2. cloud pod register POD_NAME - registeres a new pod with POD_NAME
def cloud_pod_register(url, command):
    print("The current cloud system cannot register new pods")
    # try:
    #     command_list = command.split()
    #     if len(command_list) == 4:
    #         response = requests.post(url + '/cloudproxy/pods/' + command_list[3])

    #         #for A1: consider a single pod
    #         print("Command unavailable due to insufficient resources.")

    #         #Proxy return jsonify({'result': "unknown", 'pod_name': "unknown"})
    #         response_json = response.json()
    #         result = response_json["result"]
    #         pod_name = response_json["pod_name"]
    #         print("Result: ", result)
    #         print("Pod Name: ", pod_name)

    #     elif len(command_list) == 3: #POD_NAME not provided
    #         print("Please provide a pod name.")

    #     else: #too many arguments
    #         print("Invalid number of arguments.")

    # except requests.exceptions.RequestException as e:
    #     print(f"An error occurred while sending the request: {e}")
        
    # except ValueError as e:
    #     print(f"An error occurred while parsing the response: {e}")


#TODO: print or return
#3. cloud pod rm POD_NAME - removes specified pod
def cloud_pod_rm(url, command):
    print("The current cloud system does not allow users to remove pods")
    # try:
    #     command_list = command.split()
    #     if len(command_list) == 4:
    #         response = requests.delete(url + '/cloudproxy/pods/' + command_list[3])

    #         #for A1: only consider single pod
    #         print("Can not delete the default pod.")

    #         #Proxy return jsonify({'result': "unknown", 'pod_name': "unknown"})
    #         response_json = response.json()
    #         result = response_json["result"]
    #         pod_name = response_json["pod_name"]
    #         print("Result: ", result)
    #         print("Pod Name: ", pod_name)

    #     elif len(command_list) == 3: #POD_NAME not provided
    #         print("Please provide a pod name.")
    #     else: #too many arguments
    #         print("Invalid number of arguments.")

    # except requests.exceptions.RequestException as e:
    #     print(f"An error occurred while sending the request: {e}")
        
    # except ValueError as e:
    #     print(f"An error occurred while parsing the response: {e}")


#4. cloud register NODE_NAME POD_ID   
# creates a new node and register to specified or default ID
def cloud_register(url, command):
    try:
        command_list = command.split()
        response = None
        if len(command_list) == 4:
            response = requests.post(url + '/cloudproxy/nodes/' + command_list[2] + '/' + command_list[3])
            node_name = command_list[2]
            pod_id = command_list[3]
        elif len(command_list) == 2 or len(command_list) == 3: #NODE_NAME or POD_ID not provided
            print("Please provide a node name and/or a pod name.")
        else: #too many arguments
            print("Invalid number of arguments.")

        #proxy:  return jsonify({'result': result, 'node_status': node_status, 'node_name': node_name})
        if response is not None:
           # print(response.content)
            response_json = response.json()
            result = response_json["result"]

            print("For new node named:", command_list[2], " registered on pod id: ", command_list[3], ", register status is", result)

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while sending the request: {e}")
        
    except ValueError as e:
        print(f"An error occurred while parsing the response: {e}")


#/cloudproxy/nodes/<node_name>/<pod_id>
#5. cloud rm NODE_NAME POD_ID - removes the specified node
def cloud_rm(url, command):
    try:
        command_list = command.split()
        if len(command_list) == 4:
            node_name = command_list[2]
            pod_id = command_list[3]
            response = requests.delete(f'{url}/cloudproxy/nodes/{node_name}/{pod_id}')
            response_json = response.json()
            result = response_json["result"]
            print("For node named:", node_name, " on pod id: ", pod_id, ", removed status is", result)

        elif len(command_list) == 3 or len(command_list) == 2: #NODE_NAME and/or POD_ID not provided
            print("Please provide the node name and/or pod name.")
        else: #too many arguments
            print("Invalid number of arguments.")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while sending the request: {e}")

    except ValueError as e:
        print(f"An error occurred while parsing the response: {e}")



#6. cloud launch POD_ID
def cloud_launch(url, command):
    try:
        command_list = command.split()
        if len(command_list) == 3: # cloud + launch + pod_id
            pod_id = command_list[2]
            response = requests.post(f'{url}/cloudproxy/launch/{pod_id}')
            response_json = response.json()
            result = response_json["result"]

            if result == 'Successfully launched the job.':
                port = response_json["port"]
                node_name = response_json["name"]
                is_paused = response_json["is_paused"]

                print("For pod with pod id ", pod_id, ", launching result: ", result, ", launched on node: ", node_name, " with port: " + port + " . If the pod is paused: " + str(is_paused))
            
            else:
                print("For pod with pod id ", pod_id, ", launching result: ", result)
            
        elif len(command_list) == 2: #path to job not specified
            print("Please provide the pod id.")
        else: #too many arguments
            print("Invalid number of arguments.")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while sending the request: {e}")
        
    except ValueError as e:
        print(f"An error occurred while parsing the response: {e}")

#cloud resume POD_ID
def cloud_resume(url, command):
    try:
        command_list = command.split()
        if len(command_list) == 3: # cloud + launch + pod_id
            pod_id = command_list[2]
            response = requests.put(f'{url}/cloudproxy/resume/{pod_id}')
            response_json = response.json()
            result = response_json["result"]
            print("For pod with pod id ", pod_id, ", resuming result: ", result)
            
        elif len(command_list) == 2: #path to job not specified
            print("Please provide the pod id.")
        else: #too many arguments
            print("Invalid number of arguments.")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while sending the request: {e}")
        
    except ValueError as e:
        print(f"An error occurred while parsing the response: {e}")

#cloud pause POD_ID
def cloud_pause(url, command):
    try:
        command_list = command.split()
        if len(command_list) == 3: # cloud + launch + pod_id
            pod_id = command_list[2]
            response = requests.put(f'{url}/cloudproxy/pods/pause/{pod_id}')
            response_json = response.json()
            result = response_json["response"]
            print("For pod with pod id ", pod_id, ", pause result: ", result)
            
        elif len(command_list) == 2: #path to job not specified
            print("Please provide the pod id.")
        else: #too many arguments
            print("Invalid number of arguments.")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while sending the request: {e}")
        
    except ValueError as e:
        print(f"An error occurred while parsing the response: {e}")

def cloud_watch(url, command):
    try:
        command_list = command.split()
        if len(command_list) == 3: # cloud + launch + seconds
            seconds = command_list[2]
            print(f"watching the load balancer incoming requests for {seconds}s")
            for i in range(int(seconds)):
                response = requests.get(f'{url}/cloudproxy/loadbalencer/watch').json()
                print(f'{response["response"]}')
                time.sleep(1)
            
        elif len(command_list) == 2: #no time specified
            print("Please provide the time to watch the comand for.")
        else: #too many arguments
            print("Invalid number of arguments.")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while sending the request: {e}")
        
    except ValueError as e:
        print(f"An error occurred while parsing the response: {e}")

def cloud_elasticity_disable(url, command):
    try:
        command_list = command.split()
        if len(command_list) == 6: # cloud elasticity disable [POD_NAME] 
            pod_name = command_list[3]
            response = requests.post(f'{url}/cloudproxy/elasticity/disable/{pod_name}').json()
            print(response)

        else: #too many arguments
            print("Invalid number of arguments.")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while sending the request: {e}")
        
    except ValueError as e:
        print(f"An error occurred while parsing the response: {e}")

def cloud_elasticity_enable(url, command):
    try:
        command_list = command.split()
        if len(command_list) == 6: # cloud elasticity enable [POD_NAME] [lower_size] [upper_size]
            pod_name = command_list[3]
            lower_size = command_list[4]
            upper_size = command_list[5]
            response = requests.post(f'{url}/cloudproxy/elasticity/enable/{pod_name}/{lower_size}/{upper_size}').json()
            print(response)

        else: #too many arguments
            print("Invalid number of arguments.")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while sending the request: {e}")
        
    except ValueError as e:
        print(f"An error occurred while parsing the response: {e}")

def cloud_upper_threshold(url, command):
    try:
        command_list = command.split()
        if len(command_list) == 5: # cloud elasticity upper_threshold [POD_NAME] [value]
            pod_name = command_list[3]
            value = command_list[4]
            response = requests.post(f'{url}/cloudproxy/elasticity/upper_threshold/{pod_name}/{value}').json()
            print(response)

        else: #too many arguments
            print("Invalid number of arguments.")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while sending the request: {e}")
        
    except ValueError as e:
        print(f"An error occurred while parsing the response: {e}")

def cloud_lower_threshold(url, command):
    try:
        command_list = command.split()
        if len(command_list) == 5: # cloud elasticity lower_threshold [POD_NAME] [value]
            pod_name = command_list[3]
            value = command_list[4]
            response = requests.post(f'{url}/cloudproxy/elasticity/lower_threshold/{pod_name}/{value}').json()
            print(response)

        else: #too many arguments
            print("Invalid number of arguments.")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while sending the request: {e}")
        
    except ValueError as e:
        print(f"An error occurred while parsing the response: {e}")

def main():
    #RM url given as argument
    #rm_url = sys.argv[1]
    rm_url = 'http://10.140.17.120:5001'
    while(1): #loop while taking input from client
        command = input('$ ')
        if command == 'cloud init':
            #call function that invokes corresponding endpoint in RM
            cloud_init(rm_url)
        elif command.startswith ('cloud pod register'):
            cloud_pod_register(rm_url, command)
        elif command.startswith ('cloud pod rm'):
            cloud_pod_rm(rm_url, command)
        elif command.startswith('cloud register'):
            cloud_register(rm_url, command)
        elif command.startswith ('cloud rm'):
            cloud_rm(rm_url, command)
        elif command.startswith('cloud launch'):
            cloud_launch(rm_url, command)
        elif command.startswith('cloud resume'):
            cloud_resume(rm_url, command)
        elif command.startswith('cloud pause'):
            cloud_pause(rm_url, command)
        elif command.startswith('cloud watch'):
            cloud_watch(rm_url, command)
        elif command.startswith('cloud elasticity lower_threshold'):
            cloud_lower_threshold(rm_url, command)
        elif command.startswith('cloud elasticity upper_threshold'):
            cloud_upper_threshold(rm_url, command)
        elif command.startswith('cloud elasticity enable'):
            cloud_elasticity_enable(rm_url, command)
        elif command.startswith('cloud elasticity disable'):
            cloud_elasticity_disable(rm_url, command)
        else:
            print("Invalid command entered! Please re-enter a valid command.")

#entry point
if __name__ == '__main__':
    main()


# elif command.startswith ('cloud abort'):
        #     cloud_abort(rm_url, command)
        #  #monitoring commands   
        # elif command == ('cloud pod ls'):
        #     cloud_pod_ls(rm_url, command)
        # elif command.startswith ('cloud node ls'):
        #     cloud_node_ls(rm_url, command)
        # elif command.startswith ('cloud job ls'):
        #     cloud_job_ls(rm_url, command)
        # elif command.startswith ('cloud job log'):
        #     cloud_job_log(rm_url, command)
        # elif command.startswith ('cloud log node'):
        #     cloud_log_node(rm_url, command)

# #7. cloud abort JOB_ID
# #aborts specified job
# def cloud_abort(url, command):
#     try:
#         command_list = command.split()
#         if len(command_list) == 3:
#             response = requests.delete(url + '/cloudproxy/jobs/' + command_list[2])
#             #proxy returns ex. jsonify({'result': result, 'job_id': job['id']})
#             response_json = response.json()
#             result = response_json["result"]
#             job_id = response_json["job_id"]
#             print("For job launched with job id ", job_id, ", abort result: ", result)

#         elif len(command_list) == 2: #job id not specified
#             print("Please provide the job ID.")

#         else: #too many arguments
#             print("Invalid number of arguments.")

#     except requests.exceptions.RequestException as e:
#         print(f"An error occurred while sending the request: {e}")
        
#     except ValueError as e:
#         print(f"An error occurred while parsing the response: {e}")

# #-----------CLI Commands: monitoring purposes--------------------------------------------------------
# #cloud pod ls - list all resource pods in main cluster
# def cloud_pod_ls(url, command):
#     try:
#         #print to stdout name, id, and number of nodes
#         response = requests.get(url+ '/cloudproxy/pods')
#         pods = response.json()['result']
#         print("Name\t\tID\tNodes")
#         for pod in pods:
#             print(f"{pod['name']}\t\t{pod['id']}\t{pod['nodes']}")
#     except requests.exceptions.RequestException as e:
#         print(f"An error occurred while sending the request: {e}")
#     except ValueError as e:
#         print(f"An error occurred while parsing the response: {e}")



# #cloud node ls [RES_POD_ID] - list all nodes in given resource pod (if not specified, all nodes listed)
# def cloud_node_ls(url, command):
#     try:
#         command_list = command.split()
#         response = None
#         if len(command_list) ==3:
#              response = requests.get(f'{url}/cloudproxy/nodes')
#              #print(response)
#         elif len(command_list) == 4:
#             pod_id = command_list[3]
#             response = requests.get(f'{url}/cloudproxy/nodes/{pod_id}')
#         else: #too many arguments
#             print("Invalid number of arguments.")

#         if response != None:
#            # print(response.content)
            
#            # print(response.status_code)
#             nodes = response.json()
        
#             if not nodes['result'][0]:
#                 print(nodes)
#                 print("No nodes to be displayed")
#             elif "result" in nodes and nodes["result"] == "does not exist":
#                 print(f"Pod with id {pod_id} does not exist.")
#             else:
#                # print(nodes['result'])
#                 print("Name\t\t\tID\t\t\t\t\t\t\t\t\tStatus")
#                 for node in nodes['result'][0]:
#                     print(f"{node['name']}\t\t{node['id']}\t{node['status']}")
#     except requests.exceptions.RequestException as e:
#         print(f"An error occurred while sending the request: {e}")
#     except ValueError as e:
#         print(f"An error occurred while parsing the response: {e}")

# #cloud job ls [NODE_ID] list all jobs assigned to the specific node (if not specifid, all jobs by user)
# def cloud_job_ls(url, command):
#     try:
#         response = None
#         command_list = command.split()

#         if len(command_list) == 3: #no node ID
#              response = requests.get(f'{url}/cloudproxy/jobs')
#         elif len(command_list) == 4:
#             node_id = command_list[3]
#             response = requests.get(f'{url}/cloudproxy/jobs/{node_id}')
#         else: #too many arguments
#             print("Invalid number of arguments.")

#         if response != None:
#             result = response.json()
#             if 'result' in result and result['result'] == 'does not exist':
#                 print(f"Node with id {result['node_id']} does not exist.")
#             elif 'result' in result:
#                 jobs = result['result']
#                 if jobs:
#                     print("Name\t\tID\t\t\t\t\tNode ID\t\t\t\t\tStatus")
#                     for job in jobs:
#                         print(f"{job['name']}\t\t{job['id']}\t{job['node_id']}\t{job['status']}")
#                 else:
#                     print("No jobs found.")
#             # print(response.content)
#            # jobs=response.json()
#            # print(jobs['result'])
#            # print("Name\t\tID\tNode ID\tStatus")
#            # for job in jobs:
#             #    print(f"{job['name']}\t\t{job['id']}\t{job['node_id']}\t{job['status']}")
    
#     except requests.exceptions.RequestException as e:
#         print(f"An error occurred while sending the request: {e}")
        
#     except ValueError as e:
#         print(f"An error occurred while parsing the response: {e}")


# #cloud job log JOB_ID - prints out specified job log
# def cloud_job_log(url, command):
#     try:
#         command_list = command.split()
#         if len(command_list) == 4:
#             job_id = command_list[3]
#             response = requests.get(f'{url}/cloudproxy/jobs/{job_id}/log')
#             #print("response", response)
#             #job not found 404
#             if response.status_code == 404:
#                 print("Job not found, request failed.")
#             else:
#                 log = response.json()
#                 if len(log)==2:
#                     print(log['result'])
#                 else:    
#                     print(log)

#         elif len(command_list) == 3:
#             print("Please provide the job ID.")
#         else:
#             print("Invalid number of arguments.")
            
#     except requests.exceptions.RequestException as e:
#         print(f"An error occurred while sending the request: {e}")
        
#     except ValueError as e:
#         print(f"An error occurred while parsing the response: {e}")


# #cloud log node NODE_ID - prints entire log file of specified node
# def cloud_log_node(url, command):
#     try:
#         command_list = command.split()
#         if len(command_list) == 4:
#             node_id = command_list[3]
#             response = requests.get(f'{url}/cloudproxy/nodes/{node_id}/logs')
#             #node ID not found 404
#             if response.status_code == 404:
#                 print("Node not found, request failed.")
#             else:
#                # print(response)
#                 print(response.content)
#                 #log = response.json()
#                 #print(log)

#         elif len(command_list) == 3:
#             print("Please provide the node ID.")
#         else:
#             print("Invalid number of arguments.")
            
#     except requests.exceptions.RequestException as e:
#         print(f"An error occurred while sending the request: {e}")
        
#     except ValueError as e:
#         print(f"An error occurred while parsing the response: {e}")