from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("VERSION", "r") as fh:
    version = fh.read().strip()

setup(
    name='cltl.leolani-app',
    version=version,
    package_dir={'': 'py-app'},
    packages=find_packages(include=['*'], where='py-app'),
    data_files=[('VERSION', ['VERSION'])],
    url="https://github.com/leolani/cltl-leolani-app",
    license='MIT License',
    author='CLTL',
    author_email='t.baier@vu.nl',
    description='Leolani app',
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires='>=3.8',
    install_requires=[],
    entry_points={
        'leolani': [ 'leolani = app:main']
    }
)
