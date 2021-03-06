from baxcat.utils import cc_test_utils as tu
from baxcat import cc_view 
from baxcat import cc_state
from baxcat import Engine
import pylab
import numpy

import pdb

# This script generates a column of every data type and plots inference 
# in real time

# set up the data generation
n_rows = 200
view_weights = numpy.ones(1)
cluster_weights = [ numpy.array([.33, .33, .34]) ]
cctypes = ['beta_uc', 'normal','normal_uc','poisson','multinomial','vonmises','vonmises_uc','binomial', 'lognormal']
separation = [.95]*9
distargs = [None, None, None, None, {"K":5}, None, None, None, None]

T, Zv, Zc, dims = tu.gen_data_table(
					n_rows, 
					view_weights, 
					cluster_weights, 
					cctypes, 
					distargs, 
					separation, 
					return_dims=True)

S = cc_state.cc_state(T, cctypes, distargs)
S.transition(N=100, do_plot=True)