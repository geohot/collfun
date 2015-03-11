from collections import OrderedDict
import networkx as nx
import numpy as np
import itertools
import time

class factor(object):
  """Generic factor class"""

  def __init__(self, in_dims, out_dim, double=False):
    self.dims = in_dims + [out_dim]
    self.double = double

  def dim_merge(self, x1, x2):
    ret = map(sum, zip(map(np.product, zip(self.dims, x1)), x2))
    #print x1, x2, ret
    return tuple(ret)

  def __call__(self, fxn):
    name = fxn.func_name
    ins = fxn.func_code.co_argcount
    dims = self.dims


    if self.double:
      matrix = np.zeros(map(lambda x: x*x, dims))
      #print matrix.shape
      for x1 in itertools.product(*map(range, dims[0:ins])):
        for x2 in itertools.product(*map(range, dims[0:ins])):
          if fxn(*x1) != None and fxn(*x2) != None:
            matrix[self.dim_merge(x1+(fxn(*x1),), x2+(fxn(*x2),))] = 1.0
    else:
      matrix = np.zeros(dims)
      for sins in itertools.product(*map(range, dims[0:ins])):
        matrix[sins+(fxn(*sins),)] = 1.0

    print "%8s %3d %3d %7d" % (name, np.product(dims[0:ins]), np.product(dims), np.product(matrix.shape)), dims[0:ins], dims[ins:]
    return matrix

# classes are private to FactorGraph
class Variable(object):

  # is this created for each class?
  CONDITIONS2 = OrderedDict([
    ('#', [0.00, 0.00]),
    ('0', [1.00, 0.00]),
    ('1', [0.00, 1.00]),
    ('?', [1.00, 1.00]),
  ])

  CONDITIONS = OrderedDict([
    ('#', [0.00, 0.00, 0.00, 0.00]),

    ('0', [1.00, 0.00, 0.00, 0.00]),
    ('n', [0.00, 1.00, 0.00, 0.00]),
    ('u', [0.00, 0.00, 1.00, 0.00]),
    ('1', [0.00, 0.00, 0.00, 1.00]),

    ('x', [0.00, 1.00, 1.00, 0.00]),
    ('-', [1.00, 0.00, 0.00, 1.00]),

    ('3', [1.00, 1.00, 0.00, 0.00]),
    ('5', [1.00, 0.00, 1.00, 0.00]),
    ('7', [1.00, 1.00, 1.00, 0.00]),
    ('A', [0.00, 1.00, 0.00, 1.00]),
    ('B', [1.00, 1.00, 0.00, 1.00]),
    ('C', [0.00, 0.00, 1.00, 1.00]),
    ('D', [1.00, 0.00, 1.00, 1.00]),
    ('E', [0.00, 1.00, 1.00, 1.00]),

    ('?', [1.00, 1.00, 1.00, 1.00]),
  ])

  CONDITIONS16 = '#0n3u5x71-ABCDE?'

  def __init__(self, name, dim):
    self.probs = None
    self.name = name
    self.dim = dim
    self.qt = None
    self.inFactors = []

  def __str__(self):
    if self.probs == None:
      return '!'

    if self.dim != 4:
      if max(self.probs) == 0:
        return '?'
      return "0123456789abcdefghijklmnopqrstuvwxyz"[np.argmax(self.probs)]

    for c in self.CONDITIONS:
      xx = map(lambda x: x[0]*x[1], zip(self.probs, self.CONDITIONS[c])) 
      if xx == self.probs:
        #print self.probs, c, xx
        return c

    return '!'

  def neighbors(self, depth):
    ret = {self: 0}
    for i in range(1, depth+1):
      new = set()
      for k in ret:
        for factor in k.inFactors:
          #print i, factor.name, map(lambda x: x.name, factor.rvs)
          for rv in factor.rvs:
            if rv not in ret:
              new.add(rv)
      for rv in new:
        ret[rv] = i
        
    return ret

  def update(self):
    if self.qt != None:
      self.qt.setText(str(self))

  def reset(self):
    self.setProbs(None)

  def setProbs(self, p, normalize=False):
    if p == None:
      self.probs = None
    else:
      # i don't want to normalize here...
      if normalize:
        self.probs = list(np.array(p) / sum(p))
      else:
        self.probs = p
    self.update()

  def fix(self, x):
    """Concentrate all probability in one place"""
    if type(x) is str:
      if x == '!':
        probs = None
      elif self.dim == 4:
        probs = self.CONDITIONS[x][:]
      elif self.dim == 2:
        probs = self.CONDITIONS2[x][:]
      elif self.dim == 16:
        probs = [0.0]*self.dim
        probs[self.CONDITIONS16.index(x)] = 1.0
    else:
      probs = [0.0]*self.dim
      probs[x] = 1.0
    #print x, probs
    self.setProbs(probs, True)

class Factor(object):
  def __init__(self, matrix, rvs):
    self.matrix = matrix
    self.rvs = rvs
    for rv in rvs:
      rv.inFactors.append(self)

  def compute(self):
    # if all the variables are computed except one
    if sum(map(lambda x: x.probs != None, self.rvs)) == len(self.rvs)-1:
      target_idx = map(lambda x: x.probs, self.rvs).index(None)
      new_dims = filter(lambda x: x != target_idx, range(len(self.rvs))) + [target_idx]
      #print target_idx, new_dims
      mat = self.matrix.transpose(new_dims)
      for rv in self.rvs:
        if rv.probs != None:
          #print rv.name, rv.probs
          nmat = mat[0] * rv.probs[0]
          for i in range(1, len(rv.probs)):
            nmat += mat[i] * rv.probs[i]
          mat = nmat

      self.rvs[target_idx].setProbs(list(mat))
      #print "setting ", self.rvs[-1].name, self.rvs[-1].probs
      return True
    return False

# public class
class FactorGraph(object):
  def __init__(self):
    self.variables = {}
    self.factors = []

  def __getitem__(self, key):
    return self.variables[key]

  def reset(self):
    for k in self.variables:
      self.variables[k].reset()

  def graph(self):
    g = nx.DiGraph()
    for k in self.variables:
      g.add_node(k)

    for f in self.factors:
      for rv in f.rvs[:-1]:
        g.add_edge(rv.name, f.rvs[-1].name)

    return g

  def fgraph(self):
    g = nx.DiGraph()
    for k in self.variables:
      g.add_node(k)

    i = 0
    for f in self.factors:
      fname = "f%d" % (i)
      for rv in f.rvs[:-1]:
        g.add_edge(rv.name, fname)
        g.add_edge(fname, f.rvs[-1].name)
      i += 1

    return g

  def compute(self):
    did_compute = True
    start = time.time()
    rounds = 0
    var = 0
    while did_compute:
      rounds += 1
      did_compute = False
      for f in self.factors:
        if f.compute():
          var += 1
          did_compute = True
    print "%d variables computed in %d rounds in %f s" % (var, rounds, time.time()-start)

  def addVariable(self, name, dim):
    ret = Variable(name, dim)
    self.variables[name] = ret
    return ret

  def addFactor(self, fxn, rvs):
    rvs = map(lambda x: self.variables[x], rvs)
    ret = Factor(fxn, rvs)
    self.factors.append(ret)
    return ret


