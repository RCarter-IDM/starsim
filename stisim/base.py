'''
Base classes for *sim models
'''

import numpy as np
import pandas as pd
import sciris as sc
import functools
from . import utils as ssu
from . import misc as ssm
from . import defaults as ssd
from . import parameters as sspar
from .version import __version__


# Specify all externally visible classes this file defines
__all__ = ['ParsObj', 'Result', 'BaseSim', 'BasePeople', 'FlexDict']

# Default object getter/setter
obj_set = object.__setattr__
base_key = 'uid' # Define the key used by default for getting length, etc.


def rsetattr(obj, attr, val):
    pre, _, post = attr.rpartition('.')
    return setattr(rgetattr(obj, pre) if pre else obj, post, val)


def rgetattr(obj, attr, *args):
    def _getattr(obj, attr):
        return getattr(obj, attr, *args)

    return functools.reduce(_getattr, [obj] + attr.split('.'))

#%% Define simulation classes

class FlexPretty(sc.prettyobj):
    '''
    A class that supports multiple different display options: namely obj.brief()
    for a one-line description and obj.disp() for a full description.
    '''

    def __repr__(self):
        ''' Use brief repr by default '''
        try:
            string = self._brief()
        except Exception as E:
            string = sc.objectid(self)
            string += f'Warning, something went wrong printing object:\n{str(E)}'
        return string

    def _disp(self):
        ''' Verbose output -- use Sciris' pretty repr by default '''
        return sc.prepr(self)

    def disp(self, output=False):
        ''' Print or output verbose representation of the object '''
        string = self._disp()
        if not output:
            print(string)
        else:
            return string

    def _brief(self):
        ''' Brief output -- use a one-line output, a la Python's default '''
        return sc.objectid(self)

    def brief(self, output=False):
        ''' Print or output a brief representation of the object '''
        string = self._brief()
        if not output:
            print(string)
        else:
            return string


class ParsObj(FlexPretty):
    '''
    A class based around performing operations on a self.pars dict.
    '''

    def __init__(self, pars):
        self.update_pars(pars, create=True)
        return


    def __getitem__(self, key):
        ''' Allow sim['par_name'] instead of sim.pars['par_name'] '''
        try:
            return self.pars[key]
        except:
            all_keys = '\n'.join(list(self.pars.keys()))
            errormsg = f'Key "{key}" not found; available keys:\n{all_keys}'
            raise sc.KeyNotFoundError(errormsg)


    def __setitem__(self, key, value):
        ''' Ditto '''
        if key in self.pars:
            self.pars[key] = value
        else:
            all_keys = '\n'.join(list(self.pars.keys()))
            errormsg = f'Key "{key}" not found; available keys:\n{all_keys}'
            raise sc.KeyNotFoundError(errormsg)
        return


    def update_pars(self, pars=None, create=False):
        '''
        Update internal dict with new pars.

        Args:
            pars (dict): the parameters to update (if None, do nothing)
            create (bool): if create is False, then raise a KeyNotFoundError if the key does not already exist
        '''
        if pars is not None:
            if not isinstance(pars, dict):
                raise TypeError(f'The pars object must be a dict; you supplied a {type(pars)}')
            if not hasattr(self, 'pars'):
                self.pars = pars
            if not create:
                available_keys = list(self.pars.keys())
                mismatches = [key for key in pars.keys() if key not in available_keys]
                if len(mismatches):
                    errormsg = f'Key(s) {mismatches} not found; available keys are {available_keys}'
                    raise sc.KeyNotFoundError(errormsg)
            self.pars.update(pars)
        return


class Result(object):
    '''
    Stores a single result -- by default, acts like an array.

    Args:
        name (str): name of this result, e.g. new_infections
        npts (int): if values is None, precreate it to be of this length
        scale (bool): whether or not the value scales by population scale factor
        color (str/arr): default color for plotting (hex or RGB notation)

    **Example**::

        import starsim as ss
        r1 = ss.Result(name='test1', npts=10)
        r1[:5] = 20
        print(r1.values)
    '''

    def __init__(self, name=None, npts=None, scale=True, color=None, n_rows=0, n_copies=0):
        self.name =  name  # Name of this result
        self.scale = scale # Whether or not to scale the result by the scale factor
        if color is None:
            color = '#000000'
        self.color = color # Default color
        if npts is None:
            npts = 0
        npts = int(npts)

        if n_rows > 0:
            self.values = np.zeros((n_rows, npts), dtype=ssd.result_float)
            if n_copies > 0:
                self.values = np.zeros((n_copies, n_rows, npts), dtype=ssd.result_float)
        else:
            self.values = np.zeros(npts, dtype=ssd.result_float)

        self.low  = None
        self.high = None
        return

    def __eq__(self, other):
        return self.npts == other.npts and np.all(self.values == other.values)  and self.scale == other.scale

    def __repr__(self):
        ''' Use pretty repr, like sc.prettyobj, but displaying full values '''
        output  = sc.prepr(self, skip=['values', 'low', 'high'], use_repr=False)
        output += 'values:\n' + repr(self.values)
        if self.low is not None:
            output += '\nlow:\n' + repr(self.low)
        if self.high is not None:
            output += '\nhigh:\n' + repr(self.high)
        return output


    def __getitem__(self, key):
        ''' To allow e.g. result['high'] instead of result.high, and result[5] instead of result.values[5] '''
        if isinstance(key, str):
            output = getattr(self, key)
        else:
            output = self.values.__getitem__(key)
        return output


    def __setitem__(self, key, value):
        ''' To allow e.g. result[:] = 1 instead of result.values[:] = 1 '''
        if isinstance(key, str):
            setattr(self, key, value)
        else:
            self.values.__setitem__(key, value)
        return


    def __len__(self):
        ''' To allow len(result) instead of len(result.values) '''
        return len(self.values)


    def __sum__(self):
        ''' To allow sum(result) instead of result.values.sum() '''
        return self.values.sum()

    # Numpy methods
    def sum(self):
        ''' To allow result.sum() instead of result.values.sum() '''
        return self.values.sum()

    def mean(self):
        ''' To allow result.mean() instead of result.values.mean() '''
        return self.values.mean()

    def median(self):
        ''' To allow result.median() instead of result.values.median() '''
        return self.values.median()

    @property
    def npts(self):
        return len(self.values)

    @property
    def shape(self):
        return self.values.shape


