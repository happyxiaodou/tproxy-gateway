#!/usr/bin/python3

import base64
import os
import platform
import socket
import subprocess
import time
import urllib.parse

import cli_print as cp
import common_patterns
import requests


class SSR:
    def __init__(self):
        self._server = None
        self._port = None
        self._method = None
        self._password = None
        self._protocol = None
        self._proto_param = None
        self._obfs = None
        self._obfs_param = None

        self._remarks = None
        self._group = None

        self._local_address = None
        self._local_port = None
        self._path_to_ssr_conf = None

        self._exit_ip = None

        self._cmd = None
        self._cmd_prefix = None
        self._sub_progress = None
        pass

    def __reset_attributes(self):
        self._server = ''
        self._port = 443
        self._method = ''
        self._password = ''
        self._protocol = 'origin'
        self._proto_param = None
        self._obfs = 'plain'
        self._obfs_param = None

        self._remarks = None
        self._group = None

        self._local_address = None
        self._local_port = None
        self._path_to_ssr_conf = None

        self._exit_ip = None

    @property
    def server(self):
        return self._server

    @property
    def port(self):
        return self._port

    @property
    def method(self):
        return self._method

    @property
    def password(self):
        return self._password

    @property
    def protocol(self):
        return self._protocol

    @property
    def proto_param(self):
        return self._proto_param or ''

    @property
    def obfs(self):
        return self._obfs

    @property
    def obfs_param(self):
        return self._obfs_param or ''

    @property
    def remarks(self):
        return self._remarks or ''

    @remarks.setter
    def remarks(self, value: str):
        self._remarks = value

    @property
    def group(self):
        return self._group or ''

    @group.setter
    def group(self, value: str):
        self._group = value

    @property
    def local_address(self):
        return self._local_address or '0.0.0.0'

    @local_address.setter
    def local_address(self, value: str):
        self._local_address = value

    @property
    def local_port(self):
        return self._local_port

    @local_port.setter
    def local_port(self, value: int):
        self._local_port = value

    @property
    def path_to_ssr_conf(self):
        return self._path_to_ssr_conf

    @property
    def exit_ip(self):
        return self._exit_ip

    @property
    def exit_country(self):
        if self._exit_ip:
            return self._exit_ip['country']
        return None

    @property
    def exit_country_code(self):
        if self._exit_ip:
            return self._exit_ip['country_code']
        return None

    @property
    def invalid_attributes(self):
        keys = [
            'server',
            'port',
            'method',
            'password',
            'protocol',
            'obfs',
        ]

        for key in keys:
            if not getattr(self, key):
                cp.error('Attribute `{}` is invalid.'.format(key))
                return True
        return False

    def load(self, obj):
        self.__reset_attributes()

        keys = {
            'server': '',
            'port': 443,
            'method': '',
            'password': '',
            'protocol': 'origin',
            'proto_param': None,
            'obfs': 'plain',
            'obfs_param': None,

            'remarks': None,
            'group': None,
        }

        for key, value in keys.items():
            setattr(self, '_{}'.format(key), getattr(obj, key, value))

    def set(self,
            server: str = '',
            port: int = 443,
            method: str = '',
            password: str = '',
            protocol: str = 'origin',
            proto_param: str = '',
            obfs: str = 'plain',
            obfs_param: str = '',

            remarks: str = None,
            group: str = None,
            ):
        self.__reset_attributes()

        self._server = server
        self._port = port
        self._method = method
        self._password = password
        self._protocol = protocol
        self._proto_param = proto_param
        self._obfs = obfs
        self._obfs_param = obfs_param

        if remarks:
            self._remarks = remarks
        if group:
            self._group = group

    @property
    def config(self):
        if self.invalid_attributes:
            return None

        return {
            'server': self._server,
            'port': self._port,
            'method': self._method,
            'password': self._password,
            'protocol': self._protocol,
            'proto_param': self._proto_param,
            'obfs': self._obfs,
            'obfs_param': self._obfs_param,

            'remarks': self.remarks,
            'group': self.group,
        }

    @property
    def url(self):
        # check attributes
        if self.invalid_attributes:
            return None

        prefix = '{server}:{port}:{protocol}:{method}:{obfs}:{password}'.format(
            server=self._server,
            port=self._port,
            protocol=self._protocol,
            method=self._method,
            obfs=self._obfs,
            password=encode(self._password, urlsafe=True))

        suffix_list = []
        if self._proto_param:
            suffix_list.append('protoparam={proto_param}'.format(
                proto_param=encode(self.proto_param, urlsafe=True),
            ))

        if self._obfs_param:
            suffix_list.append('obfsparam={obfs_param}'.format(
                obfs_param=encode(self.obfs_param, urlsafe=True),
            ))

        suffix_list.append('remarks={remarks}'.format(
            remarks=encode(self.remarks, urlsafe=True),
        ))

        suffix_list.append('group={group}'.format(
            group=encode(self.group, urlsafe=True),
        ))

        return 'ssr://{}'.format(encode('{prefix}/?{suffix}'.format(
            prefix=prefix,
            suffix='&'.join(suffix_list),
        ), urlsafe=True))

    @url.setter
    def url(self, url: str):
        self.__reset_attributes()

        r = url.split('://')

        try:
            if r[0] == 'ssr':
                self.__parse_ssr(r[1])
            elif r[0] == 'ss':
                self.__parse_ss(r[1])
        except Exception as e:
            cp.error(e)
            pass

    def __parse_ssr(self, ssr_base64: str):
        ssr = ssr_base64.split('#')[0]
        ssr = decode(ssr)

        if isinstance(ssr, bytes):
            return

        ssr_list = ssr.split(':')
        password_and_params = ssr_list[5].split('/?')

        self._server = ssr_list[0]
        self._port = int(ssr_list[1])
        self._protocol = ssr_list[2]
        self._method = ssr_list[3]
        self._obfs = ssr_list[4]
        self._password = decode(password_and_params[0])

        params_dict = dict()
        for param in password_and_params[1].split('&'):
            param_list = param.split('=')
            params_dict[param_list[0]] = decode(param_list[1])

        params_dict_keys = params_dict.keys()
        for key in ['proto_param', 'obfs_param', 'remarks', 'group']:
            tmp_key = key.replace('_', '')
            if tmp_key in params_dict_keys:
                setattr(self, '_{}'.format(key), params_dict[tmp_key])

    def __parse_ss(self, ss_base64: str):
        ss = ss_base64.split('#')
        if len(ss) > 1:
            self._remarks = urllib.parse.unquote(ss[1])
        ss = decode(ss[0])

        if isinstance(ss, bytes):
            return

        # use split and join, in case of the password contains "@"/":"
        str_list = ss.split('@')

        server_and_port = str_list[-1].split(':')
        method_and_pass = '@'.join(str_list[0:-1]).split(':')

        self._server = server_and_port[0]
        self._port = int(server_and_port[1])
        self._method = method_and_pass[0]
        self._password = ':'.join(method_and_pass[1:])

    @property
    def plain(self):
        # check attributes
        if self.invalid_attributes:
            return None

        return '     server: {server}\n' \
               '       port: {port}\n' \
               '     method: {method}\n' \
               '   password: {password}\n' \
               '   protocol: {protocol}\n' \
               'proto_param: {proto_param}\n' \
               '       obfs: {obfs}\n' \
               ' obfs_param: {obfs_param}\n' \
               '    remarks: {remarks}\n' \
               '      group: {group}'.format(server=self.server,
                                             port=self.port,
                                             method=self.method,
                                             password=self.password,
                                             protocol=self.protocol,
                                             proto_param=self.proto_param,
                                             obfs=self.obfs,
                                             obfs_param=self.obfs_param,
                                             remarks=self.remarks,
                                             group=self.group,
                                             )

    @property
    def config_json_string(self):
        return self.get_config_json_string()

    def get_config_json_string(self):
        # check attributes
        if self.invalid_attributes:
            return None

        configs = list()

        configs.append('"server": "{}",'.format(self.server))
        configs.append('"server_port": {},'.format(self.port))
        configs.append('"method": "{}",'.format(self.method))
        configs.append('"password": "{}",'.format(self.password))
        configs.append('"protocol": "{}",'.format(self.protocol))
        configs.append('"protocol_param": "{}",'.format(self.proto_param))
        configs.append('"obfs": "{}",'.format(self.obfs))
        configs.append('"obfs_param": "{}",'.format(self.obfs_param))
        configs.append('"local_address": "{}",'.format(self.local_address))
        configs.append('"local_port": {}'.format(self.local_port))

        return '{\n' + '\n'.join(configs) + '\n}'

    def write_config_file(self, path_to_file=None, plain_to_console: bool = False):
        # check attributes
        if self.invalid_attributes:
            return None

        if path_to_file:
            self._path_to_ssr_conf = path_to_file

        cp.about_to('生成配置文件', self.path_to_ssr_conf, 'for shadowsocksr')
        with open(self.path_to_ssr_conf, 'wb') as f:
            json_string = self.get_config_json_string()
            f.write(json_string.encode('utf-8'))
            cp.success()
            if plain_to_console:
                cp.plain_text(json_string)

    def __remove_ssr_conf(self):
        cp.about_to('Deleting', self.path_to_ssr_conf, 'config file')
        os.remove(self.path_to_ssr_conf)
        cp.success()


