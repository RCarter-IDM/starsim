"""
Define non-communicable disease (NCD) model
"""

import numpy as np
import starsim as ss
import sciris as sc


__all__ = ['NCD']

class NCD(ss.Disease):
    """
    Example non-communicable disease

    This class implements a basic NCD model with risk of developing a condition
    (e.g., hypertension, diabetes), a state for having the condition, and associated
    mortality.
    """
    def __init__(self, pars=None, **kwargs):
        self.pars = ss.Pars(
            initial_risk = ss.bernoulli(p=0.3), # Initial prevalence of risk factors
            #'affection_rate': ss.rate(p=0.1), # Instantaneous rate of acquisition applied to those at risk (units are acquisitions / year)
            dur_risk = ss.expon(scale=10),
            prognosis = ss.weibull(c=2, scale=5), # Time in years between first becoming affected and death
        )
        super().__init__(pars, **kwargs)
        
        self.add_states(
            ss.BoolArr('at_risk'),
            ss.BoolArr('affected'),
            ss.FloatArr('ti_affected'),
            ss.FloatArr('ti_dead'),
        )
        return

    @property
    def not_at_risk(self):
        return ~self.at_risk

    def set_initial_states(self, sim):
        """
        Set initial values for states. This could involve passing in a full set of initial conditions,
        or using init_prev, or other. Note that this is different to initialization of the State objects
        i.e., creating their dynamic array, linking them to a People instance. That should have already
        taken place by the time this method is called.
        """
        initial_risk = self.pars['initial_risk'].filter()
        self.at_risk[initial_risk] = True
        self.ti_affected[initial_risk] = sim.ti + sc.randround(self.pars['dur_risk'].rvs(initial_risk) / sim.dt)
        return initial_risk

    def update_pre(self, sim):
        deaths = (self.ti_dead == sim.ti).uids
        sim.people.request_death(sim, deaths)
        self.log.add_data(deaths, died=True)
        self.results.new_deaths[sim.ti] = len(deaths) # Log deaths attributable to this module
        return

    def make_new_cases(self, sim):
        new_cases = (self.ti_affected == sim.ti).uids
        self.affected[new_cases] = True
        prog_years = self.pars.prognosis.rvs(new_cases)
        self.ti_dead[new_cases] = sim.ti + sc.randround(prog_years / sim.dt)
        super().set_prognoses(sim, new_cases)
        return new_cases

    def init_results(self, sim):
        """
        Initialize results
        """
        super().init_results(sim)
        self.results += [
            ss.Result(self.name, 'n_not_at_risk', sim.npts, dtype=int),
            ss.Result(self.name, 'prevalence', sim.npts, dtype=float),
            ss.Result(self.name, 'new_deaths', sim.npts, dtype=int),
        ]
        return

    def update_results(self, sim):
        super().update_results(sim)
        ti = sim.ti
        self.results.n_not_at_risk[ti] = np.count_nonzero(self.not_at_risk)
        self.results.prevalence[ti]    = np.count_nonzero(self.affected)/len(sim.people)
        self.results.new_deaths[ti]    = np.count_nonzero(self.ti_dead == ti)
        return
