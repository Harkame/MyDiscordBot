from setuptools import setup, find_packages

with open('README.rst', 'r') as fh:
    long_description = fh.read()

setup(
    name='mydiscordbot',
    version='0.0.1',
    author='Harkame',
    description='Custom discord bot',
    long_description=long_description,
    url='https://github.com/Harkame/MyDiscordBot',
    packages=find_packages(),
    classifiers=[
        'discord',
        'bot',
    ],
)