def get_urls_by_subscribe(url: str):
    headers = {
        'User-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/71.0.3578.80 '
                      'Safari/537.36'
    }
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return get_urls_by_base64(resp.text)
    return list()


def encode(s, urlsafe: bool = False):
    if isinstance(s, str):
        s = s.encode('utf-8')
    if urlsafe:
        return base64.urlsafe_b64encode(s).decode('utf-8')
    return base64.b64encode(s).decode('utf-8')


def decode(s):
    if isinstance(s, str):
        if len(s) % 4 > 0:
            s = s + '=' * (4 - len(s) % 4)
        s = s.encode('utf-8')
    s = s.translate(bytes.maketrans(b'-_', b'+/'))
    try:
        return base64.b64decode(s).decode('utf-8')
    except UnicodeDecodeError:
        return base64.b64decode(s)


def remove(source: list, els=None):
    r = []
    if els is None:
        els = ['', None]
    elif not isinstance(els, list):
        els = [els]

    for el in source:
        if el not in els:
            r.append(el)
    return r


def unique(source: list):
    r = []
    for el in source:
        if el not in r:
            r.append(el)
    return r


def remove_and_unique(source: list, els=None):
    r = unique(remove(source=source, els=els))
    return r


def get_urls_by_base64(text_base64: str):
    text = decode(text_base64)
    if isinstance(text, str):
        return remove_and_unique(text.split('\n'))
    return list()


