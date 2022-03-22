from setuptools import setup

with open('../README.rst','rb') as f:
    long_description = f.read().decode('utf-8')

setup(
    name='pinas',
    version='1.0',
    description='Expression evaluation sandbox',
    long_description=long_description,
    url='https://github.com/AndersMunch/pinas',
    author='Anders Munch',
    author_email='ajm@flonidan.dk',
    license='MIT',
    py_modules=['pinas'],
    classifiers=[
        # 'Development Status :: 5 - Production/Stable',
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        ],
    keywords='sandbox eval',
)