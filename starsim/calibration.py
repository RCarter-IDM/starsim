"""
Define the calibration class
"""
import os
import numpy as np
import optuna as op
import pandas as pd
import datetime as dt
import sciris as sc
import starsim as ss
import matplotlib.pyplot as plt
from scipy.special import gammaln as gln
from enum import Enum


__all__ = ['Calibration', 'CalibComponent', 'eConform', 'eLikelihood']


class Calibration(sc.prettyobj):
    """
    A class to handle calibration of Starsim simulations. Uses the Optuna hyperparameter
    optimization library (optuna.org).

    Args:
        sim          (Sim)  : the base simulation to calibrate
        calib_pars   (dict) : a dictionary of the parameters to calibrate of the format dict(key1=dict(low=1, high=2, guess=1.5, **kwargs), key2=...), where kwargs can include "suggest_type" to choose the suggest method of the trial (e.g. suggest_float) and args passed to the trial suggest function like "log" and "step"
        n_workers    (int)  : the number of parallel workers (if None, will use all available CPUs)
        total_trials (int)  : the total number of trials to run, each worker will run approximately n_trials = total_trial / n_workers

        reseed       (bool) : whether to generate new random seeds for each trial

        build_fn  (callable): function that takes a sim object and calib_pars dictionary and returns a modified sim
        build_kwargs  (dict): a dictionary of options that are passed to build_fn to aid in modifying the base simulation. The API is self.build_fn(sim, calib_pars=calib_pars, **self.build_kwargs), where sim is a copy of the base simulation to be modified with calib_pars

        components (list of CalibComponent objects): CalibComponents independently assess pseudo-likelihood as part of evaluating the quality of input parameters

        eval_fn  (callable): Function mapping a sim to a float (e.g. negative log likelihood) to be maximized. If None, the default will use CalibComponents.
        eval_kwargs  (dict): Additional keyword arguments to pass to the eval_fn

        label        (str)  : a label for this calibration object
        study_name   (str)  : name of the optuna study
        db_name      (str)  : the name of the database file (default: 'starsim_calibration.db')
        keep_db      (bool) : whether to keep the database after calibration (default: false)
        storage      (str)  : the location of the database (default: sqlite)
        sampler (BaseSampler): the sampler used by optuna, like optuna.samplers.TPESampler

        die          (bool) : whether to stop if an exception is encountered (default: false)
        debug        (bool) : if True, do not run in parallel
        verbose      (bool) : whether to print details of the calibration

    Returns:
        A Calibration object
    """
    def __init__(self, sim, calib_pars, n_workers=None, total_trials=None,
                 reseed=True,
                 build_fn=None, build_kwargs=None, eval_fn=None, eval_kwargs=None,
                 components=None,

                 label=None, study_name=None, db_name=None, keep_db=None, storage=None,
                 sampler=None, die=False, debug=False, verbose=True):

        # Handle run arguments
        if total_trials is None: total_trials   = 100
        if n_workers    is None: n_workers      = sc.cpu_count()
        if study_name   is None: study_name     = 'starsim_calibration'
        if db_name      is None: db_name        = f'{study_name}.db'
        if keep_db      is None: keep_db        = False
        if storage      is None: storage        = f'sqlite:///{db_name}'
        
        self.build_fn       = build_fn or self.translate_pars
        self.build_kwargs   = build_kwargs or dict()
        self.eval_fn        = eval_fn or self._eval_fit
        self.eval_kwargs    = eval_kwargs or dict()
        self.components     = components

        n_trials = int(np.ceil(total_trials/n_workers))
        kw = dict(n_trials=n_trials, n_workers=int(n_workers), debug=debug, study_name=study_name,
                  db_name=db_name, keep_db=keep_db, storage=storage, sampler=sampler)
        self.run_args = sc.objdict(kw)

        # Handle other inputs
        self.label      = label
        self.sim        = sim
        self.calib_pars = calib_pars
        self.reseed     = reseed
        self.die        = die
        self.verbose    = verbose
        self.calibrated = False
        self.before_msim = None
        self.after_msim  = None

        # Temporarily store a filename
        self.tmp_filename = 'tmp_calibration_%05i.obj'

        # Initialize sim
        #if not self.sim.initialized:
        #    self.sim.init()

        return

    def run_sim(self, calib_pars=None, label=None):
        """ Create and run a simulation """
        sim = sc.dcp(self.sim)
        if label: sim.label = label

        sim = self.build_fn(sim, calib_pars=calib_pars, **self.build_kwargs)

        # Run the sim
        try:
            sim.run()
            return sim

        except Exception as E:
            if self.die:
                raise E
            else:
                print(f'Encountered error running sim!\nParameters:\n{calib_pars}\nTraceback:\n{sc.traceback()}')
                output = None
                return output

    @staticmethod
    def translate_pars(sim=None, calib_pars=None):
        """ Take the nested dict of calibration pars and modify the sim """

        if 'rand_seed' in calib_pars:
            sim.pars['rand_seed'] = calib_pars.pop('rand_seed')

        for parname, spec in calib_pars.items():
            if 'path' not in spec:
                raise ValueError(f'Cannot map {parname} because "path" is missing from the parameter configuration.')

            p = spec['path']

            # TODO: Allow longer paths
            if len(p) != 3:
                raise ValueError(f'Cannot map {parname} because "path" must be a tuple of length 3.')

            modtype = p[0]
            dkey = p[1]
            dparkey = p[2]
            dparval = spec['value']
            targetpar = sim[modtype][dkey].pars[dparkey]

            if sc.isnumber(targetpar):
                sim[modtype][dkey].pars[dparkey] = dparval
            elif isinstance(targetpar, ss.Dist):
                sim[modtype][dkey].pars[dparkey].set(dparval)
            else:
                errormsg = 'Type not implemented'
                raise ValueError(errormsg)

        return sim

    def _sample_from_trial(self, pardict=None, trial=None):
        """
        Take in an optuna trial and sample from pars, after extracting them from the structure they're provided in
        """
        pars = sc.dcp(pardict)
        for parname, spec in pars.items():

            if 'value' in spec:
                # Already have a value, likely running initial or final values as part of checking the fit
                continue

            if 'suggest_type' in spec:
                suggest_type = spec.pop('suggest_type')
                sampler_fn = getattr(trial, suggest_type)
            else:
                sampler_fn = trial.suggest_float

            path = spec.pop('path', None) # remove path for the sampler
            guess = spec.pop('guess', None) # remove guess for the sampler
            spec['value'] = sampler_fn(name=parname, **spec) # suggest values!
            spec['path'] = path
            spec['guess'] = guess

        return pars

    def _eval_fit(self, sim, **kwargs):
        nll = 0 # Negative log likelihood
        for c in self.components:
            nll += c(sim)

        return nll

    def run_trial(self, trial):
        """ Define the objective for Optuna """
        if self.calib_pars is not None:
            pars = self._sample_from_trial(self.calib_pars, trial)
        else:
            pars = None

        if self.reseed:
            pars['rand_seed'] = trial.suggest_int('rand_seed', 0, 1_000_000) # Choose a random rand_seed

        sim = self.run_sim(pars)

        # Compute fit
        fit = self.eval_fn(sim, **self.eval_kwargs)
        return fit

    def worker(self):
        """ Run a single worker """
        if self.verbose:
            op.logging.set_verbosity(op.logging.DEBUG)
        else:
            op.logging.set_verbosity(op.logging.ERROR)
        study = op.load_study(storage=self.run_args.storage, study_name=self.run_args.study_name, sampler=self.run_args.sampler)
        output = study.optimize(self.run_trial, n_trials=self.run_args.n_trials, callbacks=None)
        return output

    def run_workers(self):
        """ Run multiple workers in parallel """
        if self.run_args.n_workers > 1 and not self.run_args.debug: # Normal use case: run in parallel
            output = sc.parallelize(self.worker, iterarg=self.run_args.n_workers)
        else: # Special case: just run one
            output = [self.worker()]
        return output

    def remove_db(self):
        """ Remove the database file if keep_db is false and the path exists """
        try:
            if 'sqlite' in self.run_args.storage:
                # Delete the file from disk
                if os.path.exists(self.run_args.db_name):
                    os.remove(self.run_args.db_name)
                if self.verbose: print(f'Removed existing calibration file {self.run_args.db_name}')
            else:
                # Delete the study from the database e.g., mysql
                op.delete_study(study_name=self.run_args.study_name, storage=self.run_args.storage)
                if self.verbose: print(f'Deleted study {self.run_args.study_name} in {self.run_args.storage}')
        except Exception as E:
            if self.verbose:
                print('Could not delete study, skipping...')
                print(str(E))
        return

    def make_study(self):
        """ Make a study, deleting one if it already exists """
        if not self.run_args.keep_db:
            self.remove_db()
        if self.verbose: print(self.run_args.storage)
        output = op.create_study(storage=self.run_args.storage, study_name=self.run_args.study_name)
        return output

    def calibrate(self, calib_pars=None, load=False, tidyup=True, **kwargs):
        """
        Perform calibration.

        Args:
            calib_pars (dict): if supplied, overwrite stored calib_pars
            load (bool): whether to load existing trials from the database (if rerunning the same calibration)
            tidyup (bool): whether to delete temporary files from trial runs
            verbose (bool): whether to print output from each trial
            kwargs (dict): if supplied, overwrite stored run_args (n_trials, n_workers, etc.)
        """
        # Load and validate calibration parameters
        if calib_pars is not None:
            self.calib_pars = calib_pars
        self.run_args.update(kwargs) # Update optuna settings

        # Run the optimization
        t0 = sc.tic()
        self.make_study()
        self.run_workers()
        study = op.load_study(storage=self.run_args.storage, study_name=self.run_args.study_name, sampler=self.run_args.sampler)
        self.best_pars = sc.objdict(study.best_params)
        self.elapsed = sc.toc(t0, output=True)

        self.sim_results = []
        if load:
            if self.verbose: print('Loading saved results...')
            for trial in study.trials:
                n = trial.number
                try:
                    filename = self.tmp_filename % trial.number
                    results = sc.load(filename)
                    self.sim_results.append(results)
                    if tidyup:
                        try:
                            os.remove(filename)
                            if self.verbose: print(f'    Removed temporary file {filename}')
                        except Exception as E:
                            errormsg = f'Could not remove {filename}: {str(E)}'
                            if self.verbose: print(errormsg)
                    if self.verbose: print(f'  Loaded trial {n}')
                except Exception as E:
                    errormsg = f'Warning, could not load trial {n}: {str(E)}'
                    if self.verbose: print(errormsg)

        # Compare the results
        self.parse_study(study)

        if self.verbose: print('Best pars:', self.best_pars)

        # Tidy up
        self.calibrated = True
        if not self.run_args.keep_db:
            self.remove_db()

        return self

    def confirm_fit(self, n_runs=25):
        """ Run before and after simulations to validate the fit """

        if self.verbose: print('\nConfirming fit...')

        before_pars = sc.dcp(self.calib_pars)
        for spec in before_pars.values():
            spec['value'] = spec['guess'] # Use guess values

        after_pars = sc.dcp(self.calib_pars)
        for parname, spec in after_pars.items():
            spec['value'] = self.best_pars[parname]

        before_sim = self.build_fn(self.sim, calib_pars=before_pars, **self.build_kwargs)
        before_sim.label = 'Before calibration'
        self.before_msim = ss.MultiSim(before_sim, n_runs=n_runs)
        self.before_msim.run()
        self.before_fits = np.array([self.eval_fn(sim, **self.eval_kwargs) for sim in self.before_msim.sims])

        after_sim = self.build_fn(self.sim, calib_pars=after_pars, **self.build_kwargs)
        after_sim.label = 'Before calibration'
        self.after_msim = ss.MultiSim(after_sim, n_runs=n_runs)
        self.after_msim.run()
        self.after_fits = np.array([self.eval_fn(sim, **self.eval_kwargs) for sim in self.after_msim.sims])

        print(f'Fit with original pars: {self.before_fits}')
        print(f'Fit with best-fit pars: {self.after_fits}')
        if self.after_fits.mean() <= self.before_fits.mean():
            print('✓ Calibration improved fit')
        else:
            print('✗ Calibration did not improve fit, but this sometimes happens stochastically and is not necessarily an error')

        return self.before_fits, self.after_fits

    def parse_study(self, study):
        """Parse the study into a data frame -- called automatically """
        best = study.best_params
        self.best_pars = best

        if self.verbose: print('Making results structure...')
        results = []
        n_trials = len(study.trials)
        failed_trials = []
        for trial in study.trials:
            data = {'index':trial.number, 'mismatch': trial.value}
            for key,val in trial.params.items():
                data[key] = val
            if data['mismatch'] is None:
                failed_trials.append(data['index'])
            else:
                results.append(data)
        if self.verbose: print(f'Processed {n_trials} trials; {len(failed_trials)} failed')

        keys = ['index', 'mismatch'] + list(best.keys())
        data = sc.objdict().make(keys=keys, vals=[])
        for i,r in enumerate(results):
            for key in keys:
                if key not in r:
                    warnmsg = f'Key {key} is missing from trial {i}, replacing with default'
                    print(warnmsg)
                    r[key] = best[key]
                data[key].append(r[key])
        self.study_data = data
        self.df = sc.dataframe.from_dict(data)
        self.df = self.df.sort_values(by=['mismatch']) # Sort
        return

    def to_json(self, filename=None, indent=2, **kwargs):
        """ Convert the results to JSON """
        order = np.argsort(self.df['mismatch'])
        json = []
        for o in order:
            row = self.df.iloc[o,:].to_dict()
            rowdict = dict(index=row.pop('index'), mismatch=row.pop('mismatch'), pars={})
            for key,val in row.items():
                rowdict['pars'][key] = val
            json.append(rowdict)
        self.json = json
        if filename:
            return sc.savejson(filename, json, indent=indent, **kwargs)
        else:
            return json

    def plot_sims(self, **kwargs):
        """
        Plot sims, before and after calibration.

        Args:
            kwargs (dict): passed to MultiSim.plot()
        """
        if self.before_msim is None:
            self.confirm_fit()

        # Turn off jupyter mode so we can receive the figure handles
        jup = ss.options.jupyter if 'jupyter' in ss.options else sc.isjupyter()
        ss.options.jupyter = False

        self.before_msim.reduce()
        fig_before = self.before_msim.plot()
        fig_before.suptitle('Before calibration')

        self.after_msim.reduce()
        fig_after = self.after_msim.plot(fig=fig_before)
        fig_after.suptitle('After calibration')

        ss.options.jupyter = jup

        return fig_before, fig_after

    def plot_trend(self, best_thresh=None, fig_kw=None):
        """
        Plot the trend in best mismatch over time.

        Args:
            best_thresh (int): Define the threshold for the "best" fits, relative to the lowest mismatch value (if None, show all)
            fig_kw (dict): passed to plt.figure()
        """
        df = self.df.sort_values('index') # Make a copy of the dataframe, sorted by trial number
        mismatch = sc.dcp(df['mismatch'].values)
        best_mismatch = np.zeros(len(mismatch))
        for i in range(len(mismatch)):
            best_mismatch[i] = mismatch[:i+1].min()
        smoothed_mismatch = sc.smooth(mismatch)
        fig = plt.figure(**sc.mergedicts(fig_kw))

        ax1 = plt.subplot(2,1,1)
        plt.plot(mismatch, alpha=0.2, label='Original')
        plt.plot(smoothed_mismatch, lw=3, label='Smoothed')
        plt.plot(best_mismatch, lw=3, label='Best')

        ax2 = plt.subplot(2,1,2)
        max_mismatch = mismatch.min()*best_thresh if best_thresh is not None else np.inf
        inds = sc.findinds(mismatch<=max_mismatch)
        plt.plot(best_mismatch, lw=3, label='Best')
        plt.scatter(inds, mismatch[inds], c=mismatch[inds], label='Trials')
        for ax in [ax1, ax2]:
            plt.sca(ax)
            plt.grid(True)
            plt.legend()
            sc.setylim()
            sc.setxlim()
            plt.xlabel('Trial number')
            plt.ylabel('Mismatch')
        sc.figlayout()
        return fig

