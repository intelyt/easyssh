# a package to take the place of ansible, saltstack 
- 

## Install dependency packages
- pip install paramiko


## example

```
from easyssh import SSHConnection

server = {"host": "127.0.0.1", "port": 22, "username": "root", "password": "123456", "hostkey": "None"}
# initialize an ssh instance
ssh = SSHConnection(**server)
# connect to the server
ssh.connect()
# Execute the command
pwd = ssh.exec_command("pwd")
print(pwd)
# rename or move a path
rename(self, oldPath, newPath)
# upload folder
uploadFolder(self, localFolder, remoteFolder):
# download folder
downloadFolder(self, remoteFolder, localFolder):


# disconnect to the server
ssh.disconnect()
```