def set_metadata(obj, **kwargs):
    ''' Set standard metadata for an object '''
    obj.created = kwargs.get('created', sc.now())
    obj.version = kwargs.get('version', __version__)
    obj.git_info = kwargs.get('git_info', ssm.git_info())
    return


class BaseSim(ParsObj):
    '''
    The BaseSim class stores various methods useful for the Sim that are not directly
    related to simulating.
    '''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) # Initialize and set the parameters as attributes
        return


    def _disp(self):
        '''
        Print a verbose display of the sim object. Used by repr(). See sim.disp()
        for the user version. Equivalent to sc.prettyobj().
        '''
        return sc.prepr(self)


    def update_pars(self, pars=None, create=False, **kwargs):
        ''' Ensure that metaparameters get used properly before being updated '''

        # Merge everything together
        pars = sc.mergedicts(pars, kwargs)
        if pars:

            # Handle other special parameters
            if pars.get('location'):
                location = pars['location']
                pars['birth_rates'], pars['death_rates'] = sspar.get_births_deaths(location=location) # Set birth and death rates
            # Call update_pars() for ParsObj
            super().update_pars(pars=pars, create=create)

        return


    @property
    def n(self):
        ''' Count the number of people -- if it fails, assume none '''
        try: # By default, the length of the people dict
            return len(self.people)
        except:  # pragma: no cover # If it's None or missing
            return 0


    def copy(self):
        ''' Returns a deep copy of the sim '''
        return sc.dcp(self)


    def export_results(self, for_json=True, filename=None, indent=2, *args, **kwargs):
        '''
        Convert results to dict -- see also to_json().

        The results written to Excel must have a regular table shape, whereas
        for the JSON output, arbitrary data shapes are supported.

        Args:
            for_json (bool): if False, only data associated with Result objects will be included in the converted output
            filename (str): filename to save to; if None, do not save
            indent (int): indent (int): if writing to file, how many indents to use per nested level
            args (list): passed to savejson()
            kwargs (dict): passed to savejson()

        Returns:
            resdict (dict): dictionary representation of the results

        '''

        if not self.results_ready: # pragma: no cover
            errormsg = 'Please run the sim before exporting the results'
            raise RuntimeError(errormsg)

        resdict = {}
        resdict['t'] = self.results['t'] # Assume that there is a key for time

        if for_json:
            resdict['timeseries_keys'] = self.result_keys()
        for key,res in self.results.items():
            if isinstance(res, Result):
                resdict[key] = res.values
                if res.low is not None:
                    resdict[key+'_low'] = res.low
                if res.high is not None:
                    resdict[key+'_high'] = res.high
            elif for_json:
                if key == 'date':
                    resdict[key] = [str(d) for d in res] # Convert dates to strings
                else:
                    if isinstance(res, np.ndarray) and (res.ndim == 1):
                        resdict[key] = res
                    else:
                        print(f'WARNING: skipping {key} from export since not 1D array')
        if filename is not None:
            sc.savejson(filename=filename, obj=resdict, indent=indent, *args, **kwargs)
        return resdict


    def export_pars(self, filename=None, indent=2, *args, **kwargs):
        '''
        Return parameters for JSON export -- see also to_json().

        This method is required so that interventions can specify
        their JSON-friendly representation.

        Args:
            filename (str): filename to save to; if None, do not save
            indent (int): indent (int): if writing to file, how many indents to use per nested level
            args (list): passed to savejson()
            kwargs (dict): passed to savejson()

        Returns:
            pardict (dict): a dictionary containing all the parameter values
        '''
        pardict = {}
        for key in self.pars.keys():
            pardict[key] = self.pars[key]
        if filename is not None:
            sc.savejson(filename=filename, obj=pardict, indent=indent, *args, **kwargs)
        return pardict


    def to_json(self, filename=None, keys=None, tostring=False, indent=2, verbose=False, *args, **kwargs):
        '''
        Export results and parameters as JSON.

        Args:
            filename (str): if None, return string; else, write to file
            keys (str or list): attributes to write to json (default: results, parameters, and summary)
            tostring (bool): if not writing to file, whether to write to string (alternative is sanitized dictionary)
            indent (int): if writing to file, how many indents to use per nested level
            verbose (bool): detail to print
            args (list): passed to savejson()
            kwargs (dict): passed to savejson()

        Returns:
            A unicode string containing a JSON representation of the results,
            or writes the JSON file to disk

        **Examples**::

            json = sim.to_json()
            sim.to_json('results.json')
            sim.to_json('summary.json', keys='summary')
        '''

        # Handle keys
        if keys is None:
            keys = ['results', 'pars']
        keys = sc.promotetolist(keys)

        # Convert to JSON-compatible format
        d = {}
        for key in keys:
            if key == 'results':
                if self.results_ready:
                    resdict = self.export_results(for_json=True)
                    d['results'] = resdict
                else:
                    d['results'] = 'Results not available (Sim has not yet been run)'
            elif key in ['pars', 'parameters']:
                pardict = self.export_pars()
                d['parameters'] = pardict
            elif key == 'summary':
                if self.results_ready:
                    d['summary'] = dict(sc.dcp(self.summary))
                else:
                    d['summary'] = 'Summary not available (Sim has not yet been run)'
            else: # pragma: no cover
                try:
                    d[key] = sc.sanitizejson(getattr(self, key))
                except Exception as E:
                    errormsg = f'Could not convert "{key}" to JSON: {str(E)}; continuing...'
                    print(errormsg)

        if filename is None:
            output = sc.jsonify(d, tostring=tostring, indent=indent, verbose=verbose, *args, **kwargs)
        else:
            output = sc.savejson(filename=filename, obj=d, indent=indent, *args, **kwargs)

        return output


    def to_df(self, date_index=False):
        '''
        Export results to a pandas dataframe

        Args:
            date_index  (bool): if True, use the date as the index
        '''
        resdict = self.export_results(for_json=False)
        resdict = {k:v for k,v in resdict.items() if v.ndim == 1}
        df = pd.DataFrame.from_dict(resdict)
        df['year'] = self.res_yearvec
        new_columns = ['t','year'] + df.columns[1:-1].tolist() # Get column order
        df = df.reindex(columns=new_columns) # Reorder so 't' and 'date' are first
        if date_index:
            df = df.set_index('year')
        return df


    def shrink(self, skip_attrs=None, in_place=True):
        '''
        "Shrinks" the simulation by removing the people and other memory-intensive
        attributes (e.g., some interventions and analyzers), and returns a copy of
        the "shrunken" simulation. Used to reduce the memory required for RAM or
        for saved files.

        Args:
            skip_attrs (list): a list of attributes to skip (remove) in order to perform the shrinking; default "people"
            in_palce (bool): whether to perform the shrinking in place (default), or return a shrunken copy instead

        Returns:
            shrunken (Sim): a Sim object with the listed attributes removed
        '''
        # By default, skip people (~90% of memory), the popdict (which is usually empty anyway), and _orig_pars (which is just a backup)
        if skip_attrs is None:
            skip_attrs = ['popdict', 'people', '_orig_pars']

        # Create the new object, and copy original dict, skipping the skipped attributes
        if in_place:
            shrunken = self
            for attr in skip_attrs:
                setattr(self, attr, None)
        else:
            shrunken = object.__new__(self.__class__)
            shrunken.__dict__ = {k:(v if k not in skip_attrs else None) for k,v in self.__dict__.items()}

        # Don't return if in place
        if in_place:
            return
        else:
            return shrunken


    def save(self, filename=None, keep_people=None, skip_attrs=None, **kwargs):
        '''
        Save to disk as a gzipped pickle.

        Args:
            filename (str or None): the name or path of the file to save to; if None, uses stored
            kwargs: passed to sc.makefilepath()

        Returns:
            filename (str): the validated absolute path to the saved file

        **Example**::

            sim.save() # Saves to a .sim file
        '''

        # Set keep_people based on whether or not we're in the middle of a run
        if keep_people is None:
            if self.initialized and not self.results_ready:
                keep_people = True
            else:
                keep_people = False

        # Handle the filename
        if filename is None:
            filename = self.simfile
        filename = sc.makefilepath(filename=filename, **kwargs)
        self.filename = filename # Store the actual saved filename

        # Handle the shrinkage and save
        if skip_attrs or not keep_people:
            obj = self.shrink(skip_attrs=skip_attrs, in_place=False)
        else:
            obj = self
        ssm.save(filename=filename, obj=obj)

        return filename


    @staticmethod
    def load(filename, *args, **kwargs):
        '''
        Load from disk from a gzipped pickle.
        '''
        sim = ssm.load(filename, *args, **kwargs)
        if not isinstance(sim, BaseSim): # pragma: no cover
            errormsg = f'Cannot load object of {type(sim)} as a Sim object'
            raise TypeError(errormsg)
        return sim


    def _get_ia(self, which, label=None, partial=False, as_list=False, as_inds=False, die=True, first=False):
        ''' Helper method for get_interventions() and get_analyzers(); see get_interventions() docstring '''

        # Handle inputs
        if which not in ['interventions', 'analyzers']: # pragma: no cover
            errormsg = f'This method is only defined for interventions and analyzers, not "{which}"'
            raise ValueError(errormsg)

        ia_list = sc.tolist(self.analyzers if which=='analyzers' else self.interventions) # List of interventions or analyzers
        n_ia = len(ia_list) # Number of interventions/analyzers

        if label == 'summary': # Print a summary of the interventions
            df = pd.DataFrame(columns=['ind', 'label', 'type'])
            for ind,ia_obj in enumerate(ia_list):
                df = df.append(dict(ind=ind, label=str(ia_obj.label), type=type(ia_obj)), ignore_index=True)
            print(f'Summary of {which}:')
            print(df)
            return

        else: # Standard usage case
            position = 0 if first else -1 # Choose either the first or last element
            if label is None: # Get all interventions if no label is supplied, e.g. sim.get_interventions()
                label = np.arange(n_ia)
            if isinstance(label, np.ndarray): # Allow arrays to be provided
                label = label.tolist()
            labels = sc.promotetolist(label)

            # Calculate the matches
            matches = []
            match_inds = []
            for label in labels:
                if sc.isnumber(label):
                    matches.append(ia_list[label]) # This will raise an exception if an invalid index is given
                    label = n_ia + label if label<0 else label # Convert to a positive number
                    match_inds.append(label)
                elif sc.isstring(label) or isinstance(label, type):
                    for ind,ia_obj in enumerate(ia_list):
                        if sc.isstring(label) and ia_obj.label == label or (partial and (label in str(ia_obj.label))):
                            matches.append(ia_obj)
                            match_inds.append(ind)
                        elif isinstance(label, type) and isinstance(ia_obj, label):
                            matches.append(ia_obj)
                            match_inds.append(ind)
                else: # pragma: no cover
                    errormsg = f'Could not interpret label type "{type(label)}": should be str, int, list, or {which} class'
                    raise TypeError(errormsg)

            # Parse the output options
            if as_inds:
                output = match_inds
            elif as_list: # Used by get_interventions()
                output = matches
            else:
                if len(matches) == 0: # pragma: no cover
                    if die:
                        errormsg = f'No {which} matching "{label}" were found'
                        raise ValueError(errormsg)
                    else:
                        output = None
                else:
                    output = matches[position] # Return either the first or last match (usually), used by get_intervention()

            return output


    def get_interventions(self, label=None, partial=False, as_inds=False):
        '''
        Find the matching intervention(s) by label, index, or type. If None, return
        all interventions. If the label provided is "summary", then print a summary
        of the interventions (index, label, type).

        Args:
            label (str, int, Intervention, list): the label, index, or type of intervention to get; if a list, iterate over one of those types
            partial (bool): if true, return partial matches (e.g. 'beta' will match all beta interventions)
            as_inds (bool): if true, return matching indices instead of the actual interventions
        '''
        return self._get_ia('interventions', label=label, partial=partial, as_inds=as_inds, as_list=True)


    def get_intervention(self, label=None, partial=False, first=False, die=True):
        '''
        Like get_interventions(), find the matching intervention(s) by label,
        index, or type. If more than one intervention matches, return the last
        by default. If no label is provided, return the last intervention in the list.

        Args:
            label (str, int, Intervention, list): the label, index, or type of intervention to get; if a list, iterate over one of those types
            partial (bool): if true, return partial matches (e.g. 'beta' will match all beta interventions)
            first (bool): if true, return first matching intervention (otherwise, return last)
            die (bool): whether to raise an exception if no intervention is found
        '''
        return self._get_ia('interventions', label=label, partial=partial, first=first, die=die, as_inds=False, as_list=False)


    def get_analyzers(self, label=None, partial=False, as_inds=False):
        '''
        Same as get_interventions(), but for analyzers.
        '''
        return self._get_ia('analyzers', label=label, partial=partial, as_list=True, as_inds=as_inds)


    def get_analyzer(self, label=None, partial=False, first=False, die=True):
        '''
        Same as get_intervention(), but for analyzers.
        '''
        return self._get_ia('analyzers', label=label, partial=partial, first=first, die=die, as_inds=False, as_list=False)


