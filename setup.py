from setuptools import setup, find_packages

setup(
    name='insight_tools',
    version='0.1',
    description='Python tools that came out of our experience',
    author='Insight-by-Team',
    author_email='?',
    url='https://github.com/Insight-by-Team',
    packages=find_packages(),
    install_requires=[
        'numpy'
    ],
    setup_requires=['pytest-runner', 'numpy'],
    tests_require=['pytest']
)
