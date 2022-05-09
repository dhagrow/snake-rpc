import io
import os
import glob
import shutil
import contextlib

from .. import logs
from .. import utils
from .. import Service, command, param

log = logs.get(__name__)

CHUNK_SIZE = io.DEFAULT_BUFFER_SIZE

class FileService(Service):
    """Provides file access commands"""
    _name_ = 'file'

    @param('root_path', doc='root path for all file operations')
    @param('safe_root', bool,
        doc='ensures that no file operation escapes the root path')
    @param('chunk_size', int, default=CHUNK_SIZE,
        doc='size of data to buffer when reading')
    def __init__(self, root_path=None, safe_root=True, chunk_size=None):
        self.root_path = root_path or os.getcwd()
        self.safe_root = safe_root
        self.chunk_size = chunk_size or CHUNK_SIZE

    @property
    def root_path(self):
        return self._root_path

    @root_path.setter
    def root_path(self, root_path):
        # expand/normalize
        path = os.path.expandvars(os.path.expanduser(root_path))
        path = os.path.abspath(os.path.normpath(path))
        # we join '' to ensure a trailing slash
        # this protects against some path traversals at the
        # startswith(root_path) check
        self._root_path = os.path.join(path, '')

    @command(with_metadata='bool')
    def paths(self, pattern=None, with_metadata=False):
        """Iterates over path names matching the recursive glob *pattern*.

        Extended glob syntax is supported, so e.g. "**/*" can be used for
        recursion.

        If *with_metadata* is `True`, this command returns tuples of path
        metadata: `(path, file_size, modified_time, is_file)`.

        Only the path will be set in the tuple if the metadata cannot be read.
        """
        pattern = self.check_path(pattern or '*')
        if os.path.isdir(pattern):
            # match all files if pattern is a dir
            pattern = os.path.join(pattern, '*')

        for name in glob.iglob(pattern):
            if isinstance(name, bytes): # python 2
                name = name.decode('utf8')

            path = (os.path.relpath(name, self.root_path)
                if self.safe_root else name)
            if path == '.':
                continue

            if not with_metadata:
                yield path
                continue

            entry = {'path': path}

            try:
                stat = os.stat(name)
                isfile = os.path.isfile(name)

                entry.update(
                    size=stat.st_size,
                    mtime=stat.st_mtime,
                    isfile=isfile,
                    )
            except OSError as e:
                log.warning('could not read file: %s', e)
                entry.update(entry.fromkeys(['size', 'mtime', 'isfile']))

            yield utils.encoding.to_unicode(entry, dict_keys_only=True)

    @command()
    def touch(self, path):
        """Creates or updates the timestamps of a file at *path*."""
        path = self.check_path(path)
        with open(path, 'a'):
            os.utime(path, None)

    @command(recurse='bool')
    def create_dir(self, path, mode=None, recurse=False):
        """Create a directory at *path*.

        *mode* sets the directory permissions in octal (default: 755).

        If *recurse* is `True` existing directories will be ignored, and
        non-existing directories will be created as needed.

        Raises any exceptions that occur.
        """
        path = self.check_path(path)
        mode = 0o755 if mode is None else int(mode, 8)
        if recurse:
            utils.path.ensure_dirs(path, mode)
        else:
            os.mkdir(path, mode)

    @command(recurse='bool')
    def delete(self, path, recurse=False):
        """Deletes the file at *path*.

        If *recurse* is `True`, all children will also be deleted, including
        non-empty directories.

        Raises any exceptions that occur.
        """
        path = self.check_path(path)
        if os.path.isdir(path):
            if recurse:
                shutil.rmtree(path)
            else:
                os.rmdir(path)
        else:
            os.remove(path)

    @param('src', 'stream')
    @param('dst_path', doc='the remote path to upload to')
    @command()
    def upload(self, src, dst_path):
        """Uploads a file to the remote interface"""
        # first check access to the file
        path = self.check_path(dst_path)

        with open(path, 'wb') as fp:
            for chunk in src:
                fp.write(chunk)

            # ensure data is written to disk
            fp.flush()
            os.fsync(fp.fileno())

            log.info('%s bytes uploaded: %s', fp.tell(), path)

        # return the path that was used
        return self.sanitize_path(path)

    @param('src_path', doc='the remote path to download from')
    @command()
    def download(self, src_path):
        """Downloads a file from the remote interface"""
        # check access to the file
        path = self.check_path(src_path)

        with open(path, 'rb') as fp:
            for chunk in utils.path.iter_file(fp, self.chunk_size):
                yield chunk

            log.info('%s bytes downloaded: %s', fp.tell(), path)

    @command()
    def size(self, path):
        """Returns the contents of the file at *path*."""
        with self.sanitize_errors():
            path = self.check_path(path)
            return os.stat(path).st_size

    ## utils ##

    @contextlib.contextmanager
    def sanitize_errors(self):
        try:
            yield
        except OSError as e:
            e.filename = self.sanitize_path(e.filename)
            raise e

    def sanitize_path(self, path, root_path=None):
        """Returns only the public portion of the path.

        If `FileService.safe_root` is `False`, then just return the *path*
        """
        if not self.safe_root:
            return path
        return os.path.relpath(path, root_path or self.root_path)

    def check_path(self, path, root_path=None):
        """Ensures that *path* is a child of *root_path*.

        Returns *path* joined to *root_path*.

        If `FileService.safe_root` is `False`, the home dir (`~`) and
        environment variables will be expanded. Otherwise, an
        `IOError("Permission denied")` is thrown if the path does not resolve
        to a child of *root_path*.

        If *root_path* is not set, `FileService.root_path` will be used (CWD
        by default).
        """
        path = path or '.'
        root_path = root_path or self.root_path

        if not self.safe_root:
            path = os.path.expandvars(os.path.expanduser(path))
            return os.path.join(root_path, path)

        if not root_path:
            # user would have to manually set to null to get here
            raise ValueError('safe_root is enabled, but no root_path is set')

        # parent dir traversal is prohibited in safe_root mode
        if '..' in path:
            raise IOError("Permission denied: '{}'".format(path))

        # absolute path
        abs_path = os.path.join(root_path, path)

        # path has to start with root
        if not abs_path.startswith(root_path):
            raise IOError("Permission denied: '{}'".format(path))

        return abs_path