#%% Define people classes

class BasePeople(FlexPretty):
    '''
    A class to handle all the boilerplate for people -- note that as with the
    BaseSim vs Sim classes, everything interesting happens in the People class,
    whereas this class exists to handle the less interesting implementation details.
    '''

    def __init__(self, pars):
        ''' Initialize essential attributes used for filtering '''
        
        # Set meta attribute here, because BasePeople methods expect it to exist
        self.meta = ssd.PeopleMeta()  # Store list of keys and dtypes
        self.meta.validate()

        # Define lock attribute here, since BasePeople.lock()/unlock() requires it
        self._lock = False # Prevent further modification of keys

        # Load other attributes
        self.set_pars(pars)
        self.version = __version__ # Store version info
        self.contacts = None
        self.t = 0 # Keep current simulation time

        # Private variables relating to dynamic allocation
        self._data = dict()
        self._n = self.pars['n_agents']  # Number of agents (initial)
        self._s = self._n # Underlying array sizes
        self._inds = None # No filtering indices
        
        return


    def initialize(self):
        ''' Initialize underlying storage and map arrays '''
        for state in self.meta.states_to_set:
            self._data[state.name] = state.new(self.pars, self._n)
        self._map_arrays()
        self['uid'][:] = np.arange(self.pars['n_agents'])
        return


    def __len__(self):
        ''' Length of people '''
        try:
            arr = getattr(self, base_key)
            return len(arr)
        except Exception as E:
            print(f'Warning: could not get length of People (could not get self.{base_key}: {E})')
            return 0
    
    
    def _len_arrays(self):
        ''' Length of underlying arrays '''
        return len(self._data[base_key])


    def set_pars(self, pars=None):
        '''
        Re-link the parameters stored in the people object to the sim containing it,
        and perform some basic validation.
        '''
        orig_pars = self.__dict__.get('pars') # Get the current parameters using dict's get method
        if pars is None:
            if orig_pars is not None: # If it has existing parameters, use them
                pars = orig_pars
            else:
                pars = {}
        elif sc.isnumber(pars): # Interpret as a population size
            pars = {'n_agents':pars} # Ensure it's a dictionary

        # Copy from old parameters to new parameters
        if isinstance(orig_pars, dict):
            for k,v in orig_pars.items():
                if k not in pars:
                    pars[k] = v

        # Do minimal validation -- needed here since n_agents should be converted to an int when first set
        if 'n_agents' not in pars:
            errormsg = f'The parameter "n_agents" must be included in a population; keys supplied were:\n{sc.newlinejoin(pars.keys())}'
            raise sc.KeyNotFoundError(errormsg)
        pars['n_agents'] = int(pars['n_agents'])
        pars.setdefault('location', None)
        self.pars = pars # Actually store the pars
        return


    def validate(self, sim_pars=None, verbose=False):
        '''
        Perform validation on the People object.

        Args:
            sim_pars (dict): dictionary of parameters from the sim to ensure they match the current People object
            verbose (bool): detail to print
        '''

        # Check that parameters match
        if sim_pars is not None:
            mismatches = {}
            keys = ['n_agents', 'location'] # These are the keys used in generating the population
            for key in keys:
                sim_v = sim_pars.get(key)
                ppl_v = self.pars.get(key)
                if sim_v is not None and ppl_v is not None:
                    if sim_v != ppl_v:
                        mismatches[key] = sc.objdict(sim=sim_v, people=ppl_v)
            if len(mismatches):
                errormsg = 'Validation failed due to the following mismatches between the sim and the people parameters:\n'
                for k,v in mismatches.items():
                    errormsg += f'  {k}: sim={v.sim}, people={v.people}'
                raise ValueError(errormsg)

        # Check that the length of each array is consistent
        expected_len = len(self)
        for key in self.keys():
            if self[key].ndim == 1:
                actual_len = len(self[key])
            if actual_len != expected_len: # pragma: no cover
                errormsg = f'Length of key "{key}" did not match population size ({actual_len} vs. {expected_len})'
                raise IndexError(errormsg)

        return


    def lock(self):
        ''' Lock the people object to prevent keys from being added '''
        self._lock = True
        return


    def unlock(self):
        ''' Unlock the people object to allow keys to be added '''
        self._lock = False
        return

    def _grow(self, n):
        """
        Increase the number of agents stored

        Automatically reallocate underlying arrays if required
        
        Args:
            n (int): Number of new agents to add
        """
        orig_n = self._n
        new_total = orig_n + n
        if new_total > self._s:
            n_new = max(n, int(self._s / 2))  # Minimum 50% growth
            for state in self.meta.states_to_set:
                self._data[state.name] = np.concatenate([self._data[state.name], state.new(self.pars, n_new)], axis=self._data[state.name].ndim-1)
            for state_name, state in self.module_states.items():
                self._data[state_name] = np.concatenate([self._data[state_name], state.new(self.pars, n_new)],
                                                        axis=self._data[state_name].ndim - 1)
            self._s += n_new
        self._n += n
        self._map_arrays()
        new_inds = np.arange(orig_n, self._n)
        return new_inds


    def _map_arrays(self):
        """
        Set main simulation attributes to be views of the underlying data

        This method should be called whenever the number of agents required changes
        (regardless of whether or not the underlying arrays have been resized)
        """

        row_inds = slice(None, self._n)

        for k in self.state_names:
            arr = self._data[k]
            if arr.ndim == 1:
                rsetattr(self, k, arr[row_inds])
            elif arr.ndim == 2:
                rsetattr(self, k, arr[:, row_inds])
            else:
                errormsg = 'Can only operate on 1D or 2D arrays'
                raise TypeError(errormsg)

        return


    def __getitem__(self, key):
        ''' Allow people['attr'] instead of getattr(people, 'attr')
            If the key is an integer, alias `people.person()` to return a `Person` instance
        '''
        if isinstance(key, int):
            return self.person(key)
        else:
            return self.__getattribute__(key)


    def __setitem__(self, key, value):
        ''' Ditto '''
        if self._lock and key not in self.__dict__: # pragma: no cover
            errormsg = f'Key "{key}" is not a current attribute of people, and the people object is locked; see people.unlock()'
            raise AttributeError(errormsg)
        return self.__setattr__(key, value)


    # def __setattr__(self, attr, value):
    #     ''' Ditto '''
    #     if hasattr(self, '_data') and attr in self._data:
    #         # Prevent accidentally overwriting a view with an actual array - if this happens, the updated values will
    #         # be lost the next time the arrays are resized
    #         raise Exception('Cannot assign directly to a dynamic array view - must index into the view instead e.g. `people.uid[:]=`')
    #     else:   # If not initialized, rely on the default behavior
    #         obj_set(self, attr, value)
    #     return


    def __iter__(self):
        ''' Iterate over people '''
        for i in range(len(self)):
            yield self[i]


    def __add__(self, people2):
        ''' Combine two people arrays '''
        newpeople = sc.dcp(self)
        keys = list(self.keys())
        for key in keys:
            npval = newpeople[key]
            p2val = people2[key]
            if npval.ndim == 1:
                newpeople.set(key, np.concatenate([npval, p2val], axis=0), die=False) # Allow size mismatch
            elif npval.ndim == 2:
                newpeople.set(key, np.concatenate([npval, p2val], axis=1), die=False)
            else:
                errormsg = f'Not sure how to combine arrays of {npval.ndim} dimensions for {key}'
                raise NotImplementedError(errormsg)

        # Validate
        newpeople.pars['n_agents'] += people2.pars['n_agents']
        newpeople.validate()

        # Reassign UIDs so they're unique
        newpeople.set('uid', np.arange(len(newpeople)))

        return newpeople

    def addtoself(self, people2):
        ''' Combine two people arrays, avoiding dcp '''
        keys = list(self.keys())
        for key in keys:
            npval = self[key]
            p2val = people2[key]
            if npval.ndim == 1:
                self.set(key, np.concatenate([npval, p2val], axis=0), die=False) # Allow size mismatch
            elif npval.ndim == 2:
                self.set(key, np.concatenate([npval, p2val], axis=1), die=False)
            else:
                errormsg = f'Not sure how to combine arrays of {npval.ndim} dimensions for {key}'
                raise NotImplementedError(errormsg)

        # Reassign UIDs so they're unique
        self.set('uid', np.arange(len(self)))

        return

    def __radd__(self, people2):
        ''' Allows sum() to work correctly '''
        if not people2: return self
        else:           return self.__add__(people2)


    def _brief(self):
        '''
        Return a one-line description of the people -- used internally and by repr();
        see people.brief() for the user version.
        '''
        try:
            string   = f'People(n={len(self):0n})'
        except Exception as E: # pragma: no cover
            string = sc.objectid(self)
            string += f'Warning, sim appears to be malformed:\n{str(E)}'
        return string


    def set(self, key, value, die=True):
        self[key][:] = value[:] # nb. this will raise an exception the shapes don't match, and will automatically cast the value to the existing type


    def get(self, key):
        ''' Convenience method -- key can be string or list of strings '''
        if isinstance(key, str):
            return self[key]
        elif isinstance(key, list):
            arr = np.zeros((len(self), len(key)))
            for k,ky in enumerate(key):
                arr[:,k] = self[ky]
            return arr


    @property
    def is_female(self):
        ''' Boolean array of everyone female '''
        return self.sex == 0

    @property
    def is_female_alive(self):
        ''' Boolean array of everyone female and alive'''
        return ((1-self.sex) * self.alive).astype(bool)

    @property
    def is_male(self):
        ''' Boolean array of everyone male '''
        return self.sex == 1

    @property
    def is_male_alive(self):
        ''' Boolean array of everyone male and alive'''
        return (self.sex * self.alive).astype(bool)

    @property
    def f_inds(self):
        ''' Indices of everyone female '''
        return self.true('is_female')

    @property
    def m_inds(self):
        ''' Indices of everyone male '''
        return self.true('is_male')

    @property
    def int_age(self):
        ''' Return ages as an integer '''
        return np.array(self.age, dtype=np.int64)

    @property
    def round_age(self):
        ''' Rounds age up to the next highest integer'''
        return np.array(np.ceil(self.age))

    @property
    def dt_age(self):
        ''' Return ages rounded to the nearest whole timestep '''
        dt = self['pars']['dt']
        return np.round(self.age*1/dt) / (1/dt)

    @property
    def is_active(self):
        ''' Boolean array of everyone sexually active i.e. past debut '''
        return ((self.age>self.debut) * (self.alive)).astype(bool)

    @property
    def alive_inds(self):
        ''' Indices of everyone alive '''
        return self.true('alive')
    
    @property
    def n_alive(self):
        ''' Number of people alive '''
        return len(self.alive_inds)
    
    def true(self, key):
        ''' Return indices matching the condition '''
        return self[key].nonzero()[-1]

    def false(self, key):
        ''' Return indices not matching the condition '''
        return (~self[key]).nonzero()[-1]

    def defined(self, key):
        ''' Return indices of people who are not-nan '''
        return (~np.isnan(self[key])).nonzero()[0]

    def undefined(self, key):
        ''' Return indices of people who are nan '''
        return np.isnan(self[key]).nonzero()[0]

    def count(self, key, weighted=True):
        ''' Count the number of people for a given key '''
        inds = self[key].nonzero()[0]
        if weighted:
            out = self.scale[inds].sum()
        else:
            out = len(inds)
        return out
    
    def count_any(self, key, weighted=True):
        ''' Count the number of people for a given key for a 2D array if any value matches '''
        inds = self[key].sum(axis=0).nonzero()[0]
        if weighted:
            out = self.scale[inds].sum()
        else:
            out = len(inds)
        return out

    def keys(self):
        ''' Returns keys for all non-derived properties of the people object '''
        return [state.name for state in self.meta.states_to_set]

    def layer_keys(self):
        ''' Get the available contact keys -- try contacts  '''
        try:
            keys = list(self.contacts.keys())
        except: # If not fully initialized
            keys = []
        return keys

    def indices(self):
        ''' The indices of each people array '''
        return np.arange(len(self))

    def to_df(self):
        ''' Convert to a Pandas dataframe '''
        df = pd.DataFrame.from_dict({key:self[key] for key in self.keys()})
        return df

    def to_arr(self):
        ''' Return as numpy array '''
        arr = np.empty((len(self), len(self.keys())), dtype=ssd.default_float)
        for k,key in enumerate(self.keys()):
            if key == 'uid':
                arr[:,k] = np.arange(len(self))
            else:
                arr[:,k] = self[key]
        return arr

    def to_list(self):
        ''' Return all people as a list '''
        return list(self)


