"""
    Setup file for p2psc.
    Use setup.cfg to configure your project.
"""

from setuptools import setup

setup(
    name='p2psc',
    version='0.1.0',    
    description='A example Python package',
    url='https://github.com/bontric/p2psc',
    author='Benedikt Wieder',
    packages=['p2psc', 'p2psc.common'],
    install_requires=['python-osc',
                      'zeroconf',
                      ],
    entry_points={
        'console_scripts': [
            'p2psc = p2psc.main:run',
        ],
    }
)
