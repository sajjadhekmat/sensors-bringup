from glob import glob
import os

from setuptools import find_packages, setup

package_name = 'sensors_bringup'

setup(
    name=package_name,
    version='0.0.0',

    packages=find_packages(exclude=['test']),

    data_files=[
        (
            'share/ament_index/resource_index/packages',
            ['resource/' + package_name]
        ),
        (
            'share/' + package_name,
            ['package.xml']
        ),
        (
            os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')
        ),
    ],

    install_requires=['setuptools'],
    zip_safe=True,

    maintainer='lasigerobot24',
    maintainer_email='shekmat@fc.ul.pt',

    description='Bringup package for tactile and force-torque sensors',
    license='TODO: License declaration',

    extras_require={
        'test': [
            'pytest',
        ],
    },

    entry_points={
        'console_scripts': [
            'sensor_status = sensors_bringup.sensor_status:main',
        ],
    },
)
