import subprocess
from utils import create_logger, pretty_print
import config
import json
import version
import sys
import requests
import traceback
 
logger = create_logger(config.log_file_path, __name__ , config.log_level, True)

def check():
    if config.binary_node != 'oraid':
        raise Exception("This comd is only applicapble for orai network!")
    

def workspace_CUR():
    "Directory where we currently store the blockchain data folder"
    
    return  "{}/workspace".format(config.volume_current)


def workspace_NEW():
    "irectory where we plan to store going forward the blockchain data folder"
    
    return  "{}/workspace".format(config.volume_new)


def full_path_source_data():
    "The full path to the folder to backup. Argument for the backup_script.sh"
    
    return workspace_CUR()


def modifier_binary_name():
    return config.binary_node[:-1] if config.binary_node == 'junod' else config.binary_node
    

def full_path_backup_name():
    """The full path of the backup folder. Argument for the backup_script.sh.
       The zip file create by the backup script will be stored temporarily in volumne_new
    """
    return  "{}/{}".format(config.volume_new, config.binary_node)


def home_path_CUR():
    "Path to the current blockchain datafolder"
    
    return "{}/.{}".format(workspace_CUR(), modifier_binary_name())


def home_path_NEW():
    "Path to the new blockchain datafolder"
    
    return "{}/.{}".format(workspace_NEW(), modifier_binary_name())


def backup_script(cleanup="cleanup?"):
    """ This cmd is applicable only for all networks. 
        It upload source data to the digital ocean space.
        - cleanup: true, false (default true)
            -true: the local back file will be deleted
            -false: the local back file will not be deleted.
    """

    cmd_value = ["sh {script_path} {src} {space}  {bkup} {cleanup}".format(script_path=config.backup_script_path,
                                                           space=config.digital_ocean_space,
                                                           src =full_path_source_data(),
                                                           bkup=full_path_backup_name(),
                                                           cleanup=cleanup)]
    return cmd_format(cmd_value, 'backup_script') 


def backup_script_and_delete_local_copy():
    """ run the backup scrip to upload source to digital ocean and 
        delete the local copy in the new volume.
    """
    return backup_script(cleanup="true")


def backup_script_and_keep_local_copy():
    """ run the backup scrip to upload source to digital ocean and 
        keep a local copy in the new volume.
    """
    return backup_script(cleanup="false")


def s3_download(source_file='source_file?'):
    """This cmd is applicable only for all networks.
       It download source data file from the digital ocean space. 
    """

    cmd_value = ["cd {volume_new}; s3cmd get s3://{space}/{src} {src} ; tar -xzvf {src} ; rm {src}".format(volume_new=config.volume_new,
                                                                                                    space=config.digital_ocean_space,
                                                                                                    src =source_file)]
    return cmd_format(cmd_value, 's3_download') 
    

def escape_slash(name):
    return name.replace("/", "\/")


def cmd_format(cmd_value, cmd_name):
    return {'key': cmd_value, 'name': cmd_name.upper()}


def set_home_binary_systemd_file(home_path):
    "this cmd is applicable only for juno"

    HOME_PATH_NEW = escape_slash(home_path) 
    HOME = 'HOME_' + config.binary_node.upper()
    cmd_value = ["""sed -i "s/\\"{HOME}=*.*/\\"{HOME}={HOME_PATH_NEW}\\"/" /etc/systemd/system/junod.service; sudo systemctl daemon-reload""".format(HOME=HOME,
                                                                                                                                        HOME_PATH_NEW=HOME_PATH_NEW)]
    return cmd_format(cmd_value, 'start_node_CUR')


def set_home_binary_profile_file(home_path):
    "this cmd is applicable only for juno"

    HOME_PATH = escape_slash(home_path) 
    HOME = 'HOME_' + config.binary_node.upper()
    # the cmd: "source . ~/.profile" does not work.
    # Therefore we have replaced it with an equivalent one: ". ~/.profile"
    cmd_value = ["""sed -i "s/{HOME}=*.*/{HOME}={HOME_PATH}/" ~/.profile ; . ~/.profile""".format(HOME=HOME,
                                                                             HOME_PATH=HOME_PATH)]
    return cmd_format(cmd_value, 'set_home_binary_profile_file_NEW') 


