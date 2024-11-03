#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name="EndpointsMonitor",
    packages=find_packages(),
    version="1.0",
    description="A python script that monitors endpoints in JavaScript files.",
    long_description=open("README.md").read(),
    author="dd060606",
    url='https://github.com/dd060606/Endpoints-Monitor',
    py_modules=["endpoints-monitor"],
    install_requires=["requests" ,"beautifulsoup4"]
)