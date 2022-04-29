import numpy as np
import netCDF4 as nc
import graphblas as gb

_EXT = "sscdf"
_dtype_map = {
    'bool': 'i1',  # no equivalent type
    'int8': 'i1',
    'int16': 'i2',
    'int32': 'i4',
    'int64': 'i8',
    'uint8': 'u1',
    'uint16': 'u2',
    'uint32': 'u4',
    'uint64': 'u8',
    'fp32': 'f4',
    'fp64': 'f8',
}
_class_size_keys = {
    gb.Scalar: [],
    gb.Vector: ['size'],
    gb.Matrix: ['nrows', 'ncols'],
}
_format_keys = {
    # key: (gb_class, [encoded_array_values], [always_true_params])
    # Scalar
    'scalar': (gb.Scalar, ['value'], []),
    'scalar_empty': (gb.Scalar, [], []),
    # Vector
    'sparse': (gb.Vector, ['indices', 'values'], ['sorted_index']),
    'bitmap': (gb.Vector, ['bitmap', 'values'], []),
    'full': (gb.Vector, ['values'], []),
    # Matrix
    'csr': (gb.Matrix, ['indptr', 'col_indices', 'values'], ['sorted_cols']),
    'csc': (gb.Matrix, ['indptr', 'row_indices', 'values'], ['sorted_rows']),
    'hypercsr': (gb.Matrix, ['indptr', 'rows', 'col_indices', 'values'], ['sorted_cols']),
    'hypercsc': (gb.Matrix, ['indptr', 'cols', 'row_indices', 'values'], ['sorted_rows']),
    'bitmapr': (gb.Matrix, ['bitmap', 'values'], []),
    'bitmapc': (gb.Matrix, ['bitmap', 'values'], []),
    'fullr': (gb.Matrix, ['values'], []),
    'fullc': (gb.Matrix, ['values'], []),
    'coor': (gb.Matrix, ['rows', 'cols', 'values'], ['sorted_cols']),
    'cooc': (gb.Matrix, ['rows', 'cols', 'values'], ['sorted_rows']),
}


class SsCdfReadError(Exception):
    pass


class SsCdfWriteError(Exception):
    pass


def info(fp):
    """
    Returns a dict of attributes associated with the
    primary and secondary tensors.
    """
    with Reader(fp) as r:
        ret = r.info()
        if r.names():
            ret['SECONDARY'] = s = {}
            for name in r.names():
                s[name] = r.info(name)
    return ret


def read(fp):
    with Reader(fp) as r:
        return r.read()


def write(fp, x, comment=None):
    with Writer(fp) as w:
        w.write(x, comment=comment)


class Reader:
    def __init__(self, fp):
        self.ds = nc.Dataset(fp, 'r')
        try:
            verstr = self.ds.getncattr('version')
            version = tuple(int(x) for x in verstr.split('.'))
            if version > (1, 0):
                raise SsCdfReadError(f'Incompatible version number (verstr). Reader only handles version <= 1.0')
        except AttributeError:
            raise SsCdfReadError('Missing version attribute')
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tbl):
        self.close()
    
    def close(self):
        if self.ds:
            self.ds.close()

    @staticmethod
    def _parse_attrs(ds):
        """
        Returns a dict of the attributes.
        `ds` can be a Dataset or Group.
        """
        ret = {}
        attrs = ds.ncattrs()
        if 'format' not in attrs:
            tname = "main tensor" if ds.path == '/' else ds.name
            raise SsCdfReadError(f'Missing format for {tname}')
        ret['format'] = fmt = ds.getncattr('format')
        ret['datatype'] = ds.getncattr('datatype')
        if 'comment' in attrs:
            ret['comment'] = ds.getncattr('comment')
        try:
            klass, _, _ = _format_keys[fmt]
        except KeyError:
            raise SsCdfReadError(f'Unknown format found: {fmt}')
        for key in _class_size_keys[klass]:
            ret[key] = ds.variables[key].getValue().data.item()
        return ret

    @staticmethod
    def _load_tensor(ds, name=None):
        info = Reader._parse_attrs(ds)
        fmt = info['format']
        klass, array_keys, always_keys = _format_keys[fmt]
        if klass == gb.Scalar:
            s = gb.Scalar(info['datatype'])
            if 'value' in array_keys:
                s.value = ds.variables['value'].getValue().data
            return s
        import_func = getattr(klass.ss, f"import_{fmt}")
        # Build kwargs for graphblas import
        kwargs = {'format': fmt, 'dtype': info['datatype'], 'name': name}
        for key in array_keys:
            if key == 'values' and len(ds.variables[key].dimensions) == 0:
                # iso-valued
                kwargs['is_iso'] = True
                kwargs[key] = ds.variables[key].getValue().data
            else:
                kwargs[key] = ds.variables[key][:].data
        for key in _class_size_keys[klass]:
            kwargs[key] = info[key]
        for key in always_keys:
            kwargs[key] = True
        return import_func(**kwargs)
    
    def info(self, name=None):
        ds = self.ds
        if name is not None:
            ds = ds.groups[name]
        return self._parse_attrs(ds)
    
    def names(self):
        return list(self.ds.groups)
    
    def read(self, name=None):
        ds = self.ds
        if name is not None:
            ds = ds.groups[name]
        return self._load_tensor(ds, name=name)


class Writer:
    def __init__(self, fp):
        if isinstance(fp, str) and '.' not in fp:
            fp = f"{fp}.{_EXT}"
        self.ds = nc.Dataset(fp, 'w')
        self.ds.setncattr('version', '1.0')

        self._primary_written = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if self.ds:
            self.ds.close()

    @staticmethod
    def _save_tensor(ds, obj, comment=None):
        objtype = gb.utils.output_type(obj)
        if objtype == gb.Scalar:
            exp = {'dtype': obj.dtype.name.lower()}
            if obj.is_empty:
                fmt = 'scalar_empty'
            else:
                fmt = 'scalar'
                exp['value'] = np.array(obj.value, dtype=obj.dtype.np_type)
        elif objtype in (gb.Vector, gb.Matrix):
            fmt = obj.ss.format
            raw = fmt.startswith('full') or fmt.startswith('bitmap')
            exp = obj.ss.export(fmt, raw=raw, sort=True)
        else:
            raise SsCdfWriteError(f"Invalid graphblas object: {objtype}")
        klass, array_keys, _ = _format_keys[fmt]
        # Store array keys
        for key in array_keys:
            arr = exp[key]
            dtype = _dtype_map[gb.dtypes.lookup_dtype(arr.dtype).name.lower()]
            if key == 'value' or (key == 'values' and exp['is_iso']):
                var = ds.createVariable(key, dtype, ())
            else:
                ds.createDimension(key, len(arr))
                var = ds.createVariable(key, dtype, (key,), zlib=True)
            var[:] = arr
        for key in _class_size_keys[klass]:
            var = ds.createVariable(key, 'u8', ())
            var[:] = exp[key]
        # Store metadata
        ds.setncattr('format', fmt)
        ds.setncattr('datatype', obj.dtype.name.lower())
        if comment:
            ds.setncattr('comment', comment)

    def write(self, x, *, name=None, comment=None):
        if name is None:
            if self._primary_written:
                raise SsCdfWriteError("Primary tensor has already been written. Additional tensors require a name.")
            self._save_tensor(self.ds, x, comment=comment)
            self._primary_written = True
        else:
            if name in self.ds.groups:
                raise SsCdfWriteError(f"A tensor named '{name}' already exists.")
            grp = self.ds.createGroup(name)
            self._save_tensor(grp, x, comment=comment)
