from __future__ import print_function
import os
import operator
from rootpy.core import Object
from rootpy.io import File, Directory, root_open
from rootpy.plotting.hist import _HistBase
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


class HChain(list, object):
  def __init__(self, attr):
    self._attr = attr
    self._parent = None
    return super(self.__class__, self).__init__()

  def _validate(self, root_file):
    if not isinstance(root_file, Object):
      raise TypeError("Must be a rootpy Object instance")
    if self._attr not in map(lambda x: x.GetName(), root_file.keys()):
      raise ValueError("%s instance does not have %s" % (self.__class__.__name__, self._attr))

  def _get_parent_attr(self):
    if self._parent is None:
      return self._attr
    else:
      return '%s/%s' % ( self._parent._get_parent_attr(), self._attr )

  def add(self, root_file):
    return self.append(root_file)

  def append(self, root_file):
    self._validate(root_file)
    return super(self.__class__, self).append(getattr(root_file, self._attr))

  def extend(self, iterable):
    map(self._validate, iterable)
    return super(self.__class__, self).extend([getattr(root_file, self._attr) for root_file in iterable])

  def insert(self, index, item):
    self._validate(item)
    return super(self.__class__, self).insert(index, item)

  def __getitem__(self, index):
    return super(self.__class__, self).__getitem__(index)

  def __getattr__(self, attr):
    newHChain = self.__class__(attr)
    newHChain.extend(self)
    newHChain._parent = self
    return newHChain

  def keys(self):
    return set.intersection(*map(lambda x: set(map(lambda y: y.GetName(), x.keys())), self))

  def __str__(self):
    if len(self) > 6:
      innerContent = ', ..., '.join([', '.join(map(str, self[:2])), ', '.join(map(str, self[-2:]))])
    else:
      innerContent = ', '.join(map(str, self))
    return "%s('/%s')[%s]" % (self.__class__.__name__, self._get_parent_attr(), innerContent)

  def __repr__(self):
    return self.__str__()

'''
class HChain(list):
  def __init__(self, iterable=[]):
    super(self.__class__, self).__init__(filter(lambda x: isinstance(x, (Hists, Directory, _HistBase)), iterable))

  def get_dids(self):
    return map(lambda x: x.get_did(), self)

  def get_physics(self):
    return map(lambda x: x.get_physics(), self)

  def append(self, item):
    if not isinstance(item, (Hists, Directory, _HistBase)): return
    return super(self.__class__, self).append(item)

  def extend(self, iterable):
    return super(self.__class__, self).extend(filter(lambda x: isinstance(x, (Hists, Directory, _HistBase)), iterable))

  def insert(self, index, item):
    if not isinstance(item, (Hists, Directory, _HistBase)): return
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
    return self.__class__([getattr(item, attr) for item in self])

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
'''
