import os
import glob
import subprocess
import sys
import progressbar
from time import sleep


# These are here just for testing, the app asks for path when starting it
#local_path = "/home/andreas/Desktop/testfolder/"
#remote_path = "/ida/xx/xx/testfolder/"


def readall(local, remote):
    """ read local and remote filedirs. Save results on a list"""
    print("Reading local and remote disks for files...")
    local_list = []
    remote_list = []

    l_dir = local
    r_dir = remote

    try:
        if os.path.exists(l_dir):
            l_dir = os.listdir(l_dir)
            l_dir.sort()
        else:
            print("Local directory not found, check directory path!")
            sys.exit()
    except OSError as e:
        print("Error, could not read local disk, reason:\n" + e)
    # read IDA r_dir content
    command = 'ils ' + r_dir
    try:
        handle = os.popen(command)
        line = handle.read().split('\n')
        for line in line:
            line = line.strip()
            remote_list.append(line)
        # remove first line from IDA dir, which just shows the dir path
        remote_list.sort()
        remote_list.pop(0)
        remote_list.pop(0)
        handle.close()
    except (ConnectionError, IndexError) as e:
        if str(e) == "pop from empty list":
            print("Error, could not read remote disk for files,\ncheck remote directory path or check internet connection!")
            sys.exit()
        else:
            print("Error: " + str(e))
            sys.exit()

    return l_dir, remote_list


def comparison(local, remote, local_path, remote_path):
    """ run comparison between lists and get a differential list"""
    print("File comparison for local and remote directories... (this might take a while)")
    missing_list = []
    mismatch_list = []
    l, r = local, remote

    # remove extra files found in the directories specified
    l = [x for x in l if 'VLF' in x]
    r = [x for x in r if 'VLF' in x]

    bar = progressbar.ProgressBar()
    for l_item in bar(l):
        try:
            sleep(0.02)
            local_item_size = os.path.getsize(local_path+l_item)
            if l_item not in r:
                missing_list.append(l_item)
            else:
                # if file found, check that the filesize matches
                command = """iquest \"SELECT DATA_SIZE WHERE COLL_NAME = '""" + remote_path[0:-1] + "\' AND DATA_NAME = '""" + l_item + "\'\""
                handle = os.popen(command)
                remote_item_size = handle.read().split()[2]
                if int(remote_item_size) != local_item_size:
                    missing_list.append(l_item)
                    mismatch_list.append(l_item)
        except (IndexError, KeyboardInterrupt) as e:
            if KeyboardInterrupt:
                print("\nUser aborted file check!")
                sys.exit()
            else:
                print("Error, connection most probably failed during the check!")
                print(str(e))
                sys.exit()
    print("\nCheck Completed.")
    if mismatch_list:
        print("Files found with mismatched sizes: \n")
        for i in mismatch_list:
            print(i)
    if not missing_list:
        print("There is nothing to send, all files match on remote and local directories!")
        sys.exit()

    return missing_list


def send(missing_list, local_path, remote_path):
    """ use differential list to select files that are to be sent to IDA"""
    print('\nStarting upload for files...')
    m_list = missing_list
    sent_list = []
    if not missing_list:
        print("Nothing to send! App closing in 3secs...")
        sys.exit()
    else:
        bar = progressbar.ProgressBar()
        for line in bar(m_list):
            sleep(0.02)
            try:
                error_string = "USER_SOCK_CONNECT_TIMEDOUT"

                command = 'iput -rfv ' + local_path + line + ' ' + remote_path
                output1 = subprocess.getoutput([command])
                sleep(5)
                # for debugging
                # print("subprocess output: " + output1 + "\n")
                if error_string in output1:
                    # if error in sending, try again couple of times
                    print("Error in sending file: " + line + ' reason: ' + error_string)
                    print("Trying to resend file...")
                    try:
                        # try to resend file 5 times MAX!
                        sent = False
                        attempt = 0
                        sleep(1)
                        while not sent:
                            attempt = attempt + 1
                            output2 = subprocess.getoutput([command])
                            if error_string in output2:
                                print("\nAttempt: " + str(attempt) + "/5  FAILED! Attempting again...")
                                sent = False
                            else:
                                print("Re-sent file: " + line + " successfully!\nContinuing file transfers..\n")
                                sent = True
                                sent_list.append(line)
                            if attempt == 5:
                                print("Failed to send file"
                                      + line + " , ""run app again later to send missing files!")
                                break
                        else:
                            pass
                    except (ConnectionError, KeyboardInterrupt) as e:
                        if KeyboardInterrupt:
                            print("User interrupted transfer!")
                            break
                        else:
                            print("ERROR ERROR: " + str(e))
                            break
                sent_list.append(line)
            except (BrokenPipeError, KeyboardInterrupt) as e:
                if KeyboardInterrupt:
                    print("User interrupted transfer!")
                    break
                else:
                    print(e)
                    break
        else:
            print('All files sent!')
            print("Here's a full list of sent items: \n ")
            for line in sent_list:
                if sent_list:
                    print(line)
                else:
                    print('Nothing was sent!')


def finalCheck():
    """ do a final check, to determine that all files
        are sent and both locations dirs are mirrors of each others """


def main():
    """ takes local location and remote location for file dirs as parameters """
    # ask for directory data

    local_path = input("Give local path to data: (ie. /home/user/data)\n")
    remote_path = input("Give remote path to data: (ie. /ida/oy/sgo/data/...\n")

    print("This is an app for easy transfer of data to IDA\n"
          "Made by Andreas\n")
    print("\nPrefix: This programs does not create the inital connection to IDA!\n"
          "        Manually set connection to IDA with the 'iinit' command\n"
          "        (IDA (irods) connection requires username and password to IDA services.\n")

    if local_path:
        local_dir, remote_dir = readall(local_path, remote_path)
    else:
        print("You did not set local directory!")
    compare = comparison(local_dir, remote_dir, local_path, remote_path)
    send_files = send(compare, local_path, remote_path)


if __name__ == '__main__':
    main()
