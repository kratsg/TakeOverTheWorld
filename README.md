# TakeOverTheWorld - A PyRoot Codebase

This contains a collection of useful python macros for making plots from ROOT files containing histograms. Primarily, this will be biased towards output from [kratsg/TheAccountant](https://github.com/kratsg/TheAccountant).

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Major Dependencies](#major-dependencies)
- [Quick Start](#quick-start)
  - [Installing](#installing)
    - [Using virtual environment](#using-virtual-environment)
    - [Without using virtual environment](#without-using-virtual-environment)
  - [Using](#using)
  - [Profiling Code](#profiling-code)
- [Documentation](#documentation)
- [Authors](#authors)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->


## Major Dependencies
 - [PyROOT](https://root.cern.ch/drupal/content/pyroot) (which technically requires ROOT)
 - [numpy](http://www.numpy.org/)
 - [root\_numpy](http://rootpy.github.io/root_numpy/)
 - [rootpy](http://rootpy.github.io/rootpy/)

All other dependencies are listed in [requirements.txt](requirements.txt) and can be installed in one line with `pip install -r requirements.txt`.

## Quick Start

tl;dr - copy and paste, and off you go.

### Installing

#### Using virtual environment

I use [`virtualenvwrapper`](https://virtualenvwrapper.readthedocs.org/en/latest/) to manage my python dependencies and workspace. I assume you have `pip`.

```bash
pip install virtualenvwrapper
echo "source /usr/local/bin/virtualenvwrapper.sh" >> ~/.bash_profile
source ~/.bash_profile
mkvirtualenv ROOT
workon ROOT
git clone git@github.com:kratsg/TakeOverTheWorld
cd TakeOverTheWorld
pip install -r requirements.txt
python totw.py -h
```

Start a new environment with `mkvirtualenv NameOfEnv` and everytime you open a new shell, you just need to type `workon NameOfEnv`. Type `workon` alone to see a list of environments you've created already. Read the [virtualenvwrapper docs](https://virtualenvwrapper.readthedocs.org/en/latest/) for more information.

#### Without using virtual environment

```bash
git clone git@github.com:kratsg/TakeOverTheWorld
cd TakeOverTheWorld
pip install -r requirements.txt
python totw.py -h
```

### Using

### Profiling Code

This is one of those pieces of python code we always want to run as fast as possible. TakeOverTheWorld should not take long. To figure out those dead-ends, I use [snakeviz](https://jiffyclub.github.io/snakeviz/). The `requirements.txt` file contains this dependency. To run it, I first profile the code by running it:

```bash
python -m cProfile -o profiler.log totw.py
```

then I use the `snakeviz` script to help me visualize this

```bash
snakeviz profiler.log
```

and I'm good to go.

## Documentation

## Authors
- [Giordon Stark](https://github.com/kratsg)
