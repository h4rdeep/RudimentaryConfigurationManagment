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
        stdin, stdout, stderr = ssh.exec_command(ssh_args['commands'],  get_pty=True)
    except Exception as e:
        exit(e)
    ssh_result = stdout.readlines()
    ssh_error = stderr.readlines()
    # if ssh_error: 
    #     print(ssh_error)
    return ssh_result, ssh_error

def packages(package_info,ssh_info):
    def check_package():
        ssh_info["commands"]="dpkg-query -W -f='${Status}' "+ package
        pkg_stts=command_over_ssh(ssh_info)
        pkg_status= pkg_stts[0] if bool(command_over_ssh(ssh_info)[0]) else pkg_stts[1]
        return pkg_status
    # print("package function")
    # print(ssh_info)
    # print(package_info)
    for pkg_block in package_info:
        for package in pkg_block['name']:
            if pkg_block['state'] == 'present':
                print("+++++++++ \n Installing {}\n+++++++++".format(package))
                if 'ok installed' in check_package()[0]:
                    print("'"+package + "' already installed. [Ok]")
                    break
                elif 'no packages found' in check_package()[0]:
                    ssh_info["commands"]="sudo apt-get -y install " + package

            elif pkg_block['state'] == 'absent':
                print("+++++++++ \n Removing {}\n+++++++++".format(package))
                if 'ok installed' in check_package()[0]:
                    ssh_info["commands"]="sudo apt-get -y --purge remove " + package
                elif 'no packages found' in check_package()[0]:
                    print("'"+package + "' not found. [Ok]")
                    break
                else:
                    exit(check_package())
            else:
                exit("Packages state '{}' not supported.".format(pkg_block['state']))
            # print(pkg_block['state'])
            # print(ssh_info["commands"])
            ssh_out, ssh_err=command_over_ssh(ssh_info)
            # print(ssh_err)
            if bool(ssh_err): exit(ssh_err)
            for line in ssh_out:
                print(line)

def files(file_info, ssh_info):
    print("files function")
    print(file_info)
    print(ssh_info)

def services(service_info, ssh_info):
    def check_service():
        ssh_info["commands"]="systemctl show -p SubState --value  "+ srvc
        srv_stts=command_over_ssh(ssh_info)
        # print(srv_stts)
        srv_status= srv_stts[0] if bool(command_over_ssh(ssh_info)[0]) else srv_stts[1]
        return srv_status

    for srv_block in service_info:
        for srvc in srv_block['name']:
            if srv_block['state'] == 'start':
                print("+++++++++ \n Starting {} Service\n+++++++++".format(srvc))
                if 'running' in check_service()[0]:
                    print("'"+ srvc + "' already running. [Ok]")
                    break
                elif 'dead' in check_service()[0]:
                    ssh_info["commands"]="sudo systemctl start " + srvc
                else:
                    exit("Unrecognized service state '{}' for {} service.".format(check_service()[0],srvc))

            elif srv_block['state'] == 'stop':
                print("+++++++++ \n Stopping {} Service\n+++++++++".format(srvc))
                if 'running' in check_service()[0]:
                    ssh_info["commands"]="sudo systemctl stop " + srvc
                elif 'dead' in check_service()[0]:
                    print("'"+ srvc + "' already in stopped condition. [Ok]")
                    break
                else:
                    exit("Unrecognized service state '{}' for {} service.".format(check_service()[0],srvc))
            elif srv_block['state'] == 'restart':
                print("+++++++++ \n Restarting {} Service\n+++++++++".format(srvc))
                ssh_info["commands"]="sudo systemctl restart " + srvc
            elif srv_block['state'] == 'daemon-reload':
                print("+++++++++ \n Reloading the systemctl deamon\n+++++++++")
                ssh_info["commands"]="sudo systemctl daemon-reload "
            else:
                exit("Service state '{}' not supported.".format(srv_block['state']))

            ssh_out, ssh_err=command_over_ssh(ssh_info)
            if bool(ssh_err): exit(ssh_err)
            for line in ssh_out:
                print(line)
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


        for host in play['access_details']['ip']:
            ssh_args['ip']=host
            print("Playing with {} machine".format(host))
            # print(ssh_args)
            # Update the repo cache
            ssh_args['commands']="sudo apt-get update"
            command_over_ssh(ssh_args)
            for task_name, task_config in play['config'].items():
                # print()
                # print(task_name)
                # print(task_config)
                globals()[task_name](task_config,ssh_args)
                print("_______")
            print("+++++++")

if __name__ == "__main__":
    rudimentary_cm()