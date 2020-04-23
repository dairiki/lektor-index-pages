import ast
import io
import re

from setuptools import setup

with io.open('README.md', 'rt', encoding="utf8") as f:
    readme = f.read()

_description_re = re.compile(r'description\s+=\s+(?P<description>.*)')

with open('lektor_index_pages/plugin.py', 'rb') as f:
    description = str(ast.literal_eval(_description_re.search(
        f.read().decode('utf-8')).group(1)))

setup(
    author='Jeff Dairiki',
    author_email='dairiki@dairiki.org',
    description=description,
    keywords='Lektor plugin',
    license='MIT',
    long_description=readme,
    long_description_content_type='text/markdown',
    name='lektor-index-pages',
    packages=['lektor_index_pages'],
    # url='[link to your repository]',
    version='0.1',
    install_requires=[
        'more-itertools',
        'lektorlib',
        ],
    classifiers=[
        'Framework :: Lektor',
        'Environment :: Plugins',
        ],
    entry_points={
        'lektor.plugins': [
            'index-pages = lektor_index_pages:IndexPagesPlugin',
            ]
        }
    )
