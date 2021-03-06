import math
from math import log
import baxcat.utils.cc_general_utils as utils
from scipy.special import gammaln
import random
import numpy

from scipy.misc import logsumexp

import pylab
LOG2 = log(2.0)
LOGPI = log(math.pi)
LOG2PI = log(2.0*math.pi)


class cc_lognormal(object):
    """
    Log-normal (zero-bounded) data type with normal prior on mu and gamma
    prior on precision.
    Does not require additional argumets (distargs=None).
    """

    cctype = 'lognormal'

    def __init__(self, N=0, sum_log_x=0, sum_log_x_sq=0, a=1, b=1, t=1, m=0, distargs=None):
        """
        -- N: number of data points
        -- sum_log_x: suffstat, sum(log(x))
        -- sum_log_x_sq: suffstat, sum(log(x*x))
        -- a: hyperparameter
        -- b: hyperparameter
        -- t: hyperparameter
        -- m: hyperparameter
        -- distargs: not used
        """
        assert a > 0
        assert b > 0
        assert t > 0
        self.N = N
        self.sum_log_x_sq = sum_log_x_sq
        self.sum_log_x = sum_log_x
        self.m = m
        self.a = a
        self.b = b
        self.t = t

    def set_hypers(self, hypers):
        assert hypers['a'] > 0
        assert hypers['b'] > 0
        assert hypers['t'] > 0

        self.m = hypers['m']
        self.b = hypers['b']
        self.t = hypers['t']
        self.a = hypers['a']

    def insert_element(self, x):
        self.N += 1.0
        lx = log(x)
        self.sum_log_x += lx
        self.sum_log_x_sq += lx*lx

    def remove_element(self, x):
        self.N -= 1.0
        lx = log(x)
        self.sum_log_x -= lx
        self.sum_log_x_sq -= lx*lx

    def predictive_logp(self, x):
        return self.calc_predictive_logp(x, self.N, self.sum_log_x,self.sum_log_x_sq, 
                                        self.a, self.b, self.t, self.m)

    def singleton_logp(self, x):
        return self.calc_predictive_logp(x, 0, 0, 0,
                                        self.a, self.b, self.t, self.m)

    def marginal_logp(self):
        return self.calc_marginal_logp(self.N, self.sum_log_x, self.sum_log_x_sq,
                                        self.a, self.b, self.t, self.m)

    @staticmethod
    def construct_hyper_grids(X,n_grid=30):
        grids = dict()
        ssqdev = numpy.var(X)*float(len(X));
        grids['a'] = utils.log_linspace(.1,float(len(X)), n_grid)
        grids['b'] = utils.log_linspace(.1,float(len(X)), n_grid)
        grids['t'] = utils.log_linspace(.1,float(len(X)), n_grid)
        grids['m'] = utils.log_linspace(.0001, max(X), n_grid)
        return grids

    @staticmethod
    def init_hypers(grids, X=None):
        hypers = dict()
        hypers['m'] = random.choice(grids['m'])
        hypers['a'] = random.choice(grids['a'])
        hypers['b'] = random.choice(grids['b'])
        hypers['t'] = random.choice(grids['t'])

        return hypers

    @staticmethod
    def calc_predictive_logp(x, N, sum_log_x, sum_log_x_sq, a, b, t, m):

        if x == 0.0:
            return 0

        lx = log(x)
        an, bn, tn, mn = cc_lognormal.posterior_update_parameters(
            N, sum_log_x, sum_log_x_sq, a, b, t, m)

        am, bm, tm, mm = cc_lognormal.posterior_update_parameters(
            N+1, sum_log_x+lx, sum_log_x_sq+lx*lx, a, b, t, m)

        ZN = log(x)+cc_lognormal.calc_log_Z(an, bn, tn)
        ZM = cc_lognormal.calc_log_Z(am, bm, tm)

        return -.5*LOG2PI + ZM - ZN

    @staticmethod
    def calc_marginal_logp(N, sum_log_x, sum_log_x_sq, a, b, t, m):
        an, bn, tn, mn = cc_lognormal.posterior_update_parameters(
            N, sum_log_x, sum_log_x_sq, a, b, t, m)

        Z0 = sum_log_x+cc_lognormal.calc_log_Z(a, b, t)
        ZN = cc_lognormal.calc_log_Z(an, bn, tn)

        return -(float(N)/2.0)*LOG2PI + ZN - Z0

    @staticmethod
    def update_hypers(clusters, grids):
        # resample alpha
        a = clusters[0].a
        b = clusters[0].b
        t = clusters[0].t
        m = clusters[0].m

        which_hypers = [0,1,2,3]
        random.shuffle(which_hypers)
        for hyper in which_hypers:
            if hyper == 0:
                lp_a = cc_lognormal.calc_a_conditional_logps(clusters, grids['a'],b,t,m)
                a_index = utils.log_pflip(lp_a)
                a = grids['a'][a_index]
            elif hyper == 1:
                lp_b = cc_lognormal.calc_b_conditional_logps(clusters, grids['b'],a,t,m)
                b_index = utils.log_pflip(lp_b)
                b = grids['b'][b_index]
            elif hyper == 2:
                lp_t = cc_lognormal.calc_t_conditional_logps(clusters, grids['t'],a,b,m)
                t_index = utils.log_pflip(lp_t)
                t = grids['t'][t_index]
            elif hyper == 3:
                lp_m = cc_lognormal.calc_m_conditional_logps(clusters, grids['m'],a,b,t)
                m_index = utils.log_pflip(lp_m)
                m = grids['m'][m_index]
            else:
                raise ValueError("invalid hyper")

        hypers = dict()
        hypers['a'] = a
        hypers['b'] = b
        hypers['t'] = t
        hypers['m'] = m
        
        return hypers

    @staticmethod
    def posterior_update_parameters(N, sum_log_x, sum_log_x_sq, a, b, t, m):
        tmn = m*t+N

        tn = t + float(N)
        an = a + float(N)
        mn = (t*m+sum_log_x)/tn
        bn = b + sum_log_x_sq + t*m*m - tn*mn*mn

        return an, bn, tn, mn

    @staticmethod 
    def calc_log_Z(a, b, t):
        Z = ((a+1.0)/2.0)*LOG2 + .5*LOGPI - .5*log(t) - (a/2.0)*log(b) + gammaln(a/2.0)
        return Z
  
    @staticmethod
    def calc_m_conditional_logps(clusters, m_grid, a, b, t):
        lps = []
        for m in m_grid:
            lp = cc_lognormal.calc_full_marginal_conditional(clusters, a, b, t, m)
            lps.append(lp)

        return lps

    @staticmethod
    def calc_a_conditional_logps(clusters, a_grid, b, t, m):
        lps = []
        for a in a_grid:
            lp = cc_lognormal.calc_full_marginal_conditional(clusters, a, b, t, m)
            lps.append(lp)

        return lps

    @staticmethod
    def calc_b_conditional_logps(clusters, b_grid, a, t, m):
        lps = []
        for b in b_grid:
            lp = cc_lognormal.calc_full_marginal_conditional(clusters, a, b, t, m)
            lps.append(lp)

        return lps

    @staticmethod
    def calc_t_conditional_logps(clusters, t_grid, a, b, m):
        lps = []
        for t in t_grid:
            lp = cc_lognormal.calc_full_marginal_conditional(clusters, a, b, t, m)
            lps.append(lp)

        return lps

    @staticmethod
    def calc_full_marginal_conditional(clusters, a, b, t, m):
        lp = 0
        for cluster in clusters:
            N = cluster.N
            sum_log_x = cluster.sum_log_x
            sum_log_x_sq = cluster.sum_log_x_sq
            l = cc_lognormal.calc_marginal_logp(N, sum_log_x, sum_log_x_sq, a, b, t, m)
            lp += l

        return lp

    @staticmethod
    def calc_full_marginal_conditional_h(clusters, hypers):
        lp = 0
        a = clusters[0].a
        b = clusters[0].b
        t = clusters[0].t
        m = clusters[0].m
        for cluster in clusters:
            N = cluster.N
            sum_log_x = cluster.sum_log_x
            sum_log_x_sq = cluster.sum_log_x_sq
            l = cc_lognormal.calc_marginal_logp(N, sum_log_x, sum_log_x_sq, a, b, t, m)
            lp += l

        return lp

    @staticmethod
    def plot_dist(X, clusters, distargs=None):
        colors = ["red", "blue", "green", "yellow", "orange", "purple", "brown", "black"]
        x_min = min(X)
        x_max = max(X)
        Y = numpy.linspace(x_min, x_max, 200)
        K = len(clusters)
        pdf = numpy.zeros((K,200))
        denom = log(float(len(X)))

        a = clusters[0].a
        b = clusters[0].b
        t = clusters[0].t
        m = clusters[0].m

        nbins = min([len(X)/5, 50])

        pylab.hist(X, nbins, normed=True, color="black", alpha=.5, edgecolor="none")

        W = [log(clusters[k].N) - denom for k in range(K)]

        for k in range(K):
            w = W[k]
            N = clusters[k].N
            sum_log_x = clusters[k].sum_log_x
            sum_log_x_sq = clusters[k].sum_log_x_sq
            for n in range(200):
                y = Y[n]
                pdf[k, n] = numpy.exp(w + cc_lognormal.calc_predictive_logp(y, N, sum_log_x, 
                    sum_log_x_sq, a, b, t, m))

            if k >= 8:
                color = "white"
                alpha=.3
            else:
                color = colors[k]
                alpha=.7
            pylab.plot(Y, pdf[k,:],color=color, linewidth=5, alpha=alpha)

        pylab.plot(Y, numpy.sum(pdf,axis=0), color='black', linewidth=3)
        pylab.title('lognormal')
