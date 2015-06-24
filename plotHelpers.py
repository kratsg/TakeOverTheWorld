from __future__ import print_function
import os
import array
from rootpy.core import Object
from rootpy.io import File, Directory, root_open
from rootpy.plotting.hist import _HistBase, HistStack, _Hist, _Hist2D
from rootpy.io.file import _DirectoryBase
from rootpy import QROOT
from palettable import cubehelix

class HistsCollection(list, _DirectoryBase):
  def __init__(self):
    super(HistsCollection, self).__init__()
    self._attr = None
    self._parent = None

  def isinstance(self, objtype):
    return not any(not isinstance(x, objtype) for x in self)

  def _get_parent_attr(self):
    if self._parent is None:
      if self._attr is None:
        return '/'
      else:
        return self._attr
    else:
      parent_attr = self._parent._get_parent_attr()
      if parent_attr == '/':
        parent_attr = ''
      if self._attr is None:
        return '%s' % ( parent_attr )
      else:
        return '%s/%s' % ( parent_attr, self._attr )

  def _get_view(self, obj):
    if self._attr is None:
      return obj
    else:
      return getattr(obj, self._attr)

  def _validate(self, obj):
    if not isinstance(obj, Object):
      raise TypeError("Must be a Object instance")
    keys = obj.keys()
    if not isinstance(keys, set):
      keys = map(lambda x: x.GetName(), keys)
    if self._attr is not None and self._attr not in keys:
      raise ValueError("%s instance does not have %s" % (self.__class__.__name__, self._attr))

  def add(self, root_file):
    return self.append(root_file)

  def append(self, root_file):
    self._validate(root_file)
    return super(HistsCollection, self).append(self._get_view(root_file))

  def extend(self, iterable):
    map(self._validate, iterable)
    return super(HistsCollection, self).extend([self._get_view(obj) for obj in iterable])

  def insert(self, index, item):
    self._validate(item)
    return super(HistsCollection, self).insert(index, self._get_view(item))

class HGroup(HistsCollection):
  def __init__(self, group_name, attr=None):
    super(self.__class__, self).__init__()
    self._group_name = group_name
    self._attr = attr

  def isHists(self):
    return self.isinstance((_Hist, _Hist2D))

  def keys(self):
    if self.isHists(): return set()
    return set.intersection(*map(lambda x: set(map(lambda y: y.GetName(), x.keys())), self))

  def __getattr__(self, attr):
    newHColl = self.__class__(self._group_name, attr)
    newHColl.extend(self)
    newHColl._parent = self
    return newHColl

  def __str__(self):
    return "%s(%s, %d %s;%s)" % (self.__class__.__name__, self._group_name, len(self), "hists" if self.isHists() else "files", self._get_parent_attr())
  def __repr__(self):
    return self.__str__()

class HChain(HistsCollection):
  def __init__(self, attr=None):
    super(self.__class__, self).__init__()
    self._attr = attr

  def isHists(self):
    return all(obj.isHists() for obj in self)

  def walk(self):
    keys = self.keys()
    if not keys:
      yield self
    else:
      for key in keys:
        for sub in getattr(getattr(self, key), 'walk')():
          yield sub

  def __getitem__(self, index):
    return super(self.__class__, self).__getitem__(index)

  def keys(self):
    return set.intersection(*map(lambda x: x.keys(), self))

  def stack(self, colors=cubehelix.classic_16.colors):
    if not self.isHists():
      raise TypeError( "%s does not contain only 1D and 2D histograms. You can only stack 1D and 2D histograms." % self.__class__.__name__)
    newHistStack = HistStack()
    map(lambda x: setattr(x[0], 'color', x[1]), zip(self, colors))
    map(newHistStack.Add, self)
    return newHistStack

  def __getattr__(self, attr):
    newHColl = self.__class__(attr)
    newHColl.extend(self)
    newHColl._parent = self
    return newHColl

  def __str__(self):
    if len(self) > 6:
      innerContent = ', ..., '.join([', '.join(map(str, self[:2])), ', '.join(map(str, self[-2:]))])
    else:
      innerContent = ', '.join(map(str, self))
    return "%s('%s')[%s]" % (self.__class__.__name__, self._get_parent_attr(), innerContent)

  def __repr__(self):
    return self.__str__()
