#!/usr/bin/env python

# @file:    totw.py
# @purpose: make a shitload of pretty plots
# @author:  Giordon Stark <gstark@cern.ch>
# @date:    June 2015
#

# __future__ imports must occur at beginning of file
# redirect python output using the newer print function with file description
#   print(string, f=fd)
from __future__ import print_function
# used to redirect ROOT output
#   see http://stackoverflow.com/questions/21541238/get-ipython-doesnt-work-in-a-startup-script-for-ipython-ipython-notebook
import tempfile

import os, sys
# grab the stdout and have python write to this instead
# ROOT will write to the original stdout
STDOUT = os.fdopen(os.dup(sys.stdout.fileno()), 'w')

# for logging, set it up
import logging
root_logger = logging.getLogger()
root_logger.addHandler(logging.StreamHandler(STDOUT))
logger = logging.getLogger("totw")

# import all libraries
import argparse
import subprocess
import glob
import yaml

'''
  with tempfile.NamedTemporaryFile() as tmpFile:
    if not args.debug:
      ROOT.gSystem.RedirectOutput(tmpFile.name, "w")

    # execute code here

    if not args.debug:
      ROOT.gROOT.ProcessLine("gSystem->RedirectOutput(0);")
'''

# Set up ROOT
import ROOT

#root_numpy
import numpy as np
import root_numpy as rnp
import rootpy as rpy
import matplotlib.pyplot as pl
from rootpy.io import root_open
from rootpy.plotting.style import set_style
from rootpy.plotting import Canvas, Legend, HistStack
from palettable import colorbrewer

import plotHelpers as ph

def format_arg_value(arg_val):
  """ Return a string representing a (name, value) pair.

  >>> format_arg_value(('x', (1, 2, 3)))
  'x=(1, 2, 3)'
  """
  arg, val = arg_val
  return "%s=%r" % (arg, val)

# http://wordaligned.org/articles/echo
def echo(*echoargs, **echokwargs):
  logger.debug(echoargs)
  logger.debug(echokwargs)
  def echo_wrap(fn):
    """ Echo calls to a function.

    Returns a decorated version of the input function which "echoes" calls
    made to it by writing out the function's name and the arguments it was
    called with.
    """

    # Unpack function's arg count, arg names, arg defaults
    code = fn.func_code
    argcount = code.co_argcount
    argnames = code.co_varnames[:argcount]
    fn_defaults = fn.func_defaults or list()
    argdefs = dict(zip(argnames[-len(fn_defaults):], fn_defaults))

    def wrapped(*v, **k):
      # Collect function arguments by chaining together positional,
      # defaulted, extra positional and keyword arguments.
      positional = map(format_arg_value, zip(argnames, v))
      defaulted = [format_arg_value((a, argdefs[a]))
                   for a in argnames[len(v):] if a not in k]
      nameless = map(repr, v[argcount:])
      keyword = map(format_arg_value, k.items())
      args = positional + defaulted + nameless + keyword
      write("%s(%s)\n" % (fn.__name__, ", ".join(args)))
      return fn(*v, **k)
    return wrapped

  write = echokwargs.get('write', sys.stdout.write)
  if len(echoargs) == 1 and callable(echoargs[0]):
    return echo_wrap(echoargs[0])
  return echo_wrap

#@echo(write=logger.debug)
def do_totw(args):
  pass

def ensure_dir(f):
    d = os.path.dirname(f)
    if not os.path.exists(d):
        os.makedirs(d)

