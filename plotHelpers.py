from __future__ import print_function
import os
import array
from rootpy.base import Object
from rootpy.io import File, Directory, root_open
from rootpy.plotting.hist import _HistBase, _Hist, _Hist2D
from rootpy.io.file import _DirectoryBase
from rootpy import QROOT

class HistsCollection(list, _DirectoryBase):
  def __init__(self):
    super(HistsCollection, self).__init__()
    # the parent of the object, used to track hierarchy
    self._parent = None
    # rel path of object
    self._relpath = None
    # abs path of object, requires parent
    self._abspath = None
    # stores the children the parent generates dynamically from __getattr__
    self._subviews = {}

  def isinstance(self, objtype):
    return not any(not isinstance(x, objtype) for x in self)

  @property
  def path(self):
    # make sure relpath is valid
    self._relpath = '' if self._relpath is None else self._relpath
    # top of the path
    if self._parent is None:
      self._abspath = self._relpath
    elif self._abspath is None:
      # not top of the path
      self._abspath = os.path.join(self._parent.path, self._relpath)
    return self._abspath

  def _get_view(self, obj):
    if self._relpath is None:
      return obj
    else:
      return getattr(obj, self._relpath)

  def _validate(self, obj):
    if not isinstance(obj, Object):
      raise TypeError("Must be a Object instance")
    keys = obj.keys()
    if not isinstance(keys, set):
      keys = map(lambda x: x.GetName(), keys)
    if self._relpath is not None and self._relpath not in keys:
      raise ValueError("%s instance does not have %s\n\t%s <- %s" % (self.__class__.__name__, self._relpath, self, self._parent))

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
    self._relpath = attr

  @property
  def isHists(self):
    return self.isinstance((_Hist, _Hist2D))

  @property
  def group(self):
    return self._group_name

  @property
  def get_files(self):
    return map(lambda x: x.get_file(), self)

  def keys(self):
    if self.isHists: return set()
    return set.intersection(*map(lambda x: set(map(lambda y: y.GetName(), x.keys())), self))

  def __getattr__(self, attr):
    if attr in self._subviews:
      return self._subviews.get(attr)
    else:
      newHColl = self.__class__(self._group_name, attr)
      newHColl.extend(self)
      newHColl._parent = self
      self._subviews[attr] = newHColl
      return newHColl

  @property
  def flatten(self):
    newHist = sum(self)
    newHist.title = self.group
    newHist.name = '{0:s}:{1:s}'.format(self.group, self.path)
    return newHist

  def __str__(self):
    return "%s(%s, %d %s;%s)" % (self.__class__.__name__, self._group_name, len(self), "hists" if self.isHists else "files", self.path)
  def __repr__(self):
    return self.__str__()

class HChain(HistsCollection):
  def __init__(self, top=None):
    super(self.__class__, self).__init__()
    self._relpath = top
    self._keys = None

  @property
  def isHists(self):
    return all(obj.isHists for obj in self)

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

  def keys(self, regen=False):
    if self._keys is None or regen:
      self._keys = set.intersection(*map(lambda x: x.keys(), self))
    return self._keys

  def __getattr__(self, attr):
    if attr in self._subviews:
      return self._subviews.get(attr)
    else:
      newHColl = self.__class__(attr)
      newHColl.extend(self)
      newHColl._parent = self
      self._subviews[attr] = newHColl
      return newHColl

  def __str__(self):
    if len(self) > 6:
      innerContent = ', ..., '.join([', '.join(map(str, self[:2])), ', '.join(map(str, self[-2:]))])
    else:
      innerContent = ', '.join(map(str, self))
    return "%s('%s')[%s]" % (self.__class__.__name__, self.path, innerContent)

  def __repr__(self):
    return self.__str__()
