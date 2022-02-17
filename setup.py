"""setup.py
python setup.py sdist
twine upload --repository pypitest dist/osagentcoreclient-x.x.x.tar.gz
twine upload --repository pypi dist/osagentcoreclient-x.x.x.tar.gz
"""
from setuptools import setup, find_packages
from osagentcoreclient import __version__ as version
from setuptools import setup, find_packages

try:
    with open('README.md', 'r') as f:
        long_description = f.read()
except IOError:
    long_description = ''

setup(
    name='osagentcoreclient',
    packages=find_packages(),
    version=version,
    description='AgentCore Client library for building Oversight probes',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Cesbit',
    author_email='info@cesbit.com',
    url='https://github.com/oversight-monitoring/osagentcoreclient',
    download_url=(
        'https://github.com/oversight-monitoring/'
        'osagentcoreclient/tarball/v{}'.format(version)),
    keywords=['parser', 'grammar', 'autocompletion'],
    classifiers=[
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing :: Linguistic'
    ],
)
