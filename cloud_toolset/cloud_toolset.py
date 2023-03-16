import sys
import os
import requests

#-----------CLI Post Commands--------------------------------------------------------
#1. cloud init - initialize main resource cluster
def cloud_init (url):
    try: 
        response = requests.post(url + '/cloudproxy')
        response_json = response.json()
        print(response_json["result"])
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


#4. cloud register NODE_NAME [POD_ID]   
# creates a new node and register to specified or default ID
def cloud_register(url, command):
    try:
        command_list = command.split()
        response = None
        if len(command_list) == 3:
            response = requests.post(url + '/cloudproxy/nodes/' + command_list[2])
        elif len(command_list) == 4:
            response = requests.post(url + '/cloudproxy/nodes/' + command_list[2] + '/' + command_list[3])
        elif len(command_list) == 2: #NODE_NAME not provided
            print("Please provide a node name and/or a pod name.")
        else: #too many arguments
            print("Invalid number of arguments.")

        #proxy:  return jsonify({'result': result, 'node_status': node_status, 'node_name': node_name})
        if response is not None:
           # print(response.content)
            response_json = response.json()
            result = response_json["result"]
            node_status = response_json["node_status"]
            node_name = response_json["node_name"]
            if result == "failure" or result == "already exists":
                print("Creation of new node failed because of reason:", result)
            else:
                print("Result: ", result)
                print("Node Status: ", node_status)
                print("Node Name: ", node_name)

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while sending the request: {e}")
        
    except ValueError as e:
        print(f"An error occurred while parsing the response: {e}")



#5. cloud rm NODE_NAME - removes the specified node
def cloud_rm(url, command):
    try:
        command_list = command.split()
        if len(command_list) == 3:
            response = requests.delete(url + '/cloudproxy/nodes/' + command_list[2])
        #    print(response.content)
            #proxy return ex. jsonify({'result': 'node does not exist', 'node_name': node_name})
            response_json = response.json()
            result = response_json["result"]
            node_name = response_json["node_name"]
            print("For node named:", node_name, ", removed status is", result)

        elif len(command_list) == 2: #NODE_NAME not provided
            print("Please provide a node name.")
        else: #too many arguments
            print("Invalid number of arguments.")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while sending the request: {e}")

    except ValueError as e:
        print(f"An error occurred while parsing the response: {e}")



#6. cloud launch PATH_TO_JOB
import os

def cloud_launch(url, command):
    try:
        command_list = command.split()
        if len(command_list) == 3: # cloud + launch + pathToFile
            #to see if file exist
            file_path = command_list[2]
            if (os.path.isfile(file_path)):
                    #pass POST command - using requests lib
                    files = {'file': open(file_path, 'rb')}
                    #proxy return ex. jsonify({'result': 'no node is available', 'job_id': job['id']})
                    response = requests.post(url + '/cloudproxy/jobs', files=files)
                    response_json = response.json()
                    result = response_json["result"]
                    job_id = response_json["job_id"]
                    print("For job launched with job id ", job_id, ", launching result: ", result)

            else:
                print(f"The specified file path '{file_path}' does not exist.")
            
        elif len(command_list) == 2: #path to job not specified
            print("Please provide the path to the job.")
        else: #too many arguments
            print("Invalid number of arguments.")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while sending the request: {e}")
        
    except ValueError as e:
        print(f"An error occurred while parsing the response: {e}")

#7. cloud abort JOB_ID
#aborts specified job
def cloud_abort(url, command):
    try:
        command_list = command.split()
        if len(command_list) == 3:
            response = requests.delete(url + '/cloudproxy/jobs/' + command_list[2])
            #proxy returns ex. jsonify({'result': result, 'job_id': job['id']})
            response_json = response.json()
            result = response_json["result"]
            job_id = response_json["job_id"]
            print("For job launched with job id ", job_id, ", abort result: ", result)

        elif len(command_list) == 2: #job id not specified
            print("Please provide the job ID.")

        else: #too many arguments
            print("Invalid number of arguments.")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while sending the request: {e}")
        
    except ValueError as e:
        print(f"An error occurred while parsing the response: {e}")

#-----------CLI Commands: monitoring purposes--------------------------------------------------------
#cloud pod ls - list all resource pods in main cluster
def cloud_pod_ls(url, command):
    try:
        #print to stdout name, id, and number of nodes
        response = requests.get(url+ '/cloudproxy/pods')
        pods = response.json()['result']
        print("Name\t\tID\tNodes")
        for pod in pods:
            print(f"{pod['name']}\t\t{pod['id']}\t{pod['nodes']}")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while sending the request: {e}")
    except ValueError as e:
        print(f"An error occurred while parsing the response: {e}")