def set_home_binary_systemd_file_NEW():
    return set_home_binary_systemd_file(home_path_NEW())


def set_home_binary_profile_file_NEW():
    return set_home_binary_profile_file(home_path_NEW())
    

def set_home_binary_NEW():
    "this cmd is applicable only for juno"
    
    cmd_value = ['set_home_binary_systemd_file_NEW', 'set_home_binary_profile_file_NEW']
    return cmd_format(cmd_value, 'set_home_binary_NEW')


def set_home_binary_systemd_file_CUR():
    return set_home_binary_systemd_file(home_path_CUR())


def set_home_binary_profile_file_CUR():
    return set_home_binary_profile_file(home_path_CUR())


def set_home_binary_CUR():
    "this cmd is applicable only for juno"
    
    cmd_value = ['set_home_binary_systemd_file_CUR', 'set_home_binary_profile_file_CUR']
    return cmd_format(cmd_value, 'set_home_binary_CUR')


def start_node():
    "this cmd is applicable only for juno"
    
    cmd_value = ["sudo systemctl start {}".format(config.binary_node)]
    return cmd_format(cmd_value, 'start_node_CUR')


def _start_node(workspace):
    "this cmd is applicable only for orai"

    check()
    return "cd {}; docker-compose restart orai && docker-compose exec -d orai bash -c 'oraivisor start --p2p.pex false'".format(workspace)

    
def start_node_CUR():
    "this cmd is applicable only for orai"
    
    cmd_value = [_start_node(workspace_CUR())]
    return cmd_format(cmd_value, 'start_node_CUR')

    
def start_node_NEW():
    "this cmd is applicable only for orai"

    cmd_value = [_start_node(workspace_NEW())]
    return cmd_format(cmd_value, 'start_node_NEW')


def stop_node():
    "This cmd is applicable for all networks"

    cmd_value = "" 
    if config.binary_node == 'oraid':
        cmd_value = ["docker stop orai_node ; sleep 1s; docker rm orai_node; sleep 1s"]
    else: 
        cmd_value = ["sudo systemctl stop {}; sleep 2s".format(config.binary_node)]
    return cmd_format(cmd_value, 'stop_node')


def stop_remove_docker_container():
    "This cmd is applicable only for orai"

    check()
    cmd_value = ["docker stop orai_node ; docker rm orai_node; sleep 2s"]
    return cmd_format(cmd_value, 'stop_remove_docker_container')


def delete_priv_keys():
    "This cmd is applicable for all networks"

    node_key_file = "{}/config/node_key.json".format(home_path_CUR())
    priv_key_file = "{}/config/priv_validator_key.json".format(home_path_CUR())
    priv_key_state_file = "{}/data/priv_validator_state.json".format(home_path_CUR())
    cmd_value = ["rm -f {}; rm -f {}; rm -f {}".format(node_key_file, priv_key_file, priv_key_state_file)]
    return cmd_format(cmd_value, 'delete_priv_keys')

 
def remove_docker_container():
    "This cmd is applicable only for orai"
    
    cmd_value = ["docker rm orai_node"]
    return cmd_format(cmd_value, 'remove_docker_container')


def force_recreate_docker_container(workspace):
    "This cmd is applicable only for orai"

    return "cd {} ; docker-compose pull && docker-compose up -d --force-recreate".format(workspace)


def force_recreate_docker_container_CUR():
    "This cmd is applicable only for orai"
    
    cmd_value = [force_recreate_docker_container(workspace_CUR())]
    return cmd_format(cmd_value, 'force_recreate_docker_container_CUR')


def force_recreate_docker_container_NEW():
    "This cmd is applicable only for orai"
    
    cmd_value = [force_recreate_docker_container(workspace_NEW())]
    return cmd_format(cmd_value, 'force_recreate_docker_container_NEW')


def start_alert():
    "This cmd is applicable for all networks"

    cmd_value = ["sudo systemctl start indep_node_alarm"]
    return cmd_format(cmd_value, 'start_alert')


def stop_alert():
    "This cmd is applicable for all networks"

    cmd_value = ["sudo systemctl stop indep_node_alarm"]
    return cmd_format(cmd_value, 'stop_alert')


def start_signctrl():
    "This cmd is applicable only for all networks"

    cmd_value = ["sudo systemctl start signctrl"]
    return cmd_format(cmd_value, 'start_signctrl')