class FlexDict(dict):
    '''
    A dict that allows more flexible element access: in addition to obj['a'],
    also allow obj[0]. Lightweight implementation of the Sciris odict class.
    '''

    def __getitem__(self, key):
        ''' Lightweight odict -- allow indexing by number, with low performance '''
        try:
            return super().__getitem__(key)
        except KeyError as KE:
            try: # Assume it's an integer
                dictkey = self.keys()[key]
                return self[dictkey]
            except:
                raise sc.KeyNotFoundError(KE) # Raise the original error

    def keys(self):
        return list(super().keys())

    def values(self):
        return list(super().values())

    def items(self):
        return list(super().items())


class Layer(FlexDict):
    '''
    A small class holding a single layer of contact edges (connections) between people.

    The input is typically arrays including: person 1 of the connection, person 2 of
    the connection, the weight of the connection, the duration and start/end times of
    the connection. Connections are undirected; each person is both a source and sink.

    This class is usually not invoked directly by the user, but instead is called
    as part of the population creation.

    Args:
        p1 (array): an array of N connections, representing people on one side of the connection
        p2 (array): an array of people on the other side of the connection
        acts (array): an array of number of acts per timestep for each connection
        dur (array): duration of the connection
        start (array): start time of the connection
        end (array): end time of the connection
        label (str): the name of the layer (optional)
        kwargs (dict): other keys copied directly into the layer

    Note that all arguments (except for label) must be arrays of the same length,
    although not all have to be supplied at the time of creation (they must all
    be the same at the time of initialization, though, or else validation will fail).

    **Examples**::

        # Generate an average of 10 contacts for 1000 people
        n = 10_000
        n_people = 1000
        p1 = np.random.randint(n_people, size=n)
        p2 = np.random.randint(n_people, size=n)
        beta = np.ones(n)
        layer = hpv.Layer(p1=p1, p2=p2, beta=beta, label='rand')
        layer = hpv.Layer(dict(p1=p1, p2=p2, beta=beta), label='rand') # Alternate method

        # Convert one layer to another with extra columns
        index = np.arange(n)
        self_conn = p1 == p2
        layer2 = hpv.Layer(**layer, index=index, self_conn=self_conn, label=layer.label)
    '''

    def __init__(self, *args, transmission='horizontal', label=None, **kwargs):
        self.meta = {
            'p1':     ssd.default_int,   # p1
            'p2':     ssd.default_int,   # p2
            'acts':  ssd.default_float, # Default number of acts for this contact type
            'dur':   ssd.default_float, # Duration of partnership
            'start': ssd.default_int, # Date of partnership start
            'end':   ssd.default_float, # Date of partnership end
            'beta':  ssd.default_float,
        }
        self.transmission = transmission  # "vertical" or "horizontal", determines whether transmission is bidirectional
        self.basekey = 'p1' # Assign a base key for calculating lengths and performing other operations
        self.label = label

        # Handle args
        kwargs = sc.mergedicts(*args, kwargs)

        # Initialize the keys of the layers
        for key,dtype in self.meta.items():
            self[key] = np.empty((0,), dtype=dtype)

        # Set data, if provided
        for key,value in kwargs.items():
            self[key] = np.array(value, dtype=self.meta.get(key))

        # Set beta and acts if not provided
        keys = ['beta', 'acts']
        for key in keys:
            if key not in kwargs.keys():
                self[key] = np.ones(len(self), dtype=self.meta[key])

        return

    def initialize(self):
        pass

    def __len__(self):
        try:
            return len(self[self.basekey])
        except: # pragma: no cover
            return 0

    def __repr__(self):
        ''' Convert to a dataframe for printing '''
        namestr = self.__class__.__name__
        labelstr = f'"{self.label}"' if self.label else '<no label>'
        keys_str = ', '.join(self.keys())
        output = f'{namestr}({labelstr}, {keys_str})\n' # e.g. Layer("r", f, m, beta)
        output += self.to_df().__repr__()
        return output

    def __contains__(self, item):
        """
        Check if a person is present in a layer

        Args:
            item: Person index

        Returns: True if person index appears in any interactions

        """
        return (item in self['f']) or (item in self['m'])

    @property
    def members(self):
        """
        Return sorted array of all members
        """
        return np.unique([self['p1'], self['p2']])

    def meta_keys(self):
        ''' Return the keys for the layer's meta information -- i.e., f, m, beta, any others '''
        return self.meta.keys()

    def validate(self, force=True):
        '''
        Check the integrity of the layer: right types, right lengths.

        If dtype is incorrect, try to convert automatically; if length is incorrect,
        do not.
        '''
        n = len(self[self.basekey])
        for key,dtype in self.meta.items():
            if dtype:
                actual = self[key].dtype
                expected = dtype
                if actual != expected:
                    self[key] = np.array(self[key], dtype=expected) # Probably harmless, so try to convert to correct type
            actual_n = len(self[key])
            if n != actual_n:
                errormsg = f'Expecting length {n} for layer key "{key}"; got {actual_n}' # We can't fix length mismatches
                raise TypeError(errormsg)
        return

    def get_inds(self, inds, remove=False):
        '''
        Get the specified indices from the edgelist and return them as a dict.

        Args:
            inds (int, array, slice): the indices to be removed
        '''
        output = {}
        for key in self.meta_keys():
            output[key] = self[key][inds] # Copy to the output object
            if remove:
                self[key] = np.delete(self[key], inds) # Remove from the original
        return output

    def pop_inds(self, inds):
        '''
        "Pop" the specified indices from the edgelist and return them as a dict.
        Returns in the right format to be used with layer.append().

        Args:
            inds (int, array, slice): the indices to be removed
        '''
        return self.get_inds(inds, remove=True)

    def append(self, contacts):
        '''
        Append contacts to the current layer.

        Args:
            contacts (dict): a dictionary of arrays with keys f,m,beta, as returned from layer.pop_inds()
        '''
        for key in self.keys():
            new_arr = contacts[key]
            n_curr = len(self[key]) # Current number of contacts
            n_new = len(new_arr) # New contacts to add
            n_total = n_curr + n_new # New size
            self[key] = np.resize(self[key], n_total) # Resize to make room, preserving dtype
            self[key][n_curr:] = new_arr # Copy contacts into the layer
        return

    def to_df(self):
        ''' Convert to dataframe '''
        df = pd.DataFrame.from_dict(self)
        return df

    def from_df(self, df, keys=None):
        ''' Convert from a dataframe '''
        if keys is None:
            keys = self.meta_keys()
        for key in keys:
            self[key] = df[key].to_numpy()
        return self

    def to_graph(self): # pragma: no cover
        '''
        Convert to a networkx DiGraph

        **Example**::

            import networkx as nx
            sim = hpv.Sim(n_agents=20, pop_type='hybrid').run()
            G = sim.people.contacts['h'].to_graph()
            nx.draw(G)
        '''
        import networkx as nx
        data = [np.array(self[k], dtype=dtype).tolist() for k,dtype in [('p1', int), ('p2', int), ('beta', float)]]
        G = nx.DiGraph()
        G.add_weighted_edges_from(zip(*data), weight='beta')
        nx.set_edge_attributes(G, self.label, name='layer')
        return G

    def find_contacts(self, inds, as_array=True):
        """
        Find all contacts of the specified people

        For some purposes (e.g. contact tracing) it's necessary to find all of the contacts
        associated with a subset of the people in this layer. Since contacts are bidirectional
        it's necessary to check both P1 and P2 for the target indices. The return type is a Set
        so that there is no duplication of indices (otherwise if the Layer has explicit
        symmetric interactions, they could appear multiple times). This is also for performance so
        that the calling code doesn't need to perform its own unique() operation. Note that
        this cannot be used for cases where multiple connections count differently than a single
        infection, e.g. exposure risk.

        Args:
            inds (array): indices of people whose contacts to return
            as_array (bool): if true, return as sorted array (otherwise, return as unsorted set)

        Returns:
            contact_inds (array): a set of indices for pairing partners

        Example: If there were a layer with
        - P1 = [1,2,3,4]
        - P2 = [2,3,1,4]
        Then find_contacts([1,3]) would return {1,2,3}
        """

        # Check types
        if not isinstance(inds, np.ndarray):
            inds = sc.promotetoarray(inds)
        if inds.dtype != np.int64:  # pragma: no cover # This is int64 since indices often come from hpv.true(), which returns int64
            inds = np.array(inds, dtype=np.int64)

        # Find the contacts
        contact_inds = ssu.find_contacts(self['p1'], self['p2'], inds)
        if as_array:
            contact_inds = np.fromiter(contact_inds, dtype=ssd.default_int)
            contact_inds.sort()  # Sorting ensures that the results are reproducible for a given seed as well as being identical to previous versions of HPVsim

        return contact_inds

    def update(self):
        pass