#############

class eConform(Enum):
    PREVALENT = 0
    INCIDENT = 1

class eLikelihood(Enum):
    BETA_BINOMIAL = 0
    GAMMA_POISSON = 1

class CalibComponent(sc.prettyobj):
    """
    A class to compare a single channel of observed data with output from a
    simulation. The Calibration class can use several CalibComponent objects to
    form an overall understanding of how will a given simulation reflects
    observed data.

    Args:
        name (str) : the of this component. Importantly,
            sim_extract_fn is None, the code will attempt to use the name, like
            "hiv.prevalence" to automatically extract data from the simulation.
        data (df) : pandas Series containing calibration data. The index should be the time in either floating point years or datetime.
        mode (eMode): To handle misaligned timepoints between observed data and simulation output, it's important to know if the data are incident (like new cases) or prevalent (like the number infected).
            If eMode.PREVALENT, simulation outputs will be interpolated to observed timepoints.
            If eMode.INCIDENT, ...
    """
    def __init__(self, name, real_data, sim_data_fn, conform, nll_fn, weight=1):
        self.name = name
        self.real_data = real_data
        self.sim_data_fn = sim_data_fn
        self.weight = weight

        if isinstance(nll_fn, eLikelihood):
            if nll_fn == eLikelihood.BETA_BINOMIAL:
                self.nll_fn = self.beta_binomial
            elif nll_fn == eLikelihood.GAMMA_POISSON:
                self.nll_fn = self.gamma_poisson
        else:
            if not callable(conform):
                msg = f'The nll_fn argument must be an eLikelihood or callable function, not {type(nll_fn)}.'
                raise Exception(msg)
            self.nll_fn = nll_fn

        if isinstance(conform, eConform):
            if conform == eConform.INCIDENT:
                self.conform = self.linear_accum
            elif conform == eConform.PREVALENT:
                self.conform = self.linear_interp
        else:
            if not callable(conform):
                msg = f'The conform argument must be an eConform or callable function, not {type(conform)}.'
                raise Exception(msg)
            self.conform = conform

        pass

    @staticmethod
    def beta_binomial(real_data, sim_data):
        # For the beta-binomial log likelihood, we begin with a Beta(1,1) prior
        # and subsequently observe sim_data['x'] successes (positives) in sim_data['n'] trials (total observations).
        # The result is a Beta(sim_data['x']+1, sim_data['n']-sim_data['x']+1) posterior.
        # We then compare this to the real data, which has real_data['x'] successes (positives) in real_data['n'] trials (total observations).
        # To do so, we use a beta-binomial likelihood:
        # p(x|n, x, a, b) = (n choose x) B(x+a, n-x+b) / B(a, b)
        # where
        #   x=real_data['x']
        #   n=real_data['n']
        #   a=sim_data['x']+1
        #   b=sim_data['n']-sim_data['x']+1 
        # and B is the beta function, B(x, y) = Gamma(x)Gamma(y)/Gamma(x+y)

        # We compute the log of p(x|n, x, a, b), noting that gln is the log of the gamma function
        logL = gln(real_data['n'] + 1) - gln(real_data['x'] + 1) - gln(real_data['n'] - real_data['x'] + 1)
        logL += gln(real_data['x'] + sim_data['x'] + 1) + gln(real_data['n'] - real_data['x'] + sim_data['n'] - sim_data['x'] + 1) - gln(real_data['n'] + sim_data['n'] + 2)
        logL += gln(sim_data['n'] + 2) - gln(sim_data['x'] + 1) - gln(sim_data['n'] - sim_data['x'] + 1)

        return -logL

    @staticmethod
    def gamma_poisson(real_data, sim_data):
        # Also called negative binomial, but parameterized differently
        # The gamma-poisson likelihood is a Poisson likelihood with a gamma-distributed rate parameter
        #

        logL = gammaln(real_data['x'] + sim_data['x'] + 1) \
            - gammaln(real_data['x'] + 1) \
            - gammaln(sim_data['x'] + 1)

        logL += (real_data['x'] + 1) * np.log(real_data['n'])

        logL += (sim_data['x'] + 1) * np.log(sim_data['n'])

        logL -= (real_data['x'] + sim_data['x'] + 1) \
                  * np.log(real_data['n'] + sim_data['n'])

        return -logL

    @staticmethod
    def linear_interp(real_data, sim_data):
        """
        Simply interpolate
        Use for prevalent data like prevalence
        """
        t = real_data.index
        #sim_t = np.array([sc.datetoyear(t.date()) for t in sim_data.index if isinstance(t, dt.date)])

        conformed = pd.DataFrame(index=real_data.index)
        for k in sim_data:
            conformed[k] = np.interp(x=t, xp=sim_data.index, fp=sim_data[k])

        return conformed

    @staticmethod
    def linear_accum(real_data, sim_data):
        """
        Interpolate in the accumulation, then difference.
        Use for incident data like incidence or new_deaths
        """
        t = real_data.index
        t_step = np.diff(t)
        assert np.all(t_step == t_step[0])
        ti = np.append(t, t[-1] + t_step) # Add one more because later we'll diff

        sim_t = np.array([sc.datetoyear(t) for t in sim_data.index if isinstance(t, dt.date)])

        sdi = np.interp(x=ti, xp=sim_t, fp=sim_data.cumsum())
        df = pd.Series(sdi.diff(), index=t)
        return df

    def eval(self, sim):
        # Compute and return the negative log likelihood

        sim_data = self.sim_data_fn(sim) # Extract
        sim_data = self.conform(self.real_data, sim_data) # Conform

        self.nll = self.nll_fn(self.real_data, sim_data) # Negative log likelihood

        return self.weight * np.sum(self.nll)

    def __call__(self, sim):
        return self.eval(sim)

    def __repr__(self):
        return f'Calibration component with name {self.name}'

    def plot(self):
        pass