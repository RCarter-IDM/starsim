==========
What's new
==========

.. currentmodule:: starsim

All notable changes to the codebase are documented in this file. Changes that may result in differences in model output, or are required in order to run an old parameter set with the current version, are flagged with the term "Regression information".


Version 0.3.3 (2024-04-16)
--------------------------
- Changed Ebola model transmission logic.
- Fixed bug with module names not being preserved with multiple initialization.
- *GitHub info*: PR `463 <https://github.com/starsimhub/starsim/pull/463>`_


Version 0.3.2 (2024-04-08)
--------------------------
- Change to syphilis model to permit latent transmission.
- *GitHub info*: PR `450 <https://github.com/starsimhub/starsim/pull/450>`_


Version 0.3.1 (2024-03-31)
--------------------------
- Added SIS model.
- Fixes distribution initialization.
- Allows interventions and analyzers to be functions.
- Tidies up tests.
- Performance improvements in ``UIDArray`` (~3x faster for large numbers of agents).
- *GitHub info*: PR `428 <https://github.com/amath-idm/stisim/pull/428>`_


Version 0.3.0 (2024-03-30)
--------------------------

New RNGs & distributions
~~~~~~~~~~~~~~~~~~~~~~~~
- Replaces ``ss.SingleRNG()``, ``ss.MultiRNG()``, ``ss.ScipyDistribution()``, and ``ss.ScipyHistogram()`` with a single ``ss.Dist()`` class. The ``starsim.random`` and ``starsim.distributions`` submodules have been removed, and ``starsim.dists`` has been added.
- The ``ss.Dist`` class uses ``np.random.default_rng()`` rather than ``scipy.stats`` by default, although a ``scipy.stats`` distribution can be supplied as an alternative. This is up to 4x faster (including, critically, for Bernoulli distributions).
- Also removes ``ss.options.multirng`` (the new version is equivalent to it being always on).
- Removes duplicate logic for transmission (``make_new_cases()``)
- Adds new custom distributions such as ``ss.choice()`` and ``ss.delta()``.
- These distributions can be called directly, e.g. ``dist = ss.weibull(c=2); dist(5)`` will return 5 random variates from a Weibull distribution.
- Instead of being manually initialized based on the name, the ``Sim`` object is parsed and all distributions will be initialized with a unique identifier based on their place in the object (e.g. ``sim.diseases.sir.pars.dur_inf``), which is used to set their unique seed.

Other changes
~~~~~~~~~~~~~
- This PR also fixes bugs with lognormal parameters, and makes it clear whether the parameters are for the *implicit* normal distribution (``ss.lognorm_im()``, the NumPy/SciPy default, equivalent to ``ss.lognorm_mean()`` previously) or the "explicit" lognormal distribution (``ss.lognorm_ex()``, equivalent to ``ss.lognorm()`` previously).
- Renames ``ss.dx``, ``ss.tx``, ``ss.vx`` to``ss.Dx``, ``ss.Tx``, ``ss.Vx``.
- Removed ``set_numba_seed()`` as a duplicate of ``set_seed()``.
- *GitHub info*: PR `392 <https://github.com/amath-idm/stisim/pull/392>`_

Version 0.2.10 (2024-03-18)
---------------------------
- SIR duration of infection now accounts for dt
- Reworked sir_vaccine to modify rel_sus instead of moving agents from susceptible to recovered.
- n_years no longer necessarily an integer
- *GitHub info*: PR `389 <https://github.com/amath-idm/stisim/pull/389>`_


Version 0.2.9 (2024-03-18)
--------------------------
- Renames and extends the multirng option in settings, now called 'rng', which set how random numbers are handled in Starsim with three options:

    - "centralized" uses the centralized numpy random number generator for all distributions.
    - "single" uses a separate (SingleRNG) random number generator for each distribution.
    - "multi" uses a separate (MultiRNG) random number generator for each distribution.
- *GitHub info*: PR `349 <https://github.com/amath-idm/stisim/pull/349>`_


Version 0.2.8 (2024-03-13)
--------------------------
- Add ``ss.demo()`` to quickly create a default simulation.
- *GitHub info*: PR `380 <https://github.com/amath-idm/stisim/pull/380>`_


Version 0.2.7 (2024-03-09)
--------------------------
- Update ``StaticNet`` with defaults and correct argument passing
- *GitHub info*: PR `339 <https://github.com/amath-idm/stisim/pull/339>`_


Version 0.2.6 (2024-02-29)
--------------------------
- Make random number streams independent for SIR
- *GitHub info*: PR `307 <https://github.com/amath-idm/stisim/pull/307>`_


Version 0.2.5 (2024-02-29)
--------------------------
- Improve logic for making new cases with multi-RNG
- *GitHub info*: PR `337 <https://github.com/amath-idm/stisim/pull/337>`_


Version 0.2.4 (2024-02-27)
--------------------------
- Improve ``sim.summarize()``
- Improve ``sim.plot()``
- Improve SIR model defaults
- *GitHub info*: PR `320 <https://github.com/amath-idm/stisim/pull/320>`_


