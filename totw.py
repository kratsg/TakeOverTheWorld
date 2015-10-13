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
from rootpy.plotting.style import set_style, get_style
from rootpy.plotting import Canvas, Legend, HistStack, Hist, Pad
from rootpy.plotting.hist import _Hist
from palettable import colorbrewer
from itertools import cycle, chain
import copy
import re

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

def set_minmax(hist, config):
  for xy in ['x', 'y']:
    min_val = config.get('%smin' % xy, None)
    max_val = config.get('%smax' % xy, None)
    if min_val is not None and max_val is not None:
      if isinstance(hist, HistStack) and xy == 'y':
        hist.SetMaximum(max_val)
        hist.SetMinimum(min_val)
      else:
        get_axis(hist, xy).SetRangeUser(min_val, max_val)

def set_label(hist, config):
    if isinstance(hist, HistStack):
      subhist = hist[0]
    else:
      subhist = hist
    get_axis(hist, 'x').title = config.get('xlabel', get_axis(subhist, 'x').title)
    get_axis(hist, 'y').title = config.get('ylabel', get_axis(subhist, 'y').title)
    xtitleoffset = config.get('xtitleoffset', None)
    ytitleoffset = config.get('ytitleoffset', None)
    if xtitleoffset:
      get_axis(hist, 'x').SetTitleOffset(xtitleoffset)
    if ytitleoffset:
      get_axis(hist, 'y').SetTitleOffset(ytitleoffset)

