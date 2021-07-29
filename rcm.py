#!/bin/python
import json, sys
import paramiko

def command_over_ssh(ssh_args):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_port= ssh_args['port'] if 'port' in ssh_args else 22
    try:
        if 'pass' in ssh_args:
            ssh.connect(ssh_args['ip'], ssh_port, ssh_args['username'], ssh_args['pass'])
        elif 'ssh_key' in ssh_args:
            ssh.connect(ssh_args['ip'], ssh_port, ssh_args['username'],  key_filename=ssh_args['ssh_key'])
        stdin, stdout, stderr = ssh.exec_command(ssh_args['commands'])
    except paramiko.ssh_exception.AuthenticationException as e:
        exit(e)
    ssh_result = stdout.readlines()
    ssh_error = stderr.readlines()
    ssh_error = stderr.readlines()
    return ssh_result 

def packages(package_info,ssh_info):
    print("package function")
    print(ssh_info)
    print(package_info)
 
def files(file_info, ssh_info):
    print("files function")
    print(file_info)
    print(ssh_info)

def rudimentary_cm():
    ssh_args={}
    play_file=sys.argv[1]
    playbook=open(play_file)
    play_data=json.load(playbook)
    for play in play_data:
        ssh_args['username']=play['access_details']['user']
        ssh_args['port']=2222
        if 'keypair' in play['access_details']:
            ssh_args['ssh_key']=play['access_details']['keypair']
        else:
            ssh_args['pass']=play['access_details']['password']  

        ssh_args['commands']="sudo apt-get install apache3; echo $?"

        for host in play['access_details']['ip']:
            ssh_args['ip']=host
            print(ssh_args)
            print(command_over_ssh(ssh_args))
            for task_name, task_config in play['config'].items():
                print()
                print(task_name)
                # print(task_config)
                globals()[task_name](task_config,ssh_args)
                print("_______")
            print("+++++++")

if __name__ == "__main__":
    rudimentary_cm()