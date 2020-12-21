from setuptools import setup, find_namespace_packages

install_requires = [
    'GitPython', 'tensorboardX', 'matplotlib', 'wandb', 'fabric', 'cloudpickle', 'jax', 'torch'
]

setup(
    name='experiment_buddy',
    version='0.0.1',
    packages=find_namespace_packages(
        where='experiment_buddy/',
        include=['experiment_buddy.*'],
        exclude=["*.tests", "*.tests.*", "tests.*", "tests"]
    ),
    url='github.com/ministry-of-silly-code/experiment_buddy/',
    license='',
    author='Ionelia Buzatu, Manuel Del Verme',
    maintainer='Manuel Del Verme, Ionelia Buzatu',
    author_email='',
    description='',
    install_requires=install_requires,
)