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
    install_requires=[
        "cltl.backend[impl,host,service]",
        "cltl.asr[impl,service]",
        "cltl.vad[impl,service]",
        "cltl.chat-ui",
        "cltl.g2ky[impl,service]",
        "cltl.leolani",
        "cltl.emissor-data[impl,service,client]",
        "cltl.brain[service]",
        "cltl.triple_extraction[service]",
        "cltl.reply_generation[service]",
        "cltl.mention-detection[service]",
        "cltl.emotion-detection[service]",
        "cltl.dialogueclassification[service]",
        "flask",
        "werkzeug"
    ],
    entry_points={
        'leolani': [ 'leolani = app:main']
    }
)
