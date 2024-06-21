from setuptools import setup, find_packages

setup(
    name='pyflow_manager',
    version='0.2.3',
    packages=find_packages(),
    install_requires=[
        'pyyaml',
        'networkx',
    ],
    extras_require={
        'dev': ['pytest'],
    },
    entry_points={
        'console_scripts': [
            'pyflow-manager = pyflow_manager.pyflow_manager:main',
        ],
    },
    author='Huzeyfe Ayaz',
    author_email='huzeyfeayaz23@gmail.com',
    description='A workflow management system based on YAML dependencies',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/HuzeyfeAyaz/pyflow_manager',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