def stop_signctrl():
    "This cmd is applicable only for all networks"
    
    cmd_value = ["sudo systemctl stop signctrl"]
    return cmd_format(cmd_value, 'stop_signctrl')


def delete_signctrl_state():
    "This cmd is applicable only for all networks"

    cmd_value = ["rm -f /home/signer/.signctrl/signctrl_state.json"]
    return cmd_format(cmd_value, 'delete_signctrl_state')
    
    
def run_backup_delete_local_copy():
    "This cmd is applicable only for all networks"

    cmd_value = ['stop_node', 'stop_signctrl', 'delete_priv_keys', 'backup_script_and_delete_local_copy', 'delete_repo_outdated_files']
    return cmd_format(cmd_value, 'run_backup')


def run_backup_keep_local_copy():
    """This cmd is applicable only for all networks. 
       Create a backup and keep a local copy in the volume_new folder. 
    """
 
    cmd_value = ['stop_node', 'stop_signctrl', 'delete_priv_keys', 'backup_script_and_keep_local_copy', 'unzip_backup_file', 'delete_repo_outdated_files']
    return cmd_format(cmd_value, 'run_backup')
    

def restart_node():
    "This cmd is applicable only for juno"

    cmd_value = ['delete_signctrl_state', 'start_signctrl', 'start_node']
    return cmd_format(cmd_value, 'restart_node')

    
def restart_node_NEW():
    "This cmd is applicable for all networks "
    
    cmd_value = "" 
    if config.binary_node == 'oraid':
        cmd_value = ['delete_signctrl_state', 'start_signctrl', 'force_recreate_docker_container_NEW', 'start_node_NEW']
    else: 
        cmd_value = ['set_home_binary_NEW', 'restart_node']
    return cmd_format(cmd_value, 'restart_node_NEW')


def restart_node_CUR():
    "This cmd is applicable for all networks "
    
    if config.binary_node == 'oraid':
        cmd_value = ['delete_signctrl_state', 'start_signctrl', 'force_recreate_docker_container_CUR', 'start_node_CUR']
    else: 
        cmd_value = ['set_home_binary_CUR', 'restart_node']
    return cmd_format(cmd_value, 'restart_node_CUR')


def restart_sentry_node_NEW():
    "This cmd is applicable for all networks "
    
    cmd_value = "" 
    if config.binary_node == 'oraid':
        cmd_value = ['force_recreate_docker_container_NEW', 'start_node_NEW']
    else: 
        cmd_value = ['set_home_binary_NEW', 'start_node']
    return cmd_format(cmd_value, 'restart_node_NEW')


def restart_sentry_node_CUR():
    "This cmd is applicable for all networks "
    
    if config.binary_node == 'oraid':
        cmd_value = ['force_recreate_docker_container_CUR', 'start_node_CUR']
    else: 
        cmd_value = ['set_home_binary_CUR', 'start_node']
    return cmd_format(cmd_value, 'restart_sentry_node_CUR')


def restart_node_without_signctrl_NEW():
    "This cmd is applicable for all networks"
    
    if config.binary_node == 'oraid':
        cmd_value = ['config_node_without_signctrl_NEW', 'force_recreate_docker_container_NEW', 'start_node_NEW']
    else: 
        cmd_value = ['config_node_without_signctrl_NEW', 'restart_node_NEW']
    return cmd_format(cmd_value, 'restart_node_without_signctrl_NEW')


def restart_node_without_signctrl_CUR():
    "This cmd is applicable for all networks"
    
    if config.binary_node == 'oraid':
        cmd_value = ['config_node_without_signctrl_CUR', 'force_recreate_docker_container_CUR', 'start_node_CUR']
    else: 
        cmd_value = ['config_node_without_signctrl_CUR', 'restart_node_CUR']
    return cmd_format(cmd_value, 'restart_node_without_signctrl_CUR')


def priv_validator_laddr_config_reset(home_path):
    "This cmd is applicable for all networks"
    
    return ["""sed -i "s/^priv_validator_laddr *=.*/priv_validator_laddr = \\"\\" /" {home_path}/config/config.toml""".format(home_path=home_path)]
  

