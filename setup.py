#! /usr/bin/env python
from setuptools import setup

setup(name='audioled',
      version='0.1',
      description='MOLECOLE - A Modular LED Controller Workstation',
      url='http://github.com/scottlawsonbc/audio-reactive-led-strip',
      author='Sebastian Halder',
      author_email='',
      license='MIT',
      packages=['audioled'],
      zip_safe=False,
      include_package_data=True,
      install_requires=[
          'numpy',
          'pyaudio'
      ])
