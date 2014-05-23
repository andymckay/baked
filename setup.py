from setuptools import setup


setup(
    name='baked',
    version='0.2',
    description='Import order detection',
    long_description=open('README.rst').read(),
    author='Andy McKay',
    author_email='andym@mozilla.com',
    license='BSD',
    url='https://github.com/andymckay/baked',
    py_modules=['baked'],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'baked = baked:main'
        ]
    },
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
    ]
)