def priv_validator_laddr_config_reset_NEW():
    "This cmd is applicable for all networks"
    
    cmd_value = priv_validator_laddr_config_reset(home_path_NEW())
    return cmd_format(cmd_value, 'priv_validator_laddr_config_reset_NEW')  
 

def priv_validator_laddr_config_reset_CUR():
    "This cmd is applicable for all networks"
    
    cmd_value = priv_validator_laddr_config_reset(home_path_CUR())
    return cmd_format(cmd_value, 'priv_validator_laddr_config_reset_CUR')


def priv_validator_laddr_config_signctrl(home_path):
    "This cmd is applicable for all networks"
    
    return ["""sed -i "s/^priv_validator_laddr *=.*/priv_validator_laddr = \\"tcp:\\/\\/127.0.0.1:3000\\" /" {home_path}/config/config.toml""".format(home_path=home_path)]


def priv_validator_laddr_config_signctrl_NEW():
    "This cmd is applicable for all networks"
    
    cmd_value = priv_validator_laddr_config_signctrl(home_path_NEW())
    return cmd_format(cmd_value, 'priv_validator_laddr_config_signctrl_NEW')  
 

def priv_validator_laddr_config_signctrl_CUR():
    "This cmd is applicable for all networks"
    
    cmd_value = priv_validator_laddr_config_signctrl(home_path_CUR())
    return cmd_format(cmd_value, 'priv_validator_laddr_config_signctrl_CUR')
                                                                                                                       

def copy_priv_validator_key_to_home(home_path):
    "This cmd is applicable for all networks"
    
    return ["cp /home/signer/.signctrl/priv_validator_key.json {home_path}/config/; cp /home/signer/.signctrl/priv_validator_state.json {home_path}/data/".format(home_path=home_path)]
    
                                                                                                                           
def copy_priv_validator_key_to_home_NEW():
    "This cmd is applicable for all networks"
    
    cmd_value = copy_priv_validator_key_to_home(home_path_NEW()) 
    return cmd_format(cmd_value, 'copy_priv_validator_key_to_home_NEW')   


def copy_priv_validator_key_to_home_CUR():
    "This cmd is applicable for all networks"
    
    cmd_value = copy_priv_validator_key_to_home(home_path_CUR()) 
    return cmd_format(cmd_value, 'copy_priv_validator_key_to_home_CUR') 
                                                                                                                       

def config_node_without_signctrl_NEW():
    """This cmd is applicable for all networks.
       - Move private keys from /home/signer/.signctrl to new validator home (e.g /mn/volumne_new/workspace/.noded)
       - update the config.toml and set priv_validator_laddr = ""
    """
    
    cmd_value = ["priv_validator_laddr_config_reset_NEW", "copy_priv_validator_key_to_home_NEW"]
    return cmd_format(cmd_value, 'config_node_without_signctrl_NEW')


def config_node_without_signctrl_CUR():
    """This cmd is applicable for all networks.
       - Move private keys from /home/signer/.signctrl to new validator home (e.g /mn/volumne_cur/workspace/.noded)
       - update the config.toml and set priv_validator_laddr = ""
    """
    
    cmd_value = ["priv_validator_laddr_config_reset_CUR", "copy_priv_validator_key_to_home_CUR"]
    return cmd_format(cmd_value, 'config_node_without_signctrl_CUR')


def run_backup_and_restart_node_CUR():
    "This cmd is applicable for all networks"

    cmd_value = ['run_backup_delete_local_copy', 'restart_node_CUR']
    return cmd_format(cmd_value, 'run_backup_and_restart_node_CUR')

        
def run_backup_and_restart_node_NEW():
    "This cmd is applicable only for all network"

    cmd_value = ['run_backup_keep_local_copy', 'restart_node_NEW']
    return cmd_format(cmd_value, 'run_backup_and_restart_node_NEW')


def run_backup_and_restart_sentry_node_CUR():
    "This cmd is applicable for all networks"

    cmd_value = ['run_backup_delete_local_copy', 'restart_sentry_node_CUR']
    return cmd_format(cmd_value, 'run_backup_and_restart_sentry_node_CUR')

        
def run_backup_and_restart_sentry_node_NEW():
    "This cmd is applicable only for all network"

    cmd_value = ['run_backup_keep_local_copy', 'restart_sentry_node_NEW']
    return cmd_format(cmd_value, 'run_backup_and_restart_sentry_node_NEW')


