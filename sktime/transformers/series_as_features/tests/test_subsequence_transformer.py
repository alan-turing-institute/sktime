import numpy as np
import pandas as pd
import pytest
import math

from sktime.exceptions import NotFittedError
from sktime.transformers.series_as_features.subsequence_transformer \
    import SubsequenceTransformer
from sktime.utils.data_container import tabularize
from sktime.utils._testing import generate_df_from_array

# Check that exception is raised for bad subsequence length.
# input types - string, float, negative int, negative float and empty dict
# correct input is meant to be a positive integer of 1 or more.
@pytest.mark.parametrize("bad_subsequence_length", ['str', 1.2, -1.2, -1, {}])
def test_bad_input_args(bad_subsequence_length):
    X = generate_df_from_array(np.ones(10), n_rows=10, n_cols=1)

    if not isinstance(bad_subsequence_length, int):
        with pytest.raises(TypeError):
            SubsequenceTransformer(subsequence_length=bad_subsequence_length).fit(X).transform(X)
    else:
        with pytest.raises(ValueError):
            SubsequenceTransformer(subsequence_length=bad_subsequence_length).fit(X).transform(X)
            
# Check that NotFittedError is thrown if someone attempts to
# transform before calling fit
def test_early_trans_fail():
    X = generate_df_from_array(np.ones(10), n_rows=1, n_cols=1)
    st = SubsequenceTransformer()

    with pytest.raises(NotFittedError):
        st.transform(X)
     
# Check the transformer has changed the data correctly.   
def test_output_of_transformer():
    X = generate_df_from_array(np.array([1,2,3,4,5,6]), n_rows=1, n_cols=1)
    
    st = SubsequenceTransformer(subsequence_length=1).fit(X)
    res = st.transform(X)
    orig = convert_list_to_dataframe([[1.0],[2.0],[3.0],[4.0],[5.0],[6.0]])
    assert check_if_dataframes_are_equal(res,orig)

    st = SubsequenceTransformer(subsequence_length=5).fit(X)
    res = st.transform(X)
    orig = convert_list_to_dataframe([[1.0,1.0,1.0,2.0,3.0],[1.0,1.0,2.0,3.0,4.0],[1.0,2.0,3.0,4.0,5.0],[2.0,3.0,4.0,5.0,6.0],[3.0,4.0,5.0,6.0,6.0],[4.0,5.0,6.0,6.0,6.0]])
    assert check_if_dataframes_are_equal(res,orig)
    
    st = SubsequenceTransformer(subsequence_length=10).fit(X)
    res = st.transform(X)
    orig = convert_list_to_dataframe([[1.0,1.0,1.0,1.0,1.0,1.0,2.0,3.0,4.0,5.0],[1.0,1.0,1.0,1.0,1.0,2.0,3.0,4.0,5.0,6.0],[1.0,1.0,1.0,1.0,2.0,3.0,4.0,5.0,6.0,6.0],[1.0,1.0,1.0,2.0,3.0,4.0,5.0,6.0,6.0,6.0],[1.0,1.0,2.0,3.0,4.0,5.0,6.0,6.0,6.0,6.0],[1.0,2.0,3.0,4.0,5.0,6.0,6.0,6.0,6.0,6.0]])
    assert check_if_dataframes_are_equal(res,orig)
    
@pytest.mark.parametrize("time_series_length,subsequence_length",[(5,1),(10,5),(15,9),(20,13),(25,19)])
def test_output_dimensions(time_series_length,subsequence_length):
    X = generate_df_from_array(np.ones(time_series_length), n_rows=10, n_cols=1)
    
    st = SubsequenceTransformer(subsequence_length=subsequence_length).fit(X)
    res = st.transform(X)
    
    # get the dimension of the generated dataframe.
    corr_time_series_length = res.iloc[0, 0].shape[0]
    num_rows = res.shape[0]
    num_cols = res.shape[1]
    
    assert corr_time_series_length == subsequence_length
    assert num_rows == 10
    assert num_cols == time_series_length
    
# Test that subsequence transformer fails when a multivariate ts is fed into it.
def test_fails_if_multivariate():
    X = generate_df_from_array(np.ones(5), n_rows=10, n_cols=5)

    with pytest.raises(ValueError):
        s = SubsequenceTransformer().fit(X).transform(X)


def convert_list_to_dataframe(list_to_convert):
    # Convert this into a panda's data frame
    df = pd.DataFrame()
    for i in range(len(list_to_convert)):
        inst = list_to_convert[i]
        data = []
        data.append(pd.Series(inst))
        df[i] = data
        
    return df
    
"""
for some reason, this is how you check that two dataframes are equal.
"""
def check_if_dataframes_are_equal(df1,df2):
    from pandas.testing import assert_frame_equal
    
    try:
        assert_frame_equal(df1, df2)
        return True
    except AssertionError as e: 
        return False