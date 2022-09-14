import pytest
import graphblas as gb
from sscdf.highlevel import construct, deconstruct, validate_metadata
from sscdf.exceptions import SsCdfVersionError, SsCdfValidationError


def test_matrix_csr():
    g = gb.Matrix.from_values([0, 3, 4, 4], [1, 4, 2, 3], [1.0, 2.0, -3., 4.0], nrows=6, ncols=6)
    result = deconstruct(g, 'csr')
    validate_metadata(result['metadata'])
    assert result['metadata']['format'] == 'CSR'
    assert result['metadata']['shape'] == [6, 6]
    assert set(result['metadata']['data_types'].keys()) == {'pointers_0', 'indices_1', 'values'}
    assert result['metadata']['data_types']['values'] == 'float64'
    assert 'iso_value' not in result['metadata']
    # Reconstruct
    g2 = construct(**result)
    assert g2.isequal(g)


def test_matrix_dcsc():
    g = gb.Matrix.from_values([0, 3, 4, 4], [1, 4, 2, 3], [1.0, 2.0, -3., 4.0], nrows=6, ncols=6)
    result = deconstruct(g, 'hypercsc')
    validate_metadata(result['metadata'])
    assert result['metadata']['format'] == 'DCSC'
    assert result['metadata']['shape'] == [6, 6]
    assert set(result['metadata']['data_types'].keys()) == {'indices_0', 'pointers_0', 'indices_1', 'values'}
    assert result['metadata']['data_types']['values'] == 'float64'
    assert 'iso_value' not in result['metadata']
    # Reconstruct
    g2 = construct(**result)
    assert g2.isequal(g)


def test_matrix_iso():
    g = gb.Matrix.from_values([0, 3, 4, 4], [1, 4, 2, 3], [1.0, 1.0, 1.0, 1.0], nrows=6, ncols=6)
    result = deconstruct(g, 'csr')
    validate_metadata(result['metadata'])
    assert result['metadata']['format'] == 'CSR'
    assert result['metadata']['shape'] == [6, 6]
    assert set(result['metadata']['data_types'].keys()) == {'pointers_0', 'indices_1', 'values'}
    assert result['metadata']['data_types']['values'] == 'float64'
    assert result['metadata']['iso_value'] == 1.0
    assert 'values' not in result['arrays']
    # Reconstruct
    g2 = construct(**result)
    assert g2.isequal(g)


def test_vector():
    v = gb.Vector.from_values([0, 2, 4], [1, 2, -3], size=6, dtype='int16')
    result = deconstruct(v, 'bitmap')  # will auto-convert to VEC
    validate_metadata(result['metadata'])
    assert result['metadata']['format'] == 'VEC'
    assert result['metadata']['shape'] == [6]
    assert set(result['metadata']['data_types'].keys()) == {'indices_0', 'values'}
    assert result['metadata']['data_types']['values'] == 'int16'
    assert 'iso_value' not in result['metadata']
    # Reconstruct
    v2 = construct(**result)
    assert v2.isequal(v)


def test_invalid_metadata():
    v = gb.Vector.from_values([0, 2, 4], [1, 2, -3], size=6, dtype='int16')
    result = deconstruct(v)
    metadata = result['metadata']
    metadata['comment'] = "Some random comment"
    validate_metadata(metadata)
    # Wrong version
    with pytest.raises(SsCdfVersionError, match='version'):
        validate_metadata({**metadata, 'version': '2.0'})
    # Missing data_types
    with pytest.raises(SsCdfValidationError, match='data_types'):
        validate_metadata({'version': '1.0', 'format': 'csr', 'shape': [3, 3]})
    # Invalid format
    with pytest.raises(SsCdfValidationError, match='format'):
        validate_metadata({**metadata, 'format': 'invalid'})
    # Data_types don't match format
    with pytest.raises(SsCdfValidationError, match="missing an entry"):
        validate_metadata({**metadata, 'data_types': {'values': 'int16'}})
    # Invalid shape
    with pytest.raises(SsCdfValidationError, match="Expected shape to be a list"):
        validate_metadata({**metadata, 'shape': (3, 4)})
    with pytest.raises(SsCdfValidationError, match="list of ints"):
        validate_metadata({**metadata, 'shape': [3.0, 4.0]})