def list_repository_files():
    cmd_value = ["s3cmd ls s3://{space}/{binary}*".format(space=config.digital_ocean_space, binary=config.binary_node)]
    return cmd_format(cmd_value, 'list_repository_files')


def delete_repo_file(file_name='file_name?'):
    cmd_value = ['s3cmd rm  s3://{space}/{file_name}'.format(space=config.digital_ocean_space, file_name=file_name)]
    return cmd_format(cmd_value, 'delete_repo_file')


def delete_repo_outdated_files():
    """ delete outdated files.
        Keep only the last two backup
    """
    
    backup_number = 2
    cmd_value = ["""numberFiles=$(s3cmd ls s3://chandrodaya/{binary}* | wc -l) ; if (($numberFiles > {backup_number} )); then s3cmd ls s3://chandrodaya/{binary}* | sort -r | tail -n $(expr $numberFiles - {backup_number}) | grep -E -o "s3://chandrodaya/.*" | while read file; do s3cmd rm $file; done; else echo "there are NO files to delete"; fi""".format(binary=config.binary_node, backup_number=backup_number )]
    return cmd_format(cmd_value, 'delete_outdate_repo_files')


def unzip_backup_file():
    """This cmd is applicable only for all networks.
    """
    cmd_value = ["""cd {volume_new}; numberFiles=$(ls | wc -l); if (($numberFiles == 1 )); then fileName=`ls ${binary}*.gz`; tar -xzvf $fileName ; rm $fileName  ; else echo "There are too many file to unzip or the folder is empty!" ;fi""".format(volume_new=config.volume_new,
                                                                                                                                                                                                                             binary=config.binary_node)]
    return cmd_format(cmd_value, 'unzip_backup_file') 

      
def EXIT():
    "This cmd is applicable only for all network"
    cmd_value = ["Exit from the program"]
    return cmd_format(cmd_value, 'EXIT') 


def display_cmd_value(cmd):
    """cmd: one of the cmd function. The output of such function is in this form:
        {cmd_keys: ...., cmd_name: ...., cmd_level:}
        
        See cmd_format fucntion.
    """
     
    cmd_func = globals()[cmd]
    cmd_value = cmd_func()['key']
    return '; '.join(cmd_value)

    
CMD_KEY_INVARIANT = [ 'EXIT', 'delete_repo_file', 's3_download', 'run_backup_and_restart_node_CUR', 'run_backup_and_restart_node_NEW',
                 'run_backup_keep_local_copy', 'run_backup_delete_local_copy', 'delete_signctrl_state',
                 'start_signctrl', 'stop_signctrl', 'start_alert',
                 'stop_alert', 'config_node_without_signctrl_NEW', 'config_node_without_signctrl_CUR',
                 'restart_node_without_signctrl_NEW', 'restart_node_without_signctrl_CUR',
                 'run_backup_and_restart_sentry_node_CUR', 'run_backup_and_restart_sentry_node_NEW']

    
def get_CMD_MAP(): 
    
    CMD_MAP = {}
    
    # common key
    cmd_keys = CMD_KEY_INVARIANT + ['stop_node', 'stop_node', 'delete_signctrl_state', 
                                    'delete_priv_keys', 'restart_node_NEW', 'restart_node_CUR', 
                                    'restart_sentry_node_NEW', 'restart_sentry_node_CUR',
                                    'list_repository_files', 'delete_repo_outdated_files',
                                    'backup_script_and_keep_local_copy', 'backup_script_and_delete_local_copy',
                                    'backup_script', 'unzip_backup_file', 'priv_validator_laddr_config_reset_NEW',
                                    'priv_validator_laddr_config_reset_CUR', 'priv_validator_laddr_config_signctrl_NEW',
                                    'priv_validator_laddr_config_signctrl_CUR', 'copy_priv_validator_key_to_home_NEW', 
                                    'copy_priv_validator_key_to_home_CUR'
                ]

    # network specific key
    if config.binary_node == 'oraid':
        cmd_keys = cmd_keys + ['start_node_CUR', 'start_node_NEW', 'remove_docker_container',
                     'force_recreate_docker_container_CUR', 'force_recreate_docker_container_NEW']
    
    else:
        cmd_keys = cmd_keys + ['start_node', 'set_home_binary_systemd_file_NEW',
                               'set_home_binary_profile_file_NEW',
                               'set_home_binary_NEW', 'set_home_binary_systemd_file_CUR',
                               'set_home_binary_profile_file_CUR',
                               'set_home_binary_CUR','restart_node'
                               ]
        

    for cmd_key in cmd_keys:
        CMD_MAP[cmd_key] = display_cmd_value(cmd_key)

    return dict(sorted(CMD_MAP.items()))


