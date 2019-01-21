from setuptools import setup

setup(
    name='holman',
    packages=['holman'],
    install_requires=[
        'gatt>=0.2.7'
    ],
    version='0.1.0',
    description='Holman SDK for Python on Linux',
    keywords='holman',
    url='https://github.com/scottmckenzie/holman-linux-python',
    download_url='https://github.com/scottmckenzie/holman-linux-python/archive/0.1.0.tar.gz',
    author='Scott McKenzie',
    author_email='developers@noizyland.net',
    license='MIT',
    py_modules=['holmanctl'],
    entry_points={
        'console_scripts': ['holmanctl = holmanctl:main']
    }
)