if __name__ == "__main__":
  class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter):
    pass

  __version__ = subprocess.check_output(["git", "describe", "--always"], cwd=os.path.dirname(os.path.realpath(__file__))).strip()
  __short_hash__ = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=os.path.dirname(os.path.realpath(__file__))).strip()

  parser = argparse.ArgumentParser(description='Author: Giordon Stark. v.{0}'.format(__version__),
                                   formatter_class=lambda prog: CustomFormatter(prog, max_help_position=30))

  # general arguments for all
  parser.add_argument('-v','--verbose', dest='verbose', action='count', default=0, help='Enable verbose output of various levels. Use --debug to enable output for debugging.')
  parser.add_argument('--debug', dest='debug', action='store_true', help='Enable ROOT output and full-on debugging. Use this if you need to debug the application.')
  parser.add_argument('-b', '--batch', dest='batch_mode', action='store_true', help='Enable batch mode for ROOT.')

  parser.add_argument('--config', required=True, type=str, dest='config_file', metavar='<file.yml>', help='YAML file specifying input files and asssociated names')

  # parse the arguments, throw errors if missing any
  args = parser.parse_args()

  try:
    # start execution of actual program
    import timing

    # set verbosity for python printing
    if args.verbose < 5:
      logger.setLevel(25 - args.verbose*5)
    else:
      logger.setLevel(logging.NOTSET + 1)

    with tempfile.NamedTemporaryFile() as tmpFile:
      if not args.debug:
        ROOT.gSystem.RedirectOutput(tmpFile.name, "w")

      # if flag is shown, set batch_mode to true, else false
      ROOT.gROOT.SetBatch(args.batch_mode)

      # do stuff here
      logger.info("Hello world")

      configs = yaml.load(file(args.config_file))
      hall = ph.HChain("all")
      for group in configs['groups']:
        hc = ph.HGroup(group)
        for f in configs['groups'][group]['files']:
          for fname in glob.glob(f):
            hc.append(root_open(fname))
        hall.append(hc)

      #import pdb; pdb.set_trace()

      set_style('ATLAS')
      for h in hall.walk():
        # get the configurations for the given path
        config = configs['styles'].get(h.path, {})
        # create new canvas
        canvas = Canvas(config.get('canvas width', 700), config.get('canvas height', 500))

        # create a legend (an entry for each group)
        legend = Legend(len(h), leftmargin = 0.3, topmargin = 0.025, rightmargin = 0.01, textsize = 15, entrysep=0.02, entryheight=0.03)

        colors = colorbrewer.qualitative.Paired_10.colors

        hists = map(lambda hgroup: hgroup.flatten, h)
        soloHists = []
        stackHists = []
        for hist, color in zip(hists, colors):
          setattr(hist, 'color', color)
          setattr(hist, 'fillstyle', 'solid')
        for hist in hists:
          if configs['groups'][hist.title].get('stack', False) == True:
            stackHists.append(hist)
          else:
            soloHists.append(hist)

        # add each hist to the legend
        for hist in hists:
          legend.AddEntry(hist, style='F')

        hstack = HistStack(name=h.path)
        map(hstack.Add, stackHists)

        # draw it so we have access to the xaxis and yaxis
        hstack.Draw(config.get('drawoptions', 'hist'))
        for hist in soloHists:
          hist.Draw("same {0:s}".format(config.get('drawoptions', 'hist')))

        # set up axes
        hstack.xaxis.SetTitle(config.get('xlabel', ''))
        #hstack.xaxis.SetRangeUser(config.get('xmin', hstack.xaxis.GetXmin()), config.get('xmax', hstack.xaxis.GetXmax()))
        hstack.yaxis.SetTitle(config.get('ylabel', 'counts'))
        #hstack.yaxis.SetRangeUser(config.get('ymin', hstack.yaxis.GetXmin()), config.get('ymax', hstack.yaxis.GetXmax()))

        # attach the ATLAS label
        label = ROOT.TText(0.3, 0.85, 'ATLAS')
        label.SetTextFont(73)
        label.SetTextSize(25)
        label.SetNDC()
        label.Draw()

        # attach the internal label
        label2 = ROOT.TText(0.425, 0.85, 'Internal')
        label2.SetTextFont(43)
        label2.SetTextSize(25)
        label2.SetNDC()
        label2.Draw()

        # draw and update all
        legend.Draw()
        canvas.Modified()
        canvas.Update()

        # make file_name and directories if needed
        file_name = "plots/{0:s}".format(h.path)
        ensure_dir(file_name)
        for file_ext in ["root", "pdf"]:
          canvas.SaveAs("{0:s}.{1:s}".format(file_name, file_ext))

      #hc.all
      #hc.all.jets

      if not args.debug:
        ROOT.gROOT.ProcessLine("gSystem->RedirectOutput(0);")

  except Exception, e:
    # stop redirecting if we crash as well
    if not args.debug:
      ROOT.gROOT.ProcessLine("gSystem->RedirectOutput(0);")

    logger.exception("{0}\nAn exception was caught!".format("-"*20))
