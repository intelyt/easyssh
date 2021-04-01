# coding:utf-8
from easyssh import SSHConnection


class InitCentos7:

    def __init__(self, server_conf):
        self.server_conf = server_conf
        self.ssh = None
        self.connect()

    def connect(self):
        ssh = SSHConnection(**self.server_conf)
        ssh.connect()
        self.ssh = ssh

    def reconnect(self):
        self.ssh.disconnect()
        self.connect()

    def __del__(self):
        self.ssh.disconnect()

    def change_setting(self, before_command_list=None, filename=None, tag_string=None, after_command_list=None):
        if before_command_list:
            for command in before_command_list:
                self.ssh.exec_command(command)

        with self.ssh.open(filename) as f:
            if tag_string not in f.read().decode('utf-8'):
                print("start to setting {filename}".format(filename=filename))
                for command in after_command_list:
                    self.ssh.exec_command(command)
                print("end   to setting {filename}".format(filename=filename))

    def init_sshd(self):
        before_command_list = ["cat /etc/hosts.allow"]
        hosts_allow_filename = "/etc/hosts.allow"
        hosts_allow_tag_string = "###### Optimization of the sshd ======>{filename} ######".format(
            filename=hosts_allow_filename)
        hosts_allow_command = """
cat >>{hosts_allow_filename}<<EOF
{hosts_allow_tag_string}
sshd: ALL
{hosts_allow_tag_string}
EOF
        """.format(hosts_allow_filename=hosts_allow_filename, hosts_allow_tag_string=hosts_allow_tag_string)
        after_command_list = [hosts_allow_command, "service sshd restart", "cat /etc/hosts.allow"]
        self.change_setting(before_command_list=before_command_list, filename=hosts_allow_filename,
                            tag_string=hosts_allow_tag_string, after_command_list=after_command_list)

    def init_standard_software(self):
        original_yum_packages_list = self.ssh.exec_command("""yum list | sed '1d' | awk '{print $1}'""")
        software_list = ["gcc", "gcc-c++", "libstdc++-devel" "nmap", "telnet", "ping", "lsof", "tcpdump", "firewalld"]
        for software in software_list:
            if software not in original_yum_packages_list:
                command = "yum -y install %s" % software
                self.ssh.exec_command(command)

    def init_kernel_package_software(self):
        command = \
            """
            yum -y update;
            """
        result_output = self.ssh.exec_command(command)
        print(result_output)

    def init_docker(self):
        original_yum_packages_list = self.ssh.exec_command("""yum list | sed '1d' | awk '{print $1}'""")
        if "docker" not in original_yum_packages_list:
            command_list = ["yum -y install docker",
                            """echo '{"registry-mirrors":["https://mirror.ccs.tencentyun.com",
                            "http://hub-mirror.c.163.com","https://docker.mirrors.ustc.edu.cn",
                            "https://registry.docker-cn.com"]}' > /etc/docker/daemon.json;""",
                            "systemctl daemon-reload",
                            "systemctl restart docker",
                            ]
            for command in command_list:
                result_output = self.ssh.exec_command(command)
                print(result_output)

    def init_kernel_arguments(self):
        # setting /etc/sysctl.conf
        sysctl_conf_filename = "/etc/sysctl.conf"
        sysctl_tag_string = "###### Optimization of the kernel ======>{filename} ######".format(
            filename=sysctl_conf_filename)
        sysctl_command = """
cat >>{sysctl_conf_filename}<<EOF
{sysctl_tag_string}
# 设置系统内核参数优化
# 系统级限制(系统范围内所有进程可打开的文件句柄的数量限制 ---系统级别, kernel-level-----)
# 每个端口监听队列最大长度
net.core.somaxconn = 65535
# 增加系统文件描述符限制
fs.file-max = 65535
# 当网络接受速率大于内核处理速率时，允许发送到队列中的包数目
net.core.netdev_max_backlog = 65535 #
# 保持未连接的包最大数量
net.ipv4.tcp_max_syn_backlog = 65535
# 控制tcp链接等待时间 加快tcp链接回收
net.ipv4.tcp_fin_timeout = 10
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_tw_recycle = 1
# 决定tcp接受缓冲区的大小，设置大一些比较好
net.core.wmem_default = 8388608
net.core.wmem_max = 16777216
net.core.rmem_default = 8388608
net.core.rmem_max = 16777216
# 对于tcp失效链接占用系统资源的优化，加快资源回收效率
net.ipv4.tcp_keepalive_time = 120    # 链接有效时间
net.ipv4.tcp_keepalive_intvl = 30    # tcp未获得相应时重发间隔  ---
net.ipv4.tcp_keepalive_probes = 3    # 重发数量   ---
net.ipv4.tcp_timestamps = 0          # 优化tcp三次握手syn-ack
net.ipv4.tcp_mem = 94500000 915000000 927000000  # tcp内存分配,可以根据本地物理内存调试单位是Byte
net.ipv4.tcp_max_orphans = 3276800   # 最大孤儿套接字,单位个
net.ipv4.tcp_sack = 0                # tcp检测不必要的重传
net.ipv4.ip_local_port_range = 1024  65535 # tcp并发连接优化
net.ipv4.tcp_fin_timeout = 60
# 共享内存下容纳innodb缓冲池的大小
kernel.shmmax = 4294967285   # 4G 大小一般为物理内存-1byte
kernel.hung_task_timeout_secs = 0
kernel.core_pattern = /var/log/core.%st  #core文件保存位置和文件名格式
vm.swappiness = 0            # linux除非没有足够内存时才使用交换分
{sysctl_tag_string}
EOF
        """.format(sysctl_conf_filename=sysctl_conf_filename, sysctl_tag_string=sysctl_tag_string)
        sysctl_carry_out_command = "sysctl -p;"
        sysctl_command_list =[sysctl_command, sysctl_carry_out_command]
        self.change_setting(filename=sysctl_conf_filename, tag_string=sysctl_tag_string,
                            after_command_list=sysctl_command_list)

        # setting /etc/security/limits.conf
        limits_conf_filename = "/etc/security/limits.conf"
        limits_tag_string = "###### Optimization of the kernel limits ======>{filename}######".format(
            filename=limits_conf_filename)
        limits_command = """

cat >>{limits_conf_filename}<<EOF
{limits_tag_string}
* soft nofile 65535
* soft nproc  65535
* hard nofile 65535
* hard nproc  65535
{limits_tag_string}
   
        """.format(limits_conf_filename=limits_conf_filename, limits_tag_string=limits_tag_string)
        limits_command_list = [limits_command]
        self.change_setting(filename=limits_conf_filename, tag_string=limits_tag_string,
                            after_command_list=limits_command_list)

        # reconnect to refresh the result
        self.reconnect()
        limits_command_result = self.ssh.exec_command("ulimit -a")
        print(limits_command_result)

    def init_python3(self, update=False):
        original_yum_packages_list = self.ssh.exec_command("""yum list | sed '1d' | awk '{print $1}'""")
        yum_packages_list = [
            "python3",
            "zlib-devel",
            "bzip2-devel",
            "openssl-devel",
            "ncurses-devel",
            "sqlite-devel",
            "readline-devel",
            "tk-devel",
            "gdbm-devel",
            "db4-devel",
            "libpcap-devel",
            "xz-devel",
            "python-devel",
            "python3-devel",
            "mysql-devel",
        ]

        for package in yum_packages_list:
            if package not in original_yum_packages_list:
                command = "yum -y install %s " % package
                result_output = self.ssh.exec_command(command)
                print(result_output)
        self.reconnect()

        original_pip3_packages_list = self.ssh.exec_command("""pip3 list | sed '1d' | awk '{print $1 }'""").lower()
        python3_packages = "pip grequests scrapy aiohttp flask fastapi django tornado opencv-python " \
                           "opencv-contrib-python vibora jieba NLTK pandas matplotlib celery " \
                           "pymysql mysqlclient redis pymongo keras".lower().split(" ")
        for python3_package in python3_packages:
            if python3_package not in original_pip3_packages_list:
                print(python3_package)
                if update:
                    command = "pip3  install -U %s -i http://mirrors.cloud.tencent.com/pypi/simple" \
                              " --trusted-host mirrors.cloud.tencent.com " % python3_package
                else:
                    command = "pip3  install %s -i http://mirrors.cloud.tencent.com/pypi/simple" \
                              " --trusted-host mirrors.cloud.tencent.com " % python3_package
                result_output = self.ssh.exec_command(command)
                print(result_output)

    def main(self):

        self.init_sshd()
        self.init_kernel_package_software()
        self.init_kernel_arguments()
        self.init_python3()
        self.init_docker()


if __name__ == "__main__":
    server_config = {"host": "127.0.0.1", "port": 22, "username": "root", "password": "123456", "hostkey": "None"}
    i = InitCentos7(server_config)
    i.main()