def get_urls_by_string(string: str):
    return unique(common_patterns.findall_ssr_urls(string=string))


def ping(host):
    ping_str = "-n 1" if platform.system().lower() == "windows" else "-c 1"
    args = "ping " + " " + ping_str + " " + host
    need_sh = False if platform.system().lower() == "windows" else True
    return subprocess.call(args, shell=need_sh) == 0


def connect_time(host):
    try:
        host = socket.gethostbyname(host)
        before = time.perf_counter()
        s = socket.create_connection((host, 80), 2)
        after = time.perf_counter()
        return after - before
    except:
        return 10000


def write_server_file(path_to_file: str, plain_to_console: str):
    with open(path_to_file, 'wb') as f:
        f.write(plain_to_console.encode('utf-8'))


def sub_file(url: str):
    urls = get_urls_by_subscribe(url)
    small = 1000
    proxy_server = ""
    fastSSR = SSR()
    ssrObject = SSR()
    for url in urls:
        ssrObject.url = url
        response = connect_time(ssrObject.server)
        if response != 10000:
            proxy_server = proxy_server + " " + ssrObject.server
        if small > response:
            fastSSR.url = url
            small = response
        cp.about_to("测试服务器速度", ssrObject.server, response)
    cp.about_to("当前选择最快的服务为", ssrObject.remarks)
    fastSSR.local_port = "0.0.0.0"
    fastSSR.local_port = 60080
    fastSSR.write_config_file("/etc/ss-tproxy/ssr-config.json")
    write_server_file("/etc/ss-tproxy/proxy_server", proxy_server)


def ssr_file(url: str):
    fastSSR = SSR()
    fastSSR.url = url
    fastSSR.local_address = "0.0.0.0"
    fastSSR.local_port = 60080
    fastSSR.write_config_file("/etc/ss-tproxy/ssr-config.json")
    write_server_file("/etc/ss-tproxy/proxy_server", fastSSR.server)


def main():
    if "SUB_URL" in os.environ:
        cp.about_to("获取到 sub订阅号", os.environ.get("SUB_URL"))
        sub_file(os.environ.get("SUB_URL"))
        return
    if "SSR_URL" in os.environ:
        cp.about_to("获取到 ssr服务器地址", os.environ.get("SSR_URL"))
        ssr_file(os.environ.get("SSR_URL"))
        return
    cp.error("无法获取服务配置参数 SUB_URL  SSR_URL ")



if __name__ == '__main__':
    main()
