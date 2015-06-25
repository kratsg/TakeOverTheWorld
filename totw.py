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
from rootpy.plotting import Canvas, Legend, HistStack, Hist
from palettable import colorbrewer
from itertools import cycle, chain
import copy

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

def get_axis(hist, xy='x'):
  return hist.xaxis if xy=='x' else hist.yaxis

def get_min(hist, xy='x'):
  return get_axis(hist, xy).GetBinLowEdge(1)

def get_max(hist, xy='x'):
  return get_axis(hist, xy).GetBinUpEdge(get_axis(hist, xy).GetNbins())

def set_minmax(hist, config):
  for xy in ['x', 'y']:
    min_val = config.get('min', get_min(hist, xy))
    max_val = config.get('max', get_max(hist, xy))
    get_axis(hist, xy).SetRangeUser(min_val, max_val)

def set_label(hist, config):
    if isinstance(hist, HistStack):
      subhist = hist[0]
    else:
      subhist = hist
    get_axis(hist, 'x').title = config.get('xlabel', get_axis(subhist, 'x').title)
    get_axis(hist, 'y').title = config.get('ylabel', get_axis(subhist, 'y').title)

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

      configs = yaml.load(file(args.config_file))
      groups = dict([(group['name'], group) for group in configs['groups']])
      # get the plots group configuration
      plots = configs.get('plots')
      # global configurations for plots
      plots_config = plots.get('config', {})
      # all paths to plot
      plots_paths = plots.get('paths')


      hall = ph.HChain("all")
      for group in configs['groups']:
        hc = ph.HGroup(group['name'])
        for f in group['files']:
          for fname in glob.glob(f):
            hc.append(root_open(fname))
        hall.append(hc)

      set_style('ATLAS')
      for h in (h for h in hall.walk() if h.path in plots_paths):
        # get the configurations for the given path
        # this is the current path
        plots_path = plots_paths.get(h.path)

        # create new canvas
        canvasConfigs = copy.copy(plots_config.get('canvas', {}))
        canvasConfigs.update(plots_path.get('canvas', {}))
        canvas = Canvas(canvasConfigs.get('width', 500), canvasConfigs.get('height', 500))

        # create a legend (an entry for each group)
        legendConfigs = copy.copy(plots_config.get('legend', {}))
        legendConfigs.update(plots_path.get('legend', {}))
        legend = Legend(len(h), **legendConfigs)

        # set a list of colors to loop through if not set
        default_colors = cycle(colorbrewer.qualitative.Paired_10.colors)
        hists = map(lambda hgroup: hgroup.flatten, h)
        soloHists = []
        stackHists = []

        # loop over all histograms, set their styles, split them up
        for hist in hists:
          group = groups.get(hist.title)
          hist_styles = group.get('styles', {})

          # auto loop through colors
          hist_styles['color'] = hist_styles.get('color', next(default_colors))
          # decorate it
          hist.decorate(**hist_styles)

          if group.get('stack it', False):
            # overwrite with solid when stacking
            hist.fillstyle = 'solid'
            stackHists.append(hist)
          else:
            soloHists.append(hist)

          # add each hist to the legend
          legend.AddEntry(hist)#, style=group.get('legendstyle', 'F'))

        hstack = HistStack(name=h.path)
        # for some reason, this causes noticable slowdowns
        hstack.drawstyle = 'hist'
        map(hstack.Add, stackHists)

        # this is where we would set various parameters of the min, max and so on?
        # need to set things like min, max, change to log, etc for hstack and soloHists

        # cycle through all draw options and make sure we don't overwrite
        drawOptions = ["same"]*len(soloHists)
        drawOptions = cycle([''] + drawOptions)

        # draw it so we have access to the xaxis and yaxis
        if hstack:
          hstack.Draw(next(drawOptions))
          # set up axes
          set_minmax(hstack, plots_path)
          set_label(hstack, plots_path)

        for hist in soloHists:
          set_minmax(hist, plots_path)
          set_label(hist, plots_path)
          hist.Draw(next(drawOptions))

        # draw the text we need
        for text in plots.get('config', {}).get('texts', []):
          # attach the label
          label = ROOT.TText(text['x'], text['y'], text['label'])
          label.SetTextFont(text['font'])
          label.SetTextSize(text['size'])
          label.SetNDC()
          label.Draw()

        # draw and update all
        legend.Draw()
        canvas.Modified()
        canvas.Update()

        # make file_name and directories if needed
        file_name = "plots/{0:s}".format(h.path)
        print("Saving {0:s}... \r".format(file_name), end='\r')
        ensure_dir(file_name)
        for file_ext in ["root", "pdf"]:
          canvas.SaveAs("{0:s}.{1:s}".format(file_name, file_ext))
        sys.stdout.flush()
        print("Saved {0:s} successfully.".format(file_name))

        canvas.Close()

      if not args.debug:
        ROOT.gROOT.ProcessLine("gSystem->RedirectOutput(0);")

  except Exception, e:
    # stop redirecting if we crash as well
    if not args.debug:
      ROOT.gROOT.ProcessLine("gSystem->RedirectOutput(0);")

    logger.exception("{0}\nAn exception was caught!".format("-"*20))