did_regex = re.compile('(\d{6,8})')
def get_did(hist):
  if not isinstance(hist, _Hist):
    raise TypeError("Must pass in a rootpy Hist object")
  m = did_regex.search(hist.get_directory().get_file().name)
  if m is None:
    raise ValueError("%s is not a valid filename")
  return m.groups()[0]

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
  parser.add_argument('--weights', required=True, type=str, dest='weights_file', metavar='<file.yml>', help='YAML file specifying the weights by dataset id')

  parser.add_argument('-i', '--input', dest='topLevel', type=str, help='Top level directory containing plots.', default='all')

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
      # get the weights configurations for scaling
      weights = yaml.load(file(args.weights_file))
      # global configurations for plots
      plots_config = plots.get('config', {})
      # all paths to plot
      plots_paths = plots.get('paths')

      hall = ph.HChain(args.topLevel)
      for group in configs['groups']:
        hc = ph.HGroup(group['name'])
        logger.log(25, "Group: {0:s}".format(group['name']))
        for f in group['files']:
          logger.log(25, "\tPattern: {0:s}".format(f))
          for fname in glob.glob(f):
            logger.log(25, "\t\tAdding {0:s}".format(fname))
            rootFile = root_open(fname)
            hc.append(rootFile)
        if len(hc) == 0:
          raise ValueError("{0:s} has no files loaded.".format(group['name']))
        logger.log(25, "\tAdding {0:s}".format(hc))
        hall.append(hc)

      set_style('ATLAS')
      for h in (h for h in hall.walk() if h.path in plots_paths):#hall.walk()
        # get the configurations for the given path
        # this is the current path

        # continue going up in the path until we find a non-empty dict
        plots_path = None
        topLevelPath = h.path
        while True:
          # non-empty dict, so break
          if plots_paths.get(topLevelPath, {}):
            break
          topLevelPath = os.path.dirname(topLevelPath)
          # top level path empty so break
          if not topLevelPath:
            break
        plots_path = plots_paths.get(topLevelPath, {})

        # create new canvas
        canvasConfigs = copy.copy(plots_config.get('canvas', {}))
        canvasConfigs.update(plots_path.get('canvas', {}))
        canvas = Canvas(canvasConfigs.get('width', 500), canvasConfigs.get('height', 500))

        canvas.SetRightMargin(canvasConfigs.get('rightmargin', 0.1))
        canvas.SetBottomMargin(canvasConfigs.get('bottommargin', 0.2))
        canvas.SetLeftMargin(canvasConfigs.get('leftmargin', 0.2))

        if canvasConfigs.get('logy', False) == True:
          canvas.set_logy()

        # create a legend (an entry for each group)
        legendConfigs = copy.copy(plots_config.get('legend', {}))
        legendConfigs.update(plots_path.get('legend', {}))
        legend = Legend(len(h), **legendConfigs)

        # scale the histograms before doing anything else
        for hgroup in h:
          if groups.get(hgroup.group).get('do not scale me', False):
            logger.info("Skipping %s for scaling" % hgroup.group)
            continue
          for hist in hgroup:
            # scale the histograms, look up weights by did
            did = get_did(hist)
            weight = weights.get(did)
            if weight is None:
              raise KeyError("Could not find the weights for did=%s" % did)
            scaleFactor = 1.0
            scaleFactor /= weight.get('num events')
            scaleFactor *= weight.get('cross section')
            scaleFactor *= weight.get('filter efficiency')
            scaleFactor *= weight.get('k-factor')
            scaleFactor *= weights.get('global_luminosity')*1000
            hist.scale(scaleFactor)
            logger.info("Scale factor for %s: %0.6f" % (did, scaleFactor))

        # set a list of colors to loop through if not set
        default_colors = cycle(colorbrewer.qualitative.Paired_10.colors)
        hists = map(lambda hgroup: hgroup.flatten, h)
        soloHists = []
        stackHists = []

        # loop over all histograms, set their styles, split them up, scale if need
        for hist in hists:
          group = groups.get(hist.title)
          hist_styles = group.get('styles', {})

          # auto loop through colors
          hist_styles['color'] = hist_styles.get('color', next(default_colors))
          # decorate it
          hist.decorate(**hist_styles)

          # set axis
          get_axis(hist, 'x').SetNdivisions(canvasConfigs.get('ndivisions', 1))

          # add each hist to the legend
          legend.AddEntry(hist)#, style=group.get('legendstyle', 'F'))

          # rebin?
          rebin = plots_path.get('rebin', plots_config.get('rebin', None))
          if rebin is not None:
            hist.rebin(rebin)

          # exclusion, so we don't need to plot it
          if hist.title in plots_path.get('exclude', []): continue
          if group.get('stack it', False):
            # overwrite with solid when stacking
            hist.fillstyle = 'solid'
            stackHists.append(hist)
          else:
            soloHists.append(hist)


        hstack = HistStack(name=h.path)
        # for some reason, this causes noticable slowdowns
        hstack.drawstyle = 'hist'
        map(hstack.Add, stackHists)

        # this is where we would set various parameters of the min, max and so on?
        # need to set things like min, max, change to log, etc for hstack and soloHists
        normalizeTo = plots_path.get('normalize', plots_config.get('normalize', None))
        if normalizeTo is not None:
          dataScale = 0.
          if normalizeTo not in [hist.title for hist in soloHists]: raise ValueError("Could not find %s as a solo hist for normalizing to." % normalizeTo)
          for hist in soloHists:
            if hist.title == normalizeTo: dataScale = hist.integral()
          mcScale = 0.
          for hist in hstack:
            mcScale += hist.integral()
          normalizeFactor = dataScale/mcScale
          for hist in hstack:
            hist.scale(dataScale/mcScale)

        # cycle through all draw options and make sure we don't overwrite
        drawOptions = ["same"]*len(soloHists)
        drawOptions = cycle([''] + drawOptions)

        # draw it so we have access to the xaxis and yaxis
        if hstack:
          hstack.Draw(next(drawOptions))
          # set up axes
          set_minmax(hstack, plots_path)
          set_label(hstack, plots_path)
          get_axis(hstack, 'x').SetNdivisions(canvasConfigs.get('ndivisions', 5))

        for hist in soloHists:
          hist.Draw(next(drawOptions))
          set_minmax(hist, plots_path)
          set_label(hist, plots_path)
          if canvasConfigs.get('logy', False) == True:
            hist.set_minimum(1e-5)
          get_axis(hist, 'x').SetNdivisions(canvasConfigs.get('ndivisions', 5))

        # draw the text we need
        textConfigs = plots.get('config', {}).get('texts', [])
        textLocals = plots_path.get('texts', [])
        for text in chain(textConfigs, textLocals):
          # attach the label
          label = ROOT.TLatex(text['x'], text['y'], text['label'])
          label.SetTextFont(text['font'])
          label.SetTextSize(text['size'])
          label.SetNDC()
          label.Draw()

        # draw the ratio
        if plots_path.get('ratio', False):
          canvas.get_pad(0).set_bottom_margin(0.3)
          p = Pad(0,0,1,1)  # create new pad, fullsize to have equal font-sizes in both plots
          #p.set_top_margin(1-canvas.get_bottom_margin())  # top-boundary (should be 1-thePad->GetBottomMargin())
          p.set_top_margin(1-canvas.get_pad(0).get_bottom_margin())  # top-boundary (should be 1-thePad->GetBottomMargin())
          p.set_right_margin(canvas.get_right_margin())
          p.set_left_margin(canvas.get_left_margin())
          p.set_fill_style(0)  # needs to be transparent
          p.set_gridy(True)
          p.Draw()
          p.cd()

          # do ratio for each histogram in solo hist
          for hist in soloHists:
            ratio = Hist.divide(hist, sum(hstack))
            ratio.draw()
            #set_minmax(ratio, plots_path)
            #get_axis(ratio, 'x').SetNdivisions(canvasConfigs.get('ndivisions', 5))

            ratio.yaxis.title = "Data / MC"
            ratio.yaxis.set_label_size(0.025)
            ratio.yaxis.set_decimals(True)
            ratio.yaxis.set_range_user(0, 5)
            ratio.yaxis.SetNdivisions(5)

            # copy over formatting
            ratio.xaxis.set_label_size(hstack.xaxis.get_label_size()/canvas.width)
            ratio.xaxis.set_label_color(hstack.xaxis.get_label_color())
            ratio.xaxis.set_title_size(hstack.xaxis.get_title_size()/canvas.width)
            ratio.xaxis.set_title_color(hstack.xaxis.get_title_color())

            ratio.xaxis.set_title_offset(hstack.xaxis.get_title_offset())
            ratio.yaxis.set_title_offset(hstack.yaxis.get_title_offset())

            # clear the xaxis on the histograms
            hist.xaxis.set_label_size(0)
            hist.xaxis.set_label_color(0)
            hist.xaxis.set_title_size(0)
            hist.xaxis.set_title_color(0)

          # clear the xaxis on the stack
          hstack.xaxis.set_label_size(0)
          hstack.xaxis.set_label_color(0)
          hstack.xaxis.set_title_size(0)
          hstack.xaxis.set_title_color(0)

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
        del canvas

      if not args.debug:
        ROOT.gROOT.ProcessLine("gSystem->RedirectOutput(0);")

  except Exception, e:
    # stop redirecting if we crash as well
    if not args.debug:
      ROOT.gROOT.ProcessLine("gSystem->RedirectOutput(0);")

    logger.exception("{0}\nAn exception was caught!".format("-"*20))