#cloud node ls [RES_POD_ID] - list all nodes in given resource pod (if not specified, all nodes listed)
def cloud_node_ls(url, command):
    try:
        command_list = command.split()
        response = None
        if len(command_list) ==3:
             response = requests.get(f'{url}/cloudproxy/nodes')
             #print(response)
        elif len(command_list) == 4:
            pod_id = command_list[3]
            response = requests.get(f'{url}/cloudproxy/nodes/{pod_id}')
        else: #too many arguments
            print("Invalid number of arguments.")

        if response != None:
           # print(response.content)
            
           # print(response.status_code)
            nodes = response.json()
        
            if not nodes['result'][0]:
                print(nodes)
                print("No nodes to be displayed")
            elif "result" in nodes and nodes["result"] == "does not exist":
                print(f"Pod with id {pod_id} does not exist.")
            else:
               # print(nodes['result'])
                print("Name\t\t\tID\t\t\t\t\t\t\t\t\tStatus")
                for node in nodes['result'][0]:
                    print(f"{node['name']}\t\t{node['id']}\t{node['status']}")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while sending the request: {e}")
    except ValueError as e:
        print(f"An error occurred while parsing the response: {e}")

#cloud job ls [NODE_ID] list all jobs assigned to the specific node (if not specifid, all jobs by user)
def cloud_job_ls(url, command):
    try:
        response = None
        command_list = command.split()

        if len(command_list) == 3: #no node ID
             response = requests.get(f'{url}/cloudproxy/jobs')
        elif len(command_list) == 4:
            node_id = command_list[3]
            response = requests.get(f'{url}/cloudproxy/jobs/{node_id}')
        else: #too many arguments
            print("Invalid number of arguments.")

        if response != None:
            result = response.json()
            if 'result' in result and result['result'] == 'does not exist':
                print(f"Node with id {result['node_id']} does not exist.")
            elif 'result' in result:
                jobs = result['result']
                if jobs:
                    print("Name\t\tID\t\t\t\t\tNode ID\t\t\t\t\tStatus")
                    for job in jobs:
                        print(f"{job['name']}\t\t{job['id']}\t{job['node_id']}\t{job['status']}")
                else:
                    print("No jobs found.")
            # print(response.content)
           # jobs=response.json()
           # print(jobs['result'])
           # print("Name\t\tID\tNode ID\tStatus")
           # for job in jobs:
            #    print(f"{job['name']}\t\t{job['id']}\t{job['node_id']}\t{job['status']}")
    
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while sending the request: {e}")
        
    except ValueError as e:
        print(f"An error occurred while parsing the response: {e}")


#cloud job log JOB_ID - prints out specified job log
def cloud_job_log(url, command):
    try:
        command_list = command.split()
        if len(command_list) == 4:
            job_id = command_list[3]
            response = requests.get(f'{url}/cloudproxy/jobs/{job_id}/log')
            #print("response", response)
            #job not found 404
            if response.status_code == 404:
                print("Job not found, request failed.")
            else:
                log = response.json()
                if len(log)==2:
                    print(log['result'])
                else:    
                    print(log)

        elif len(command_list) == 3:
            print("Please provide the job ID.")
        else:
            print("Invalid number of arguments.")
            
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while sending the request: {e}")
        
    except ValueError as e:
        print(f"An error occurred while parsing the response: {e}")


#cloud log node NODE_ID - prints entire log file of specified node
def cloud_log_node(url, command):
    try:
        command_list = command.split()
        if len(command_list) == 4:
            node_id = command_list[3]
            response = requests.get(f'{url}/cloudproxy/nodes/{node_id}/logs')
            #node ID not found 404
            if response.status_code == 404:
                print("Node not found, request failed.")
            else:
               # print(response)
                print(response.content)
                #log = response.json()
                #print(log)

        elif len(command_list) == 3:
            print("Please provide the node ID.")
        else:
            print("Invalid number of arguments.")
            
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while sending the request: {e}")
        
    except ValueError as e:
        print(f"An error occurred while parsing the response: {e}")


def main():
    #RM url given as argument
    #rm_url = sys.argv[1]
    rm_url = 'http://10.140.17.120:5000'
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
        elif command.startswith ('cloud abort'):
            cloud_abort(rm_url, command)
         #monitoring commands   
        elif command == ('cloud pod ls'):
            cloud_pod_ls(rm_url, command)
        elif command.startswith ('cloud node ls'):
            cloud_node_ls(rm_url, command)
        elif command.startswith ('cloud job ls'):
            cloud_job_ls(rm_url, command)
        elif command.startswith ('cloud job log'):
            cloud_job_log(rm_url, command)
        elif command.startswith ('cloud log node'):
            cloud_log_node(rm_url, command)
        else:
            print("Invalid command entered! Please re-enter a valid command.")



#entry point
if __name__ == '__main__':

    main()
