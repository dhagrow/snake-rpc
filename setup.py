import os
from setuptools import setup, find_packages

def get_version():
    path = os.path.join(os.path.dirname(__file__), 'snekrpc/__init__.py')
    with open(path) as f:
        for line in f:
            if line.startswith('__version__'):
                return line.split('=')[1].strip().strip("'")
        return '0.0.0'

def get_readme():
    with open('README.md') as f:
        return f.read()

setup(
    name='snekrpc',
    version=get_version(),
    url='https://github.com/dhagrow/snekrpc',
    author='Miguel Turner',
    author_email='cymrow@gmail.com',
    description='A Python RPC library for prototyping.',
    long_description=get_readme(),
    long_description_content_type='text/markdown',
    packages=find_packages(exclude=['test']),
    entry_points={
        'console_scripts': [
            'snekrpc=snekrpc.__main__:main',
            'snekrpc-pack=snekrpc.pack:main',
            ],
    },
    install_requires=[
        'msgpack',
        'temporenc',
        ],
    )
