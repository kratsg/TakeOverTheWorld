#!/usr/bin/env python

# @file:    cutflows.py
# @purpose: make a table of cutflows for a given set of outputs from TheAccountant
# @author:  Giordon Stark <gstark@cern.ch>
# @date:    August 2015
#

# Based on https://svnweb.cern.ch/trac/atlasinst/browser/Institutes/SLAC/ProofAna/trunk/scripts/printCutflow.py

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
logger = logging.getLogger("cutflows")

# import all libraries
import argparse
import subprocess
import glob
import yaml

import sys
import os
import re
import math

from rootpy.io import root_open
from rootpy.plotting import Hist
import ROOT

class CutFlow(Hist, object):
  def __init__(self, hist):
    super(CutFlow, self).__init__(hist)

  @property
  def n(self):
    return self.get_bin_content(1)

  @n.setter
  def n(self, val):
    print(self.n)
    print(val)
    self.set_bin_content(1, val)

  @property
  def nwgt(self):
    return self.get_bin_content(2)

  @nwgt.setter
  def nwgt(self, val):
    self.set_bin_content(2, val)

  def add(self, cut):
    if not isinstance(cut, self.__class__):
      raise TypeError("The cut is not a cutflow object. It is {0:s}".format(cut.__class__.__name__))
    if self.name != cut.name:
      raise ValueError("Incompatible cutflows. Trying to add {0:s} to {1:s}".format(cut.name, self.name))

    self.n += cut.n
    self.nwgt += cut.nwgt
    #self.nerror = math.sqrt(self.nerror*self.nerror + cut.nerror*cut.nerror)
    #self.nwgterror = math.sqrt(self.nwgterror*self.nwgterror + cut.nwgterror*cut.nwgterror)

  def __lt__(self, other):
    return self.n > other.n


def printCutflow(name,cuts):
  # convert to list, sort by nentries
  mylist = [ ]
  for cutnames, cut in cuts.items():
    mylist.append(cut)

  mylist.sort()

  ncol = 1
  if not noEntries:
    if not noRaw:
      ncol += 1
    if not noWeights:
      ncol += 1
  if not noAbsEff:
    if not noRaw:
      ncol += 1
    if not noWeights:
      ncol += 1
  if not noRelEff:
    if not noRaw:
      ncol += 1
    if not noWeights:
      ncol += 1

  if doLatex:
    name = name.replace("_","\_")
    print("\\begin{table}")
    print("\\footnotesize")
    print("\\begin{center}\\renewcommand\\arraystretch{1.6}")
    str = "\\begin{tabular}{|c|"
    for i in xrange(1,ncol):
      if i==1:
        str += "|"
      str += "c|"
    str += "}\hline"
    print(str)
    print("\multicolumn{%d}{|c|}{%s Cut Flow} \\\\ \hline" % (ncol, name))
    str = "Cut"
    if not noEntries:
      if not noRaw:
        str += " & Entries"
      if not noWeights:
        str += " & Weighted Entries"
    if not noAbsEff:
      if not noRaw:
        str += " & Abs. Eff."
      if not noWeights:
        str += "& W. Abs. Eff."
    if not noRelEff:
      if not noRaw:
        str += "& Rel. Eff."
      if not noWeights:
        str += "& W. Rel. Eff."
    str += "\\\\ \hline\hline"
    print(str)
  else:
    print("Analysis",name,"cut flow:")
    print("********************************************************************************************************************************************************")
    print("* Cut                                  | Entries                | Weighted Entries               | Abs. Eff. | W. Abs. Eff. | Rel. Eff. | W. Rel. Eff. *")
    print("*------------------------------------------------------------------------------------------------------------------------------------------------------*")

  ntotal = mylist[0].n
  nwgttotal = mylist[0].nwgt
  prevntotal = mylist[0].n
  prevnwgttotal = mylist[0].nwgt

  percent = "%"
  pm = "+/-"
  if doLatex:
    percent = "\%"
    pm = "$\pm$"

  for cut in mylist:
    first = cut.name
    if doLatex:
      first = cut.name.replace("_","\_")
    second = '%.0f' % cut.n
    if not noErrors:
      err = " %s %.1f" % (pm, cut.nerror)
      second += err
    third = '%.2f' % cut.nwgt
    if not noErrors:
      err =  " %s %.2f" % (pm, cut.nwgterror)
      third += err
    abseff = 100.*cut.n/ntotal
    fourth = '%.1f%s' % (abseff, percent)
    wabseff = 100.*cut.nwgt/nwgttotal
    fifth = '%.1f%s' % (wabseff, percent)
    releff = 100.*cut.n/prevntotal
    sixth = '%.1f%s' % (releff, percent)
    wreleff = 100.*cut.nwgt/prevnwgttotal
    seventh = '%.1f%s' % (wreleff, percent)
    if doLatex:
      str = first
      if not noEntries:
        if not noRaw:
          str += " & "
          str += second
        if not noWeights:
          str += " & "
          str += third
      if not noAbsEff:
        if not noRaw:
          str += " & "
          str += fourth
        if not noWeights:
          str += " & "
          str += fifth
      if not noRelEff:
        if not noRaw:
          str += " & "
          str += sixth
        if not noWeights:
          str += " & "
          str += seventh
      str += "\\\\"
      print(str)
    else:
      print("* %-36s | %22s | %30s | %9s | %12s | %9s | %12s *" % (first, second, third, fourth, fifth, sixth, seventh))
    prevntotal = cut.n
    prevnwgttotal = cut.nwgt

  if doLatex:
    print("\hline")
    print("\end{tabular}")
    str = "\caption{Cut flow for the %s analysis.}\label{tab:%s}" % (name, name)
    print(str)
    print("\end{center}")
    print("\end{table}")
  else:
    print("********************************************************************************************************************************************************")
  print("")

