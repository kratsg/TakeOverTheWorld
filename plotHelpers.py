from __future__ import print_function
import os
import operator
from rootpy.io import File, root_open
from rootpy import QROOT

# why must it inherit from TFile???
class Hists(File, QROOT.TFile):
  def __init__(self, filename):
    super(self.__class__, self).__init__(filename)
    self.filename = os.path.basename(filename)
    self.rootpath = os.path.dirname(filename)
    self.fullpath = filename
    self.parse_filename()

  def parse_filename(self):
    #hist-user.mswiatlo.00266919.physics_Main.f594_m1435_p2361_12_output_xAOD.root.root
    #hist-user.mswiatlo.361025.Pythia8EvtGen_A14NNPDF23LO_jetjet_JZ5W.e3668_s2576_s2132_r6633_r6264_p2353_12_output_xAOD.root.root
    scope, username, did, physics, variousIdentifiers = ['', '', '', '', '']
    try:
      splitArgs = self.filename.split(".")
      username = splitArgs[1]
      did = splitArgs[2]
      physics = splitArgs[3]
    except IndexError:
      print("Could not understand the filename. Perhaps it's custom?")
    self._username = username
    self._did = did
    self._physics = physics

  def get_username(self):
    return self._username

  def get_did(self):
    return self._did

  def get_physics(self):
    return self._physics

  def __str__(self):
    return "%s(did=%s)" % (self.__class__.__name__, self.get_did())

  def __repr__(self):
    return self.__str__()


class HChain(list):
  def __init__(self, iterable=[]):
    super(self.__class__, self).__init__(filter(lambda x: isinstance(x, Hists), iterable))

  def get_dids(self):
    return map(lambda x: x.get_did(), self)

  def get_physics(self):
    return map(lambda x: x.get_physics(), self)

  def append(self, item):
    if not isinstance(item, Hists): return
    return super(self.__class__, self).append(item)

  def extend(self, iterable):
    return super(self.__class__, self).extend(filter(lambda x: isinstance(x, Hists), iterable))

  def insert(self, index, item):
    if not isinstance(item, Hists): return
    return super(self.__class__, self).insert(index, item)

  def __getitem__(self, index):
    if isinstance(index, str):
      if index in self.get_dids():
        index = self.get_dids().index(index)
      elif index in self.get_physics():
        index = self.get_physics().index(index)
      else:
        raise ValueError("'%s' is not in HChain" % index)
    return super(self.__class__, self).__getitem__(index)

  def __getattr__(self, attr):
    return type(self)((getattr(item, attr) for item in self))

  def keys(self):
    return set.intersection(*map(lambda x: set(map(lambda y: y.GetName(), x.keys())), self))

  def __str__(self):
    if len(self) > 6:
      innerContent = ', ..., '.join([', '.join(map(str, self[:2])), ', '.join(map(str, self[-2:]))])
    else:
      innerContent = ', '.join(map(str, self))
    return "%s[%s]" % (self.__class__.__name__, innerContent)

  def __repr__(self):
    return self.__str__()

