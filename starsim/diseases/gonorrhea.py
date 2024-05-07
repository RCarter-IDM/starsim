"""
Define default gonorrhea disease module and related interventions
"""

import numpy as np
import starsim as ss


__all__ = ['Gonorrhea']

class Gonorrhea(ss.Infection):

    def __init__(self, pars=None, *args, **kwargs):
        # Parameters
        super().__init__()
        self.default_pars(
            beta = 1.0, # Placeholder value
            dur_inf_in_days = ss.lognorm_ex(mean=10, stdev=0.6),  # median of 10 days (IQR 7–15 days) https://sti.bmj.com/content/96/8/556
            p_symp    = ss.bernoulli(0.5),  # Share of infections that are symptomatic. Placeholder value
            p_clear   = ss.bernoulli(0.2),  # Share of infections that spontaneously clear: https://sti.bmj.com/content/96/8/556
            init_prev = ss.bernoulli(0.1),
        )
        self.update_pars(pars=pars, **kwargs)
        
        # States additional to the default disease states (see base class)
        # Additional states dependent on parameter values, e.g. self.p_symp?
        # These might be useful for connectors to target, e.g. if HIV reduces p_clear
        self.add_states(
            ss.BoolArr('symptomatic'),
            ss.FloatArr('ti_clearance'),
            ss.FloatArr('p_symp', default=1),
        )
        
        return

    def init_results(self, sim):
        """
        Initialize results
        """
        super().init_results(sim)
        self.results += ss.Result(self.name, 'new_clearances', sim.npts, dtype=int)
        return

    def update_results(self, sim):
        ti = sim.ti
        super(Gonorrhea, self).update_results(sim)
        self.results.n_symptomatic[ti] = self.symptomatic.count()
        self.results.new_clearances[ti] = np.count_nonzero(self.ti_clearance == ti)
        return

    def update_pre(self, sim):
        # What if something in here should depend on another module?
        # I guess we could just check for it e.g., 'if HIV in sim.modules' or
        # 'if 'hiv' in sim.people' or something
        # Natural clearance
        clearances = self.ti_clearance <= sim.ti
        self.susceptible[clearances] = True
        self.infected[clearances] = False
        self.symptomatic[clearances] = False
        self.ti_clearance[clearances] = sim.ti

        return
    
    def make_new_cases(self, sim):
        super(Gonorrhea, self).make_new_cases(sim)
        return

    def set_prognoses(self, sim, target_uids, source_uids=None):
        """
        Natural history of gonorrhea for adult infection
        """
        super().set_prognoses(sim, target_uids, source_uids)

        # Set infection status
        self.susceptible[target_uids] = False
        self.infected[target_uids] = True
        self.ti_infected[target_uids] = sim.ti

        # Set infection status
        symp_uids = self.pars.p_symp.filter(target_uids)
        self.symptomatic[symp_uids] = True

        # Set natural clearance
        clear_uids = self.pars.p_clear.filter(target_uids)
        dur = sim.ti + self.pars.dur_inf_in_days.rvs(clear_uids)/365/sim.dt # Convert from days to years and then adjust for dt
        self.ti_clearance[clear_uids] = dur

        return

    def set_congenital(self, sim, target_uids, source_uids=None):
        pass