def exec_shell_recursive_cmd(cmd_key):
    cmd = globals()[cmd_key]()
    logger.info("************** START {} ***********************".format(cmd['name']))
    if len(cmd['key']) == 1 and  cmd['key'][0] not in list(get_CMD_MAP().keys()): 
        result = exec_shell_cmd(cmd['key'])
        if result != 0 :
            logger.info("************** {} FAILED! ***********************".format(cmd['name']))
            return 1 
    else:
        for _cmd_key in cmd['key']:
            result = exec_shell_recursive_cmd(_cmd_key)
            if result != 0 :
                logger.info("************** {} FAILED! ***********************".format(cmd['name']))
                return 1
             
    logger.info("************** END {} ***********************".format(cmd['name']))
    return 0

    
def exec_shell_cmd(cmd):
    "cmd: shell command to execute"
    
    result = None
    try:
        logger.info("EXEC CMD: {}".format(cmd))
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True, executable='/bin/bash')
        logger.info(result.stdout.decode())
        return result.returncode 
    except subprocess.CalledProcessError as exc:
        logger.error("\n\n********** EXEC FAIL! {}*********".format(exc.stdout.decode()))
        return (exc.returncode) 


def repl():
    while True:
        logger.info("\n********** START CMD: version={}***************\n".format(version.number))
        pretty_print(get_CMD_MAP())
        print("\nENTER A CMD_KEY:")
         
        cmd_key = input()
        if cmd_key.lower() == 'exit':
            break
          
        if cmd_key not in  list(get_CMD_MAP().keys()):
            logger.error('Invalid CMD_KEY={}! Try again.'.format(cmd_key))   
        elif cmd_key == 's3_download':
            print("ENTER source_file:")
            source_file = input()
            cmd = s3_download(source_file)
            exec_shell_cmd(cmd['key'])
        elif cmd_key == 'backup_script':
            print("ENTER cleanup (true/false):")
            cleanup = input()
            cmd = backup_script(cleanup)
            exec_shell_cmd(cmd['key'])
        elif cmd_key in ['config_node_without_signctrl_NEW', 'config_node_without_signctrl_CUR', 'restart_node_without_signctrl_NEW', 'restart_node_without_signctrl_CUR']:
            print("The above cmd is dangerous. It may cause double signing. Are you sure, you want to continue? (yes/no):")
            yes_or_no = input()
            if yes_or_no == 'yes':
                exec_shell_recursive_cmd(cmd_key)
            else:
                print('abort cmd!')
        elif cmd_key == 'delete_repo_file':
            print("ENTER file_name:")
            file_name = input()
            cmd = delete_repo_file(file_name)
            exec_shell_cmd(cmd['key'])
        else:
            exec_shell_recursive_cmd(cmd_key)


def send_msg_to_telegram(msg):
    try:
        requestURL = "https://api.telegram.org/bot" + str(config.telegram_token) + "/sendMessage?chat_id=" + config.telegram_chat_id + "&text="
        requestURL = requestURL + str(msg)
        requests.get(requestURL, timeout=1)
    except Exception:
        error_msg = traceback.format_exc()
        logger.error(error_msg)

       
if __name__ == "__main__":    
    nr_args = len(sys.argv)
    if nr_args == 1:
        repl()
    elif nr_args == 2:
        cmd_key = sys.argv[1]    
        if cmd_key not in  list(get_CMD_MAP().keys()):
            logger.error('Invalid cmd_key={}! Try again.'.format(cmd_key))
        else:
            res = exec_shell_recursive_cmd(cmd_key)
            msg = "{}: {}".format(cmd_key.upper(), 'PASS' if res == 0 else 'FAIL')    
            send_msg_to_telegram(msg)
    else:
        logger.error('Too many arguments!')