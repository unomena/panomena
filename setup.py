from setuptools import setup, find_packages

setup(
    name='panya',
    version='0.1.5.unomena.1',
    description='Panya base app.',
    long_description = open('README.rst', 'r').read() + open('AUTHORS.rst', 'r').read() + open('CHANGELOG.rst', 'r').read(),
    author='Praekelt Foundation',
    author_email='dev@praekelt.com',
    license='BSD',
    url='http://github.com/praekelt/panya',
    packages = find_packages(),
    dependency_links = [
        'http://dist.plone.org/thirdparty/',
        'http://github.com/praekelt/django-photologue/tarball/2.6.praekelt#egg=django-photologue-2.6.praekelt',
        'http://github.com/unomena/django-cache-machine/tarball/master#egg=django-cache-machine-0.4.1.unomena',
    ],
    install_requires = [
        'PIL',
        'django-category',
        'django-photologue==2.6.praekelt',
        'django-publisher',
        'django-secretballot',
        'python-memcached==1.47',
        'django-cache-machine==0.4.1.unomena',
        'django-reversion==1.3.2',
    ],
    include_package_data=True,
    classifiers = [
        "Programming Language :: Python",
        "License :: OSI Approved :: BSD License",
        "Development Status :: 4 - Beta",
        "Operating System :: OS Independent",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    zip_safe=False,
)
