from setuptools import setup

setup(name='bpndtrustar',
    version='1.0.1',
    python_requires='>3.5.2',
    description='command line client for interacting with Trustar TIP',
    url='https://github.com/trbpnd/bpndtrustar',
    author='Evan Dygert',
    author_email='evand@dygertconsulting.com',
    license='MIT',
    packages=['bpndtrustar'],
    entry_points = {
        'console_scripts': ['bpndtrustar=bpndtrustar.bpndtrustar:main'],
    },
    install_requires=[
            'trustar',
            'argparse',
            'requests'
          ],
    zip_safe=False)
