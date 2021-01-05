# -*- coding: utf-8 -*-
"""
rescaling.py
=========================
Signature rescaling methods. This implements the pre- and post- signature
rescaling methods along with generic scaling methods along feature
dimensions of 3D tensors.

Code for `rescale_path` and `rescale_signature` written by Patrick Kidger.
"""
import math
import numpy as np
from sktime.utils.check_imports import _check_soft_dependencies

_check_soft_dependencies("esig")
import esig  # noqa: E402


def _rescale_path(path, depth):
    """Rescales the input path by depth! ** (1 / depth), so that the last
    signature term should be roughly O(1).

    Parameters
    ----------
    path : torch.Tensor
        Input path of shape [N, L, C].
    depth : int
        Depth the signature will be computed to.

    Returns
    -------
    torch.Tensor:
        Tensor of the same shape as path, corresponding to the scaled path.
    """
    coeff = math.factorial(depth) ** (1 / depth)
    return coeff * path


def _rescale_signature(signature, channels, depth):
    """Rescales the output signature by multiplying the depth-d term by d!,
    with the aim that every term become ~O(1).

    Parameters
    ----------
    signature : torch.Tensor
        The signature of a path. Shape [N, Sig_dim].
    channels : int
        The number of channels of the path the signature was computed from.
    depth : int
        The depth the signature was computed to.

    Returns
    -------
    torch.Tensor:
        The signature with factorial depth scaling.
    """
    if (esig.siglength(channels, depth) - 1) != signature.shape[-1]:
        raise ValueError(
            "Given a sigtensor with {} channels, a path with {} channels and "
            "a depth of {}, which are not consistent.".format(
                signature.shape[-1], channels, depth
            )
        )

    end = 0
    term_length = 1
    val = 1
    terms = []
    for d in range(1, depth + 1):
        start = end
        term_length *= channels
        end = start + term_length

        val *= d

        terms.append(signature[..., start:end] * val)

    return np.concatenate(terms, axis=-1)
