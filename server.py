import os
import owncloud
import tempfile


from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from pyftpdlib.filesystems import AbstractedFS


ftp_username = os.environ['FTP_USERNAME']
ftp_password = os.environ['FTP_PASSWORD']

owncloud_url = os.environ['OWNCLOUD_URL']
owncloud_username = os.environ['OWNCLOUD_USERNAME']
owncloud_password = os.environ['OWNCLOUD_PASSWORD']
owncloud_basedir = os.environ['OWNCLOUD_BASEDIR']

oc = owncloud.Client(owncloud_url)
oc.login(owncloud_username, owncloud_password)


class OCFD():
    def __init__(self, name, file_info, mode):
        self.closed = False
        self.file_info = file_info
        self.name = name
        self.filename = name
        self.mode = mode

        self.temp_file_path = None
        self.temp_file = None

        if 'r' in self.mode:
            return
        else:  # write
            self.temp_file_path = tempfile.mkstemp()[1]
            self.temp_file = open(self.temp_file_path, 'wb')

    def write(self, data):
        if 'r' in self.mode:
            raise OSError(1, 'Operation not permitted')
        self.temp_file.write(data)

    def close(self):
        if 'r' in self.mode:
            return
        self.temp_file.close()
        fn = os.path.basename(self.name)
        try:
            oc.put_file(owncloud_basedir+fn, self.temp_file_path)
        except Exception as e:
            print(e)
            return

        os.remove(self.temp_file_path)
        self.temp_file_path = None
        self.temp_file = None

    def read(self, size=65536):
        if self.f.is_dir():
            return

    def seek(self, *kargs, **kwargs):
        raise OSError(1, 'Operation not permitted')


class OCFS(AbstractedFS):
    def __init__(self, root, cmd_channel):
        super().__init__(root, cmd_channel)

    def stat(self, path):
        st_size = 0
        st_mode = 600
        f = oc.file_info(path)

        if f.is_dir():
            st_mode = st_mode | 40600
        else:
            st_size = f.get_size()
        return os.stat_result([st_mode, 0, 0, 0, 0, 0, st_size, 0, 0, 0])

    def open(self, filename, mode):
        try:
            file_info = oc.file_info(filename)

            if file_info.is_dir():
                self.cwd = file_info.path
                return
            return OCFD(filename, file_info, mode)
        except Exception as e:
            return OCFD(filename, None, mode)

    def listdir(self, path):
        res = [f.path for f in oc.list(owncloud_basedir)]
        return res


def pre_flight_check():
    try:
        f = oc.file_info(owncloud_basedir)
        if not f.is_dir:
            raise Exception(f'Owncloud basedir {owncloud_basedir} not found')
    except owncloud.HTTPResponseError:
        raise Exception(f'Owncloud basedir {owncloud_basedir} not found')


def run():
    authorizer = DummyAuthorizer()
    authorizer.add_user(ftp_username, ftp_password, '/tmp', perm='elradfmwM')
    handler = FTPHandler
    handler.authorizer = authorizer
    handler.abstracted_fs = OCFS

    address = ('', 21)
    server = FTPServer(address, handler)
    server.max_cons = 256
    server.max_cons_per_ip = 10

    pre_flight_check()
    print(f'owncloud basedir: {owncloud_basedir}')

    server.serve_forever()


if __name__ == '__main__':
    run()
