#!/bin/python
import json, sys
import time
import paramiko

def command_over_ssh(ssh_args, mode="ssh"):
        # time.sleep(2)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_port= ssh_args['port'] if 'port' in ssh_args else 22
        try:
            if 'pass' in ssh_args:
                ssh.connect(ssh_args['ip'], ssh_port, ssh_args['username'], ssh_args['pass'])
            elif 'ssh_key' in ssh_args:
                ssh.connect(ssh_args['ip'], ssh_port, ssh_args['username'],  key_filename=ssh_args['ssh_key'])
            if mode=="ssh":
                stdin, stdout, stderr = ssh.exec_command(ssh_args['commands'],  get_pty=True)
            elif mode=="scp":
                ftp_client=ssh.open_sftp()
                file_name=ssh_args["source_file"].split("/")[-1]
                stdout = ftp_client.put(ssh_args["source_file"],"/tmp/"+file_name)
                ftp_client.close()  
        except Exception as e:
            print("exception occured")
            exit(e)
        try:
            ssh_result = stdout.readlines()
            ssh_error = stderr.readlines()
        except AttributeError as e:
            ssh_result = stdout
            ssh_error = []
        if ssh_error:
            print("SSH Error {}:".format(ssh_error))
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
            validate_package=check_package()
            if pkg_block['state'] == 'present':
                print("+++++++++ \n Installing {}\n+++++++++".format(package))
                if 'ok installed' in validate_package[0]:
                    print("'"+package + "' already installed. [Ok]")
                    continue
                elif 'no packages found' in validate_package[0]:
                    ssh_info["commands"]="sudo apt-get -y install " + package

            elif pkg_block['state'] == 'absent':
                print("+++++++++ \n Removing {}\n+++++++++".format(package))
                if 'ok installed' in validate_package[0]:
                    ssh_info["commands"]="sudo apt-get -y --purge remove " + package
                elif 'no packages found' in validate_package[0]:
                    print("'"+package + "' not found. [Ok]")
                    continue
                else:
                    exit(validate_package)
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
    print(len(file_info))
    def check_files():
        ssh_info['commands']="diff -qs /tmp/"+ ssh_info['source_file'].split('/')[-1] +" "+ssh_info['destination_file']
        file_stts=command_over_ssh(ssh_info)
        file_status= file_stts[0] if bool(command_over_ssh(ssh_info)[0]) else file_stts[1]
        print(file_status)
        return file_status
    for file_block in file_info:
        print(file_block)
        ssh_info["destination_file"]=file_block["destination"]
        if file_block["state"]=='copy':
            print("+++++++++ \n Moving Files: {}\n+++++++++".format(file_block["source"]))
            ssh_info["source_file"]=file_block["source"]
            ssh_info["file_mode"]=file_block["mode"]
            ssh_info["file_owner"]=file_block["owner"]
            ssh_info["file_group"]=file_block["group"] if 'group' in file_block else  file_block["owner"]
            file_transfer=command_over_ssh(ssh_info,'scp')
            print(file_transfer)
            file_check=check_files()
            if 'identical' in file_check[0]:
                print("'"+file_block["source"] + "' and '"+ file_block["destination"] +"' are identical. [Ok]")
                continue
            elif 'differ' in file_check[0] or 'No such file' in file_check[0]:
                print("different")
                print(file_block["name"])
                if 'No such file' in file_check[0]:
                    ssh_info['commands']="sudo touch "+ ssh_info['destination_file']
                    # ssh_info['commands']="sudo cp /tmp/"+ file_block["name"] +" "+ ssh_info['destination_file']
                    create_file=command_over_ssh(ssh_info)
                    # print(create_file)
                ssh_info['commands']="sudo chmod 777 "+ ssh_info['destination_file']
                change_permission=command_over_ssh(ssh_info)
                ssh_info['commands']="sudo cat /tmp/"+ file_block["name"] +" > "+ ssh_info['destination_file']
                copy_content=command_over_ssh(ssh_info)
                print("copy_content: {}".format(copy_content))
                if "Permission denied" in copy_content:
                    exit(copy_content[0])
                ssh_info["commands"]="sudo chown "+ ssh_info["file_owner"] + ":" + ssh_info["file_owner"]+" "+  ssh_info['destination_file'] +"; sudo chmod "+ ssh_info["file_mode"]+" "+ssh_info['destination_file']
                file_perm=command_over_ssh(ssh_info)
                print(file_perm)
        elif file_block["state"]=='absent':
            print("+++++++++ \n Delete remote Files: {}\n+++++++++".format(file_block["destination"]))
            ssh_info['commands']="sudo chmod 777 "+ ssh_info['destination_file']
            perm_file=command_over_ssh(ssh_info)
            ssh_info['commands']="sudo rm -f "+ ssh_info['destination_file']
            del_file=command_over_ssh(ssh_info)




        

def services(service_info, ssh_info):
    def check_service():
        ssh_info["commands"]="systemctl show -p SubState --value  "+ srvc
        srv_stts=command_over_ssh(ssh_info)
        # print(srv_stts)
        srv_status= srv_stts[0] if bool(command_over_ssh(ssh_info)[0]) else srv_stts[1]
        return srv_status

    for srv_block in service_info:
        for srvc in srv_block['name']:
            validate_service=check_service()
            if srv_block['state'] == 'start':
                print("+++++++++ \n Starting {} Service\n+++++++++".format(srvc))
                if 'running' in validate_service[0]:
                    print("'"+ srvc + "' already running. [Ok]")
                    continue
                elif 'dead' in validate_service[0]:
                    ssh_info["commands"]="sudo systemctl start " + srvc
                else:
                    exit("Unrecognized service state '{}' for {} service.".format(validate_service[0],srvc))

            elif srv_block['state'] == 'stop':
                print("+++++++++ \n Stopping {} Service\n+++++++++".format(srvc))
                if 'running' in validate_service[0]:
                    ssh_info["commands"]="sudo systemctl stop " + srvc
                elif 'dead' in validate_service[0]:
                    print("'"+ srvc + "' already in stopped condition. [Ok]")
                    continue
                else:
                    exit("Unrecognized service state '{}' for {} service.".format(validate_service[0],srvc))
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
    # play_file=sys.argv[1]
    play_file = "playbook.json"
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