if __name__ == "__main__":
  class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter):
    pass

  __version__ = subprocess.check_output(["git", "describe", "--always"], cwd=os.path.dirname(os.path.realpath(__file__))).strip()
  __short_hash__ = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=os.path.dirname(os.path.realpath(__file__))).strip()

  parser = argparse.ArgumentParser(description='Author: Giordon Stark. v.{0}'.format(__version__),
                                   formatter_class=lambda prog: CustomFormatter(prog, max_help_position=30))

  parser.add_argument('files', nargs='+', type=str, help='Files to use')

  # general arguments for all
  parser.add_argument('-v','--verbose', dest='verbose', action='count', default=0, help='Enable verbose output of various levels. Use --debug to enable output for debugging.')
  parser.add_argument('--debug', dest='debug', action='store_true', help='Enable ROOT output and full-on debugging. Use this if you need to debug the application.')
  parser.add_argument('-b', '--batch', dest='batch_mode', action='store_true', help='Enable batch mode for ROOT.')

  parser.add_argument('--accept', required=False, nargs='+', type=str, help='pattern of what to accept', default=[])
  parser.add_argument('--exclude', required=False, nargs='+', type=str, help='pattern of what to exclude', default=[])
  parser.add_argument('-f', '--format', required=False, type=str, choices=['latex', 'plain'], help='Output format', default='plain')

  parser.add_argument('--noentries',    action='store_true', help='...')
  parser.add_argument('--noabseff',     action='store_true', help='...')
  parser.add_argument('--noreleff',     action='store_true', help='...')
  parser.add_argument('--noweights',    action='store_true', help='...')
  parser.add_argument('--noraw',        action='store_true', help='...')
  parser.add_argument('--noerrors',     action='store_true', help='...')

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

      doLatex   = args.format == 'latex'
      noEntries = args.noentries
      noAbsEff  = args.noabseff
      noRelEff  = args.noreleff
      noWeights = args.noweights
      noRaw     = args.noraw
      noErrors  = args.noerrors


      files = [ ]
      accepts = [ ]
      excludes = [ ]

      for p in args.accept:
        try:
          accepts.append(re.compile("^{0:s}$".format(p)))
        except re.error:
          logger.exception("Invalid regular expression: {0:s}".format(p))

      for p in args.exclude:
        try:
          excludes.append(re.compile("^{0:s}$".format(p)))
        except re.error:
          logger.exception("Invalid regular expression: {0:s}".format(p))

      for f in args.files:
        if not os.path.isfile(f):
          raise IOError("Not a valid file: {0:s}".format(f))
        files.append(f)

      if len(files) == 0:
        raise ValueError("No files were specified")

      for filename in files:
        f = root_open(f)
        for cutflow in f.cutflow:
          # accept if at least one
          if sum(bool(p.match(cutflow.name)) for p in accepts) == 0:
            continue
          # exclude if at least one
          if sum(bool(p.match(cutflow.name)) for p in excludes) != 0:
            continue

          readCutflow(cutflow, {})

        f.close()

      printCutflow(ana,cuts)

      print("Accept regexps (OR'ed):")
      for regexp in accepts:
        print("     ", regexp.pattern)
      print("Exclude regexps (AND'ed):")
      for regexp in excludes:
        print("     ", regexp.pattern)


      if not args.debug:
        ROOT.gROOT.ProcessLine("gSystem->RedirectOutput(0);")

  except Exception, e:
    # stop redirecting if we crash as well
    if not args.debug:
      ROOT.gROOT.ProcessLine("gSystem->RedirectOutput(0);")

    logger.exception("{0}\nAn exception was caught!".format("-"*20))