Version 0.2.3 (2024-02-26)
--------------------------
- Removes ``STI`` class
- Changes default death rate from units of per person to per thousand people
- Allows ``ss.Sim(demographics=True)`` to enable births and deaths
- Fix pickling of ``State`` objects
- Rename ``networks.py`` to ``network.py``, and fix HIV mortality
- *GitHub info*: PRs `305 <https://github.com/amath-idm/stisim/pull/305>`_, `308 <https://github.com/amath-idm/stisim/pull/308>`_, `317 <https://github.com/amath-idm/stisim/pull/317>`_


Version 0.2.2 (2024-02-26)
--------------------------
- Add the ``Samples`` class
- *GitHub info*: PR `311 <https://github.com/amath-idm/stisim/pull/311>`_


Version 0.2.1 (2024-02-22)
--------------------------
- Only remove dead agents on certain timesteps
- *GitHub info*: PR `294 <https://github.com/amath-idm/stisim/pull/294>`_


Version 0.2.0 (2024-02-15)
--------------------------
- Code reorganization, including making ``networks.py`` and ``disease.py`` to the top level
- Networks moved from ``People`` to ``Sim``
- Various classes renamed (e.g. ``FusedArray`` to ``UIDArray``, ``STI`` to ``Infection``)
- Better type checking
- Added ``MultiSim``
- Added cholera, measles, and Ebola
- Added vaccination
- More flexible inputs
- *GitHub info*: PR `235 <https://github.com/amath-idm/stisim/pull/235>`_


Version 0.1.8 (2024-01-30)
--------------------------
- Transmission based on number of contacts
- *GitHub info*: PR `220 <https://github.com/amath-idm/stisim/pull/220>`_


Version 0.1.7 (2024-01-27)
--------------------------
- Performance enhancement for disease transmission, leading to a 10% decrease in runtime.
- *GitHub info*: PR `217 <https://github.com/amath-idm/stisim/pull/217>`_


Version 0.1.6 (2024-01-23)
--------------------------
- Adds template interventions and products for diagnostics and treatment
- Adds syphilis screening & treatment interventions
- *GitHub info*: PR `210 <https://github.com/amath-idm/stisim/pull/210>`_


Version 0.1.5 (2024-01-23)
--------------------------
- Renamed ``stisim`` to ``starsim``.
- *GitHub info*: PR `200 <https://github.com/amath-idm/stisim/pull/200>`_


Version 0.1.4 (2024-01-23)
--------------------------
- Adds a syphilis module
- *GitHub info*: PR `206 <https://github.com/amath-idm/stisim/pull/206>`_


Version 0.1.3 (2024-01-22)
--------------------------
- Read in age distributions for people initializations 
- *GitHub info*: PR `205 <https://github.com/amath-idm/stisim/pull/205>`_


Version 0.1.2 (2024-01-19)
--------------------------
- Functionality for converting birth & fertility data to a callable parameter within SciPy distributions
- *GitHub info*: PR `203 <https://github.com/amath-idm/stisim/pull/203>`_


Version 0.1.1 (2024-01-12)
--------------------------
- Improving performance of MultiRNG
- Now factoring the timestep, ``dt``, into transmission calculations
- *GitHub info*: PRs `204 <https://github.com/amath-idm/stisim/pull/204>`_


Version 0.1.0 (2023-12-10)
--------------------------
- Allows SciPy distributions to be used as parameters
- Optionally use multiple random number streams and other tricks to maintain coherence between simulations
- Adding functionality to convert death rate data to a callable parameter within a SciPy distribution
- *GitHub info*: PRs `170 <https://github.com/amath-idm/stisim/pull/170>`_ and `202 <https://github.com/amath-idm/stisim/pull/202>`_


Version 0.0.8 (2023-10-04)
--------------------------
- Enable removing people from simulations following death
- *GitHub info*: PR `121 <https://github.com/amath-idm/stisim/pull/121>`_


Version 0.0.7 (2023-09-08)
--------------------------
- Refactor distributions to use new Distribution class
- *GitHub info*: PR `112 <https://github.com/amath-idm/stisim/pull/112>`_


Version 0.0.6 (2023-08-30)
--------------------------
- Changes agent IDs from index-based to UID-based
- Allows states to store their own data and live within modules
- *GitHub info*: PR `88 <https://github.com/amath-idm/stisim/pull/88>`_


Version 0.0.5 (2023-08-29)
--------------------------
- Refactor file structure 
- *GitHub info*: PRs `77 <https://github.com/amath-idm/stisim/pull/77>`_ and `86 <https://github.com/amath-idm/stisim/pull/86>`_


Version 0.0.2 (2023-06-29)
--------------------------
- Adds in basic Starsim functionality
- *GitHub info*: PR `17 <https://github.com/amath-idm/stisim/pull/17>`__


Version 0.0.1 (2023-06-22)
--------------------------
- Initial version.
