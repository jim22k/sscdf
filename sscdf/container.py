import os
import json
import netCDF4 as nc
import graphblas as gb
from .highlevel import deconstruct, construct, validate_metadata, _format_keys
from .exceptions import SsCdfError, SsCdfReadError, SsCdfWriteError

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
    'float32': 'f4',
    'float64': 'f8',
}


class Reader:
    def __init__(self, file):
        if hasattr(file, 'close'):
            self.ds = nc.Dataset('.', 'r', memory=file.read())
        else:
            if '.' not in file:
                if not os.path.exists(file) and os.path.exists(f'{file}.{_EXT}'):
                    file = f'{file}.{_EXT}'
            self.ds = nc.Dataset(file, 'r')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tbl):
        self.close()

    def close(self):
        if self.ds:
            self.ds.close()

    @staticmethod
    def _parse_metadata(ds):
        """
        Returns the metadata.
        `ds` can be a Dataset or Group.
        """
        tname = "Primary Object" if ds.path == '/' else ds.name
        try:
            metadata_enc = ds.getncattr('metadata')
        except AttributeError:
            raise SsCdfReadError('Missing "metadata" netCDF attribute')
        try:
            metadata = json.loads(metadata_enc)
        except json.JSONDecodeError:
            raise SsCdfReadError(f'Unable to parse metadata as JSON for {tname}')

        try:
            validate_metadata(metadata)
        except SsCdfError:
            raise SsCdfReadError(f'Invalid metadata for {tname}')
        return metadata

    @staticmethod
    def _load_tensor(ds, name=None):
        metadata = Reader._parse_metadata(ds)
        fmt = metadata['format']
        arrays = {}
        for key in _format_keys[fmt]:
            arrays[key] = ds.variables[key][:].data
        if 'iso_value' not in metadata:
            arrays['values'] = ds.variables['values'][:].data
        return construct(metadata, arrays, name=name)

    def info(self, name=None):
        ds = self.ds
        if name is not None:
            ds = ds.groups[name]
        return self._parse_metadata(ds)

    def names(self):
        return list(self.ds.groups)

    def read(self, name=None):
        ds = self.ds
        if name is not None:
            ds = ds.groups[name]
        return self._load_tensor(ds, name=name)


class Writer:
    def __init__(self, file):
        self._fp = file
        if hasattr(file, 'close'):
            self.ds = nc.Dataset('.', 'w', memory=100)
        else:
            if '.' not in file:
                file = f'{file}.{_EXT}'
            self.ds = nc.Dataset(file, 'w')

        self._primary_written = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if self.ds:
            buffer = self.ds.close()
            if hasattr(self._fp, 'close'):
                self._fp.write(buffer)

    @staticmethod
    def _save_tensor(ds, obj, comment=None, format=None):
        dct = deconstruct(obj, format)

        # Store metadata
        metadata = dct["metadata"]
        if comment:
            metadata["comment"] = comment
        ds.setncattr("metadata", json.dumps(metadata))

        # Store arrays
        arrays = dct["arrays"]
        for name, array in arrays.items():
            dtype = _dtype_map[str(gb.dtypes.lookup_dtype(array.dtype).numba_type)]
            ds.createDimension(name, len(array))
            var = ds.createVariable(name, dtype, (name,))
            var[:] = array

    def write(self, x, *, name=None, comment=None, format=None):
        if name is None:
            if self._primary_written:
                raise SsCdfWriteError("Primary tensor has already been written. Additional tensors require a name.")
            self._save_tensor(self.ds, x, comment=comment)
            self._primary_written = True
        else:
            if name in self.ds.groups:
                raise SsCdfWriteError(f"A tensor named '{name}' already exists.")
            grp = self.ds.createGroup(name)
            self._save_tensor(grp, x, comment=comment, format=format)
