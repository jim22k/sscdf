import numpy as np
import graphblas as gb
from .exceptions import SsCdfVersionError, SsCdfValidationError

# Format mapping
_gbfmt_to_fmt = {
    "csr": "CSR",
    "csc": "CSC",
    "hypercsr": "DCSR",
    "hypercsc": "DCSC",
    "bitmapr": "CSR",
    "bitmapc": "CSC",
    "fullr": "CSR",
    "fullc": "CSC",
    "sparse": "VEC",
    "bitmap": "VEC",
    "full": "VEC",
}
_fmt_to_gbfmt = {
    "CSR": "csr",
    "CSC": "csc",
    "DCSR": "hypercsr",
    "DCSC": "hypercsc",
    "COOR": "coor",
    "COOC": "cooc",
    "COO": "coo",
    "VEC": "sparse",
}

# Format keys
_format_keys = {
    'CSR': {'pointers_0': 'indptr', 'indices_1': 'col_indices'},
    'CSC': {'pointers_0': 'indptr', 'indices_1': 'row_indices'},
    'DCSR': {'indices_0': 'rows', 'pointers_0': 'indptr', 'indices_1': 'col_indices'},
    'DCSC': {'indices_0': 'cols', 'pointers_0': 'indptr', 'indices_1': 'row_indices'},
    'COOR': {'indices_0': 'rows', 'indices_1': 'cols'},
    'COOC': {'indices_0': 'cols', 'indices_1': 'rows'},
    'VEC': {'indices_0': 'indices'},
}
# Aliases
_format_keys['COO'] = _format_keys['COOR']
# Build reverse lookup
_gbformat_keys = {
    _fmt_to_gbfmt[fmt]: {v: k for k, v in d.items()} for fmt, d in _format_keys.items()
}


def validate_metadata(metadata):
    if 'version' not in metadata:
        raise SsCdfVersionError(f'Missing version attribute in metadata')
    version = tuple(int(x) for x in metadata['version'].split('.'))
    if version > (1, 0):
        raise SsCdfVersionError(f'Incompatible version number (verstr). Reader only handles version <= 1.0')

    for attr in ('format', 'shape', 'data_types'):
        if attr not in metadata:
            raise SsCdfValidationError(f'Missing attribute: {attr}')
    format = metadata['format'].upper()
    if format not in _format_keys:
        raise SsCdfValidationError(f'Invalid format: {format}, must be one of {list(_format_keys.keys())}')
    shape = metadata['shape']
    if not isinstance(shape, list):
        raise SsCdfValidationError(f'Expected shape to be a list, found {type(shape)}')
    if not all(type(x) == int for x in shape):
        raise SsCdfValidationError('Shape must be a list of ints')
    datatypes = metadata['data_types']
    if not isinstance(datatypes, dict):
        raise SsCdfValidationError(f'Expected data_types to be a dict, found {type(datatypes)}')
    for name in _format_keys[format]:
        if name not in datatypes:
            raise SsCdfValidationError(f'data_types is missing an entry for {name}')


def construct(metadata, arrays, name=None):
    """
    Constructs a GraphBLAS object from its separate pieces.

    :param metadata: dict
    :param arrays: dict of numpy arrays
    :param name: Optional name to give the created object
    :return: GraphBLAS Matrix or Vector
    """
    validate_metadata(metadata)

    # Split shape into components
    shape = metadata["shape"]
    if len(shape) == 2:
        exp = {"nrows": shape[0], "ncols": shape[1], "sorted_rows": True, "sorted_cols": True}
        import_func = gb.Matrix.ss.import_any
    elif len(shape) == 1:
        exp = {"size": shape[0], "sorted_index": True}
        import_func = gb.Vector.ss.import_any
    else:
        raise ValueError(f"Invalid shape: {shape}")

    # Add expected elements based on format
    fmt = metadata["format"].upper()
    exp["format"] = _fmt_to_gbfmt[fmt]
    for key, exp_name in _format_keys[fmt].items():
        exp[exp_name] = arrays[key]
    exp["dtype"] = metadata["data_types"]["values"]

    # Add values
    if "iso_value" in metadata:
        exp["is_iso"] = True
        exp["values"] = np.array([metadata["iso_value"]],
                                 dtype=gb.dtypes.lookup_dtype(exp["dtype"]).np_type)
    else:
        exp["values"] = arrays["values"]

    # Construct graphblas object
    return import_func(**exp, name=name)


def deconstruct(obj, format=None):
    """
    Deconstructs a GraphBLAS object into its separate pieces.

    :param obj: GraphBLAS Matrix or Vector
    :param format: GraphBLAS format, if not specified uses the existing storage format
    :return: dict with keys -- metadata, arrays
    """
    # Determine format
    objtype = gb.utils.output_type(obj)
    if objtype not in (gb.Vector, gb.Matrix):
        raise TypeError(f"Invalid graphblas object: {objtype}, expected Matrix or Vector")
    gbfmt = obj.ss.format if format is None else format
    fmt = _gbfmt_to_fmt[gbfmt]

    # Export using normalized gbfmt
    exp = obj.ss.export(_fmt_to_gbfmt[fmt], sort=True)

    # Build output for structure
    fmt_keys = _format_keys[fmt]
    metadata = {
        "version": "1.0",
        "format": fmt,
        "shape": list(obj.shape),
        "data_types": {key: "uint64" for key in fmt_keys},
    }
    arrays = {key: exp[exp_name] for key, exp_name in fmt_keys.items()}
    # Build output for values
    values = exp["values"]
    metadata["data_types"]["values"] = str(gb.dtypes.lookup_dtype(values.dtype).numba_type)
    if obj.ss.is_iso:
        metadata["iso_value"] = values[0].item()
    else:
        arrays["values"] = values

    return {"metadata": metadata, "arrays": arrays}
